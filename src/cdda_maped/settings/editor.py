"""
Editor-related settings for CDDA-maped.
"""

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings


class EditorSettings:
    """Manages editor-related settings."""

    def __init__(self, settings: "QSettings"):
        self.settings = settings

    def _get_str(self, key: str, default: str = "") -> str:
        """Type-safe string retrieval from settings."""
        value = self.settings.value(key, default)
        return str(value) if value is not None else default

    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Type-safe boolean retrieval from settings."""
        value = self.settings.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value) if value is not None else default

    def _get_float(self, key: str, default: float = 0.0) -> float:
        """Type-safe float retrieval from settings."""
        value = self.settings.value(key, default)
        try:
            if value is None:
                return default
            return float(cast(str | float, value))
        except (ValueError, TypeError):
            return default

    @property
    def default_tileset(self) -> str:
        """Get default tileset name for orthogonal view."""
        return self._get_str("editor/default_tileset", "UltimateCataclysm")

    @default_tileset.setter
    def default_tileset(self, value: str) -> None:
        """Set default tileset name for orthogonal view."""
        self.settings.setValue("editor/default_tileset", value)
        self.settings.sync()

    @property
    def default_tileset_iso(self) -> str:
        """Get default tileset name for isometric view."""
        return self._get_str("editor/default_tileset_iso", "Ultica_iso")

    @default_tileset_iso.setter
    def default_tileset_iso(self, value: str) -> None:
        """Set default tileset name for isometric view."""
        self.settings.setValue("editor/default_tileset_iso", value)
        self.settings.sync()

    @property
    def grid_visible(self) -> bool:
        """Check if grid should be visible."""
        return self._get_bool("editor/grid_visible", True)

    @grid_visible.setter
    def grid_visible(self, value: bool) -> None:
        """Set grid visibility."""
        self.settings.setValue("editor/grid_visible", value)
        self.settings.sync()

    @property
    def zoom_level(self) -> float:
        """Get zoom level."""
        return self._get_float("editor/zoom_level", 1.0)

    @zoom_level.setter
    def zoom_level(self, value: float) -> None:
        """Set zoom level."""
        self.settings.sync()
        self.settings.setValue("editor/zoom_level", value)

    def _get_int(self, key: str, default: int = 0) -> int:
        """Type-safe integer retrieval from settings."""
        value = self.settings.value(key, default)
        try:
            if value is None:
                return default
            return int(cast(str | int, value))
        except (ValueError, TypeError):
            return default

    @property
    def animation_timeout(self) -> int:
        """Get animation timeout in milliseconds (1-1000 ms)."""
        value = self._get_int("editor/animation_timeout", 10)
        # Validate range
        return max(1, min(1000, value))

    @animation_timeout.setter
    def animation_timeout(self, value: int) -> None:
        """Set animation timeout in milliseconds (1-1000 ms)."""
        # Validate range
        validated = max(1, min(1000, value))
        self.settings.setValue("editor/animation_timeout", validated)
        self.settings.sync()
