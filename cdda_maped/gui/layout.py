"""
Dock widget layout manager for main application window.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt

from .object_browser import ObjectBrowser

if TYPE_CHECKING:
    from .main_window import MainWindow


class DockLayoutBuilder:
    """Manages dock widgets and layout for the main window."""

    def __init__(self, main_window: "MainWindow") -> None:
        """
        Initialize dock layout manager.

        Args:
            main_window: MainWindow instance that owns the docks
        """
        self.main_window = main_window
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def setup_dock_widgets(self) -> None:
        """
        Setup dock widgets for tools and browsers.

        Layout (minimal):
        - Left: Object Browser
        - Center: empty placeholder
        """
        self._create_browser_dock()
        self._create_empty_central()
        self._connect_signals()

        self.logger.debug("Dock widgets created")

    def _create_browser_dock(self) -> None:
        """Create and setup object browser dock at the left."""
        mw = self.main_window

        # Object browser dock (LEFT side)
        mw.browser_dock = QDockWidget()
        mw.browser_dock.setObjectName("browser_dock")
        mw.object_browser = ObjectBrowser(emit_selection_signals=False)
        mw.object_browser.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )

        # Wrap the browser to add a button below it (requested UX).
        browser_container = QWidget()
        browser_layout = QVBoxLayout(browser_container)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_layout.setSpacing(6)
        browser_layout.addWidget(mw.object_browser)

        mw.open_in_object_explorer_button = QPushButton("Open in Object Explorer")
        mw.open_in_object_explorer_button.setObjectName("open_in_object_explorer_button")
        mw.open_in_object_explorer_button.clicked.connect(
            mw.main_window_actions.open_object_explorer_with_selected_object
        )
        browser_layout.addWidget(mw.open_in_object_explorer_button)

        mw.browser_dock.setWidget(browser_container)
        mw.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, mw.browser_dock)

    def _create_empty_central(self) -> None:
        """Create minimal central placeholder (no additional widgets)."""
        mw = self.main_window
        placeholder = QWidget()
        mw.setCentralWidget(placeholder)

    def _connect_signals(self) -> None:
        """Connect signals between widgets."""
        mw = self.main_window # type: ignore

        # Do not connect object browser selection to main window actions.
        # Selection is handled in the Object Explorer window.

    def reset_widget_layout(self) -> None:
        """Reset all dock widgets to default positions and sizes."""
        mw = self.main_window
        self.logger.info("Resetting widget layout to defaults")

        # Only browser dock remains
        if hasattr(mw, "browser_dock"):
            mw.browser_dock.show()
            mw.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, mw.browser_dock)

        # Reset window size to default
        mw.resize(1200, 800)

        if hasattr(mw, "status_bar"):
            mw.status_bar.showMessage("Widget layout reset to defaults", 3000)
        self.logger.info("Widget layout reset completed")
