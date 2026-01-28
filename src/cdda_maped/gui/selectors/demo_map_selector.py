"""
Demo map selector widget for CDDA-maped.

Provides a UI component for selecting available demo maps.
Minimalist design: icon on the left, selector on the right (Photoshop-style).
"""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from .icon_selector import IconSelector
from ...maps import MapManager


class DemoMapSelector(IconSelector):
    """
    Widget for selecting active demo map.

    Emits demoMapChanged signal when the user selects a different demo map.
    Uses minimalist design with fixed Material Design icon.
    """

    # Signal emitted when demo map changes (demo_id: str)
    demoMapChanged = Signal(str)

    # Fixed icon for demo map selector
    ICON_NAME = "mdi.map"
    SETTINGS_KEY = "demo_map"

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the demo map selector."""
        super().__init__(parent)

        self.map_manager: Optional[MapManager] = None
        self.current_demo_map_id = "default"

        # Connect signals
        self.combo.currentTextChanged.connect(self.on_demo_map_changed)
        self._enable_auto_save()

    def set_map_manager(self, manager: MapManager):
        """Set map manager and populate combo box."""
        self.map_manager = manager
        self.load_demo_maps()

    def load_demo_maps(self):
        """Load available demo maps into combo box."""
        if not self.map_manager:
            return

        try:
            demo_maps = self.map_manager.get_available_demos()

            # Block signals while updating
            self.combo.blockSignals(True)
            self.combo.clear()

            # Add each demo map: display name as text, ID as user data
            for meta in demo_maps:
                self.combo.addItem(meta.name, meta.id)

            self.combo.blockSignals(False)

            if demo_maps:
                # Try to restore saved state, fallback to first item
                if not self.restore_state():
                    # Select first demo and emit signal
                    first_meta = demo_maps[0]
                    self.combo.setCurrentIndex(0)
                    self.current_demo_map_id = first_meta.id
                    self.on_demo_map_changed(first_meta.name)

            self.logger.info(f"Loaded {len(demo_maps)} demo map(s)")

        except Exception as e:
            self.logger.error(f"Failed to load demo maps: {e}")

    def on_demo_map_changed(self, demo_map_name: str):
        """Handle demo map selection change."""
        # Get demo ID from current item's user data
        demo_map_id = self.combo.currentData()

        if demo_map_id and demo_map_id != self.current_demo_map_id:
            self.current_demo_map_id = demo_map_id
            self.logger.debug(f"Demo map changed to: {demo_map_id} ({demo_map_name})")
            self.demoMapChanged.emit(demo_map_id)

    def get_current_demo_map_id(self) -> str:
        """Get the currently selected demo map ID."""
        return self.current_demo_map_id

    def set_current_demo_map_id(self, demo_map_id: str):
        """Set the current demo map programmatically.

        Args:
            demo_map_id: Demo map ID to select
        """
        # Find index by demo ID in user data
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == demo_map_id:
                self.combo.setCurrentIndex(i)
                self.current_demo_map_id = demo_map_id
                break

    def _get_save_value(self) -> Optional[str]:
        """Get demo ID (user data) to save instead of display name."""
        return self.combo.currentData()

    def _restore_value(self, value: str) -> bool:
        """Restore demo map by ID (not by display name).

        Args:
            value: Saved demo ID to restore

        Returns:
            True if value was found and restored, False otherwise
        """
        # Find by user data (demo ID), not by text (display name)
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == value:
                self.combo.setCurrentIndex(i)
                self.current_demo_map_id = value
                return True
        return False
