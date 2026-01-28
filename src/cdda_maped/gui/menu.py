"""
Menu builder for main application window.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenuBar
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from .main_window import MainWindow


class MenuBuilder:
    """Builds and manages the application menu bar."""

    def __init__(self, main_window: "MainWindow") -> None:
        """
        Initialize menu builder.

        Args:
            main_window: MainWindow instance that owns the menus
        """
        self.main_window = main_window
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def setup_actions(self) -> None:
        """Create all actions for menus and toolbar."""
        self._setup_file_actions()
        self._setup_settings_actions()
        self._setup_extras_actions()
        self._setup_help_actions()

        self.logger.debug("Actions created")

    def _setup_file_actions(self) -> None:
        """Create File menu actions."""
        mw = self.main_window
        actions = mw.main_window_actions

        mw.action_new = QAction("&New Map", mw)
        mw.action_new.setShortcut(QKeySequence.StandardKey.New)
        mw.action_new.setStatusTip("Create a new map")
        mw.action_new.triggered.connect(actions.new_map)

        mw.action_open = QAction("&Open Map", mw)
        mw.action_open.setShortcut(QKeySequence.StandardKey.Open)
        mw.action_open.setStatusTip("Open an existing map")
        mw.action_open.triggered.connect(actions.open_map)

        mw.action_save = QAction("&Save Map", mw)
        mw.action_save.setShortcut(QKeySequence.StandardKey.Save)
        mw.action_save.setStatusTip("Save the current map")
        mw.action_save.triggered.connect(actions.save_map)
        mw.action_save.setEnabled(False)  # Disabled until map is loaded

        mw.action_save_as = QAction("Save &As...", mw)
        mw.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        mw.action_save_as.setStatusTip("Save the current map with a new name")
        mw.action_save_as.triggered.connect(actions.save_map_as)
        mw.action_save_as.setEnabled(False)

        mw.action_exit = QAction("E&xit", mw)
        mw.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        mw.action_exit.setStatusTip("Exit the application")
        mw.action_exit.triggered.connect(mw.close)

    def _setup_settings_actions(self) -> None:
        """Create Settings menu actions."""
        mw = self.main_window
        actions = mw.main_window_actions

        mw.action_setup_game_path = QAction("Setup &Game Path...", mw)
        mw.action_setup_game_path.setStatusTip("Configure CDDA game directory path")
        mw.action_setup_game_path.triggered.connect(actions.setup_game_path)

        mw.action_select_mods = QAction("Select &Mods...", mw)
        mw.action_select_mods.setStatusTip("Configure active mods and their priorities")
        mw.action_select_mods.triggered.connect(actions.select_mods)

        mw.action_type_slot_mapping = QAction("&Type-Slot Mapping...", mw)  # type: ignore[attr-defined]
        mw.action_type_slot_mapping.setStatusTip(  # type: ignore[attr-defined]
            "Configure which object types map to which cell slots"
        )
        mw.action_type_slot_mapping.triggered.connect(  # type: ignore[attr-defined]
            actions.type_slot_mapping_settings
        )

        mw.action_logging_settings = QAction("&Logging Settings...", mw)
        mw.action_logging_settings.setStatusTip("Configure logging settings")
        mw.action_logging_settings.triggered.connect(actions.logging_settings)

        mw.action_animation_timeout = QAction("&Animation Timeout...", mw)
        mw.action_animation_timeout.setStatusTip(
            "Configure animation timeout (1-1000 ms)"
        )
        mw.action_animation_timeout.triggered.connect(
            actions.animation_timeout_settings
        )

        mw.action_multi_z_level = QAction("&Multi-Z-Level Rendering...", mw)
        mw.action_multi_z_level.setStatusTip(
            "Configure multi-z-level rendering settings"
        )
        mw.action_multi_z_level.triggered.connect(actions.multi_z_level_settings)

    def _setup_extras_actions(self) -> None:
        """Create Extras menu actions."""
        mw = self.main_window
        actions = mw.main_window_actions

        mw.action_show_log = QAction("Show &Log Window", mw)
        mw.action_show_log.setShortcut(QKeySequence("`"))  # Backtick key under ESC
        mw.action_show_log.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut
        )  # Work even when log window is focused
        mw.action_show_log.setStatusTip("Show/hide log window (press ` key)")
        mw.action_show_log.triggered.connect(actions.toggle_log_window)

        # Object Explorer actions
        mw.action_toggle_object_explorer = QAction("Toggle Object Explorer Window", mw)
        mw.action_toggle_object_explorer.setShortcut(QKeySequence("F2"))
        mw.action_toggle_object_explorer.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut
        )  # Work even when Object Explorer window is focused
        mw.action_toggle_object_explorer.setStatusTip(
            "Show/hide Object Explorer window"
        )
        mw.action_toggle_object_explorer.triggered.connect(
            actions.toggle_object_explorer_window
        )

        # Object Explorer z-order option
        mw.action_object_explorer_stay_above_main = QAction(
            "Object Explorer stays above main window",
            mw,
        )
        mw.action_object_explorer_stay_above_main.setCheckable(True)
        mw.action_object_explorer_stay_above_main.setChecked(
            bool(getattr(mw.settings, "explorer_stay_above_main", False))
        )
        mw.action_object_explorer_stay_above_main.setStatusTip(
            "Keep Object Explorer above the main window"
        )
        mw.action_object_explorer_stay_above_main.toggled.connect(
            actions.set_object_explorer_stay_above_main
        )

    def _setup_help_actions(self) -> None:
        """Create Help menu actions."""
        mw = self.main_window
        actions = mw.main_window_actions

        mw.action_about = QAction("&About", mw)
        mw.action_about.setStatusTip("About CDDA-maped")
        mw.action_about.triggered.connect(actions.about)

    def setup_menus(self) -> None:
        """Setup the menu bar."""
        menubar = self.main_window.menuBar()

        self._setup_file_menu(menubar)
        self._setup_settings_menu(menubar)
        self._setup_extras_menu(menubar)
        self._setup_help_menu(menubar)

        self.logger.debug("Menus created")

    def _setup_file_menu(self, menubar: QMenuBar) -> None:
        """Setup File menu."""
        mw = self.main_window
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(mw.action_new)  # type: ignore[arg-type]
        file_menu.addAction(mw.action_open)  # type: ignore[arg-type]
        file_menu.addSeparator()
        file_menu.addAction(mw.action_save)  # type: ignore[arg-type]
        file_menu.addAction(mw.action_save_as)  # type: ignore[arg-type]
        file_menu.addSeparator()
        file_menu.addAction(mw.action_exit)  # type: ignore[arg-type]

    def _setup_settings_menu(self, menubar: QMenuBar) -> None:
        """Setup Settings menu."""
        mw = self.main_window
        settings_menu = menubar.addMenu("&Settings")
        settings_menu.addAction(mw.action_setup_game_path)  # type: ignore[arg-type]
        settings_menu.addSeparator()
        settings_menu.addAction(mw.action_select_mods)  # type: ignore[arg-type]
        settings_menu.addAction(mw.action_type_slot_mapping)  # type: ignore[arg-type,attr-defined]
        settings_menu.addSeparator()
        settings_menu.addAction(mw.action_logging_settings)  # type: ignore[arg-type]
        settings_menu.addAction(mw.action_animation_timeout)  # type: ignore[arg-type]
        settings_menu.addAction(mw.action_multi_z_level)  # type: ignore[arg-type]

    def _setup_extras_menu(self, menubar: QMenuBar) -> None:
        """Setup Extras menu."""
        mw = self.main_window
        extras_menu = menubar.addMenu("&Extras")
        extras_menu.addAction(mw.action_show_log)  # type: ignore[arg-type]
        extras_menu.addAction(mw.action_toggle_object_explorer)  # type: ignore[arg-type]
        extras_menu.addAction(mw.action_object_explorer_stay_above_main)  # type: ignore[arg-type]

    def _setup_help_menu(self, menubar: QMenuBar) -> None:
        """Setup Help menu."""
        mw = self.main_window
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(mw.action_about)  # type: ignore[arg-type]
