"""
High-level service for working with tilesets.

Provides orchestration and public API for loading, managing and resolving
Cataclysm: DDA tilesets including mods and priority overrides.
Responsibilities:
    * Discover base tilesets under <game>/gfx
    * Discover mod tilesets under <game>/data/mods
    * Build sheet registry and global sprite indices
    * Build tile registry with mod override support
    * Provide lookup helpers returning fully materialized `TileObject`.
"""

import orjson
import logging
from pathlib import Path
from typing import cast, Any, Optional, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from dataclasses import fields
from importlib import resources

from .models import TileSource, Tile, TileObject, WeightedSprite, SheetInfo, Tileset
from .managers import TilesetManager, SheetManager, TilesManager, Sheet, FallbackSheet

if TYPE_CHECKING:
    from ..settings import AppSettings


class TilesetService:
    """Facade for tileset operations.

    Instantiate with path to a CDDA game directory. Immediately triggers
    scanning and registration of base tilesets and mods.
    """

    def __init__(self, game_path: str, settings: Optional["AppSettings"] = None):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.game_path = Path(game_path)
        self.settings = settings

        self.tilesets = TilesetManager()
        self.sheets = SheetManager()
        self.tiles = TilesManager()
        self._init_tilesets()

    def _init_tilesets(self):
        """Initialize tileset loading (base + mods)."""
        # Сначала загружаем базовые тайлсеты
        self._load_base_tilesets()
        # Затем загружаем моды
        self._load_mod_tilesets()

    @staticmethod
    def _is_valid_tileset_dir(tileset_dir: Path) -> bool:
        """Check if directory contains tileset files.

        A valid tileset directory must contain at least one of:
        - tileset.txt
        - tile_config.json

        Args:
            tileset_dir: Path to potential tileset directory

        Returns:
            True if directory contains tileset files, False otherwise
        """
        return (tileset_dir / "tileset.txt").exists() or (
            tileset_dir / "tile_config.json"
        ).exists()

    def _load_base_tilesets(self):
        """Load core tilesets from the `gfx` directory in parallel."""
        gfx_path = self.game_path / "gfx"
        if not gfx_path.exists() or not gfx_path.is_dir():
            raise RuntimeError(f"Tilesets path is invalid: {gfx_path}")

        # Filter only valid tileset directories
        all_dirs = [d for d in gfx_path.iterdir() if d.is_dir()]
        tileset_dirs = [d for d in all_dirs if self._is_valid_tileset_dir(d)]

        skipped = len(all_dirs) - len(tileset_dirs)
        if skipped > 0:
            self.logger.debug(f"Skipped {skipped} non-tileset directories in gfx")

        self.logger.debug(f"total {len(tileset_dirs)} base tileset dirs found")

        # Use ThreadPoolExecutor for parallel loading
        # max_workers=4 is a good balance for IO-bound operations
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all tileset loading tasks
            future_to_dir = {
                executor.submit(self._process_tileset_dir, ts_dir, "dda"): ts_dir
                for ts_dir in tileset_dirs
            }

            # Process completed tasks and update GUI
            for future in as_completed(future_to_dir):
                ts_dir = future_to_dir[future]
                try:
                    future.result()  # Get result or raise exception if any
                    self.logger.info(f"  base tileset: {ts_dir.name}")
                    # Обеспечиваем наличие default fallback для каждого тайлсета
                    self._ensure_default_fallback(ts_dir.name)
                    # Try to process Qt events if available
                    try:
                        from PySide6.QtWidgets import QApplication

                        app = QApplication.instance()
                        if app:
                            app.processEvents()
                    except ImportError:
                        pass
                except Exception as e:
                    self.logger.error(f"Failed to load tileset {ts_dir.name}: {e}")

    def _load_mod_tilesets(self):
        """Load `mod_tileset` JSON objects from the `data/mods` tree."""
        mods_path = self.game_path / "data" / "mods"
        if not mods_path.exists() or not mods_path.is_dir():
            self.logger.warning(f"Mods path not found: {mods_path}")
            return

        mod_dirs = [d for d in mods_path.iterdir() if d.is_dir()]
        self.logger.debug(f"total {len(mod_dirs)} mod dirs found")

        for _, mod_dir in enumerate(mod_dirs):
            self.logger.debug(f"processing mod: {mod_dir.name}")
            self._process_mod_dir(mod_dir)
            # Try to process Qt events if available
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                if app:
                    app.processEvents()
            except ImportError:
                pass

    def _process_tileset_dir(self, ts_dir: Path, mod_id: str):
        """Process a base tileset directory and register all sheets.

        Two-phase loading for maximum performance:
        1. Load all images in parallel (IO-bound, benefits from threading)
        2. Register tiles and sheets sequentially (CPU-bound, avoids locking overhead)

        IMPORTANT: Preserves original sheet order for correct global sprite indexing.
        """
        tileset_info = self.tilesets.add_tileset(str(ts_dir))

        # Phase 1: Load all images in parallel, preserving order
        loaded_sheets_with_index: list[tuple[int, Sheet, str, str]] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit with index to preserve order
            future_to_index = {
                executor.submit(
                    self._load_sheet_image, sheet_info, ts_dir, mod_id, tileset_info
                ): idx
                for idx, sheet_info in enumerate(tileset_info.objects_source)
            }

            # Collect all loaded sheets with their original indices
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    sheet = future.result()
                    if sheet:
                        loaded_sheets_with_index.append(
                            (idx, sheet, ts_dir.name, mod_id)
                        )
                except Exception as e:
                    self.logger.error(f"Error loading sheet in {ts_dir.name}: {e}")

        # Sort by original index to preserve order
        loaded_sheets_with_index.sort(key=lambda x: x[0])

        # Phase 2: Register tiles and add sheets sequentially in correct order
        for idx, sheet, tileset_name, mod_id in loaded_sheets_with_index:
            if not isinstance(sheet, FallbackSheet):
                self._register_tiles_from_sheet(sheet, tileset_name, mod_id)
            self.sheets.add_sheet(tileset_name, sheet)

        # Phase 3: Finalize tileset - rebuild global sprite index once
        self.sheets.finalize_tileset(ts_dir.name)

    def _process_mod_dir(self, mod_dir: Path):
        """Process a mod directory; scan JSON files for `mod_tileset` entries."""
        # Track unique messages to avoid duplicate logging
        not_found_tilesets: set[str] = set()
        loaded_mappings: set[tuple[str, str]] = set()  # (requested_name, actual_folder)

        # Ищем все JSON файлы в моде
        json_files = list(mod_dir.rglob("*.json"))
        for json_file in json_files:
            try:
                with json_file.open("rb") as f:
                    data = orjson.loads(f.read())

                objects: list[Any] = (
                    cast(list[Any], data) if isinstance(data, list) else [data]
                )
                for obj in objects:
                    if isinstance(obj, dict):
                        obj_dict = cast(dict[str, Any], obj)
                        if obj_dict.get("type") == "mod_tileset":
                            self._process_mod_tileset(
                                obj_dict, mod_dir, not_found_tilesets, loaded_mappings
                            )

            except (orjson.JSONDecodeError, Exception) as e:
                self.logger.warning(f"Error processing mod file {json_file}: {e}")

        # Log unique messages once per mod
        mod_id = mod_dir.name
        for tileset_name in sorted(not_found_tilesets):
            self.logger.info(
                f"   mod tileset: {mod_id} cant find '{tileset_name}' tileset to extend"
            )
        for requested_name, actual_folder in sorted(loaded_mappings):
            self.logger.info(
                f"   mod tileset: {mod_id} extends {actual_folder} (requested: {requested_name})"
            )

    def _process_mod_tileset(
        self,
        mod_tileset_obj: dict[str, Any],
        mod_dir: Path,
        not_found_tilesets: set[str],
        loaded_mappings: set[tuple[str, str]],
    ):
        """Process a single `mod_tileset` JSON object.

        compatibility: list of base tileset folder names this mod augments.
        tiles-new: list of sheet descriptors identical in shape to base ones.
        """
        compatibility = mod_tileset_obj.get("compatibility", [])
        tiles_new = mod_tileset_obj.get("tiles-new", [])
        mod_id = mod_dir.name  # используем имя папки мода как mod_id

        # Resolve all compatible tilesets once (cache lookup results)
        resolved_tilesets: list[tuple[str, Tileset]] = []
        for tileset_name in compatibility:
            # Try direct folder name first, then check short name
            tileset_info = self.tilesets.get_tileset(tileset_name)
            if not tileset_info:
                # Not found by folder_name, try by short_name
                tileset_info = self.tilesets.get_tileset_by_short_name(tileset_name)

            if tileset_info:
                resolved_tilesets.append((tileset_name, tileset_info))
                # Track name mappings for later logging
                if tileset_name != tileset_info.folder_name:
                    loaded_mappings.add((tileset_name, tileset_info.folder_name))
            else:
                # Track not found tilesets for later logging
                not_found_tilesets.add(tileset_name)

        # Process each sheet for all resolved tilesets
        for sheet_info in tiles_new:
            for tileset_name, tileset_info in resolved_tilesets:
                self._process_sheet_info(
                    sheet_info, mod_dir, tileset_info.folder_name, mod_id, tileset_info
                )

    def _build_sheet_name(
        self,
        sheet_file: str,
        sheet_info: dict[str, Any],
        tileset_info: Tileset,
        is_fallback: bool,
    ) -> str:
        """Generate unique sheet name based on file and parameters.

        Args:
            sheet_file: Base filename (e.g., "tiles.png")
            sheet_info: JSON object with sprite dimensions and offsets
            tileset_info: Tileset metadata for defaults
            is_fallback: Whether this is a fallback sheet

        Returns:
            Unique sheet identifier string
        """
        if is_fallback:
            return sheet_file

        offset_x = sheet_info.get("sprite_offset_x", 0)
        offset_y = sheet_info.get("sprite_offset_y", 0)
        width = sheet_info.get("sprite_width", tileset_info.grid_width)
        height = sheet_info.get("sprite_height", tileset_info.grid_height)
        return f"{sheet_file}_{width}x{height}_{offset_x}_{offset_y}"

    def _create_sheet_from_json(
        self,
        sheet_class: type[Sheet],
        sheet_name: str,
        sheet_file: str,
        sheet_info: dict[str, Any],
        image_path: Path,
        tileset_info: Tileset,
        mod_id: str,
    ) -> Sheet:
        """Create Sheet or FallbackSheet instance from JSON configuration.

        Args:
            sheet_class: Sheet or FallbackSheet class
            sheet_name: Unique sheet identifier
            sheet_file: Original filename
            sheet_info: JSON configuration dict
            image_path: Path to sprite sheet image
            tileset_info: Tileset metadata for defaults
            mod_id: Mod identifier

        Returns:
            Instantiated Sheet/FallbackSheet with loaded sprites
        """
        sheet_data: dict[str, Any] = {
            "name": str(sheet_name),
            "file": str(sheet_file),
            "image": Image.open(image_path),
            "sprite_width": int(
                sheet_info.get("sprite_width", tileset_info.grid_width)
            ),
            "sprite_height": int(
                sheet_info.get("sprite_height", tileset_info.grid_height)
            ),
            "mod_id": str(mod_id),
            "sprite_offset_x": int(sheet_info.get("sprite_offset_x", 0)),
            "sprite_offset_y": int(sheet_info.get("sprite_offset_y", 0)),
            "sprite_offset_x_retracted": int(
                sheet_info.get("sprite_offset_x_retracted", 0)
            ),
            "sprite_offset_y_retracted": int(
                sheet_info.get("sprite_offset_y_retracted", 0)
            ),
            "pixelscale": int(sheet_info.get("pixelscale", tileset_info.pixelscale)),
            "tiles_source": list(sheet_info.get("tiles", [])),
        }
        return sheet_class.from_dict(sheet_data)

    def _register_tile(
        self,
        tileset_name: str,
        tile_id: str,
        source_obj: dict[str, Any],
        sheet_id: str,
        mod_id: str,
    ) -> None:
        """Register a single tile from sheet tile source.

        Args:
            tileset_name: Target tileset name
            tile_id: Tile identifier
            source_obj: JSON tile source dict
            sheet_id: Parent sheet identifier
            mod_id: Mod identifier
        """
        tile_source_obj = source_obj.copy()
        tile_source_obj["id"] = tile_id
        allowed_keys = {f.name for f in fields(TileSource)}
        filtered = {k: v for k, v in tile_source_obj.items() if k in allowed_keys}
        tile_source = TileSource.from_dict(filtered)
        tile_obj = Tile(
            tileid=str(tile_id), source=tile_source, sheet_id=sheet_id, mod_id=mod_id
        )
        self.tiles.add_tile(tileset_name, tile_obj)

    def _register_tiles_from_sheet(
        self, sheet: Sheet, tileset_name: str, mod_id: str
    ) -> None:
        """Process and register all tiles from a sheet's tile sources.

        Args:
            sheet: Sheet instance with tiles_source
            tileset_name: Target tileset name
            mod_id: Mod identifier
        """
        for source_obj in sheet.tiles_source:
            source_obj_id = source_obj["id"]
            if isinstance(source_obj_id, list):
                # Handle multiple IDs in one tile definition
                for single_id in cast(list[str], source_obj_id):
                    self._register_tile(
                        tileset_name, single_id, source_obj, sheet.sheet_id, mod_id
                    )
            else:
                # Single ID
                self._register_tile(
                    tileset_name, source_obj_id, source_obj, sheet.sheet_id, mod_id
                )

    def _load_sheet_image(
        self,
        sheet_info: dict[str, Any],
        base_dir: Path,
        mod_id: str,
        tileset_info: Tileset,
    ) -> Sheet | None:
        """Load sheet image from disk (parallelizable, IO-bound).

        Returns Sheet object with loaded image, or None if failed.
        This method only does Image.open and Sheet creation, no registration.
        """
        sheet_file = sheet_info.get("file")
        if not sheet_file:
            return None

        sheet_class = FallbackSheet if sheet_file == "fallback.png" else Sheet
        is_fallback = sheet_class is FallbackSheet

        sheet_name = self._build_sheet_name(
            sheet_file, sheet_info, tileset_info, is_fallback
        )

        try:
            image_path = base_dir / sheet_file
            if not image_path.exists():
                self.logger.warning(f"Image file not found: {image_path}")
                return None

            current_sheet = self._create_sheet_from_json(
                sheet_class,
                sheet_name,
                sheet_file,
                sheet_info,
                image_path,
                tileset_info,
                mod_id,
            )

            return current_sheet

        except Exception as e:
            self.logger.error(
                f"Error loading sheet {sheet_file} from mod {mod_id}: {e}"
            )
            return None

    def _process_sheet_info(
        self,
        sheet_info: dict[str, Any],
        base_dir: Path,
        tileset_name: str,
        mod_id: str,
        tileset_info: Tileset,
    ):
        """Materialize a sheet definition into a `Sheet` or `FallbackSheet`.

        sheet_info: Raw JSON object containing fields like file, sprite_width
        base_dir:   Path where the image file is located.
        tileset_name: Name of the tileset being extended.
        mod_id:     Identifier of the contributing mod ("dda" for base).
        tileset_info: Object offering grid defaults (width/height).
        """
        sheet_file = sheet_info.get("file")
        if not sheet_file:
            return

        sheet_class = FallbackSheet if sheet_file == "fallback.png" else Sheet
        is_fallback = sheet_class is FallbackSheet

        sheet_name = self._build_sheet_name(
            sheet_file, sheet_info, tileset_info, is_fallback
        )

        try:
            image_path = base_dir / sheet_file
            if not image_path.exists():
                self.logger.warning(f"Image file not found: {image_path}")
                return

            current_sheet = self._create_sheet_from_json(
                sheet_class,
                sheet_name,
                sheet_file,
                sheet_info,
                image_path,
                tileset_info,
                mod_id,
            )

            if not is_fallback:
                self._register_tiles_from_sheet(current_sheet, tileset_name, mod_id)

            self.sheets.add_sheet(tileset_name, current_sheet)

        except Exception as e:
            self.logger.error(
                f"Error processing sheet {sheet_file} from mod {mod_id}: {e}"
            )

    def _collect_all_sprite_indices(self, ts: TileSource) -> list[int]:
        """Collect all sprite indices referenced by a TileSource tree.

        Traverses fg, bg and nested additional_tiles, unfolding WeightedSprite
        collections. Returns a flat list of integer indices.
        """
        result: list[int] = []

        def extract(
            value: int | list[int] | list[WeightedSprite] | WeightedSprite | None,
        ) -> None:
            if value is None:
                return
            if isinstance(value, int):
                result.append(value)
            elif isinstance(value, list):
                if not value:
                    return
                first = value[0]
                if isinstance(first, int):
                    result.extend(cast(list[int], value))
                else:
                    for ws in cast(list[WeightedSprite], value):
                        if isinstance(ws.sprite, int):
                            result.append(ws.sprite)
                        else:
                            result.extend(ws.sprite)
            else:
                ws = value
                if isinstance(ws.sprite, int):
                    result.append(ws.sprite)
                else:
                    result.extend(ws.sprite)

        extract(ts.fg)
        extract(ts.bg)

        if ts.additional_tiles:
            for subtile in ts.additional_tiles:
                extract(subtile.fg)
                extract(subtile.bg)
                if subtile.additional_tiles:
                    # recurse into deeper nested tiles
                    result.extend(self._collect_all_sprite_indices(subtile))

        return result

    def _get_object_and_sprites(
        self,
        tileset_name: str,
        object_id: str,
        fallback_color: str,
        fallback_symbol: str,
        season: str = "spring",
    ) -> TileObject:
        """Return a `TileObject` either for the given object id or fallback.

        If the object id is unknown we return a fallback TileObject using
        the ASCII glyph identified by (fallback_color, fallback_symbol).
        """
        # Поиск по object_id с поддержкой сезонов
        tile_obj = self.tiles.get_tile_with_season(tileset_name, object_id, season)
        fb_sprite = self.sheets.get_ascii(
            tileset_name, "fallback.png", fallback_color, fallback_symbol
        )

        if tile_obj:
            sprites_dict: dict[int, Image.Image] = {}
            for sprite_index in self._collect_all_sprite_indices(tile_obj.source):
                # Различаем core и mod спрайты
                if tile_obj.mod_id == "dda":
                    # Core спрайт - используем глобальный индекс
                    sprite_image = self.sheets.get_sprite_by_global_index(
                        tileset_name, sprite_index
                    )
                else:
                    # Mod спрайт - используем локальный индекс в листе мода
                    sprite_image = self.sheets.get_sprite_by_mod_index(
                        tileset_name, tile_obj.mod_id, sprite_index, tile_obj.sheet_id
                    )
                if sprite_image:
                    sprites_dict[sprite_index] = sprite_image
            return TileObject(
                source=tile_obj.source,
                style=self.sheets.get_sheet_info(tileset_name, tile_obj.sheet_id)
                or SheetInfo(),
                sprites=sprites_dict,
            )
        else:
            # Ensure fb_sprite is not None; if it is, create a blank image as fallback
            if fb_sprite is None:
                fb_sprite = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            return TileObject(
                source=TileSource(id=object_id, fg=-1),
                style=self.sheets.get_sheet_info(tileset_name, "fallback.png")
                or SheetInfo(),
                sprites={-1: fb_sprite},
            )

    def get_available_mods(self, tileset_name: str) -> list[str]:
        """Return list of mods that contribute either sheets or tiles."""
        sheet_mods = self.sheets.get_available_mods(tileset_name)
        tile_mods = self.tiles.get_available_mods(tileset_name)
        return list(set(sheet_mods + tile_mods))

    def get_mod_statistics(self, tileset_name: str) -> dict[str, dict[str, int]]:
        """Return per-mod statistics: number of sheets and tiles."""
        result: dict[str, dict[str, int]] = {}
        for mod_id in self.get_available_mods(tileset_name):
            result[mod_id] = {
                "sheets": len(self.sheets.get_sheets_from_mod(tileset_name, mod_id)),
                "tiles": len(
                    self.tiles.tilesets_by_mod.get(tileset_name, {}).get(mod_id, {})
                ),
            }
        return result

    def get_object_and_sprites_from_mod(
        self, tileset_name: str, mod_id: str, object_id: str
    ) -> TileObject | None:
        """Return object/sprites strictly from a specific mod or None.

        Returns None if object is not found in the specified mod.
        """
        tile_obj = self.tiles.get_tile_from_mod(tileset_name, mod_id, object_id)
        if tile_obj:
            sprites_dict: dict[int, Image.Image] = {}
            for sprite_index in self._collect_all_sprite_indices(tile_obj.source):
                sprite_image = self.sheets.get_sprite_by_global_index(
                    tileset_name, sprite_index
                )
                if sprite_image:
                    sprites_dict[sprite_index] = sprite_image
            return TileObject(
                source=tile_obj.source,
                style=self.sheets.get_sheet_info(tileset_name, tile_obj.sheet_id)
                or SheetInfo(),
                sprites=sprites_dict,
            )
        return None

    def get_object_and_sprites_with_priority(
        self,
        tileset_name: str,
        object_id: str,
        fallback_color: str,
        fallback_symbol: str,
        season: str = "spring",
    ) -> TileObject:
        """Return object/sprites honoring preferred mod order from settings.

        Uses active_mods from settings to determine mod priority.
        Falls back to base tile or ASCII sprite if not found.

        Args:
            tileset_name: Name of the tileset to use
            object_id: ID of the object to find tile for
            fallback_color: Color for ASCII fallback
            fallback_symbol: Symbol for ASCII fallback
            season: Season variant to use (default: "spring")
        """
        # Get preferred_mods from settings
        preferred_mods = self.settings.active_mods if self.settings else None

        tile_obj = self.tiles.get_tile_with_season_and_priority(
            tileset_name, object_id, season, preferred_mods
        )
        fb_sprite = self.sheets.get_ascii(
            tileset_name, "fallback.png", fallback_color, fallback_symbol
        )

        if tile_obj:
            sprites_dict: dict[int, Image.Image] = {}
            for sprite_index in self._collect_all_sprite_indices(tile_obj.source):
                # Различаем core и mod спрайты
                if tile_obj.mod_id == "dda":
                    # Core спрайт - используем глобальный индекс
                    sprite_image = self.sheets.get_sprite_by_global_index(
                        tileset_name, sprite_index
                    )
                else:
                    # Mod спрайт - используем локальный индекс в листе мода
                    sprite_image = self.sheets.get_sprite_by_mod_index(
                        tileset_name, tile_obj.mod_id, sprite_index, tile_obj.sheet_id
                    )
                if sprite_image:
                    sprites_dict[sprite_index] = sprite_image
            return TileObject(
                source=tile_obj.source,
                style=self.sheets.get_sheet_info(tileset_name, tile_obj.sheet_id)
                or SheetInfo(),
                sprites=sprites_dict,
            )
        else:
            if fb_sprite is None:
                fb_sprite = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            return TileObject(
                source=TileSource(id=object_id, fg=-1),
                style=self.sheets.get_sheet_info(tileset_name, "fallback.png")
                or SheetInfo(),
                sprites={-1: fb_sprite},
            )

    def _ensure_default_fallback(self, tileset_name: str):
        """Inject a default fallback sheet when tileset lacks `fallback.png`."""
        # Проверяем, есть ли уже fallback.png лист
        if self.sheets.get_sheet_info(tileset_name, "fallback.png"):
            return  # Уже есть собственный fallback

        # Получаем путь к default_fallback.png через importlib.resources
        try:
            with resources.path(
                "cdda_maped.resources", "default_fallback.png"
            ) as default_fallback_path:
                if not default_fallback_path.exists():
                    self.logger.warning(
                        f"Default fallback file not found: {default_fallback_path}"
                    )
                    return

                # Загружаем и создаем лист внутри with блока
                self._create_default_fallback_sheet(tileset_name, default_fallback_path)
        except (FileNotFoundError, ImportError) as e:
            self.logger.warning(f"Could not load default fallback resource: {e}")
            return

    def _create_default_fallback_sheet(
        self, tileset_name: str, default_fallback_path: Path
    ):
        """Create and register a default fallback sheet from a resource file."""
        try:
            # Create fallback sheet instance
            fallback_kwargs: dict[str, Any] = {
                "name": "fallback.png",  # Имя должно быть fallback.png для правильного sheet_id
                "file": "default_fallback.png",
                "image": Image.open(default_fallback_path),
                "sprite_width": 32,  # Обычный размер для fallback
                "sprite_height": 32,
                "mod_id": "dda",
                "sprite_offset_x": 0,
                "sprite_offset_y": 0,
                "sprite_offset_x_retracted": 0,
                "sprite_offset_y_retracted": 0,
                "pixelscale": 1,
                "tiles_source": [],
            }
            default_fallback_sheet = FallbackSheet.from_dict(fallback_kwargs)

            # Добавляем в менеджер листов
            self.sheets.add_sheet(tileset_name, default_fallback_sheet)
            self.logger.debug(f"Added default fallback for tileset: {tileset_name}")

        except Exception as e:
            self.logger.error(
                f"Failed to create default fallback sheet for {tileset_name}: {e}"
            )
            raise

    def get_preferred_tileset(self, preferred_name: str, is_iso: bool = False) -> str:
        """Get a tileset by preference, with smart fallback.

        Attempts to find a tileset matching the preferred name. If not found,
        tries to find a tileset matching the type (iso/ortho). If nothing matches,
        returns the first available tileset.

        Args:
            preferred_name: Preferred tileset short_name (e.g., "UltimateCataclysm")
            is_iso: Whether to prefer isometric (True) or orthogonal (False) tileset

        Returns:
            Name of a suitable tileset (guaranteed to exist)
        """
        available = self.get_available_tilesets()
        if not available:
            raise ValueError("No tilesets available")

        # Try exact match first
        if preferred_name in available:
            return preferred_name

        # Try to find a tileset of the preferred type (iso/ortho)
        for tileset_name in available:
            tileset = self.get_tileset(tileset_name)
            if tileset.is_iso == is_iso:
                return tileset_name

        # Fallback to first available
        return available[0]

    def get_available_tilesets(self) -> list[str]:
        """Get list of available tileset names."""
        return list(self.tilesets.tilesets.keys())

    def get_tileset(self, tileset_name: str) -> Tileset:
        """Get tileset metadata object.

        Args:
            tileset_name: Name of the tileset to retrieve

        Returns:
            Tileset instance

        Raises:
            KeyError: If tileset not found (indicates tileset_name was not from
                      get_available_tilesets() or service not initialized properly)
        """
        tileset = self.tilesets.get_tileset(tileset_name)
        if not tileset:
            raise KeyError(
                f"Tileset '{tileset_name}' not found. Available: {self.get_available_tilesets()}"
            )
        return tileset

    def tileset_has_real_sprites(self, tileset_name: str) -> bool:
        """Return True if any registered tile in this tileset has a
        non-fallback sprite.

        We use the existing `_get_object_and_sprites` helper: if that
        function returns a TileObject whose `sprites` mapping contains any
        key other than -1, it means the tile resolved to a graphical
        sprite (not the ASCII/fallback entry which uses index -1).
        """
        tiles_for_ts = self.tiles.tilesets.get(tileset_name, {})
        if not tiles_for_ts:
            return False

        # Iterate through registered tiles and ask for their resolved sprites.
        # Stop early when we find any non-fallback sprite.
        for tileid in tiles_for_ts.keys():
            try:
                tile_obj: TileObject = self._get_object_and_sprites(
                    tileset_name, tileid, "white", "?"
                )
            except Exception:
                # Be robust: skip problematic tiles
                self.logger.debug(
                    f"tileset_has_real_sprites: failed to resolve {tileid}"
                )
                continue

            # If any sprite index is not -1, it's a real sprite
            for idx in tile_obj.sprites.keys():
                if idx != -1:
                    return True

        return False
