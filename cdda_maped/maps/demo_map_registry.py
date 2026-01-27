"""Registry for available demo maps.

Manages discovery and lazy-loading of demo maps from builtin resources
and user configuration directories.
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QStandardPaths

from .models import DemoMap
from .demo_map_metadata import DemoMapMetadata
from .demo_map_loader import DemoMapLoader


class DemoMapRegistry:
    """Central registry for available demo maps.

    Discovers demo maps from:
    1. Built-in resources (cdda_maped/resources/demo_maps/)
    2. User config directory (platform-specific AppData location)

    Maps are loaded lazily - metadata is scanned at startup, but full
    DemoMap instances are only created when requested.
    """

    def __init__(self):
        """Initialize the registry."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self._metadata: dict[str, DemoMapMetadata] = {}
        self._loader = DemoMapLoader()

        # Discover available demo maps
        self._scan_builtin_demos()
        self._scan_user_demos()

    def _get_builtin_demo_maps_dir(self) -> Path:
        """Get path to built-in demo maps directory.

        Uses importlib.resources for compatibility with both development
        and packaged (PyInstaller/Nuitka) environments.

        Returns:
            Path to demo_maps directory in resources
        """
        try:
            from importlib.resources import files
            demo_maps_ref = files("cdda_maped.resources.demo_maps")

            # Convert to Path - handle both Traversable and regular paths
            try:
                # Try direct path conversion first
                path = Path(str(demo_maps_ref))
                if path.exists() and path.is_dir():
                    return path
            except Exception:
                pass

            # If that didn't work, fall through to fallback

        except Exception as e:
            self.logger.debug(f"importlib.resources failed: {e}")

        # Fallback: relative to this module's parent
        fallback = Path(__file__).parent.parent / "resources" / "demo_maps"
        self.logger.debug(f"Using fallback path: {fallback}")
        return fallback

    def _get_user_demo_maps_dir(self) -> Path:
        """Get path to user's demo maps directory.

        Uses QStandardPaths to get platform-appropriate config directory:
        - Windows: %APPDATA%/cdda-maped/demo_maps/
        - Linux: ~/.config/cdda-maped/demo_maps/
        - macOS: ~/Library/Application Support/cdda-maped/demo_maps/

        Returns:
            Path to user's demo_maps directory
        """
        app_data = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) # type: ignore
        user_demos = Path(app_data) / "demo_maps"

        # Ensure directory exists
        try:
            user_demos.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.warning(f"Failed to create user demo maps directory {user_demos}: {e}")

        return user_demos

    def _scan_builtin_demos(self) -> None:
        """Scan and register built-in demo maps."""
        builtin_dir = self._get_builtin_demo_maps_dir()

        if not builtin_dir.exists():
            self.logger.warning(f"Built-in demo maps directory not found: {builtin_dir}")
            return

        self.logger.info(f"Scanning built-in demo maps from: {builtin_dir}")
        count = self._scan_directory(builtin_dir, is_builtin=True)
        self.logger.info(f"Registered {count} built-in demo map(s)")

    def _scan_user_demos(self) -> None:
        """Scan and register user's custom demo maps."""
        user_dir = self._get_user_demo_maps_dir()

        if not user_dir.exists():
            self.logger.debug(f"User demo maps directory does not exist yet: {user_dir}")
            return

        self.logger.info(f"Scanning user demo maps from: {user_dir}")
        count = self._scan_directory(user_dir, is_builtin=False)
        if count > 0:
            self.logger.info(f"Registered {count} user demo map(s)")

    def _scan_directory(self, directory: Path, is_builtin: bool) -> int:
        """Scan directory for demo map JSON files.

        Args:
            directory: Directory to scan
            is_builtin: True if from resources, False if from user config

        Returns:
            Number of successfully registered maps
        """
        count = 0
        for json_file in directory.glob("*.json"):
            try:
                metadata = self._loader.load_metadata(json_file)
                metadata.is_builtin = is_builtin

                # User maps can override builtin maps by ID
                if metadata.id in self._metadata and is_builtin:
                    self.logger.debug(f"Skipping builtin '{metadata.id}', already registered")
                    continue

                self._metadata[metadata.id] = metadata
                count += 1
                self.logger.debug(f"Registered demo map: {metadata}")

            except Exception as e:
                self.logger.error(f"Failed to load metadata from {json_file}: {e}")

        return count

    def get_metadata(self, demo_id: str) -> Optional[DemoMapMetadata]:
        """Get metadata for a demo map by ID.

        Args:
            demo_id: Demo map identifier

        Returns:
            DemoMapMetadata if found, None otherwise
        """
        return self._metadata.get(demo_id)

    def get_all_metadata(self) -> list[DemoMapMetadata]:
        """Get list of all registered demo maps.

        Returns:
            List of DemoMapMetadata, sorted by name
        """
        return sorted(self._metadata.values(), key=lambda m: m.name)

    def get_all_ids(self) -> list[str]:
        """Get list of all registered demo map IDs.

        Returns:
            List of demo map IDs, sorted alphabetically
        """
        return sorted(self._metadata.keys())

    def has_demo_map(self, demo_id: str) -> bool:
        """Check if a demo map is registered.

        Args:
            demo_id: Demo map identifier

        Returns:
            True if registered, False otherwise
        """
        return demo_id in self._metadata

    def load_demo_map(self, demo_id: str) -> DemoMap:
        """Load a demo map by ID.

        Loads the full DemoMap instance from JSON. Not cached - creates
        a new instance each time.

        Args:
            demo_id: Demo map identifier

        Returns:
            Loaded DemoMap instance

        Raises:
            KeyError: If demo map ID is not registered
            ValueError: If JSON file is invalid
        """
        if demo_id not in self._metadata:
            available = ", ".join(self._metadata.keys())
            raise KeyError(
                f"Demo map '{demo_id}' not found in registry. Available: {available}"
            )

        metadata = self._metadata[demo_id]
        self.logger.info(f"Loading demo map '{demo_id}' from {metadata.file_path}")

        return self._loader.load_from_json(metadata.file_path)

    def reload_registry(self) -> None:
        """Re-scan directories and rebuild registry.

        Useful if user added new demo maps while app is running.
        """
        self.logger.info("Reloading demo map registry")
        self._metadata.clear()
        self._scan_builtin_demos()
        self._scan_user_demos()
