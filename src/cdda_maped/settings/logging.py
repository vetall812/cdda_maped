"""
Logging-related settings for CDDA-maped.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)

# Константа для пути к логу
LOG_FILE_PATH = "logs/cdda_maped.csv"


class LoggingSettings:
    """Manages logging-related settings."""

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

    # === CONSOLE LOGGING SETTINGS ===

    @property
    def console_logging(self) -> bool:
        """Check if console logging is enabled."""
        return self._get_bool("logging/console_enabled", False)

    @console_logging.setter
    def console_logging(self, value: bool) -> None:
        """Set console logging enabled state."""
        self.settings.setValue("logging/console_enabled", value)
        self.settings.sync()

    @property
    def console_log_level(self) -> str:
        """Get console logging level."""
        return self._get_str("logging/console_level", "INFO")

    @console_log_level.setter
    def console_log_level(self, value: str) -> None:
        """Set console logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if value.upper() in valid_levels:
            self.settings.setValue("logging/console_level", value.upper())
            self.settings.sync()
        else:
            logger.warning(
                f"Invalid console log level: {value}, keeping current: {self.console_log_level}"
            )

    @property
    def console_use_colors(self) -> bool:
        """Check if console should use colors."""
        return self._get_bool("logging/console_use_colors", True)

    @console_use_colors.setter
    def console_use_colors(self, value: bool) -> None:
        """Set console color usage."""
        self.settings.sync()
        self.settings.setValue("logging/console_use_colors", value)

    # === FILE LOGGING SETTINGS ===

    @property
    def file_logging(self) -> bool:
        """Check if file logging is enabled."""
        return self._get_bool("logging/file_enabled", False)

    @file_logging.setter
    def file_logging(self, value: bool) -> None:
        """Set file logging enabled state."""
        self.settings.setValue("logging/file_enabled", value)

    @property
    def log_file_path(self) -> str:
        """Get log file path (read-only, always returns constant)."""
        return LOG_FILE_PATH

    @property
    def log_file_absolute_path(self) -> Path:
        """Get absolute path to log file."""
        return Path(LOG_FILE_PATH).resolve()

    # === GUI LOGGING SETTINGS ===

    @property
    def gui_logging(self) -> bool:
        """Check if GUI logging is enabled (always True)."""
        return True  # GUI logging always enabled

    @property
    def gui_log_level(self) -> str:
        """Get GUI logging level."""
        return self._get_str("logging/gui_level", "INFO")

    @gui_log_level.setter
    def gui_log_level(self, value: str) -> None:
        """Set GUI logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if value.upper() in valid_levels:
            self.settings.setValue("logging/gui_level", value.upper())
        else:
            logger.warning(
                f"Invalid GUI log level: {value}, keeping current: {self.gui_log_level}"
            )

    @property
    def gui_show_on_startup(self) -> bool:
        """Check if GUI log window should show on startup."""
        return self._get_bool("logging/gui_show_on_startup", True)

    @gui_show_on_startup.setter
    def gui_show_on_startup(self, value: bool) -> None:
        """Set GUI log window show on startup."""
        self.settings.setValue("logging/gui_show_on_startup", value)

    @property
    def gui_show_on_error(self) -> bool:
        """Check if GUI log window should show on errors."""
        return self._get_bool("logging/gui_show_on_error", True)

    @gui_show_on_error.setter
    def gui_show_on_error(self, value: bool) -> None:
        """Set GUI log window show on error."""
        self.settings.setValue("logging/gui_show_on_error", value)

    @property
    def gui_focus_on_error(self) -> bool:
        """Check if GUI log window should gain focus on errors."""
        return self._get_bool("logging/gui_focus_on_error", True)

    @gui_focus_on_error.setter
    def gui_focus_on_error(self, value: bool) -> None:
        """Set GUI log window focus on error."""
        self.settings.setValue("logging/gui_focus_on_error", value)

    @property
    def gui_max_lines(self) -> int:
        """Get maximum number of lines to keep in GUI log buffer."""
        value = self.settings.value("logging/gui_max_lines", 1000)
        try:
            return int(str(value)) if value is not None else 1000
        except (ValueError, TypeError):
            return 1000

    @gui_max_lines.setter
    def gui_max_lines(self, value: int) -> None:
        """Set maximum number of lines in GUI log buffer."""
        if value > 0:
            self.settings.setValue("logging/gui_max_lines", value)
        else:
            logger.warning(
                f"Invalid GUI max lines: {value}, keeping current: {self.gui_max_lines}"
            )
