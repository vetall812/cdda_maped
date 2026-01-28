"""
Base icon selector widget for CDDA-maped.

Provides a minimalist selector with icon on left, combobox on right (Photoshop-style).
"""

import logging
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPalette, QIcon, QPixmap
import qtawesome as qta  # type: ignore

if TYPE_CHECKING:
    from ...settings import AppSettings


class IconSelector(QWidget):
    """
    Base class for minimalist icon+combobox selectors.

    Provides:
    - Fixed Material Design icon on the left
    - QComboBox on the right
    - Theme-aware icon coloring
    - Signal emission on selection change

    Subclasses should:
    - Define ICON_NAME class attribute (Material Design icon name)
    - Define selectionChanged signal
    - Populate combobox in __init__ after calling super().__init__()
    """

    # To be defined in subclasses
    ICON_NAME: str = ""
    # Settings key for this selector (e.g., "tileset", "season", "time", "weather")
    SETTINGS_KEY: str = ""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the icon selector."""
        super().__init__(parent)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.settings: Optional["AppSettings"] = None
        self._auto_save_enabled = False
        self._auto_save_connected = False
        # Suppress auto-saving while restoring state to avoid redundant writes
        self._is_restoring_state = False

        self._setup_ui()

        self.logger.debug(f"{self.__class__.__name__} initialized")

    def _setup_ui(self):
        """Setup the user interface with minimalist design."""
        # Horizontal layout: icon left, combo right
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Icon label (Material Design, fixed icon)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._setup_icon()
        layout.addWidget(self.icon_label)

        # Combo box
        self.combo = QComboBox()
        self.combo.setMinimumWidth(100)
        layout.addWidget(self.combo)

    def _setup_icon(self):
        """Setup the fixed icon with theme-aware color."""
        if not self.ICON_NAME:
            self.logger.warning(f"{self.__class__.__name__}: ICON_NAME not defined")
            return

        try:
            # Get color from current palette (theme-aware)
            icon_color = self.palette().color(QPalette.ColorRole.WindowText)
            icon: QIcon = QIcon(qta.icon(self.ICON_NAME, color=icon_color))  # type: ignore[arg-type]
            pixmap: QPixmap = icon.pixmap(QSize(20, 20))
            if not pixmap.isNull():
                self.icon_label.setPixmap(pixmap)
            else:
                self.logger.warning(
                    f"Failed to create pixmap from icon {self.ICON_NAME}"
                )
        except Exception as e:
            self.logger.warning(f"Failed to load icon {self.ICON_NAME}: {e}")

    def get_current_value(self) -> Optional[str]:
        """Get currently selected value."""
        return self.combo.currentText() or None

    def get_current_data(self) -> Optional[str]:
        """Get currently selected item's user data."""
        return self.combo.currentData()

    def set_settings(self, settings: "AppSettings") -> None:
        """Set AppSettings instance and enable auto-save."""
        self.settings = settings
        self._auto_save_enabled = True
        self._enable_auto_save()  # Connect signal for auto-saving

    def save_state(self) -> None:
        """Save current selection to settings (if settings available)."""
        if not self.settings or not self.SETTINGS_KEY:
            return
        current_value = self._get_save_value()
        if current_value is not None:
            self.settings.settings.setValue(
                f"selectors/{self.SETTINGS_KEY}", current_value
            )
            self.settings.settings.sync()  # Force immediate write to registry
            self.logger.debug(f"Saved {self.SETTINGS_KEY} state: {current_value}")

    def restore_state(self) -> bool:
        """Restore selection from settings.

        Returns:
            True if state was successfully restored, False otherwise
        """
        if not self.settings or not self.SETTINGS_KEY:
            return False

        saved_value = self.settings.settings.value(
            f"selectors/{self.SETTINGS_KEY}", None
        )
        if saved_value is None:
            self.logger.debug(f"No saved state for {self.SETTINGS_KEY}")
            return False

        # Try to restore the value
        self._is_restoring_state = True
        try:
            success = self._restore_value(str(saved_value))
            if success:
                self.logger.info(f"Restored {self.SETTINGS_KEY} state: {saved_value}")
                # Emit change signal manually since currentTextChanged may not fire
                # if the value was already set during initialization
                current_text = self.combo.currentText()
                if current_text:
                    self.combo.currentTextChanged.emit(current_text)
            else:
                self.logger.warning(
                    f"Failed to restore {self.SETTINGS_KEY} state: {saved_value} (value not available)"
                )
            return success
        finally:
            self._is_restoring_state = False

    def _get_save_value(self) -> Optional[str]:
        """Get value to save. Override in subclasses if needed."""
        return self.combo.currentText() or None

    def _restore_value(self, value: str) -> bool:
        """Restore value from settings. Override in subclasses if needed.

        Args:
            value: Saved value to restore

        Returns:
            True if value was found and restored, False otherwise
        """
        # Try to find and select the value in combo
        index = self.combo.findText(value)
        if index >= 0:
            # Avoid emitting signals during programmatic selection; we'll emit manually
            self.combo.blockSignals(True)
            self.combo.setCurrentIndex(index)
            self.combo.blockSignals(False)
            return True
        return False

    def _enable_auto_save(self) -> None:
        """Connect signal for auto-saving on change."""
        if self._auto_save_enabled and not self._auto_save_connected:
            self.combo.currentTextChanged.connect(self._on_auto_save)
            self._auto_save_connected = True

    def _on_auto_save(self) -> None:
        """Auto-save handler."""
        # Skip saving if we are in the middle of restoring state
        if self._is_restoring_state:
            return
        if self._auto_save_enabled:
            self.save_state()
