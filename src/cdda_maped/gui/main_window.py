"""
Main application window for CDDA-maped.
"""

import logging
from typing import Optional, Any

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QDockWidget,
    QPushButton,
    QApplication,
)

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QCloseEvent, QShowEvent

from ..settings import AppSettings
from .menu import MenuBuilder
from .layout import DockLayoutBuilder
from ..utils.gui_log_manager import close_gui_log, get_gui_log_manager
from ..utils.global_key_filter import GlobalKeyEventFilter
from ..tilesets.service import TilesetService
from ..game_data.service import GameDataService
from ..resources import get_app_icon
from .object_explorer_window import ObjectExplorerWindow
from .actions import MainWindowActions


class MainWindow(QMainWindow):
    """Main application window."""

    # Menu actions (created by MenuBuilder)
    action_new: QAction
    action_open: QAction
    action_save: QAction
    action_save_as: QAction
    action_exit: QAction
    action_zoom_in: QAction
    action_zoom_out: QAction
    action_zoom_fit: QAction
    action_setup_game_path: QAction
    action_select_mods: QAction
    action_logging_settings: QAction
    action_animation_timeout: QAction
    action_multi_z_level: QAction
    action_show_log: QAction
    action_toggle_object_explorer: QAction
    action_object_explorer_stay_above_main: QAction
    action_reset_layout: QAction
    action_about: QAction

    # Dock widgets (created by DockLayoutManager)
    browser_dock: QDockWidget
    object_browser: Any  # ObjectBrowser
    open_in_object_explorer_button: QPushButton  # Button in browser dock

    def __init__(self, settings: AppSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self.setObjectName("main_window")
        self.settings = settings
        self.current_object_id: Optional[str] = None  # Track currently selected object

        # Initialize managers
        self.menu_builder = MenuBuilder(self)
        self.dock_layout_builder = DockLayoutBuilder(self)
        self.main_window_actions = MainWindowActions(self)

        # Setup UI components
        self.dock_layout_builder.setup_dock_widgets()
        self.menu_builder.setup_actions()
        self.menu_builder.setup_menus()
        self.setup_status_bar()

        # Restore window geometry from settings
        if not self.settings.restore_window_geometry(self):
            # Default size if no saved geometry
            self.resize(1200, 800)

        self.setWindowTitle("CDDA-maped - Visual Map Editor")
        self.setWindowIcon(get_app_icon())

        # Install global key event filter for backtick key handling (layout-independent)
        app = QApplication.instance()
        if app:
            self._key_filter = GlobalKeyEventFilter(self)
            app.installEventFilter(self._key_filter)

        # Initialize services/content after all UI components are ready
        self.setup_demo_content()

        self.logger.info("Main window initialized")

    def showEvent(self, event: QShowEvent) -> None:
        """Handle window show event."""
        super().showEvent(event)
        # Log window hiding is now managed in setup_demo_content

    def setup_status_bar(self) -> None:
        """Setup the status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready - CDDA-maped loaded successfully", 5000)

        # Show configuration info
        QTimer.singleShot(100, self.show_config_info)  # type: ignore

        self.logger.debug("Status bar created")

    def show_config_info(self) -> None:
        """Show configuration information in status bar."""
        cdda_path = (
            self.settings.cdda_path.name if self.settings.cdda_path else "Not set"
        )
        self.status_bar.showMessage(f"CDDA: {cdda_path}", 10000)

    def setup_demo_content(self) -> None:
        """Setup demo content for visualization."""
        if not self.settings.cdda_path:
            self.logger.warning("CDDA path not configured, prompting user")
            # Show main window first so user sees something
            self.show()

            # Show dialog to configure CDDA path on first run
            from PySide6.QtWidgets import QMessageBox

            reply = QMessageBox.question(
                self,
                "CDDA Path Not Set",
                "Welcome to CDDA-maped!\n\n"
                "The path to Cataclysm: Dark Days Ahead is not configured.\n"
                "Would you like to select the game directory now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.main_window_actions.setup_game_path()
                # If path was set successfully, continue loading
                if self.settings.cdda_path:
                    # Recursive call to retry loading with new path
                    # (setup_game_path already calls setup_demo_content, so just return)
                    return

            # User declined or path not set - show main window with message
            self.statusBar().showMessage(
                "CDDA path not set. Use File → Setup Game Path to configure", 10000
            )
            return

        try:
            # Show log window during initialization so user sees progress
            gui_log_manager = get_gui_log_manager()
            if gui_log_manager and gui_log_manager.is_available():
                gui_log_manager.show_window()
                self.logger.info("Log window shown for service initialization")

            # Initialize services with progress updates
            self.logger.info("Initializing services...")

            # Process events to keep GUI responsive
            app = QApplication.instance()
            if app:
                app.processEvents()

            self.tileset_service = TilesetService(
                str(self.settings.cdda_path), self.settings
            )

            if app:
                app.processEvents()

            self.game_data_service = GameDataService(
                str(self.settings.cdda_path), self.settings
            )

            if app:
                app.processEvents()

            # Configure UI components
            self.logger.info("Configuring UI components...")
            self.object_browser.set_game_data_service(self.game_data_service)

            self.logger.info("Services loaded successfully (minimal UI)")

            # Show main window after initialization is complete
            self.logger.info("Showing main window after initialization complete")
            self.show()

            # Show secondary Object Explorer window after main window appears
            self.show_object_explorer_window_if_ready()

            # Hide log window after a delay (optional)
            gui_log_manager = get_gui_log_manager()
            if gui_log_manager and gui_log_manager.is_available():
                gui_log_manager.hide_after_startup(500)

        except Exception as e:
            self.logger.error(f"Failed to setup demo content: {e}")
            # Show error in status bar
            self.statusBar().showMessage(f"Failed to load demo: {e}", 5000)
            # Still show main window even if demo content failed
            self.logger.info("Showing main window despite initialization errors")
            self.show()

            # Try to show Object Explorer if services were initialized
            self.show_object_explorer_window_if_ready()

    def show_object_explorer_window_if_ready(self) -> None:
        """Show Object Explorer window if services are available."""
        try:
            if not hasattr(self, "game_data_service") or not hasattr(
                self, "tileset_service"
            ):
                # Services not ready; skip
                self.logger.debug("ObjectExplorerWindow skipped: services not ready")
                return

            # Create once and reuse
            if not hasattr(self, "object_explorer_window"):
                parent = self if self.settings.explorer_stay_above_main else None
                self.object_explorer_window = ObjectExplorerWindow(
                    settings=self.settings,
                    game_data_service=self.game_data_service,
                    tileset_service=self.tileset_service,
                    parent=parent,
                )

            self.object_explorer_window.show()
            # Enable the toggle action now that window exists
            if hasattr(self, "action_toggle_object_explorer"):
                self.action_toggle_object_explorer.setEnabled(True)
            # Set focus to ortho view
            if (
                hasattr(self.object_explorer_window, "view_ortho")
                and self.object_explorer_window.view_ortho
            ):
                self.object_explorer_window.view_ortho.setFocus()
        except Exception as e:
            self.logger.error(f"Failed to show Object Explorer window: {e}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event to save settings."""
        # Save window geometry and state
        self.settings.save_window_geometry(self)

        # If Object Explorer was created without a parent, close it explicitly.
        if hasattr(self, "object_explorer_window"):
            try:
                self.object_explorer_window.close()
            except Exception:
                pass

        # Close log window if it's open (will save its geometry too)
        close_gui_log()

        self.logger.info("Window geometry saved")
        super().closeEvent(event)
