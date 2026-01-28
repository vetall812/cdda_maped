"""
Managers for tilesets, sprite sheets, and tiles.

Provides indexing, lookup and bookkeeping for different components of the
tileset system. No I/O or heavy logic beyond basic JSON reading.
"""

from pathlib import Path
from typing import Dict
from dataclasses import dataclass, field
from PIL import Image
import orjson
import threading

from .models import Tileset, Sheet, FallbackSheet, Tile, TileSource, SheetInfo


class TilesetManager:
    """Manage tileset metadata discovered on disk.

    Holds a dictionary of `Tileset` objects keyed by folder_name.
    """

    def __init__(self):
        self.tilesets = dict[str, Tileset]()

    def add_tileset(self, ts_path: str) -> Tileset:
        """Add a tileset from the given directory path.

        Reads tileset.txt and tile_info.json to populate basic metadata.
        Returns the `Tileset` instance registered in the manager.
        """
        if not Path(ts_path).exists():
            raise FileNotFoundError(f"Tileset path not found: {ts_path}")

        ts_dir = Path(ts_path)
        ts_metadata = Tileset(folder_name=ts_dir.name)

        # 1) Parse tileset.txt
        json_name = None
        try:
            tileset_txt = ts_dir / "tileset.txt"
            if tileset_txt.exists():
                with open(tileset_txt, encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("NAME:"):
                            ts_metadata.short_name = line.partition(":")[2].strip()
                        elif line.startswith("VIEW:"):
                            ts_metadata.view_name = line.partition(":")[2].strip()
                        elif line.startswith("JSON:"):
                            json_name = line.partition(":")[2].strip()
        except Exception as e:
            print(f"Error reading tileset.txt: {e}")

        # 2) Parse tile_info.json
        try:
            if json_name:
                json_path = ts_dir / json_name
            else:
                json_path = ts_dir / "tile_info.json"
            if json_path.exists():
                with open(json_path, "rb") as f:
                    data = orjson.loads(f.read())
                    tile_info = data.get("tile_info", [{}])[0]
                    ts_metadata.pixelscale = tile_info.get(
                        "pixelscale", ts_metadata.pixelscale
                    )
                    ts_metadata.grid_width = tile_info.get(
                        "width", ts_metadata.grid_width
                    )
                    ts_metadata.grid_height = tile_info.get(
                        "height", ts_metadata.grid_height
                    )
                    ts_metadata.grid_z_height = tile_info.get(
                        "zlevel_height", ts_metadata.grid_z_height
                    )
                    ts_metadata.is_iso = tile_info.get("iso", ts_metadata.is_iso)
                    ts_metadata.retract_dist_min = tile_info.get(
                        "retract_dist_min", ts_metadata.retract_dist_min
                    )
                    ts_metadata.retract_dist_max = tile_info.get(
                        "retract_dist_max", ts_metadata.retract_dist_max
                    )
                    # Store parsed tiles_new list directly (no re-serialization)
                    tiles_new = data.get("tiles-new", [])
                    ts_metadata.objects_source = tiles_new
        except Exception as e:
            print(f"Error reading tile_info.json: {e}")

        self.tilesets[ts_metadata.folder_name] = ts_metadata
        return ts_metadata

    def get_tileset(self, folder_name: str) -> Tileset | None:
        """Return tileset by folder name if present."""
        return self.tilesets.get(folder_name, None)

    def get_tileset_by_short_name(self, short_name: str) -> Tileset | None:
        """Return tileset by short_name if present.

        Searches through all tilesets to find one with matching short_name.
        Returns None if not found.
        """
        for tileset in self.tilesets.values():
            if tileset.short_name == short_name:
                return tileset
        return None


@dataclass
class TilesManager:
    """Manage tiles indexed by tileset and mod.

    Two-level indices are maintained:
    - tilesets[tileset][id] -> Tile (last-wins override behavior)
    - tilesets_by_mod[tileset][mod_id][id] -> Tile (for precise origin lookups)
    """

    # tileset_name -> id -> tile
    tilesets: Dict[str, Dict[str, Tile]] = field(default_factory=lambda: {})
    # tileset_name -> mod_id -> id -> tile (для поиска по модам)
    tilesets_by_mod: Dict[str, Dict[str, Dict[str, Tile]]] = field(
        default_factory=lambda: {}
    )

    def __post_init__(self):
        self.tilesets = {}
        self.tilesets_by_mod = {}

    def add_tile(self, tileset: str, tile_obj: Tile):
        """Add a tile to indices, honoring mod priority (last-wins)."""
        if tileset not in self.tilesets:
            self.tilesets[tileset] = {}
        if tileset not in self.tilesets_by_mod:
            self.tilesets_by_mod[tileset] = {}
        if tile_obj.mod_id not in self.tilesets_by_mod[tileset]:
            self.tilesets_by_mod[tileset][tile_obj.mod_id] = {}

        # Основной индекс - последний тайл с таким ID побеждает (приоритет модов)
        self.tilesets[tileset][tile_obj.tileid] = tile_obj
        # Индекс по модам - для точного поиска
        self.tilesets_by_mod[tileset][tile_obj.mod_id][tile_obj.tileid] = tile_obj

    def get_tile(self, tileset: str, tileid: str) -> Tile | None:
        """Get a tile by id within a tileset, if present."""
        return self.tilesets.get(tileset, {}).get(tileid)

    def get_tile_from_mod(self, tileset: str, mod_id: str, tileid: str) -> Tile | None:
        """Get a tile from a specific mod."""
        return self.tilesets_by_mod.get(tileset, {}).get(mod_id, {}).get(tileid)

    def get_tile_with_priority(
        self, tileset: str, tileid: str, preferred_mods: list[str] | None = None
    ) -> Tile | None:
        """Get a tile honoring a preferred mod order, falling back to default."""
        if preferred_mods:
            for mod_id in preferred_mods:
                tile_obj = self.get_tile_from_mod(tileset, mod_id, tileid)
                if tile_obj:
                    return tile_obj
        return self.get_tile(tileset, tileid)

    def get_available_mods(self, tileset: str) -> list[str]:
        """List mods that contribute tiles to the given tileset."""
        return list(self.tilesets_by_mod.get(tileset, {}).keys())

    def get_tile_source(self, tileset: str, tileid: str) -> TileSource | None:
        """Return raw TileSource for a tile id if present."""
        t = self.get_tile(tileset, tileid)
        return t.source if t else None

    def get_tile_with_season(
        self, tileset: str, tileid: str, season: str = "spring"
    ) -> Tile | None:
        """Get a tile with seasonal support, trying seasonal variant first."""
        # First try seasonal variant: {tileid}_season_{season}
        seasonal_id = f"{tileid}_season_{season}"
        seasonal_tile = self.get_tile(tileset, seasonal_id)
        if seasonal_tile:
            return seasonal_tile

        # Fall back to base tile (for objects that don't change with seasons)
        return self.get_tile(tileset, tileid)

    def get_tile_with_season_and_priority(
        self,
        tileset: str,
        tileid: str,
        season: str = "spring",
        preferred_mods: list[str] | None = None,
    ) -> Tile | None:
        """Get a tile with both seasonal and mod priority support."""
        seasonal_id = f"{tileid}_season_{season}"

        # First try seasonal variant with mod priority
        if preferred_mods:
            for mod_id in preferred_mods:
                seasonal_tile = self.get_tile_from_mod(tileset, mod_id, seasonal_id)
                if seasonal_tile:
                    return seasonal_tile

        # Try base seasonal tile
        seasonal_tile = self.get_tile(tileset, seasonal_id)
        if seasonal_tile:
            return seasonal_tile

        # Fall back to base tile with mod priority
        return self.get_tile_with_priority(tileset, tileid, preferred_mods)


class SheetManager:
    """Manage sprite sheets and global sprite index per tileset."""

    def __init__(self):
        # tileset_name -> sheet_id -> Sheet
        self.sheets: dict[str, dict[str, Sheet]] = {}
        # tileset_name -> mod_id -> [sheet_ids] (for mod-scoped lookups)
        self.sheets_by_mod: dict[str, dict[str, list[str]]] = {}
        # Global sprite index: tileset_name -> global_index -> (sheet_id, local_index)
        self.global_sprite_index: dict[str, dict[int, tuple[str, int]]] = {}
        # Thread safety lock
        self._lock = threading.Lock()

    def add_sheet(self, tileset_name: str, sheet: Sheet):
        """Register a sheet, update mod index. Note: global sprite index rebuild is deferred.

        This method is now called sequentially (not from threads), so no lock needed here.
        """
        if tileset_name not in self.sheets:
            self.sheets[tileset_name] = {}
            self.sheets_by_mod[tileset_name] = {}
            self.global_sprite_index[tileset_name] = {}

        # Добавляем лист
        self.sheets[tileset_name][sheet.sheet_id] = sheet

        # Index by mod
        if sheet.mod_id not in self.sheets_by_mod[tileset_name]:
            self.sheets_by_mod[tileset_name][sheet.mod_id] = []
        self.sheets_by_mod[tileset_name][sheet.mod_id].append(sheet.sheet_id)

    def finalize_tileset(self, tileset_name: str):
        """Rebuild global sprite index after all sheets are loaded.

        Call this once after loading all sheets for a tileset to avoid O(n²) complexity.
        """
        with self._lock:
            self._update_global_sprite_index(tileset_name)

    def _update_global_sprite_index(self, tileset_name: str):
        """Recompute mapping from global index to (sheet_id, local_index)."""
        global_index = 0
        self.global_sprite_index[tileset_name] = {}

        for sheet_id, sheet in self.sheets[tileset_name].items():
            for local_index in range(len(sheet.sprites)):
                self.global_sprite_index[tileset_name][global_index] = (
                    sheet_id,
                    local_index,
                )
                global_index += 1

    def get_sprite_by_global_index(
        self, tileset_name: str, global_index: int
    ) -> Image.Image | None:
        """Return sprite image by global index, or None if not found."""
        if tileset_name not in self.global_sprite_index:
            return None

        mapping = self.global_sprite_index[tileset_name].get(global_index)
        if not mapping:
            return None

        sheet_id, local_index = mapping
        sheet = self.sheets[tileset_name].get(sheet_id)
        if not sheet:
            return None

        return sheet.get_sprite_by_index(local_index)

    def get_sprite_by_mod_index(
        self,
        tileset_name: str,
        mod_id: str,
        local_index: int,
        sheet_hint: str | None = None,
    ) -> Image.Image | None:
        """Return sprite image by local index from mod sheet, or None if not found."""
        # Получаем список листов для данного мода
        mod_sheet_ids = self.get_sheets_from_mod(tileset_name, mod_id)
        if not mod_sheet_ids:
            # TODO: logging using logging module
            return None

        # Если подсказка по листу дана, попробуем её первой
        if sheet_hint and sheet_hint in mod_sheet_ids:
            sheet = self.sheets[tileset_name].get(sheet_hint)
            if sheet and local_index < len(sheet.sprites):
                return sheet.get_sprite_by_index(local_index)

        # Иначе ищем по всем листам мода
        for sheet_id in mod_sheet_ids:
            sheet = self.sheets[tileset_name].get(sheet_id)
            if sheet and local_index < len(sheet.sprites):
                return sheet.get_sprite_by_index(local_index)

        return None

    def get_sheet_info(self, tileset_name: str, sheet_id: str) -> SheetInfo | None:
        """Return lightweight info about a sheet.

        Args:
            tileset_name: Name of the tileset
            sheet_id: ID of the sheet

        Returns:
            SheetInfo instance or None if not found
        """
        sheet = self.sheets.get(tileset_name, {}).get(sheet_id)
        if not sheet:
            return None

        return SheetInfo(
            name=sheet.name,
            file=sheet.file,
            sprite_width=sheet.sprite_width,
            sprite_height=sheet.sprite_height,
            mod_id=sheet.mod_id,
            sprite_count=len(sheet.sprites),
            sprite_offset_x=getattr(sheet, "sprite_offset_x", 0),
            sprite_offset_y=getattr(sheet, "sprite_offset_y", 0),
            sprite_offset_x_retracted=getattr(sheet, "sprite_offset_x_retracted", 0),
            sprite_offset_y_retracted=getattr(sheet, "sprite_offset_y_retracted", 0),
            pixelscale=getattr(sheet, "pixelscale", 1),
        )

    def get_ascii(
        self, tileset_name: str, sheet_id: str, color: str, char: str
    ) -> Image.Image | None:
        """Get ASCII sprite from a fallback sheet if available."""
        sheet = self.sheets.get(tileset_name, {}).get(sheet_id)
        if isinstance(sheet, FallbackSheet):
            return sheet.get_ascii_sprite(color, char)
        return None

    def get_available_mods(self, tileset_name: str) -> list[str]:
        """List mods that contribute sheets to the tileset."""
        return list(self.sheets_by_mod.get(tileset_name, {}).keys())

    def get_sheets_from_mod(self, tileset_name: str, mod_id: str) -> list[str]:
        """Return list of sheet ids originating from a specific mod."""
        return self.sheets_by_mod.get(tileset_name, {}).get(mod_id, [])
