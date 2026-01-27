"""
Main entry point for CDDA-maped application.
Usage: python -m cdda_maped
"""

import sys
import logging
from typing import Optional

from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .settings import AppSettings
from .gui.main_window import MainWindow
from .utils.gui_log_manager import get_gui_log_manager
from .utils.logging_config import setup_logging
from .resources.style_manager import style_manager
from .resources import get_app_icon


def show_error_dialog(title: str, message: str, details: Optional[str] = None) -> None:
    """Show error dialog to user."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)

    if details:
        msg_box.setDetailedText(details)

    msg_box.exec()


def main() -> int:
    """Main application entry point."""
    logger = logging.getLogger(f"{__name__}.main")
    try:
        # Load configuration first
        settings = AppSettings()

        # Create Qt application first (required for GUI logging)
        app = QApplication(sys.argv)
        app.setApplicationName("cdda_maped")
        app.setApplicationVersion(__version__)
        app.setOrganizationName("vetall812")
        app.setWindowIcon(get_app_icon())

        # Setup logging with GUI enabled if configured (singleton initialized automatically)
        setup_logging(settings)

        logger.info("Starting CDDA-maped application")
        logger.info(f"Configuration loaded from {settings.get_settings_file_path()}")

        # Validate settings on startup
        validation = settings.validate()
        if validation.warnings:
            logger.warning("Configuration warnings detected:")
            for warning in validation.warnings:
                logger.warning(f"  {warning}")

        if not validation.is_valid:
            logger.error("Configuration validation failed:")
            for error in validation.errors:
                logger.error(f"  {error}")
            show_error_dialog(
                "Configuration Error",
                "Configuration validation failed. Please check your settings.",
                "\n".join(validation.errors),
            )
            return 1

        # Get singleton GUI log manager
        gui_log_manager = get_gui_log_manager()
        if gui_log_manager and gui_log_manager.is_available():
            logger.info("GUI logging initialized")
        else:
            logger.info("GUI logging disabled")

        # Apply Qt Fusion theme with automatic light/dark adaptation
        app.setStyle("Fusion")
        logger.debug("Applied Qt Fusion theme with automatic system adaptation")

        # Show only log window during initialization
        if gui_log_manager and gui_log_manager.is_available():
            gui_log_manager.show_window()
            logger.debug("Log window shown at startup")
        else:
            logger.error("Log window not available to show at startup")

        # Apply application styles
        style_manager.apply_app_style(app, "main")

        # Create main window but don't show it yet (no log_manager parameter needed!)
        logger.info("Creating main window...")
        _main_window = MainWindow(settings)  # Keep reference alive for Qt event loop

        # Main window will show itself after demo content is loaded
        logger.info("Main window created, waiting for initialization to complete...")

        logger.info("Application started successfully")
        return app.exec()

    except Exception as e:
        logger.exception("Unhandled exception in main")
        show_error_dialog("Application Error", "An unexpected error occurred.", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
