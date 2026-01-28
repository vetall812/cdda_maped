"""
Zoom level selector widget for CDDA-maped.

Provides discrete zoom control with predefined steps.
Minimalist design: icon, slider, zoom label.
"""

import logging
from typing import Optional, TYPE_CHECKING, cast

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QPalette, QIcon, QPixmap
import qtawesome as qta  # type: ignore

if TYPE_CHECKING:
    from ...settings import AppSettings


class ZoomSelector(QWidget):
    """Widget for selecting zoom level with discrete steps."""

    zoomChanged = Signal(float)

    ICON_NAME = "mdi.magnify-plus-outline"
    SETTINGS_KEY = "zoom"
    ZOOM_LEVELS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
    DEFAULT_INDEX = 2  # 1.0x

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.settings: Optional["AppSettings"] = None
        self._is_restoring_state = False
        self.current_index = self.DEFAULT_INDEX

        self._setup_ui()
        self._connect_signals()

        self.logger.debug("ZoomSelector initialized")

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._setup_icon()
        layout.addWidget(self.icon_label)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(0)
        self.zoom_slider.setMaximum(len(self.ZOOM_LEVELS) - 1)
        self.zoom_slider.setValue(self.DEFAULT_INDEX)
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom_slider.setTickInterval(1)
        self.zoom_slider.setMinimumWidth(140)
        layout.addWidget(self.zoom_slider)

        self.zoom_label = QLabel()
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._update_zoom_label()
        layout.addWidget(self.zoom_label)

    def _setup_icon(self) -> None:
        """Setup zoom icon respecting current palette."""
        try:
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

    def _connect_signals(self) -> None:
        self.zoom_slider.valueChanged.connect(self.on_zoom_index_changed)

    def _update_zoom_label(self) -> None:
        self.zoom_label.setText(self._format_zoom_label(self.get_current_zoom()))

    def _format_zoom_label(self, zoom: float) -> str:
        if zoom >= 1:
            return f"{zoom:.1f}x" if zoom % 1 else f"{int(zoom)}x"
        return f"{zoom:.2f}x"

    def on_zoom_index_changed(self, index: int) -> None:
        if index != self.current_index:
            self.current_index = index
        self._update_zoom_label()
        zoom = self.get_current_zoom()
        self.zoomChanged.emit(zoom)
        if not self._is_restoring_state:
            self.save_state()

    def get_current_zoom(self) -> float:
        return self.ZOOM_LEVELS[self.zoom_slider.value()]

    def get_current_index(self) -> int:
        return self.zoom_slider.value()

    def set_zoom_index(self, index: int) -> None:
        if 0 <= index < len(self.ZOOM_LEVELS):
            self.zoom_slider.setValue(index)

    def set_current_zoom(self, zoom: float) -> None:
        closest_index = min(
            range(len(self.ZOOM_LEVELS)),
            key=lambda i: abs(self.ZOOM_LEVELS[i] - zoom),
        )
        self.set_zoom_index(closest_index)

    def set_settings(self, settings: "AppSettings") -> None:
        self.settings = settings

    def save_state(self) -> None:
        if not self.settings:
            return
        zoom_value = self.get_current_zoom()
        self.settings.settings.setValue(f"selectors/{self.SETTINGS_KEY}", zoom_value)
        self.settings.settings.sync()
        self.logger.debug(f"Saved {self.SETTINGS_KEY} state: {zoom_value}")

    def restore_state(self) -> bool:
        if not self.settings:
            return False

        saved_value = self.settings.settings.value(
            f"selectors/{self.SETTINGS_KEY}", None
        )
        if saved_value is None:
            self.logger.debug(f"No saved state for {self.SETTINGS_KEY}")
            return False

        try:
            zoom_value = float(cast(str | float, saved_value))
            self._is_restoring_state = True
            try:
                self.set_current_zoom(zoom_value)
            finally:
                self._is_restoring_state = False
            self.logger.info(f"Restored {self.SETTINGS_KEY} state: {zoom_value}")
            return True
        except (ValueError, TypeError):
            self.logger.warning(f"Failed to parse saved zoom: {saved_value}")
            return False
