"""Menu builder for Object Explorer window."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenuBar
from PySide6.QtGui import QAction

if TYPE_CHECKING:
    from .window import ObjectExplorerWindow


class ObjectExplorerMenuBuilder:
    """Builds and manages the Object Explorer window menu bar."""

    def __init__(self, explorer_window: "ObjectExplorerWindow") -> None:
        """
        Initialize menu builder.

        Args:
            explorer_window: ObjectExplorerWindow instance that owns the menus
        """
        self.explorer_window = explorer_window
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def setup_menus(self) -> None:
        """Setup the menu bar."""
        menubar = self.explorer_window.menuBar()
        self._setup_view_menu(menubar)
        self._setup_widgets_menu(menubar)
        self.logger.debug("Object Explorer menus created")

    def _setup_view_menu(self, menubar: QMenuBar) -> None:
        """Setup View menu with view-related actions."""
        view_menu = menubar.addMenu("&View")
        ew = self.explorer_window

        # Toggle grid action
        toggle_grid_action = QAction("Toggle &Grid", ew)
        toggle_grid_action.setStatusTip("Toggle grid visibility in demo views")
        toggle_grid_action.setCheckable(True)
        toggle_grid_action.setChecked(True)  # Grid is visible by default
        toggle_grid_action.triggered.connect(self._on_toggle_grid)
        view_menu.addAction(toggle_grid_action)  # type: ignore

    def _setup_widgets_menu(self, menubar: QMenuBar) -> None:
        """Setup Widgets menu with actions for Object Explorer's dock widgets."""
        widgets_menu = menubar.addMenu("&Widgets")
        ew = self.explorer_window

        # Add toggle actions for dock widgets from Object Explorer window
        if hasattr(ew, "selectors_dock"):
            selectors_action = ew.selectors_dock.toggleViewAction()
            selectors_action.setText("Toggle &Selectors Widget")
            widgets_menu.addAction(selectors_action)  # type: ignore

        if hasattr(ew, "browser_dock"):
            browser_action = ew.browser_dock.toggleViewAction()
            browser_action.setText("Toggle Object &Browser Widget")
            widgets_menu.addAction(browser_action)  # type: ignore

        if hasattr(ew, "game_json_dock"):
            game_json_action = ew.game_json_dock.toggleViewAction()
            game_json_action.setText("Toggle &Game Data JSON Widget")
            widgets_menu.addAction(game_json_action)  # type: ignore

        if hasattr(ew, "tileset_json_dock"):
            ortho_json_action = ew.tileset_json_dock.toggleViewAction()
            ortho_json_action.setText("Toggle &Ortho Tileset JSON Widget")
            widgets_menu.addAction(ortho_json_action)  # type: ignore

        if hasattr(ew, "tileset_iso_json_dock"):
            iso_json_action = ew.tileset_iso_json_dock.toggleViewAction()
            iso_json_action.setText("Toggle &ISO Tileset JSON Widget")
            widgets_menu.addAction(iso_json_action)  # type: ignore

        # Reset view proportions action
        widgets_menu.addSeparator()
        reset_views_action = QAction("Reset &View Proportions", ew)
        reset_views_action.setStatusTip("Reset the proportions of the map views")
        reset_views_action.triggered.connect(ew.reset_view_proportions)
        widgets_menu.addAction(reset_views_action)  # type: ignore

        # Reset layout action
        reset_layout_action = QAction("&Reset Widget Layout", ew)
        reset_layout_action.setStatusTip("Reset all widget positions and sizes to default")
        reset_layout_action.triggered.connect(ew.reset_widget_layout)
        widgets_menu.addAction(reset_layout_action)  # type: ignore

    def _on_toggle_grid(self, checked: bool) -> None:
        """Handle toggle grid action."""
        ew = self.explorer_window
        # Apply grid visibility to both ortho and iso views
        if hasattr(ew, "view_ortho") and ew.view_ortho:
            ew.view_ortho.set_grid_visible(checked)
        if hasattr(ew, "view_iso") and ew.view_iso:
            ew.view_iso.set_grid_visible(checked)
