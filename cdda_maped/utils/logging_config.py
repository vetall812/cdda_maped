"""
Logging configuration for CDDA-maped.
"""

import logging
import logging.handlers
from pathlib import Path
from collections import deque
from typing import Optional, List, Callable, Union

from PySide6.QtCore import QObject, Signal
from ..settings import AppSettings


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветным выводом для консоли."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        # Получаем цвет для уровня
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # Применяем базовое форматирование
        formatted = super().format(record)

        # Добавляем цвет только к уровню логирования
        if record.levelname in formatted:
            formatted = formatted.replace(
                record.levelname, f"{color}{record.levelname}{reset}"
            )

        return formatted


class CSVFormatter(logging.Formatter):
    """CSV-безопасный форматтер для файлового логирования."""

    def format(self, record: logging.LogRecord) -> str:
        # Получаем базовые значения
        timestamp = self.formatTime(record, self.datefmt)
        level = record.levelname.ljust(8)  # Выравниваем по ширине
        duration = f"{int(record.relativeCreated)} ms"
        module = record.name
        line_no = str(record.lineno)
        message = record.getMessage()

        # Экранируем кавычки в сообщении (стандартный CSV способ)
        message = message.replace('"', '""')

        # Формируем CSV строку с кавычками
        return f'"{timestamp}";{level};"{duration}";"{module}";"{line_no}";"{message}"'


class GuiLogFormatter(logging.Formatter):
    """Formatter for GUI log display - similar to CSV but with module/line after message."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record similar to CSV format."""
        # Получаем базовые значения
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S").ljust(20)
        level = record.levelname.ljust(8)  # Выравниваем по ширине
        duration = f"{int(record.relativeCreated)} ms".ljust(15)
        message = record.getMessage().ljust(100)
        line_no = str(record.lineno)
        module = record.name

        # Формируем строку: timestamp, level, duration, message, module, line
        return f"{timestamp}: {level}: {duration}: {message}: {module}:{line_no}"


