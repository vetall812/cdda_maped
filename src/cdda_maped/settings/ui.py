"""
UI-related settings for CDDA-maped.
"""

from typing import Union, TYPE_CHECKING, Any

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QWidget, QMainWindow

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings


class UISettings:
    """Manages UI-related settings."""

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

    def get_explorer_stay_above_main(self) -> bool:
        """Whether Object Explorer should stay above the main window."""
        return self._get_bool("explorer/stay_above_main", False)

    def set_explorer_stay_above_main(self, value: bool) -> None:
        """Persist 'stay above main window' option for Object Explorer."""
        self.settings.setValue("explorer/stay_above_main", bool(value))
        self.settings.sync()

    def save_window_geometry(self, widget: Union[QWidget, QMainWindow]) -> None:
        """Save window geometry and state."""
        if hasattr(widget, "saveGeometry"):
            self.settings.setValue("ui/window_geometry", widget.saveGeometry())
        # Only QMainWindow has saveState
        if isinstance(widget, QMainWindow):
            self.settings.setValue("ui/window_state", widget.saveState())
        self.settings.sync()

    def save_explorer_window_geometry(
        self, widget: Union[QWidget, QMainWindow]
    ) -> None:
        """Save object explorer window geometry and state."""
        if hasattr(widget, "saveGeometry"):
            self.settings.setValue("explorer/window_geometry", widget.saveGeometry())
        if isinstance(widget, QMainWindow):
            self.settings.setValue("explorer/window_state", widget.saveState())
        self.settings.sync()

    def restore_window_geometry(self, widget: Union[QWidget, QMainWindow]) -> bool:
        """Restore window geometry and state. Returns True if restored."""
        geometry: Any = self.settings.value("ui/window_geometry")
        state: Any = self.settings.value("ui/window_state")

        restored = False
        if geometry and hasattr(widget, "restoreGeometry"):
            # Ensure it's QByteArray
            if isinstance(geometry, bytes):
                geometry = QByteArray(geometry)
            elif not isinstance(geometry, QByteArray):
                # Try to convert from string or other format
                try:
                    geometry = QByteArray(bytes(geometry))
                except (TypeError, ValueError):
                    geometry = None

            if geometry:
                widget.restoreGeometry(geometry)
                restored = True

        if state and isinstance(widget, QMainWindow):
            # Ensure it's QByteArray
            if isinstance(state, bytes):
                state = QByteArray(state)
            elif not isinstance(state, QByteArray):
                try:
                    state = QByteArray(bytes(state))
                except (TypeError, ValueError):
                    state = None

            if state:
                widget.restoreState(state)
                restored = True

        return restored

    def restore_explorer_window_geometry(
        self, widget: Union[QWidget, QMainWindow]
    ) -> bool:
        """Restore object explorer window geometry/state. Returns True if restored."""
        geometry: Any = self.settings.value("explorer/window_geometry")
        state: Any = self.settings.value("explorer/window_state")

        # Fallback to legacy keys if new ones are absent (backward compatibility)
        if geometry is None and state is None:
            geometry = self.settings.value("ui/window_geometry")
            state = self.settings.value("ui/window_state")

        restored = False
        if geometry and hasattr(widget, "restoreGeometry"):
            if isinstance(geometry, bytes):
                geometry = QByteArray(geometry)
            elif not isinstance(geometry, QByteArray):
                try:
                    geometry = QByteArray(bytes(geometry))
                except (TypeError, ValueError):
                    geometry = None
            if geometry:
                restored = widget.restoreGeometry(geometry) or restored

        if state and isinstance(widget, QMainWindow):
            if isinstance(state, bytes):
                state = QByteArray(state)
            elif not isinstance(state, QByteArray):
                try:
                    state = QByteArray(bytes(state))
                except (TypeError, ValueError):
                    state = None
            if state:
                restored = widget.restoreState(state) or restored

        return restored

    def save_log_window_geometry(self, widget: Union[QWidget, QMainWindow]) -> None:
        """Save log window geometry (separate from main window)."""
        if hasattr(widget, "saveGeometry"):
            self.settings.setValue("ui/log_window_geometry", widget.saveGeometry())
        self.settings.sync()

    def restore_log_window_geometry(self, widget: Union[QWidget, QMainWindow]) -> bool:
        """Restore log window geometry. Returns True if restored."""
        geometry: Any = self.settings.value("ui/log_window_geometry")

        if geometry and hasattr(widget, "restoreGeometry"):
            # Ensure it's QByteArray
            if isinstance(geometry, bytes):
                geometry = QByteArray(geometry)
            elif not isinstance(geometry, QByteArray):
                # Try to convert from string or other format
                try:
                    geometry = QByteArray(bytes(geometry))
                except (TypeError, ValueError):
                    geometry = None

            if geometry:
                widget.restoreGeometry(geometry)
                return True

        return False

    @property
    def theme(self) -> str:
        """Get UI theme name."""
        return self._get_str("ui/theme", "system")

    @theme.setter
    def theme(self, value: str) -> None:
        """Set UI theme name."""
        self.settings.setValue("ui/theme", value)
        self.settings.sync()
