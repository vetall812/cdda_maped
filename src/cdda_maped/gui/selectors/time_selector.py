"""
Time of day selector widget for CDDA-maped.

Provides a UI component for selecting the time of day (hour).
Minimalist design: icon on the left, slider in the middle, time display on the right.
"""

import logging
from typing import Optional, TYPE_CHECKING, cast

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QPalette, QIcon, QPixmap
import qtawesome as qta  # type: ignore

if TYPE_CHECKING:
    from ...settings import AppSettings


class TimeSelector(QWidget):
    """
    Widget for selecting time of day (hour).

    Emits timeChanged signal when the user changes the hour.
    Uses minimalist design with clock icon and slider.
    """

    # Signal emitted when time changes (hour: int, 0-23)
    timeChanged = Signal(int)

    # Fixed icon for time selector
    ICON_NAME = "mdi.clock-outline"
    SETTINGS_KEY = "time"

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the time selector."""
        super().__init__(parent)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.settings: Optional["AppSettings"] = None
        # Suppress saving while restoring programmatic state
        self._is_restoring_state = False

        self.current_hour = 12  # Default: noon

        self._setup_ui()
        self._connect_signals()

        self.logger.debug("TimeSelector initialized")

    def _setup_ui(self):
        """Setup the user interface with minimalist design."""
        # Horizontal layout: icon left, slider middle, time label right
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Clock icon (Material Design, fixed)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._setup_icon()
        layout.addWidget(self.icon_label)

        # Time slider (horizontal, 0-23 hours)
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(23)
        self.time_slider.setValue(self.current_hour)
        self.time_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.time_slider.setTickInterval(6)  # Tick every 6 hours
        self.time_slider.setMinimumWidth(150)
        layout.addWidget(self.time_slider)

        # Time display label
        self.time_label = QLabel()
        self.time_label.setMinimumWidth(50)
        self.time_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._update_time_label()
        layout.addWidget(self.time_label)

    def _setup_icon(self):
        """Setup the fixed clock icon with theme-aware color."""
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

    def _connect_signals(self):
        """Connect slider signals to handlers."""
        self.time_slider.valueChanged.connect(self.on_time_changed)

    def _update_time_label(self):
        """Update the time display label."""
        self.time_label.setText(f"{self.current_hour:02d}:00")

    def on_time_changed(self, hour: int):
        """Handle time slider change (updates UI and emits signal)."""
        if hour != self.current_hour:
            self.current_hour = hour
            self._update_time_label()
            self.timeChanged.emit(hour)
            # Save immediately on change unless restoring programmatically
            if not self._is_restoring_state:
                self.save_state()

    def on_slider_released(self):
        """Deprecated: saving occurs on valueChanged now."""
        self.logger.debug(f"Time changed to: {self.current_hour}:00 (released)")

    def get_current_hour(self) -> int:
        """Get the currently selected hour (0-23)."""
        return self.current_hour

    def set_current_hour(self, hour: int):
        """Set the current hour programmatically."""
        if 0 <= hour <= 23:
            self.time_slider.setValue(hour)
            self.current_hour = hour
            self._update_time_label()
        else:
            self.logger.warning(f"Invalid hour value: {hour} (must be 0-23)")

    def set_settings(self, settings: "AppSettings") -> None:
        """Set AppSettings instance."""
        self.settings = settings

    def save_state(self) -> None:
        """Save current hour to settings."""
        if not self.settings:
            return
        self.settings.settings.setValue(
            f"selectors/{self.SETTINGS_KEY}", self.current_hour
        )
        self.settings.settings.sync()  # Force immediate write to registry
        self.logger.debug(f"Saved {self.SETTINGS_KEY} state: {self.current_hour}")

    def restore_state(self) -> bool:
        """Restore hour from settings.

        Returns:
            True if state was successfully restored, False otherwise
        """
        if not self.settings:
            return False

        saved_value = self.settings.settings.value(
            f"selectors/{self.SETTINGS_KEY}", None
        )
        if saved_value is None:
            self.logger.debug(f"No saved state for {self.SETTINGS_KEY}")
            return False

        try:
            hour = int(cast(str | int, saved_value))
            if 0 <= hour <= 23:
                # Avoid saving while restoring programmatically
                self._is_restoring_state = True
                try:
                    self.set_current_hour(hour)
                finally:
                    self._is_restoring_state = False
                self.logger.info(f"Restored {self.SETTINGS_KEY} state: {hour}")
                return True
            else:
                self.logger.warning(f"Invalid saved hour: {hour} (must be 0-23)")
                return False
        except (ValueError, TypeError):
            self.logger.warning(f"Failed to parse saved hour: {saved_value}")
            return False