class GuiLogHandler(logging.Handler):
    """
    Log handler that emits log records for GUI display.
    Uses Qt signals to safely pass log records from any thread to GUI thread.
    """

    def __init__(self, max_lines: int = 1000):
        super().__init__()
        self.max_lines = max_lines
        self.buffer: deque[logging.LogRecord] = deque(maxlen=max_lines)
        self.log_emitter: Optional["LogEmitter"] = None
        self.log_callback: Optional[Callable[[logging.LogRecord, str], None]] = None
        self.error_callback: Optional[Callable[[logging.LogRecord, str], None]] = None

        # Always capture DEBUG and above for buffer, but let GUI decide what to show
        super().setLevel(logging.DEBUG)
        self.display_level = logging.INFO  # Default display level

        # Lazy-create LogEmitter (requires QApplication)
        try:
            self.log_emitter = LogEmitter()
        except Exception:
            # QApplication not available yet - will be created lazily later
            pass

    def setLevel(self, level: Union[int, str]) -> None:
        """Override setLevel to always capture DEBUG+ but store display level preference."""
        # Always capture everything for buffer
        super().setLevel(logging.DEBUG)
        # Store the requested level for GUI display (but don't use it here)
        self.display_level = level  # type: ignore[assignment]

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record for GUI display."""
        try:
            # Format the record
            msg = self.format(record)

            # Add to buffer
            self.buffer.append(record)

            # Use callbacks if Qt not available
            if self.log_callback:
                self.log_callback(record, msg)

            # Check for ERROR level
            if record.levelno >= logging.ERROR and self.error_callback:
                self.error_callback(record, msg)

            # Emit Qt signal if available
            if self.log_emitter:
                self.log_emitter.log_received.emit(record, msg)  # type: ignore

                if record.levelno >= logging.ERROR:
                    self.log_emitter.error_occurred.emit(record, msg)  # type: ignore

        except Exception:
            # Don't let logging errors crash the application
            self.handleError(record)

    def get_buffer(self) -> List[logging.LogRecord]:
        """Get current log buffer as a list."""
        return list(self.buffer)

    def clear_buffer(self) -> None:
        """Clear the log buffer."""
        self.buffer.clear()

    def set_log_callback(
        self, callback: Callable[[logging.LogRecord, str], None]
    ) -> None:
        """Set callback for log messages (fallback if Qt not available)."""
        self.log_callback = callback

    def set_error_callback(
        self, callback: Callable[[logging.LogRecord, str], None]
    ) -> None:
        """Set callback for error messages (fallback if Qt not available)."""
        self.error_callback = callback


class LogEmitter(QObject):
    """Qt object for emitting log signals safely across threads."""

    log_received = Signal(logging.LogRecord, str)
    error_occurred = Signal(logging.LogRecord, str)


def setup_logging(settings: "AppSettings") -> None:
    """
    Setup application logging with console, file, and GUI handlers.

    Initializes singleton GUI logging automatically.

    Args:
        settings: AppSettings instance for all logging configuration
    """
    # Get settings
    console_enabled = settings.console_logging
    console_level = settings.console_log_level
    use_colors = settings.console_use_colors
    file_enabled = settings.file_logging
    log_file = settings.log_file_path
    gui_level = settings.gui_log_level
    gui_max_lines = settings.gui_max_lines

    # Configure root logger to capture everything
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Root captures all levels

    # But set our project logger to be more verbose
    cdda_logger = logging.getLogger("cdda_maped")
    cdda_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler - only if enabled
    if console_enabled:
        if use_colors:
            console_formatter = ColoredFormatter(
                fmt="%(asctime)s : %(levelname)-8s : %(message)s", datefmt="%H:%M:%S"
            )  # type: ignore[assignment]
        else:
            console_formatter = logging.Formatter(  # type: ignore[assignment]
                fmt="%(asctime)s : %(levelname)-8s : %(message)s", datefmt="%H:%M:%S"
            )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation - only if enabled
    log_path = None
    if file_enabled:
        try:
            # CSV formatter for file - structured data with semicolon separator
            log_path = Path(log_file)
            log_path.parent.mkdir(exist_ok=True)
            detailed_formatter = CSVFormatter(datefmt="%Y-%m-%d %H:%M:%S")

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",  # Fix encoding for Russian text
            )
            file_handler.setLevel(logging.DEBUG)  # File always captures DEBUG
            file_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, just continue with console logging
            root_logger.warning(f"Could not setup file logging: {e}")

    # Suppress DEBUG logs from noisy libraries
    logging.getLogger("PIL").setLevel(logging.INFO)
    logging.getLogger("PIL.PngImagePlugin").setLevel(logging.INFO)
    logging.getLogger("PIL.JpegImagePlugin").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("requests").setLevel(logging.INFO)

    # GUI handler - always enabled
    gui_handler = None
    try:
        gui_handler = GuiLogHandler(max_lines=gui_max_lines)
        gui_formatter = GuiLogFormatter()
        gui_handler.setFormatter(gui_formatter)
        gui_handler.setLevel(getattr(logging, gui_level.upper(), logging.INFO))
        root_logger.addHandler(gui_handler)
    except Exception as e:
        # If GUI logging fails, continue without it
        logging.getLogger(__name__).warning(f"Could not setup GUI logging: {e}")

    # Initialize singleton GUI logging
    if gui_handler:
        try:
            from .gui_log_manager import GuiLogManager

            GuiLogManager.initialize(settings, gui_handler)
            logger = logging.getLogger(__name__)
            logger.debug("Singleton GUI logging initialized")
        except ImportError:
            # GUI components not available
            pass

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized")
    if console_enabled:
        logger.debug(f"Console logging: {console_level} (colors: {use_colors})")
    if file_enabled and log_path:
        logger.debug(f"File logging: DEBUG at {log_path.absolute()}")
    logger.debug(f"GUI logging: {gui_level}")
