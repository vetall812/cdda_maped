"""Coordinate transformations for map rendering.

This module handles all coordinate system transformations,
including orthogonal to isometric conversions and sorting keys.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cdda_maped.tilesets.service import TilesetService


class CoordinateTransformer:
    """Handles coordinate transformations between orthogonal and isometric spaces."""

    def __init__(self, tile_width: int, tile_height: int, is_isometric: bool):
        """Initialize the coordinate transformer.

        Args:
            tile_width: Width of a single tile in pixels
            tile_height: Height of a single tile in pixels
            is_isometric: Whether to use isometric projection
        """
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.is_isometric = is_isometric

    @staticmethod
    def from_tileset(
        tileset_service: Optional["TilesetService"], tileset_name: Optional[str]
    ) -> "CoordinateTransformer":
        """Create transformer from tileset info.

        Args:
            tileset_service: TilesetService instance
            tileset_name: Current tileset name

        Returns:
            Configured CoordinateTransformer instance
        """
        tile_width, tile_height = 32, 32
        is_isometric = False

        if tileset_service and tileset_name:
            tileset = tileset_service.get_tileset(tileset_name)
            tile_width = tileset.grid_width * tileset.pixelscale
            tile_height = tileset.grid_height * tileset.pixelscale
            is_isometric = tileset.is_iso

        return CoordinateTransformer(tile_width, tile_height, is_isometric)

    def tiles_to_pixels(self, tile_x: float, tile_y: float) -> tuple[float, float]:
        """Convert tile grid coordinates to pixel coordinates in scene space.

        For orthogonal projection: simple multiplication by tile dimensions.
        For isometric projection: apply isometric transformation formula.

        Args:
            tile_x: Column in map (can be fractional for sub-tile positions)
            tile_y: Row in map (can be fractional for sub-tile positions)

        Returns:
            (pixel_x, pixel_y) in scene coordinate space
        """
        if not self.is_isometric:
            # Orthogonal: direct multiplication
            return (float(tile_x * self.tile_width), float(tile_y * self.tile_height))

        # Isometric projection with correct orientation (N-E-S-W)
        pixel_x = (tile_x + tile_y) * self.tile_width / 2
        pixel_y = (tile_y - tile_x) * self.tile_height / 2
        return (pixel_x, pixel_y)

    def get_iso_sort_key(self, tile_x: int, tile_y: int) -> tuple[int, int]:
        """Get sort key for isometric rendering order.

        Tiles are sorted by scene_y first (y-x), then scene_x (x+y)
        to ensure correct depth ordering (far to near).

        Args:
            x: Column in orthogonal grid
            y: Row in orthogonal grid

        Returns:
            (sort_y, sort_x) tuple for sorting
        """
        # Match the corrected isometric projection formula
        return (tile_y - tile_x, tile_x + tile_y)

    def get_scene_position(
        self,
        tile_x: int,
        tile_y: int,
        scene_offset_x: float,
        scene_offset_y: float,
        sprite_offset_x: int = 0,
        sprite_offset_y: int = 0,
    ) -> tuple[float, float]:
        """Calculate scene position for a tile with all offsets applied.

        Converts tile coordinates to pixel coordinates, then adds all offsets.
        Works uniformly for both orthogonal and isometric projections.

        Args:
            tile_x: Map X coordinate
            tile_y: Map Y coordinate
            scene_offset_x: Scene X offset in pixels (pan/scroll)
            scene_offset_y: Scene Y offset in pixels (pan/scroll)
            sprite_offset_x: Sprite X offset from style in pixels (default 0)
            sprite_offset_y: Sprite Y offset from style in pixels (default 0)

        Returns:
            (scene_x, scene_y) tuple in QGraphicsScene pixel coordinates
        """
        # Convert tile coordinates to pixel coordinates
        pixel_x, pixel_y = self.tiles_to_pixels(tile_x, tile_y)

        # Add all offsets (all in pixel space)
        iso_tile_adjust = self.tile_height / 2 if self.is_isometric else 0
        scene_x = pixel_x + scene_offset_x + sprite_offset_x
        scene_y = pixel_y + scene_offset_y + sprite_offset_y - iso_tile_adjust

        return (scene_x, scene_y)
