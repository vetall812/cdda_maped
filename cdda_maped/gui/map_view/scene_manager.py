"""Scene size and offset management for map rendering.

This module calculates scene boundaries and positioning offsets
for both orthogonal and isometric projections.
"""

import logging

from .coord_transformer import CoordinateTransformer


class SceneManager:
    """Manages scene size calculations and rendering offsets."""

    # Scene expansion factor for panning space
    EXPANSION_FACTOR = 3

    def __init__(
        self,
        map_width: int,
        map_height: int,
        num_of_z_levels: int,
        transformer: CoordinateTransformer,
        z_level_height: int = 0,
    ):
        """Initialize the scene manager.

        Args:
            map_width: Width of the map in cells (tiles) = sector_width * num_of_sectors_x
            map_height: Height of the map in cells (tiles) = sector_height * num_of_sectors_y
            num_of_z_levels: Number of z-levels in the map
            transformer: Coordinate transformer for projection calculations
            z_level_height: Z-level height in pixels from tileset (default 0)
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.map_width = map_width
        self.map_height = map_height
        self.transformer = transformer
        self.z_level_height = z_level_height
        self.num_of_z_levels = num_of_z_levels

        # Calculated properties
        self.scene_width: float = 0
        self.scene_height: float = 0
        self.offset_x: float = 0
        self.offset_y: float = 0

        self._calculate_scene_bounds()

    def _calculate_scene_bounds(self):
        """Calculate scene size and content offsets."""
        if self.transformer.is_isometric:
            self._calculate_iso_bounds()
        else:
            self._calculate_ortho_bounds()


    def _calculate_iso_bounds(self):
        """Calculate bounds for isometric projection."""
        tile_width = self.transformer.tile_width

        # Calculate corner positions in ISO space
        top_x, top_y = self.transformer.tiles_to_pixels(self.map_width - 1, 0)
        bottom_x, bottom_y = self.transformer.tiles_to_pixels(0, self.map_height - 1)
        left_x, left_y = self.transformer.tiles_to_pixels(0, 0)
        right_x, right_y = self.transformer.tiles_to_pixels(self.map_width - 1, self.map_height - 1)

        # Calculate content bounds (diamond shape)
        min_x = min(left_x, bottom_x)
        max_x = max(top_x, right_x)
        min_y = min(top_y, left_y)
        max_y = max(bottom_y, right_y)

        content_width = max_x - min_x
        content_height = max_y - min_y

        # Expand scene for panning space
        self.scene_width = content_width * self.EXPANSION_FACTOR
        self.scene_height = content_height * self.EXPANSION_FACTOR + self.z_level_height * self.num_of_z_levels

        # Center content in expanded scene
        center_offset_x = (self.scene_width - content_width) / 2
        center_offset_y = (self.scene_height - content_height) / 2 #+ self.z_level_height

        # Apply ISO-specific shift (content shifted left by half tile)
        shift_x = -(tile_width / 2)
        self.offset_x = -min_x + shift_x + center_offset_x
        self.offset_y = -min_y + center_offset_y

    def _calculate_ortho_bounds(self):
        """Calculate bounds for orthogonal projection."""
        tile_width = self.transformer.tile_width
        tile_height = self.transformer.tile_height

        content_width = self.map_width * tile_width
        content_height = self.map_height * tile_height

        # Expand scene for panning space
        self.scene_width = content_width * self.EXPANSION_FACTOR
        self.scene_height = content_height * self.EXPANSION_FACTOR

        # Center content in expanded scene
        self.offset_x = (self.scene_width - content_width) / 2
        self.offset_y = (self.scene_height - content_height) / 2
