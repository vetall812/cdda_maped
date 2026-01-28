"""Fallback placeholder rendering for missing sprites.

Draws colored shapes (rhombus for ISO, rectangle for ortho) when
sprite rendering fails or sprites are not available.
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QPolygonF, QPixmap, QColor, QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsPolygonItem

from ..coord_transformer import CoordinateTransformer
from ..scene_manager import SceneManager


class PlaceholderRenderer:
    """Renders fallback placeholders for missing sprites.

    Draws colored geometric shapes (rhombus for isometric, rectangle
    for orthogonal) when tile sprites cannot be loaded or rendered.
    """

    def __init__(
        self,
        scene: QGraphicsScene,
        transformer: CoordinateTransformer,
        scene_manager: SceneManager,
    ):
        """Initialize the placeholder renderer.

        Args:
            scene: QGraphicsScene to render on
            transformer: Coordinate transformer for projection
            scene_manager: Scene manager for offsets
        """
        self.scene = scene
        self.transformer = transformer
        self.scene_manager = scene_manager

    def draw_placeholder(self, tile_x: int, tile_y: int, object_id: str):
        """Draw a placeholder for a tile that couldn't be rendered.

        Chooses between isometric (rhombus) or orthogonal (rectangle)
        based on transformer settings.

        Args:
            tile_x: Grid X coordinate
            tile_y: Grid Y coordinate
            object_id: Object ID for determining placeholder color
        """
        if self.transformer.is_isometric:
            self._draw_iso_placeholder(tile_x, tile_y, object_id)
        else:
            self._draw_ortho_placeholder(tile_x, tile_y, object_id)

    def _draw_iso_placeholder(self, tile_x: int, tile_y: int, object_id: str):
        """Draw a rhombus placeholder for isometric projection.

        Args:
            tile_x: Grid X coordinate
            tile_y: Grid Y coordinate
            object_id: Object ID for determining placeholder color
        """
        tile_width = self.transformer.tile_width
        tile_height = self.transformer.tile_height

        # Get scene position (no sprite offset)
        scene_x, scene_y = self.transformer.get_scene_position(
            tile_x,
            tile_y,
            self.scene_manager.offset_x,
            self.scene_manager.offset_y,
            0,
            0,
        )

        # ISO rhombus - four corners
        half_w = tile_width / 2
        half_h = tile_height / 2

        polygon = QPolygonF(
            [
                QPointF(scene_x + half_w, scene_y),  # Top corner (right)
                QPointF(scene_x + tile_width, scene_y + half_h),  # Right corner
                QPointF(scene_x + half_w, scene_y + tile_height),  # Bottom corner
                QPointF(scene_x, scene_y + half_h),  # Left corner
            ]
        )

        brush = self._get_placeholder_color(object_id)
        item = QGraphicsPolygonItem(polygon)
        item.setBrush(brush)
        item.setPen(QPen(Qt.GlobalColor.black))
        self.scene.addItem(item)

    def _draw_ortho_placeholder(self, tile_x: int, tile_y: int, object_id: str):
        """Draw a rectangle placeholder for orthogonal projection.

        Args:
            tile_x: Grid X coordinate
            tile_y: Grid Y coordinate
            object_id: Object ID for determining placeholder color
        """
        tile_width = self.transformer.tile_width
        tile_height = self.transformer.tile_height

        # Get scene position (no sprite offset)
        scene_x, scene_y = self.transformer.get_scene_position(
            tile_x,
            tile_y,
            self.scene_manager.offset_x,
            self.scene_manager.offset_y,
            0,
            0,
        )

        # Inset rectangle slightly to show grid lines
        rect = QRectF(
            scene_x + 2,
            scene_y + 2,
            tile_width - 4,
            tile_height - 4,
        )

        brush = self._get_placeholder_color(object_id)
        item = QGraphicsRectItem(rect)
        item.setBrush(brush)
        item.setPen(QPen(Qt.GlobalColor.black))
        self.scene.addItem(item)

    def _get_placeholder_color(self, object_id: str) -> QBrush:
        """Get placeholder brush with stripe pattern based on object type.

        Args:
            object_id: Object ID (e.g., "t_wall", "f_table")

        Returns:
            QBrush with striped pattern and appropriate color for the object type
        """
        if object_id.startswith("t_"):  # terrain
            # 90 degrees - narrow horizontal stripes
            color = QColor(Qt.GlobalColor.green)
            return self._create_striped_brush(color, stripe_width=2, stripe_spacing=4)
        elif object_id.startswith("f_"):  # furniture
            # 180 degrees - wider horizontal stripes (vertical orientation, doubled width)
            color = QColor(Qt.GlobalColor.blue)
            return self._create_striped_brush(color, stripe_width=4, stripe_spacing=8)
        else:  # other
            # Vertical stripes
            color = QColor(Qt.GlobalColor.gray)
            return self._create_striped_brush(
                color, stripe_width=2, stripe_spacing=4, vertical=True
            )

    def _create_striped_brush(
        self,
        color: QColor,
        stripe_width: int = 2,
        stripe_spacing: int = 4,
        vertical: bool = False,
    ) -> QBrush:
        """Create a brush with diagonal or vertical stripes.

        Args:
            color: Base color for the stripes
            stripe_width: Width of each stripe in pixels
            stripe_spacing: Distance between stripes in pixels
            vertical: If True, create vertical stripes; else horizontal

        Returns:
            QBrush with striped pattern
        """
        # Create pattern pixmap with transparency
        pattern_size = stripe_width + stripe_spacing
        pattern = QPixmap(pattern_size, pattern_size)
        pattern.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pattern)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if vertical:
            # Vertical stripes
            painter.fillRect(0, 0, stripe_width, pattern_size, color)
        else:
            # Horizontal stripes
            painter.fillRect(0, 0, pattern_size, stripe_width, color)

        painter.end()

        brush = QBrush(pattern)
        return brush
