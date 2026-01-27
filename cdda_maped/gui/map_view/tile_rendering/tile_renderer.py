"""Main tile rendering orchestrator.

Coordinates sprite selection, transformation, and rendering for map tiles.
Handles multitile objects, seasonal sprites, rotation, and fallback rendering.
"""

import logging
from typing import Any, Optional, cast

from PIL import Image
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem

from cdda_maped.game_data.service import GameDataService
from cdda_maped.maps.models import MapCell
from cdda_maped.tilesets.service import TilesetService
from cdda_maped.tilesets.models import WeightedSprite, TileObject

from ..coord_transformer import CoordinateTransformer
from ..scene_manager import SceneManager
from ..animation_manager import AnimationStateManager
from .sprite_selector import SpriteSelector
from .sprite_transformer import SpriteTransformer
from .placeholder_renderer import PlaceholderRenderer


class TileRenderer:
    """Renders individual tiles with sprites on a QGraphicsScene.

    This is the main orchestrator that handles:
    - Subtile/connectivity calculation
    - Sprite selection (weighted/animated)
    - Sprite transformation (rotation/scaling)
    - Fallback rendering (placeholders)
    """

    # Available seasons for seasonal sprites
    SEASONS = ["spring", "summer", "autumn", "winter"]

    # Lookup table for rotates_to unconnected multitile indices
    # Binary mask: N=8, E=4, S=2, W=1
    ROTATES_TO_LOOKUP = {
        0b0000: 15,  # no rotates_to - fallback
        0b1000: 2,   # N
        0b0100: 3,   # E
        0b0010: 0,   # S
        0b0001: 1,   # W
        0b1100: 6,   # N+E
        0b0110: 7,   # E+S
        0b0011: 4,   # S+W
        0b1001: 5,   # N+W
        0b0111: 8,   # E+S+W
        0b1011: 9,   # S+W+N
        0b1101: 10,  # W+N+E
        0b1110: 11,  # N+E+S
        0b1111: 12,  # center
    }

    # ASCII symbols for subtile rendering
    ASCII_ENDPIECE = [210, 198, 208, 181]  # ╥ ╞ ╨ ╡ (N, W, S, E)
    ASCII_T_CONNECTION = [203, 204, 202, 185]  # ╦ ╠ ╩ ╣ (N, W, S, E missing)
    ASCII_EDGE_NS = 186  # ║
    ASCII_EDGE_WE = 205  # ═
    ASCII_CORNER_NW = 188  # ╝
    ASCII_CORNER_WS = 187  # ╗
    ASCII_CORNER_SE = 201  # ╔
    ASCII_CORNER_EN = 200  # ╚
    ASCII_CENTER = 206  # ╬

    # Workbench alignment index mapping
    # Maps neighbor cell index [N, W, S, E] to wb_index [2, 1, 0, 3]
    # Result: N→2, W→1, S→0, E→3
    WB_INDEX_MAP = [2, 1, 0, 3]

    def __init__(
        self,
        scene: QGraphicsScene,
        transformer: CoordinateTransformer,
        scene_manager: SceneManager,
        tileset_service: Optional[TilesetService] = None,
        game_data_service: Optional[GameDataService] = None,
        animation_state_manager: Optional[AnimationStateManager] = None,
    ):
        """Initialize the tile renderer.

        Args:
            scene: QGraphicsScene to render on
            transformer: Coordinate transformer for projection
            scene_manager: Scene manager for offsets
            tileset_service: Service for loading sprites (optional)
            game_data_service: Service for game object data (optional)
            animation_state_manager: Manager for animated tile states (optional)
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.scene = scene
        self.transformer = transformer
        self.scene_manager = scene_manager
        self.tileset_service = tileset_service
        self.game_data_service = game_data_service

        self.current_season = "spring"
        self.current_tileset: Optional[str] = None
        self._season_index = 0  # Cached season index

        # Initialize helper classes with composition
        self.sprite_selector = SpriteSelector(animation_state_manager)
        self.sprite_transformer = SpriteTransformer()
        self.placeholder_renderer = PlaceholderRenderer(scene, transformer, scene_manager)

        # Track resolved object IDs for tiles rendered via looks_like
        # Maps (x, y) -> resolved_object_id
        self._resolved_objects: dict[tuple[int, int], str] = {}

    def set_tileset_service(self, service: TilesetService):
        """Set the tileset service for sprite loading."""
        self.tileset_service = service

    def set_game_data_service(self, service: GameDataService):
        """Set the game data service for object information."""
        self.game_data_service = service

    def set_animation_state_manager(self, manager: AnimationStateManager):
        """Set the animation state manager for animated tiles."""
        self.sprite_selector.animation_state_manager = manager

    def set_current_tileset(self, tileset_name: str):
        """Set the current active tileset. Clears pixmap cache on change."""
        if self.current_tileset != tileset_name:
            self.sprite_transformer.clear_pixmap_cache()
        self.current_tileset = tileset_name

    def set_current_season(self, season: str):
        """Set the current season for seasonal sprites."""
        if season not in self.SEASONS:
            self.logger.warning(f"Invalid season '{season}', using 'spring'")
            season = "spring"
        self.current_season = season
        self._season_index = self.SEASONS.index(season)

    def get_resolved_object_id(self, x: int, y: int) -> Optional[str]:
        """Get the resolved object ID for a tile rendered via looks_like."""
        return self._resolved_objects.get((x, y))

    def render_tile(self, tile_x: int, tile_y: int, cell: MapCell, neighbors_cells: list[MapCell | None], transparency: bool = False, y_offset_zlevel: int = 0, brightness_factor: float = 1.0, transparency_factor: float = 1.0) -> None:
        """Render a tile at the specified coordinates based on MapCell content.

        Renders terrain first, then furniture on top if present.

        Args:
            tile_x: Grid X coordinate
            tile_y: Grid Y coordinate
            cell: MapCell containing slot contents
            neighbors_cells: List of neighboring MapCells [N, W, S, E]
            transparency: Whether the tile should be rendered with transparency
            y_offset_zlevel: Y offset in pixels for z-level stacking (negative = above)
        """
        if not self.game_data_service:
            raise RuntimeError("Game data service not set in TileRenderer")

        cell_obj_ids = cell.get_all_object_ids()
        cell_z_height = 0

        # Pre-determine tileset name once for transparency checks
        tileset_name = None
        if transparency and self.tileset_service:
            tileset_name = self.current_tileset
            if not tileset_name:
                available = self.tileset_service.get_available_tilesets()
                tileset_name = available[0] if available else None

        for object_id in cell_obj_ids:
            # By default use the base object id
            candidate_id = object_id

            # If transparency requested, prefer an object_id with "_transparent"
            # suffix but only if that variant actually resolves to a non-fallback
            # sprite in the current tileset. Otherwise keep the original id.
            if transparency and tileset_name and self.tileset_service:
                transparent_id = object_id + "_transparent"
                try:
                    fb_color, fb_symbol = self._get_fallback_params(object_id)
                    tile_obj = self.tileset_service.get_object_and_sprites_with_priority(
                        tileset_name=tileset_name,
                        object_id=transparent_id,
                        fallback_color=fb_color,
                        fallback_symbol=fb_symbol,
                        season=self.current_season,
                    )

                    # If the resolved TileObject contains any sprite index != -1
                    # then it's a real graphical sprite and we can use the suffix.
                    has_real = any(idx != -1 for idx in tile_obj.sprites.keys()) if tile_obj and tile_obj.sprites else False
                    if has_real:
                        candidate_id = transparent_id
                except Exception:
                    # On any error, fall back to original id
                    pass

            obj_height = self._render_object(tile_x, tile_y, candidate_id, cell_z_height, neighbors_cells, y_offset_zlevel, brightness_factor, transparency_factor)
            try:
                cell_z_height += int(obj_height or 0)
            except Exception:
                pass

    def _render_object(
        self,
        tile_x: int,
        tile_y: int,
        object_id: str,
        z_offset: int,
        neighbors_cells: list[MapCell | None],
        y_offset_zlevel: int = 0,
        brightness_factor: float = 1.0,
        transparency_factor: float = 1.0
    ) -> int:
        """Render a single object at the specified coordinates and return its 3D height.

        This is the universal tile rendering function used for all objects,
        whether they are terrain (t_dirt), furniture (f_table), or any other game object.

        Args:
            tile_x: Grid X coordinate
            tile_y: Grid Y coordinate
            object_id: Game object identifier (e.g., "t_dirt", "f_table")
            z_offset: Vertical offset in pixels for stacking objects within a cell
            neighbors_cells: List of neighboring MapCells [N, W, S, E]
            y_offset_zlevel: Y offset in pixels for z-level stacking (negative = above)
        """
        if not self.tileset_service:
            self.placeholder_renderer.draw_placeholder(tile_x, tile_y, object_id)
            raise RuntimeError("Tileset service not set in TileRenderer")

        if not self.game_data_service:
            self.placeholder_renderer.draw_placeholder(tile_x, tile_y, object_id)
            raise RuntimeError("Game data service not set in TileRenderer")

        try:
            # Use current tileset or fallback to first available
            tileset_name = self.current_tileset
            if not tileset_name:
                available_tilesets = self.tileset_service.get_available_tilesets()
                tileset_name = available_tilesets[0]
                self.logger.warning(f"No tileset set, defaulting to: {tileset_name}")

            # Get game object once and reuse
            game_object = self.game_data_service.get_resolved_object(object_id)

            # Get fallback parameters from game object
            fallback_color, fallback_symbol = self._get_fallback_params_from_object(game_object, object_id)

            # Calculate subtile connectivity
            subtile_type, subtile_index, alt_index, subtile_symbol = self._calculate_subtile(
                object_id, neighbors_cells, fallback_symbol
            )

            # Cache flags for reuse
            flags: list[str] = game_object.get("flags", []) if game_object else []

            # We need to check if current object have ALIGN_WORKBENCH flag
            # and if so - check neighbors for "workbench" property
            # as result we need an integer equal to first workbench found in neighbors:
            # 0 - none or south, 1 - west, 2 - north, 3 - east
            wb_index = 0  # default: none or south
            if "ALIGN_WORKBENCH" in flags:
                for index, neighbor in enumerate(neighbors_cells):
                    if not neighbor:
                        continue
                    # Check each neighbor object for "workbench" property
                    neighbor_obj_ids = neighbor.get_all_object_ids()
                    for neighbor_obj_id in neighbor_obj_ids:
                        neighbor_obj = self.game_data_service.get_resolved_object(neighbor_obj_id)
                        if neighbor_obj and neighbor_obj.get("workbench"):
                            wb_index = self.WB_INDEX_MAP[index]
                            break
                    if wb_index != 0:
                        break

            # Override fallback symbol for AUTO_WALL_SYMBOL objects
            if "AUTO_WALL_SYMBOL" in flags:
                fallback_symbol = subtile_symbol

            # Try to resolve looks_like if sprite is missing
            original_object_id = object_id
            resolved_via_looks_like = False

            tile_object = self.tileset_service.get_object_and_sprites_with_priority(
                tileset_name=tileset_name,
                object_id=object_id,
                fallback_color=fallback_color,
                fallback_symbol=fallback_symbol,
                season=self.current_season
            )

            # If fg sprite is -1 (fallback), try looks_like
            if (tile_object.source.fg is not None and
                isinstance(tile_object.source.fg, int) and
                tile_object.source.fg == -1):
                object_id, resolved_via_looks_like = self._try_looks_like(original_object_id, game_object)
                if resolved_via_looks_like:
                    tile_object = self.tileset_service.get_object_and_sprites_with_priority(
                        tileset_name=tileset_name,
                        object_id=object_id,
                        fallback_color=fallback_color,
                        fallback_symbol=fallback_symbol,
                        season=self.current_season
                    )

            # Track resolved object IDs
            if resolved_via_looks_like:
                self._resolved_objects[(tile_x, tile_y)] = object_id
            else:
                self._resolved_objects.pop((tile_x, tile_y), None)

            # Get sprites for this tile
            # Try alt_index first (for ROTATES_TO), fallback to subtile_index if needed
            fg_sprite, bg_sprite = None, None
            for index in (alt_index, subtile_index):
                fg_sprite, bg_sprite = self._get_sprites_for_tile(
                    tile_object, tile_x, tile_y, object_id,
                    subtile_type, index, wb_index
                )
                # Stop if we found fg sprite (bg is optional but fg is critical)
                # Continue to next index if we only found bg without fg
                if fg_sprite:
                    break


            # If no sprites found, draw placeholder
            if not fg_sprite and not bg_sprite:
                self.placeholder_renderer.draw_placeholder(tile_x, tile_y, object_id)
                # Even when placeholder is used, return 0 height
                return 0

            # Get sprite style properties
            style = tile_object.style
            sprite_offset_x = style.sprite_offset_x
            # Apply both z_offset (within-cell stacking) and y_offset_zlevel (z-level stacking)
            sprite_offset_y = style.sprite_offset_y - z_offset + y_offset_zlevel
            sprite_pixelscale = style.pixelscale

            # Get scene position
            scene_x, scene_y = self.transformer.get_scene_position(
                tile_x, tile_y,
                self.scene_manager.offset_x,
                self.scene_manager.offset_y,
                sprite_offset_x,
                sprite_offset_y,
            )

            # Draw sprites (BG first, then FG)
            if bg_sprite:
                bg_pixmap = self.sprite_transformer.scale_sprite_for_pixelscale(
                    bg_sprite, sprite_pixelscale
                )
                bg_item = QGraphicsPixmapItem(bg_pixmap)
                bg_item.setPos(scene_x, scene_y)

                # Apply brightness and transparency as item effects
                if brightness_factor != 1.0 or transparency_factor != 1.0:
                    self._apply_visual_effects(bg_item, brightness_factor, transparency_factor)

                self.scene.addItem(bg_item)

            if fg_sprite:
                fg_pixmap = self.sprite_transformer.scale_sprite_for_pixelscale(
                    fg_sprite, sprite_pixelscale
                )
                fg_item = QGraphicsPixmapItem(fg_pixmap)
                fg_item.setPos(scene_x, scene_y)

                # Apply brightness and transparency as item effects
                if brightness_factor != 1.0 or transparency_factor != 1.0:
                    self._apply_visual_effects(fg_item, brightness_factor, transparency_factor)

                self.scene.addItem(fg_item)
            # Return the object's 3D height if provided by the tileset
            try:
                return int(getattr(tile_object.source, "height_3d", 0) or 0)
            except Exception:
                return 0

        except Exception as e:
            self.logger.warning(f"Failed to render tile {object_id} at ({tile_x}, {tile_y}): {e}")
            self.placeholder_renderer.draw_placeholder(tile_x, tile_y, object_id)
            return 0

    def _get_fallback_params_from_object(self, game_object: dict[str, Any] | None, object_id: str) -> tuple[str, str]:
        """Get fallback color and symbol from already fetched game object.

        Args:
            game_object: Pre-fetched game object dict or None
            object_id: Object ID for logging

        Returns:
            (fallback_color, fallback_symbol) tuple
        """
        if not game_object:
            self.logger.debug(f"Game object not found for {object_id}")
            return "white", "?"

        raw_color = game_object.get("color", "white")
        raw_symbol = game_object.get("symbol", "?")

        fallback_color = self._seasonal_value(raw_color, "white", self._season_index)
        fallback_symbol = self._seasonal_value(raw_symbol, "?", self._season_index)
        fallback_color = self._normalize_color(fallback_color)

        return fallback_color, fallback_symbol

    def _get_fallback_params(self, object_id: str) -> tuple[str, str]:
        """Get fallback color and symbol from game object data.

        Returns:
            (fallback_color, fallback_symbol) tuple
        """
        try:
            if not self.game_data_service:
                return "white", "?"
            game_object = self.game_data_service.get_resolved_object(object_id)
        except Exception as e:
            self.logger.error(f"Failed to get game object for {object_id}: {e}")
            return "white", "?"

        return self._get_fallback_params_from_object(game_object, object_id)

    @staticmethod
    def _normalize_groups(raw: str | list[str] | None) -> set[str]:
        """Normalize connect/rotate groups to a set of strings."""
        if not raw:
            return set()
        if isinstance(raw, str):
            return {raw}
        return {g for g in raw if g}

    @staticmethod
    def _groups_to_mask(groups: list[bool]) -> int:
        """Convert NESW boolean list to bitmask."""
        n, w, s, e = groups
        return (8 if n else 0) | (1 if w else 0) | (2 if s else 0) | (4 if e else 0)

    @classmethod
    def _rotates_to_unconnected_index(cls, groups: list[bool]) -> int:
        """Compute unconnected multitile index for NESW connectivity.

        Args:
            groups: [N, W, S, E] boolean list
        """
        m = cls._groups_to_mask(groups)
        return cls.ROTATES_TO_LOOKUP.get(m, 15)

    @staticmethod
    def _rotates_to_edge_like_index(orientation_index: int, groups: list[bool]) -> int:
        """Calculate edge-like index based on orientation and neighbor groups.

        Args:
            orientation_index: 0 = NS, 1 = EW
            groups: [N, W, S, E] boolean list
        """
        orientation_index = orientation_index % 2
        N, W, S, E = groups

        if orientation_index == 0:  # NS orientation
            match (W, E):
                case (True, False):  return 0
                case (False, True):  return 2
                case (True, True):   return 4
                case (False, False): return 6
        else:  # EW orientation
            match (N, S):
                case (False, True):  return 1
                case (True, False):  return 3
                case (True, True):   return 5
                case (False, False): return 7

    @staticmethod
    def _seasonal_value(raw: str | list[str], default: str, season_index: int) -> str:
        """Pick seasonal value if list, otherwise return scalar."""
        if isinstance(raw, list):
            if not raw:
                return default
            return raw[season_index] if season_index < len(raw) else raw[-1]
        return raw

    @staticmethod
    def _normalize_color(value: str) -> str:
        """Collapse compound color names like 'green_yellow' -> 'green'."""
        if "_" not in value:
            return value
        parts = value.split("_")
        if len(parts) >= 2 and parts[0] in ["light", "dark"]:
            return "_".join(parts[:2])
        return parts[0]

    def _calculate_subtile(
        self,
        object_id: str,
        neighbors_cells: list[MapCell | None],
        fallback_symbol: str
    ) -> tuple[str, int, int, str]:
        """Calculate subtile type, index, alt index, and ASCII symbol based on connectivity.
           Where alt index is used for ROTATES_TO variants.

        Returns:
            (subtile_type, subtile_index, alt_index, subtile_symbol) tuple
        """
        if not self.game_data_service:
            return "unconnected", 0, 0, fallback_symbol

        game_object = self.game_data_service.get_resolved_object(object_id)
        if not game_object:
            return "unconnected", 0, 0, fallback_symbol
        # region Determine connectivity to neighbors
        # Calculate connected neighbors [N, W, S, E]
        # And rotates to neighbors [N, W, S, E]
        connected_neighbors = [False, False, False, False]
        rotates_to_neighbors = [False, False, False, False]

        connects_to_groups = self._normalize_groups(game_object.get("connects_to", []))
        rotates_to_groups = self._normalize_groups(game_object.get("rotates_to", []))

        # Precompute neighbor object ids and groups once
        neighbors_info: list[dict[str, set[str]] | None] = []
        for neighbor in neighbors_cells:
            if not neighbor:
                neighbors_info.append(None)
                continue

            neighbor_obj_ids = neighbor.get_all_object_ids()
            neighbor_groups: set[str] = set()
            for neighbor_obj_id in neighbor_obj_ids:
                neighbor_obj = self.game_data_service.get_resolved_object(neighbor_obj_id)
                if not neighbor_obj:
                    continue
                neighbor_groups |= self._normalize_groups(neighbor_obj.get("connect_groups", []))

            neighbors_info.append({"ids": set(neighbor_obj_ids), "groups": neighbor_groups})

        # Single pass per direction: self-connect, connects_to, rotates_to
        for index, info in enumerate(neighbors_info):
            if not info:
                continue

            if (not connected_neighbors[index]
                and object_id in info["ids"]):
                connected_neighbors[index] = True

            if (not connected_neighbors[index]
                and connects_to_groups
                and connects_to_groups & info["groups"]):
                connected_neighbors[index] = True

            if (not rotates_to_neighbors[index]
                and rotates_to_groups
                and rotates_to_groups & info["groups"]):
                rotates_to_neighbors[index] = True

            # Early exit if all neighbors are processed
            if (all(connected_neighbors) and
                (not rotates_to_groups or all(rotates_to_neighbors))):
                break

        #endregion

        # Determine subtile type/index/symbol based on connection count
        num_connected = sum(connected_neighbors)

        match num_connected:
            case 1:
                subtile_type = "end_piece"
                idx = connected_neighbors.index(True)
                subtile_index = [2, 3, 0, 1][idx]  # N→S, W→E, S→N, E→W
                alt_index = self._rotates_to_edge_like_index(subtile_index, rotates_to_neighbors)
                subtile_symbol = chr(self.ASCII_ENDPIECE[subtile_index])

            case 2:
                if connected_neighbors[0] and connected_neighbors[2]:  # N+S
                    subtile_type = "edge"
                    subtile_index = 0
                    alt_index = self._rotates_to_edge_like_index(subtile_index, rotates_to_neighbors)
                    subtile_symbol = chr(self.ASCII_EDGE_NS)
                elif connected_neighbors[1] and connected_neighbors[3]:  # W+E
                    subtile_type = "edge"
                    subtile_index = 1
                    alt_index = self._rotates_to_edge_like_index(subtile_index, rotates_to_neighbors)
                    subtile_symbol = chr(self.ASCII_EDGE_WE)
                else:  # Adjacent corners
                    subtile_type = "corner"
                    if connected_neighbors[0] and connected_neighbors[1]:  # N+W
                        subtile_index = 2
                        alt_index = subtile_index
                        subtile_symbol = chr(self.ASCII_CORNER_NW)
                    elif connected_neighbors[1] and connected_neighbors[2]:  # W+S
                        subtile_index = 3
                        alt_index = subtile_index
                        subtile_symbol = chr(self.ASCII_CORNER_WS)
                    elif connected_neighbors[2] and connected_neighbors[3]:  # S+E
                        subtile_index = 0
                        alt_index = subtile_index
                        subtile_symbol = chr(self.ASCII_CORNER_SE)
                    else:  # E+N
                        subtile_index = 1
                        alt_index = subtile_index
                        subtile_symbol = chr(self.ASCII_CORNER_EN)

            case 3:
                subtile_type = "t_connection"
                subtile_index = connected_neighbors.index(False)
                alt_index = subtile_index
                subtile_symbol = chr(self.ASCII_T_CONNECTION[subtile_index])

            case 4:
                subtile_type = "center"
                subtile_index = 0
                alt_index = subtile_index
                subtile_symbol = chr(self.ASCII_CENTER)

            case _:
                subtile_type = "unconnected"
                subtile_index = 0
                alt_index = self._rotates_to_unconnected_index(rotates_to_neighbors)
                subtile_symbol = fallback_symbol

        return subtile_type, subtile_index, alt_index, subtile_symbol

    def _try_looks_like(
        self,
        object_id: str,
        game_object: dict[str, Any] | None = None,
    ) -> tuple[str, bool]:
        """Try to resolve object via looks_like chain.

        Args:
            object_id: Object ID to resolve
            game_object: Pre-fetched game object (optional, will fetch if not provided)

        Returns:
            (resolved_object_id, success) tuple
        """
        if game_object is None:
            if not self.game_data_service:
                return object_id, False
            game_object = self.game_data_service.get_resolved_object(object_id)

        if game_object and "looks_like" in game_object:
            looks_like_id = game_object["looks_like"]
            self.logger.debug(f"FG sprite is fallback for {object_id}, trying looks_like: {looks_like_id}")
            return looks_like_id, True
        return object_id, False

    def _get_sprites_for_tile(
        self,
        tile_object: TileObject,
        tile_x: int,
        tile_y: int,
        object_id: str,
        subtile_type: str,
        subtile_index: int,
        wb_index: int = 0
    ) -> tuple[Image.Image | None, Image.Image | None]:
        """Get FG and BG sprites for a tile, handling multitile/rotation/weighted.

        Returns:
            (fg_sprite, bg_sprite) tuple of PIL Images or (None, None)
        """
        # Handle multitile objects
        if tile_object.source.multitile:
            fg_sprite, bg_sprite = self._get_multitile_sprites(
                tile_object, tile_x, tile_y, object_id, subtile_type, subtile_index
            )
        else:
            # Simple non-multitile object
            fg_sprite = self._get_simple_sprite(tile_object, tile_x, tile_y, object_id, wb_index, is_fg=True)
            bg_sprite = self._get_simple_sprite(tile_object, tile_x, tile_y, object_id, wb_index, is_fg=False)

        return fg_sprite, bg_sprite

    def _get_multitile_sprites(
        self,
        tile_object: TileObject,
        tile_x: int,
        tile_y: int,
        object_id: str,
        subtile_type: str,
        subtile_index: int
    ) -> tuple[Image.Image | None, Image.Image | None]:
        """Get sprites for multitile object, with rotation support."""
        source = tile_object.source
        additional_tiles = source.additional_tiles or []
        subtile = next((t for t in additional_tiles if t.id == subtile_type), None)

        def _resolve_multitile_value(
            value: int | list[int] | list[WeightedSprite] | None,
            idx: int,
            is_bg: bool = False
        ) -> int | None:
            """Resolve multitile FG/BG: int, list[int], or list[WeightedSprite]."""
            if value is None or isinstance(value, int):
                return value
            if not value:
                return None

            first_elem = value[0]
            is_animated = bool((subtile and subtile.animated) or source.animated)

            # Case A: list[int]
            if isinstance(first_elem, int):
                int_list = cast(list[int], value)
                # Lets return None if index is out of bounds or list is empty
                return int_list[idx] if 0 <= idx < len(int_list) else None

            # Case B: list[WeightedSprite]
            frame_list = cast(list[WeightedSprite], value)
            key = f"{object_id}#{subtile_type}{'_bg' if is_bg else ''}"
            frame = self.sprite_selector.select_weighted_frame(frame_list, tile_x, tile_y, key, is_animated)

            if isinstance(frame.sprite, int):
                return frame.sprite

            orient_list = frame.sprite
            # Lets return None if index is out of bounds or list is empty
            return orient_list[idx] if 0 <= idx < len(orient_list) else None

        # Get resolved sprite indices
        if subtile:
            source_fg = _resolve_multitile_value(subtile.fg, subtile_index)
            source_bg = _resolve_multitile_value(subtile.bg, subtile_index, is_bg=True)
        else:
            source_fg = source.fg
            source_bg = source.bg

        # Convert indices to sprites
        # Skip fallback sprites (-1) to allow fallback to subtile_index
        fg_sprite = tile_object.sprites.get(source_fg) if isinstance(source_fg, int) and source_fg != -1 else None
        bg_sprite = tile_object.sprites.get(source_bg) if isinstance(source_bg, int) and source_bg != -1 else None

        # Apply rotation if rotates flag and single sprites
        if source.rotates and subtile:
            if isinstance(subtile.fg, int) and fg_sprite:
                angle = self.sprite_transformer.get_multitile_rotation_angle(subtile_type, subtile_index)
                fg_sprite = self.sprite_transformer.rotate_pil_image(fg_sprite, angle)
            if isinstance(subtile.bg, int) and bg_sprite:
                angle = self.sprite_transformer.get_multitile_rotation_angle(subtile_type, subtile_index)
                bg_sprite = self.sprite_transformer.rotate_pil_image(bg_sprite, angle)

        return fg_sprite, bg_sprite

    def _get_simple_sprite(
        self,
        tile_object: TileObject,
        tile_x: int,
        tile_y: int,
        object_id: str,
        wb_index: int = 0,
        is_fg: bool = True
    ) -> Image.Image | None:
        """Get sprite for simple (non-multitile) object, handling rotation/weighted."""
        source = tile_object.source
        source_val = source.fg if is_fg else source.bg

        # Simple int index
        if isinstance(source_val, int):
            return tile_object.sprites.get(source_val)

        # List of indices (rotation) or weighted sprites
        if isinstance(source_val, list) and source_val:
            first_elem = source_val[0]
            is_rotates = source.rotates

            # Rotation case: list[int]
            if isinstance(first_elem, int):
                if is_rotates:
                    current_rotation = wb_index  # Use workbench alignment index for rotation
                    selected_index = current_rotation % len(source_val)
                    int_list = cast(list[int], source_val)
                    sprite_index = int_list[selected_index]
                    return tile_object.sprites.get(sprite_index)
                else:
                    self.logger.error(f"List of indices without rotates for {object_id}")
                    return None

            # Weighted case: list[WeightedSprite]
            else:
                if is_rotates:
                    self.logger.error(f"Weighted sprites with rotates for {object_id}")
                    return None
                else:
                    is_animated = source.animated or False
                    weighted_list = cast(list[WeightedSprite], source_val)
                    sprite_index = self.sprite_selector.select_weighted_sprite(
                        weighted_list, tile_x, tile_y, object_id, is_animated
                    )
                    return tile_object.sprites.get(sprite_index)

        return None

    def _apply_visual_effects(self, item: QGraphicsPixmapItem, brightness_factor: float, transparency_factor: float):
        """Apply brightness and transparency effects to a graphics item.

        Uses Qt's graphics effects for efficient rendering without pixmap modification.

        Args:
            item: QGraphicsPixmapItem to apply effects to
            brightness_factor: Brightness multiplier (< 1.0 darkens, > 1.0 brightens)
            transparency_factor: Opacity multiplier (0.0 = invisible, 1.0 = opaque)
        """
        from PySide6.QtWidgets import QGraphicsColorizeEffect
        from PySide6.QtGui import QColor

        # Apply opacity (transparency)
        if transparency_factor != 1.0:
            item.setOpacity(transparency_factor)

        # Apply brightness adjustment
        if brightness_factor != 1.0:
            # For darkening: use black colorize effect with reduced strength
            # For brightening: use white colorize effect
            effect = QGraphicsColorizeEffect()

            if brightness_factor < 1.0:
                # Darken: blend with black
                effect.setColor(QColor(0, 0, 0))
                strength = 1.0 - brightness_factor  # 0.0-1.0 range
                effect.setStrength(strength)
            else:
                # Brighten: blend with white
                effect.setColor(QColor(255, 255, 255))
                strength = min(brightness_factor - 1.0, 1.0)  # Clamp to 0.0-1.0
                effect.setStrength(strength)

            item.setGraphicsEffect(effect)
