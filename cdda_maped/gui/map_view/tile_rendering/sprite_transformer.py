"""Sprite transformation utilities (rotation, scaling).

Handles pixel-perfect rotation of sprites for multitile objects
and scaling sprites according to tileset pixelscale settings.
"""

import logging
from PIL import Image
from PySide6.QtGui import QPixmap


class SpriteTransformer:
    """Transforms sprites through rotation and scaling.

    Provides pixel-perfect rotation for tile sprites and caching
    for scaled QPixmap objects.
    """

    def __init__(self):
        """Initialize the sprite transformer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Cache for converted QPixmap to avoid repeated PIL->QImage->QPixmap conversions
        # Key: (id(pil_image), pixelscale), Value: QPixmap
        self._pixmap_cache: dict[tuple[int, int], QPixmap] = {}
        self._pixmap_cache_max_size = 1000

    def clear_pixmap_cache(self):
        """Clear the QPixmap cache.

        Call this when switching tilesets or when memory usage needs to be reduced.
        """
        cache_size = len(self._pixmap_cache)
        self._pixmap_cache.clear()
        if cache_size > 0:
            self.logger.debug(f"Pixmap cache cleared ({cache_size} items)")

    def get_multitile_rotation_angle(
        self, subtile_type: str, subtile_index: int
    ) -> int:
        """Get rotation angle (clockwise) for a multitile subtile.

        Default orientations (before rotation):
        - end_piece[0]: points south (0°)
        - end_piece[1]: points east (270° cw = -90° ccw)
        - corner[0]: SE corner (0°)
        - corner[1]: NE corner (270°)
        - edge[0]: vertical NS (0°)
        - edge[1]: horizontal EW (90°)
        - t_connection[0]: no south (0°)
        - t_connection[1]: no west (90°)
        - center/unconnected: no rotation (0°)

        Args:
            subtile_type: Type of subtile (end_piece, corner, edge, t_connection, center, unconnected)
            subtile_index: Index within the subtile type (0..3 for 4-way, 0..1 for 2-way)

        Returns:
            Rotation angle in degrees, clockwise (0, 90, 180, 270)
        """
        rotation_map = {
            "end_piece": [0, 270, 180, 90],
            "corner": [0, 270, 180, 90],
            "edge": [0, 90],
            "t_connection": [0, 90, 180, 270],
            "center": [0],
            "unconnected": [0],
        }

        angles = rotation_map.get(subtile_type, [0])
        if subtile_index < len(angles):
            return angles[subtile_index]
        return 0

    def rotate_pil_image(self, image: Image.Image, angle_clockwise: int) -> Image.Image:
        """Rotate PIL image by angle (clockwise, pixel-perfect).

        Uses transpose() for integer rotations to preserve pixel-art quality.
        No interpolation, no fill color needed.

        Args:
            image: PIL Image to rotate
            angle_clockwise: Rotation angle in degrees (0, 90, 180, 270)

        Returns:
            Rotated image (or original if angle is 0)
        """
        angle = angle_clockwise % 360
        if angle == 0:
            return image
        elif angle == 90:
            return image.transpose(Image.Transpose.ROTATE_270)
        elif angle == 180:
            return image.transpose(Image.Transpose.ROTATE_180)
        elif angle == 270:
            return image.transpose(Image.Transpose.ROTATE_90)
        return image

    def scale_sprite_for_pixelscale(
        self, pil_image: Image.Image, pixelscale: int
    ) -> QPixmap:
        """Convert PIL Image to QPixmap and scale it according to pixelscale.

        Results are cached to avoid repeated PIL->QImage->QPixmap conversions.

        Args:
            pil_image: Source PIL image (pre-cut sprite)
            pixelscale: Scaling factor from tileset (typically 1 or 2)

        Returns:
            Scaled QPixmap ready for display
        """
        from PIL.ImageQt import ImageQt

        # Check cache first
        cache_key = (id(pil_image), pixelscale)
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]

        # Clear cache if it grows too large (keep memory usage bounded)
        if len(self._pixmap_cache) >= self._pixmap_cache_max_size:
            self._pixmap_cache.clear()
            self.logger.debug(
                f"Pixmap cache cleared (was {self._pixmap_cache_max_size} items)"
            )

        # Normalize to a Qt-friendly mode
        if pil_image.mode not in ("RGBA", "RGB", "LA", "L"):
            pil_image = pil_image.convert("RGBA")

        # Scale the image if pixelscale > 1 using NEAREST for pixel art
        if pixelscale > 1:
            new_width = pil_image.width * pixelscale
            new_height = pil_image.height * pixelscale
            pil_image = pil_image.resize(
                (new_width, new_height), Image.Resampling.NEAREST
            )

        qt_image = ImageQt(pil_image)
        pixmap = QPixmap.fromImage(qt_image)

        # Store in cache
        self._pixmap_cache[cache_key] = pixmap
        return pixmap
