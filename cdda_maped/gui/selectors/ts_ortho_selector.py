"""
Orthogonal tileset selector widget.

Provides a dropdown for selecting available orthogonal (non-isometric) tilesets.
Filters tilesets to show only those with iso: false.
Minimalist design: icon on the left, selector on the right (Photoshop-style).
"""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from ...tilesets.service import TilesetService
from .icon_selector import IconSelector


class TsOrthoSelector(IconSelector):
    """
    Widget for selecting active orthogonal tileset.

    Provides a combobox with available orthogonal tilesets (iso: false)
    and emits signals on change.
    Uses minimalist design with fixed Material Design icon.
    """

    # Signal emitted when orthogonal tileset is changed (tileset_name: str)
    ts_ortho_changed = Signal(str)

    # Fixed icon for tileset selector
    # ICON_NAME = "mdi.palette"
    ICON_NAME = "mdi.grid"
    SETTINGS_KEY = "tileset"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.tileset_service: Optional[TilesetService] = None

        # Connect signals
        self.combo.currentTextChanged.connect(self.on_tileset_changed)
        self._enable_auto_save()

    def set_tileset_service(self, service: TilesetService):
        """Set tileset service and populate combo box."""
        self.tileset_service = service
        self.load_tilesets()

    def load_tilesets(self):
        """Load available orthogonal tilesets into combo box (iso: false only)."""
        if not self.tileset_service:
            return

        try:
            all_tilesets = self.tileset_service.get_available_tilesets()

            # Filter only orthogonal tilesets (is_iso == False)
            ortho_tilesets: list[str] = []
            for tileset_name in all_tilesets:
                tileset = self.tileset_service.get_tileset(tileset_name)
                if not tileset.is_iso:
                    ortho_tilesets.append(tileset_name)

            # Block signals while updating
            self.combo.blockSignals(True)
            self.combo.clear()
            self.combo.addItems(ortho_tilesets)
            self.combo.blockSignals(False)

            if ortho_tilesets:
                # Try to restore saved state, fallback to preferred tileset
                if not self.restore_state():
                    # Get preferred tileset from settings
                    preferred = (
                        self.tileset_service.get_preferred_tileset(
                            self.settings.default_tileset, is_iso=False
                        )
                        if self.settings
                        else ortho_tilesets[0]
                    )
                    # Find index and select
                    try:
                        index = ortho_tilesets.index(preferred)
                        self.combo.setCurrentIndex(index)
                    except ValueError:
                        # Fallback to first if preferred not in filtered list
                        self.combo.setCurrentIndex(0)
                        preferred = ortho_tilesets[0]
                    self.on_tileset_changed(preferred)

            self.logger.info(
                f"Loaded {len(ortho_tilesets)} orthogonal tilesets (filtered from {len(all_tilesets)} total)"
            )

        except Exception as e:
            self.logger.error(f"Failed to load tilesets: {e}")

    def on_tileset_changed(self, tileset_name: str):
        """Handle tileset selection change."""
        if tileset_name:
            self.ts_ortho_changed.emit(tileset_name)

    def get_current_tileset(self) -> Optional[str]:
        """Get currently selected tileset name."""
        return self.get_current_value()
