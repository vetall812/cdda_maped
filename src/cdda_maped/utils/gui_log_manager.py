"""
Singleton GUI log manager for CDDA-maped.

Provides global access to GUI logging functionality, following the same
pattern as console and file logging.
"""

import logging
from typing import Optional
from PySide6.QtCore import QTimer

from .log_window import LogWindow
from ..settings import AppSettings
from .logging_config import GuiLogHandler


class GuiLogManager:
    """
    Singleton GUI log manager that provides global access to GUI logging,
    similar to how console and file logging work globally.
    """

    _instance: Optional["GuiLogManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "GuiLogManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if GuiLogManager._initialized:
            return
        GuiLogManager._initialized = True

        self.gui_handler: Optional["GuiLogHandler"] = None
        self.log_window: Optional["LogWindow"] = None
        self._settings: Optional["AppSettings"] = None

    @classmethod
    def initialize(
        cls, settings: "AppSettings", gui_handler: Optional["GuiLogHandler"] = None
    ) -> "GuiLogManager":
        """
        Initialize the singleton with settings and optional existing handler.
        Should be called once during application startup.
        """
        instance = cls()
        instance._settings = settings

        if settings.gui_logging:
            instance._setup_gui_logging(gui_handler)

        return instance

    @classmethod
    def instance(cls) -> Optional["GuiLogManager"]:
        """Get the singleton instance. Returns None if not initialized."""
        return cls._instance if cls._initialized else None

    def _setup_gui_logging(self, existing_handler: Optional["GuiLogHandler"] = None):
        """Setup GUI logging components."""
        if not self._settings:
            return

        from .logging_config import GuiLogHandler, GuiLogFormatter

        # Don't create log_window here - defer until first use (when QApplication exists)
        # self.log_window will be created on-demand in show_window()

        # Use existing handler or create new one
        if existing_handler:
            self.gui_handler = existing_handler
        else:
            self.gui_handler = GuiLogHandler(max_lines=self._settings.gui_max_lines)
            gui_formatter = GuiLogFormatter()
            self.gui_handler.setFormatter(gui_formatter)
            display_level = getattr(logging, self._settings.gui_log_level, logging.INFO)
            self.gui_handler.setLevel(display_level)

            # Add to root logger (like console/file handlers)
            root_logger = logging.getLogger()
            root_logger.addHandler(self.gui_handler)

        # Connect error handler signals if emitter is available
        # (window connection happens lazily in show_window)
        if self.gui_handler and self.gui_handler.log_emitter:
            self.gui_handler.log_emitter.error_occurred.connect(  # type: ignore
                self._on_error_occurred
            )

    def _load_buffer_history(self):
        """Load existing messages from handler buffer to window."""
        if not self.gui_handler or not self.log_window:
            return

        buffer = self.gui_handler.get_buffer()
        if buffer and self.gui_handler.formatter:
            logger = logging.getLogger(__name__)
            logger.debug(f"Loading {len(buffer)} messages from buffer to GUI window")

            for record in buffer:
                formatted_msg = self.gui_handler.formatter.format(record)
                self.log_window.add_log_message(record, formatted_msg)

    def show_window(self) -> None:
        """Show log window if available. Creates it on-demand if needed."""
        # Lazy-initialize LogWindow (only when QApplication exists)
        if not self.log_window and self._settings:
            try:
                from .log_window import LogWindow

                display_level = getattr(
                    logging, self._settings.gui_log_level, logging.INFO
                )
                self.log_window = LogWindow(self._settings)
                self.log_window.current_filter_level = display_level

                # Connect handler to window
                if self.gui_handler and self.gui_handler.log_emitter:
                    self.gui_handler.log_emitter.log_received.connect(
                        self.log_window.add_log_message
                    )

                # Load buffer history after window creation
                self._load_buffer_history()
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create log window: {e}")
                return

        if self.log_window:
            self.log_window.show_and_raise()

    def hide_window(self) -> None:
        """Hide log window if available."""
        if self.log_window:
            self.log_window.hide()

    def close_window(self) -> None:
        """Close log window (with saveGeometry). Used when main app is closing."""
        if self.log_window:
            self.log_window.close()

    def toggle_window(self) -> None:
        """Toggle log window visibility."""
        if self.log_window:
            if self.log_window.isVisible():
                self.hide_window()
            else:
                self.show_window()

    def is_available(self) -> bool:
        """Check if GUI logging is available (initialized)."""
        return self.gui_handler is not None

    def is_window_visible(self) -> bool:
        """Check if log window is visible."""
        return self.log_window.isVisible() if self.log_window else False

    def show_on_startup(self) -> None:
        """Show log window on application startup if configured."""
        if not self._settings or not self._settings.gui_show_on_startup:
            return

        logger = logging.getLogger(__name__)
        logger.debug("Showing log window on startup")
        self.show_window()

    def hide_after_startup(self, delay_ms: int = 3000) -> None:
        """Hide log window after startup delay."""
        if self.log_window and self.log_window.isVisible():
            QTimer.singleShot(delay_ms, self.hide_window)  # type: ignore

    def _on_error_occurred(
        self, record: logging.LogRecord, formatted_message: str
    ) -> None:
        """Handle ERROR/CRITICAL log messages."""
        if not self._settings or not self._settings.gui_show_on_error:
            return

        if self.log_window:
            # Show window if it's hidden
            if not self.log_window.isVisible():
                self.show_window()

            # Focus window if configured
            if self._settings.gui_focus_on_error:
                self.log_window.show_and_focus()

    def get_log_buffer(self) -> list[logging.LogRecord]:
        """Get current log buffer from handler."""
        if self.gui_handler:
            return self.gui_handler.get_buffer()
        return []

    def clear_log_buffer(self) -> None:
        """Clear the log buffer."""
        if self.gui_handler:
            self.gui_handler.clear_buffer()
        if self.log_window:
            self.log_window.clear_logs()

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.gui_handler:
            # Remove handler from logger
            root_logger = logging.getLogger()
            root_logger.removeHandler(self.gui_handler)
            self.gui_handler = None

        if self.log_window:
            self.log_window.hide()
            self.log_window = None


# Convenience functions for global access (like logging.getLogger)
def get_gui_log_manager() -> Optional[GuiLogManager]:
    """Get the GUI log manager instance. Returns None if not available."""
    return GuiLogManager.instance()


def show_gui_log() -> None:
    """Show GUI log window if available."""
    manager = get_gui_log_manager()
    if manager:
        manager.show_window()


def hide_gui_log() -> None:
    """Hide GUI log window if available."""
    manager = get_gui_log_manager()
    if manager:
        manager.hide_window()


def close_gui_log() -> None:
    """Close GUI log window (saves geometry). Used when main app is closing."""
    manager = get_gui_log_manager()
    if manager:
        manager.close_window()


def toggle_gui_log() -> None:
    """Toggle GUI log window visibility."""
    manager = get_gui_log_manager()
    if manager:
        manager.toggle_window()


def is_gui_log_available() -> bool:
    """Check if GUI logging is available."""
    manager = get_gui_log_manager()
    return manager.is_available() if manager else False


def is_gui_log_visible() -> bool:
    """Check if GUI log window is visible."""
    manager = get_gui_log_manager()
    return manager.is_window_visible() if manager else False
