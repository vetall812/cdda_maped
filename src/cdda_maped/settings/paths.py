"""
Path-related settings for CDDA-maped.
"""

from pathlib import Path
from typing import List, Optional, Union, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings


class PathSettings:
    """Manages path-related settings."""

    def __init__(self, settings: "QSettings"):
        self.settings = settings

    def _get_str(self, key: str, default: str = "") -> str:
        """Type-safe string retrieval from settings."""
        value = self.settings.value(key, default)
        return str(value) if value is not None else default

    def _get_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        """Type-safe list retrieval from settings."""
        if default is None:
            default = []
        value = self.settings.value(key, default)
        if isinstance(value, list):
            return [
                str(item) if item is not None else ""
                for item in cast(list[object], value)
            ]
        return default

    @property
    def cdda_path(self) -> Optional[Path]:
        """Get CDDA game directory path."""
        path_str = self._get_str("paths/cdda", "")
        return Path(path_str) if path_str else None

    @cdda_path.setter
    def cdda_path(self, value: Optional[Path]) -> None:
        """Set CDDA game directory path."""
        self.settings.setValue("paths/cdda", str(value) if value else "")
        self.settings.sync()

    @property
    def cdda_data_path(self) -> Optional[Path]:
        """Get CDDA data directory path (derived from cdda_path)."""
        if self.cdda_path:
            return self.cdda_path / "data"
        return None

    @property
    def tilesets_path(self) -> Optional[Path]:
        """Get tilesets directory path (derived from cdda_path)."""
        if self.cdda_path:
            return self.cdda_path / "gfx"
        return None

    @property
    def recent_files(self) -> List[str]:
        """Get list of recently opened files."""
        return self._get_list("paths/recent_files", [])

    def add_recent_file(self, file_path: Union[str, Path]) -> None:
        """Add file to recent files list (max 10 items)."""
        recent = self.recent_files
        file_str = str(file_path)

        # Remove if already exists
        if file_str in recent:
            recent.remove(file_str)

        # Add to beginning
        recent.insert(0, file_str)

        # Keep only 10 most recent
        recent = recent[:10]

        self.settings.setValue("paths/recent_files", recent)
        self.settings.sync()

    def clear_recent_files(self) -> None:
        """Clear recent files list."""
        self.settings.sync()
        self.settings.setValue("paths/recent_files", [])
