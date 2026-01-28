"""Map manager for loading and resetting maps.

Provides centralized management for map state, including loading predefined
maps and resetting them to their initial state.
"""

import logging
from typing import Optional

from .models import DemoMap
from .demo_map_registry import DemoMapRegistry
from .demo_map_metadata import DemoMapMetadata


class MapManager:
    """Manages map loading and state reset functionality.

    Uses DemoMapRegistry to discover and load demo maps from JSON files.
    Maintains cache of currently loaded map for reset functionality.
    """

    def __init__(self):
        """Initialize the map manager."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Registry for discovering available demo maps
        self.registry = DemoMapRegistry()

        # Currently active map and its ID
        self._current_map: Optional[DemoMap] = None
        self._current_map_id: Optional[str] = None

    def get_demomap(self, demo_id: str = "default") -> DemoMap:
        """Get a demo map by ID.

        If the map is requested for the first time, it will be loaded from JSON.
        Subsequent calls return the same instance until reset_demomap() is called.

        Args:
            demo_id: ID of the demo map to load (default: "default")

        Returns:
            DemoMap instance

        Raises:
            KeyError: If demo map ID is not found in registry
            ValueError: If JSON file is invalid
        """
        # Load new map if not loaded or if ID changed
        if self._current_map is None or self._current_map_id != demo_id:
            self.logger.info(f"Loading demo map: {demo_id}")
            self._current_map = self.registry.load_demo_map(demo_id)
            self._current_map_id = demo_id

        return self._current_map

    def reset_demomap(self) -> DemoMap:
        """Reset the current demo map to its initial state.

                Rebuilds the map using the stored factory function, discarding all
                user modifications.

                Returns:
                    Freshly built DemoMap instance
        loads the map from JSON, discarding all user modifications.

                Returns:
                    Freshly loaded DemoMap instance

                Raises:
                    RuntimeError: If no map has been loaded yet
        """
        if self._current_map_id is None:
            raise RuntimeError("No demo map loaded. Call get_demomap() first.")

        self.logger.info(
            f"Resetting demo map '{self._current_map_id}' to initial state"
        )
        self._current_map = self.registry.load_demo_map(self._current_map_id)
        return self._current_map

    def get_available_demos(self) -> list[DemoMapMetadata]:
        """Get list of all available demo maps.

        Returns:
            List of DemoMapMetadata, sorted by name
        """
        return self.registry.get_all_metadata()

    def get_current_demo_map_id(self) -> Optional[str]:
        """Get ID of currently loaded demo map.

        Returns:
            Demo map ID or None if no map loaded
        """
        return self._current_map_id
