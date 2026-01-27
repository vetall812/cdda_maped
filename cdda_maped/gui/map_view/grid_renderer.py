"""Grid rendering for map views.

This module handles rendering of grid lines for both
orthogonal and isometric projections.
"""

import logging
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QPen
from PySide6.QtWidgets import QGraphicsScene

from .coord_transformer import CoordinateTransformer
from .scene_manager import SceneManager


class GridRenderer:
    """Renders grid lines on a QGraphicsScene."""

    def __init__(
        self,
        scene: QGraphicsScene,
        transformer: CoordinateTransformer,
        scene_manager: SceneManager,
    ):
        """Initialize the grid renderer.

        Args:
            scene: QGraphicsScene to render on
            transformer: Coordinate transformer for projection
            scene_manager: Scene manager for offsets
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.scene = scene
        self.transformer = transformer
        self.scene_manager = scene_manager

        # Grid style
        self.grid_pen = QPen(Qt.GlobalColor.darkGray, 1, Qt.PenStyle.DotLine)
        self.label_color = QPalette().color(QPalette.ColorRole.Light)

        # Rotation state (0, 1, 2, 3 for 0°, 90°, 180°, 270°)
        self._rotation_state: int = 0

    def draw_grid(self, map_width: int, map_height: int, min_z: int = 0, max_z: int = 0, z_level_height: int = 0, current_z: int = 0):
        """Draw grid lines on the scene.

        Args:
            map_width: Width of the map in tiles
            map_height: Height of the map in tiles
            min_z: Minimum z-level on the map
            max_z: Maximum z-level on the map
            z_level_height: Height of one z-level in pixels (from tileset)
            current_z: Current z-level (local origin)
        """

        # Apply rotation to dimensions for grid drawing
        rotated_width = map_width
        rotated_height = map_height
        if self._rotation_state in (1, 3):  # 90° or 270°
            rotated_width, rotated_height = map_height, map_width

        self._draw_axes(rotated_width, rotated_height, min_z, max_z, z_level_height, current_z)

        if self.transformer.is_isometric:
            self._draw_iso_grid(rotated_width, rotated_height)
        else:
            self._draw_ortho_grid(rotated_width, rotated_height)

    def _draw_axes(self, map_width: int, map_height: int, min_z: int = 0, max_z: int = 0, z_level_height: int = 0, current_z: int = 0):
        """Draw coordinate axes from the appropriate map corner based on rotation.

        For orthogonal: red X (horizontal), green Y (vertical)
        For isometric: red X (diagonal up-right), green Y (diagonal down-right), blue Z (vertical)
        Uses dotted lines for negative direction, solid for positive.

        Args:
            map_width: Width of the map in tiles (original, unrotated)
            map_height: Height of the map in tiles (original, unrotated)
            min_z: Minimum z-level on the map
            max_z: Maximum z-level on the map
            z_level_height: Height of one z-level in pixels (from tileset)
            current_z: Current z-level (local origin)
        """
        # Select which corner of the map to draw axes from based on rotation
        # rotation 0: (0, 0) - top-left corner
        # rotation 1 (90° CW): (height, 0) - top-right corner
        # rotation 2 (180°): (width, height) - bottom-right corner
        # rotation 3 (270° CW): (0, width) - bottom-left corner
        if self._rotation_state == 0:
            origin_tile_x = 0
            origin_tile_y = 0
        elif self._rotation_state == 1:
            origin_tile_x = map_width
            origin_tile_y = 0
        elif self._rotation_state == 2:
            origin_tile_x = map_width
            origin_tile_y = map_height
        else:  # rotation_state == 3
            origin_tile_x = 0
            origin_tile_y = map_height

        # Convert to pixel coordinates
        pixel_x, pixel_y = self.transformer.tiles_to_pixels(origin_tile_x, origin_tile_y)

        # Add scene offset
        origin_x = pixel_x + self.scene_manager.offset_x
        origin_y = pixel_y + self.scene_manager.offset_y

        if self.transformer.is_isometric:
            self._draw_iso_axes(origin_x, origin_y, min_z, max_z, z_level_height, current_z, map_width, map_height)
        else:
            self._draw_ortho_axes(origin_x, origin_y)

    def _draw_ortho_axes(self, mid_x: float, mid_y: float):
        """Draw orthogonal axes (straight lines)."""
        tile_width = self.transformer.tile_width
        tile_height = self.transformer.tile_height

        # Red X axis (horizontal)
        pen_dotted = QPen(Qt.GlobalColor.red)
        pen_dotted.setStyle(Qt.PenStyle.DotLine)
        pen_solid = QPen(Qt.GlobalColor.red)
        pen_solid.setStyle(Qt.PenStyle.SolidLine)

        # Negative tail: 2 tiles
        neg_x_start = max(0, mid_x - 2 * tile_width)
        self.scene.addLine(neg_x_start, mid_y, mid_x, mid_y, pen_dotted)
        self.scene.addLine(mid_x, mid_y, self.scene_manager.scene_width, mid_y, pen_solid)

        # Green Y axis (vertical)
        pen_dotted = QPen(Qt.GlobalColor.green)
        pen_dotted.setStyle(Qt.PenStyle.DotLine)
        pen_solid = QPen(Qt.GlobalColor.green)
        pen_solid.setStyle(Qt.PenStyle.SolidLine)

        # Negative tail: 2 tiles
        neg_y_start = max(0, mid_y - 2 * tile_height)
        self.scene.addLine(mid_x, neg_y_start, mid_x, mid_y, pen_dotted)
        self.scene.addLine(mid_x, mid_y, mid_x, self.scene_manager.scene_height, pen_solid)

    def set_rotation_state(self, rotation_state: int) -> None:
        """Set the rotation state for axis rendering.

        Args:
            rotation_state: Rotation state (0-3) representing 0°, 90°, 180°, 270°
        """
        self._rotation_state = rotation_state % 4

    def _draw_iso_axes(self, mid_x: float, mid_y: float, min_z: int = 0, max_z: int = 0, z_level_height: int = 0, current_z: int = 0, map_width: int = 0, map_height: int = 0):
        """Draw isometric axes (diagonal lines with Z axis).

        Args:
            mid_x: Origin X coordinate in scene
            mid_y: Origin Y coordinate in scene
            min_z: Minimum z-level on the map
            max_z: Maximum z-level on the map
            z_level_height: Height of one z-level in pixels (from tileset)
            current_z: Current z-level (local origin)
            map_width: Width of the map in tiles
            map_height: Height of the map in tiles
        """
        # In isometric, there are 4 fixed diagonal directions:
        # NE (right-up), SE (right-down), SW (left-down), NW (left-up)
        # When map rotates, we cyclically shift which direction represents which axis,
        # but the angles remain constant.

        tile_width = self.transformer.tile_width
        tile_height = self.transformer.tile_height

        # Axis scale for positive direction (full scene)
        axis_length_positive = max(self.scene_manager.scene_width, self.scene_manager.scene_height) / 2
        # Negative direction: only 2 tiles
        axis_length_negative = 2 * max(tile_width, tile_height)

        # Four fixed isometric directions (normalized)
        # NE: right-up
        ne_x = tile_width / 2
        ne_y = -tile_height / 2
        ne_len = (ne_x**2 + ne_y**2) ** 0.5
        if ne_len > 0:
            ne_x /= ne_len
            ne_y /= ne_len

        # SE: right-down
        se_x = tile_width / 2
        se_y = tile_height / 2
        se_len = (se_x**2 + se_y**2) ** 0.5
        if se_len > 0:
            se_x /= se_len
            se_y /= se_len

        # SW: left-down
        sw_x = -tile_width / 2
        sw_y = tile_height / 2
        sw_len = (sw_x**2 + sw_y**2) ** 0.5
        if sw_len > 0:
            sw_x /= sw_len
            sw_y /= sw_len

        # NW: left-up
        nw_x = -tile_width / 2
        nw_y = -tile_height / 2
        nw_len = (nw_x**2 + nw_y**2) ** 0.5
        if nw_len > 0:
            nw_x /= nw_len
            nw_y /= nw_len

        # Assign directions to X and Y axes based on rotation state
        # rotation_state 0: X=NE, Y=SE
        # rotation_state 1: X=SE, Y=SW (90° CW)
        # rotation_state 2: X=SW, Y=NW (180°)
        # rotation_state 3: X=NW, Y=NE (270° CW)
        directions = [(ne_x, ne_y), (se_x, se_y), (sw_x, sw_y), (nw_x, nw_y)]

        x_dir_x, x_dir_y = directions[self._rotation_state % 4]
        y_dir_x, y_dir_y = directions[(self._rotation_state + 1) % 4]

        # Z axis direction (blue): (0, -1) - straight up
        z_dir_x = 0
        z_dir_y = -1

        # Draw X axis (red)
        pen_dotted = QPen(Qt.GlobalColor.red)
        pen_dotted.setStyle(Qt.PenStyle.DotLine)
        pen_solid = QPen(Qt.GlobalColor.red)
        pen_solid.setStyle(Qt.PenStyle.SolidLine)

        # Negative direction (dotted) - 2 tiles
        self.scene.addLine(
            mid_x,
            mid_y,
            mid_x - x_dir_x * axis_length_negative,
            mid_y - x_dir_y * axis_length_negative,
            pen_dotted,
        )
        # Positive direction (solid)
        self.scene.addLine(
            mid_x,
            mid_y,
            mid_x + x_dir_x * axis_length_positive,
            mid_y + x_dir_y * axis_length_positive,
            pen_solid,
        )

        # Draw ticks along X axis
        tick_pen = QPen(self.label_color)
        tick_size = 8
        # Ticks on X axis should be parallel to Y axis
        tick_dir_x = y_dir_x
        tick_dir_y = y_dir_y

        # Calculate actual tile spacing using transformer
        p0_x, p0_y = self.transformer.tiles_to_pixels(0, 0)
        p1_x, p1_y = self.transformer.tiles_to_pixels(1, 0)  # One tile along X
        tick_interval = ((p1_x - p0_x)**2 + (p1_y - p0_y)**2) ** 0.5

        # Determine which map dimension to use for X axis (depends on rotation)
        # rotation 0, 2: X follows map width
        # rotation 1, 3: X follows map height (axes swapped)
        x_axis_limit = map_height if self._rotation_state in [1, 3] else map_width

        # Ticks in positive direction (limited by appropriate map dimension)
        num_ticks_positive = min(x_axis_limit, int(axis_length_positive / tick_interval)) if x_axis_limit > 0 else int(axis_length_positive / tick_interval)
        for i in range(1, num_ticks_positive + 1):
            tick_center_x = mid_x + x_dir_x * i * tick_interval
            tick_center_y = mid_y + x_dir_y * i * tick_interval
            self.scene.addLine(
                tick_center_x - tick_dir_x * tick_size,
                tick_center_y - tick_dir_y * tick_size,
                tick_center_x + tick_dir_x * tick_size,
                tick_center_y + tick_dir_y * tick_size,
                tick_pen
            )
            # Label
            label_text = "x" if i == num_ticks_positive else str(i)
            text_item = self.scene.addText(label_text)
            text_item.setDefaultTextColor(self.label_color)
            rect = text_item.boundingRect()

            # Position label on the "outer" side based on rotation
            # rotation 0: X axis goes NE (up-right) → labels above and to the right
            # rotation 1: X axis goes SE (down-right) → labels below and to the right
            # rotation 2: X axis goes SW (down-left) → labels below and to the left
            # rotation 3: X axis goes NW (up-left) → labels above and to the left
            if self._rotation_state == 0:
                # Labels above and to the right.
                label_x = tick_center_x - 5
                label_y = tick_center_y - rect.height() - 5
            elif self._rotation_state == 1:
                # Labels below and to the right.
                label_x = tick_center_x + rect.width() + 5
                label_y = tick_center_y - rect.height()/2 -5
            elif self._rotation_state == 2:
                # Labels below and to the left
                label_x = tick_center_x - rect.width() + 5
                label_y = tick_center_y + 5
            else:  # rotation_state == 3
                # Labels above and to the left
                label_x = tick_center_x - rect.width()*2
                label_y = tick_center_y - 5

            text_item.setPos(label_x, label_y)

        # Draw Y axis (green)
        pen_dotted = QPen(Qt.GlobalColor.green)
        pen_dotted.setStyle(Qt.PenStyle.DotLine)
        pen_solid = QPen(Qt.GlobalColor.green)
        pen_solid.setStyle(Qt.PenStyle.SolidLine)

        # Negative direction (dotted) - 2 tiles
        self.scene.addLine(
            mid_x,
            mid_y,
            mid_x - y_dir_x * axis_length_negative,
            mid_y - y_dir_y * axis_length_negative,
            pen_dotted,
        )
        # Positive direction (solid)
        self.scene.addLine(
            mid_x,
            mid_y,
            mid_x + y_dir_x * axis_length_positive,
            mid_y + y_dir_y * axis_length_positive,
            pen_solid,
        )

        # Draw ticks along Y axis
        tick_pen = QPen(self.label_color)
        tick_size = 8
        # Ticks on Y axis should be parallel to X axis
        tick_dir_x = x_dir_x
        tick_dir_y = x_dir_y

        # Calculate actual tile spacing using transformer (Y direction)
        p0_x, p0_y = self.transformer.tiles_to_pixels(0, 0)
        p1_x, p1_y = self.transformer.tiles_to_pixels(0, 1)  # One tile along Y
        tick_interval_y = ((p1_x - p0_x)**2 + (p1_y - p0_y)**2) ** 0.5

        # Determine which map dimension to use for Y axis (depends on rotation)
        # rotation 0, 2: Y follows map height
        # rotation 1, 3: Y follows map width (axes swapped)
        y_axis_limit = map_width if self._rotation_state in [1, 3] else map_height

        # Ticks in positive direction (limited by appropriate map dimension)
        num_ticks_positive_y = min(y_axis_limit, int(axis_length_positive / tick_interval_y)) if y_axis_limit > 0 else int(axis_length_positive / tick_interval_y)
        for i in range(1, num_ticks_positive_y + 1):
            tick_center_x = mid_x + y_dir_x * i * tick_interval_y
            tick_center_y = mid_y + y_dir_y * i * tick_interval_y
            self.scene.addLine(
                tick_center_x - tick_dir_x * tick_size,
                tick_center_y - tick_dir_y * tick_size,
                tick_center_x + tick_dir_x * tick_size,
                tick_center_y + tick_dir_y * tick_size,
                tick_pen
            )
            # Label
            label_text = "y" if i == num_ticks_positive_y else str(i)
            text_item = self.scene.addText(label_text)
            text_item.setDefaultTextColor(self.label_color)
            rect = text_item.boundingRect()

            # Position label on the "outer" side based on rotation
            # rotation 0: Y axis goes SE (down-right) → labels below and to the left
            # rotation 1: Y axis goes SW (down-left) → labels above and to the right
            # rotation 2: Y axis goes NW (up-left) → labels above and to the left
            # rotation 3: Y axis goes NE (up-right) → labels below and to the right
            if self._rotation_state == 0:
                # Labels below and to the left.
                label_x = tick_center_x - 5
                label_y = tick_center_y + 5
            elif self._rotation_state == 1:
                # Labels above and to the right.
                label_x = tick_center_x - rect.width() - 15
                label_y = tick_center_y - rect.height()/2 - 5
            elif self._rotation_state == 2:
                # Labels above and to the left
                label_x = tick_center_x - rect.width() + 5
                label_y = tick_center_y - rect.height() - 5
            else:  # rotation_state == 3
                # Labels below and to the right
                label_x = tick_center_x + rect.width()/2 + 5
                label_y = tick_center_y - 5

            text_item.setPos(label_x, label_y)

        # Draw Z axis (blue) - vertical with dynamic length
        pen_dotted = QPen(Qt.GlobalColor.blue)
        pen_dotted.setStyle(Qt.PenStyle.DotLine)
        pen_solid = QPen(Qt.GlobalColor.blue)
        pen_solid.setStyle(Qt.PenStyle.SolidLine)

        # Use z_level_height from tileset, or fallback to tile_height
        grid_z_height = z_level_height if z_level_height > 0 else self.transformer.tile_height

        # Calculate lengths for positive and negative directions relative to current_z
        # Positive direction: from current_z up to max_z
        levels_above = max_z - current_z
        # Negative direction: from min_z up to current_z
        levels_below = current_z - min_z

        # Positive direction: always add extra 0.5-1.5 heights for visual guide
        if levels_above > 0:
            # There are levels above: draw to them + 0.5 extra
            z_length_positive = (levels_above + 0.5) * grid_z_height
        else:
            # No levels above: draw 1.5 for visual guide
            z_length_positive = 1.5 * grid_z_height

        # Negative direction: just the actual levels below
        z_length_negative = levels_below * grid_z_height if levels_below > 0 else 0

        # Draw positive direction (solid) - upward
        if z_length_positive > 0:
            self.scene.addLine(
                mid_x,
                mid_y,
                mid_x + z_dir_x * z_length_positive,
                mid_y + z_dir_y * z_length_positive,
                pen_solid,
            )

            # Draw ticks and labels for positive z-levels
            tick_pen = QPen(self.label_color)
            tick_size = 8
            symbol_size = 1*20 # Approximate width of '0' character in pixels

            # Start from current_z + 1, go up to max_z
            for z in range(current_z + 1, max_z + 1):
                offset_from_origin = z - current_z
                if offset_from_origin * grid_z_height > z_length_positive:
                    break
                tick_x = mid_x + z_dir_x * offset_from_origin * grid_z_height
                tick_y = mid_y + z_dir_y * offset_from_origin * grid_z_height
                # Horizontal tick
                self.scene.addLine(tick_x - tick_size, tick_y, tick_x + tick_size, tick_y, tick_pen)
                # Label with actual z-level
                text_item = self.scene.addText(f"{z}")
                text_item.setDefaultTextColor(self.label_color)
                rect = text_item.boundingRect()
                text_item.setPos(tick_x - tick_size - symbol_size, tick_y - rect.height() / 2)

        # Draw negative direction (dotted) - downward
        if z_length_negative > 0:
            self.scene.addLine(
                mid_x,
                mid_y,
                mid_x - z_dir_x * z_length_negative,
                mid_y - z_dir_y * z_length_negative,
                pen_dotted,
            )

            # Draw ticks and labels for negative z-levels
            tick_pen = QPen(self.label_color)
            tick_size = 8
            symbol_size = 1*20 # Approximate width of '0' character in pixels

            # Start from current_z - 1, go down to min_z
            for z in range(current_z - 1, min_z - 1, -1):
                offset_from_origin = current_z - z
                if offset_from_origin * grid_z_height > z_length_negative:
                    break
                tick_x = mid_x - z_dir_x * offset_from_origin * grid_z_height
                tick_y = mid_y - z_dir_y * offset_from_origin * grid_z_height
                # Horizontal tick
                self.scene.addLine(tick_x - tick_size, tick_y, tick_x + tick_size, tick_y, tick_pen)
                # Label with actual z-level
                text_item = self.scene.addText(str(z))
                text_item.setDefaultTextColor(self.label_color)
                rect = text_item.boundingRect()
                text_item.setPos(tick_x - tick_size - symbol_size, tick_y - rect.height() / 2)

        # Label at origin (current_z)
        text=f"z : {current_z}"
        symbol_size = 10  # Approximate width of '0' character in pixels
        text_item = self.scene.addText(text)
        text_item.setDefaultTextColor(self.label_color)
        rect = text_item.boundingRect()
        text_item.setPos(mid_x - len(text) * symbol_size, mid_y - rect.height() / 2)

    def _draw_ortho_grid(self, map_width: int, map_height: int):
        """Draw orthogonal grid (regular squares).

        Args:
            map_width: Width of the map in tiles
            map_height: Height of the map in tiles
        """
        tile_width = self.transformer.tile_width
        tile_height = self.transformer.tile_height

        tick_pen = QPen(self.label_color)
        tick_size = 6

        # Calculate grid bounds
        grid_width = map_width * tile_width
        grid_height = map_height * tile_height

        # Vertical lines
        for x in range(map_width + 1):
            x_pos = x * tile_width + self.scene_manager.offset_x
            self.scene.addLine(x_pos, self.scene_manager.offset_y, x_pos, self.scene_manager.offset_y + grid_height, self.grid_pen)

            tick_top = self.scene_manager.offset_y
            self.scene.addLine(x_pos, tick_top, x_pos, tick_top - tick_size, tick_pen)

            label_text = "x" if x == map_width else str(x)
            text_item = self.scene.addText(label_text)
            text_item.setDefaultTextColor(self.label_color)
            rect = text_item.boundingRect()
            text_item.setPos(x_pos , tick_top - tick_size - rect.height())

        # Horizontal lines
        for y in range(map_height + 1):
            y_pos = y * tile_height + self.scene_manager.offset_y
            self.scene.addLine(self.scene_manager.offset_x, y_pos, self.scene_manager.offset_x + grid_width, y_pos, self.grid_pen)

            tick_left = self.scene_manager.offset_x
            self.scene.addLine(tick_left, y_pos, tick_left - tick_size, y_pos, tick_pen)

            label_text = "y" if y == map_height else str(y)
            text_item = self.scene.addText(label_text)
            text_item.setDefaultTextColor(self.label_color)
            rect = text_item.boundingRect()
            text_item.setPos(tick_left - tick_size - rect.width(), y_pos )

    def _draw_iso_grid(self, map_width: int, map_height: int):
        """Draw isometric grid (diamonds).

        Args:
            map_width: Width of the map in tiles
            map_height: Height of the map in tiles
        """

        # Draw grid lines
        # Lines going NW-SE (constant x in ortho)
        for tile_x in range(map_width + 1):
            points: list[tuple[float, float]] = []
            for tile_y in range(map_height + 1):
                pixel_x, pixel_y = self.transformer.tiles_to_pixels(tile_x, tile_y)
                scene_x = pixel_x + self.scene_manager.offset_x
                scene_y = pixel_y + self.scene_manager.offset_y
                points.append((scene_x, scene_y))

            for i in range(len(points) - 1):
                self.scene.addLine(
                    points[i][0],
                    points[i][1],
                    points[i + 1][0],
                    points[i + 1][1],
                    self.grid_pen,
                )

        # Lines going NE-SW (constant y in ortho)
        for tile_y in range(map_height + 1):
            points: list[tuple[float, float]] = []
            for tile_x in range(map_width + 1):
                pixel_x, pixel_y = self.transformer.tiles_to_pixels(tile_x, tile_y)
                scene_x = pixel_x + self.scene_manager.offset_x
                scene_y = pixel_y + self.scene_manager.offset_y
                points.append((scene_x, scene_y))

            for i in range(len(points) - 1):
                self.scene.addLine(
                    points[i][0],
                    points[i][1],
                    points[i + 1][0],
                    points[i + 1][1],
                    self.grid_pen,
                )

    def set_grid_pen(self, pen: QPen):
        """Set the pen style for grid lines.

        Args:
            pen: QPen to use for grid lines
        """
        self.grid_pen = pen
