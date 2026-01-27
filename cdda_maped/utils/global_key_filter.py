"""
Global key event filter for application-wide keyboard shortcut handling.

Allows keyboard shortcuts to work regardless of which window has focus or
which keyboard layout is active.
"""

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Qt

if TYPE_CHECKING:
    from cdda_maped.gui.main_window import MainWindow


logger = logging.getLogger(__name__)


class GlobalKeyEventFilter(QObject):
    """Global event filter for detecting special keys regardless of keyboard layout.

    This filter operates at the QApplication level, allowing it to intercept
    keyboard events before they reach individual windows. It detects:
    - Backtick key by its physical position (native scan code) for log window toggle
    - F2 key for Object Explorer window toggle

    On Windows:
    - English layout: backtick (`) key
    - Russian layout: ё/Ё key at the same physical position
    - Other layouts: various characters, but same physical position
    - F2 works on all layouts
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initialize the global key filter.

        Args:
            main_window: Reference to the main application window.
        """
        super().__init__()
        self.main_window = main_window

    def eventFilter(self, watched: Any, event: Any) -> bool:
        """Filter events at application level.

        Args:
            watched: The object that the event is associated with.
            event: The event to filter.

        Returns:
            True if the event was handled and should be consumed, False otherwise.
        """
        if event.type() == 6:  # QEvent.KeyPress = 6
            key_event = event
            native_scan_code = key_event.nativeScanCode()
            key = key_event.key()

            # Check for backtick key by scan code 0x29 (standard Windows)
            # This works regardless of keyboard layout
            if native_scan_code == 0x29:
                self.main_window.logger.debug(
                    f"Global backtick detected: scan=0x{native_scan_code:02x}"
                )
                self.main_window.toggle_log_window()
                return True  # Consume the event

            # Check for F2 key (Qt.Key_F2 = 0x01000031 = 16777265)
            if key == Qt.Key.Key_F2:
                self.main_window.logger.debug(
                    f"Global F2 detected: key={key}"
                )
                self.main_window.toggle_object_explorer_window()
                return True  # Consume the event

        return False  # Don't consume other events
