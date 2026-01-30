"""Layout builder for Object Explorer window.

Manages dock widgets, views, selectors and JSON displays.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QDockWidget,
    QWidget,
    QHBoxLayout,
    QSizePolicy,
    QSplitter,
)
from PySide6.QtCore import Qt

from ..map_view import MapView
from ..object_browser import ObjectBrowser
from ..selectors.ts_ortho_selector import TsOrthoSelector
from ..selectors.ts_iso_selector import TsIsoSelector
from ..selectors.season_selector import SeasonSelector
from ..selectors.time_selector import TimeSelector
from ..selectors.weather_selector import WeatherSelector
from ..selectors.zoom_selector import ZoomSelector
from ..selectors.demo_map_selector import DemoMapSelector
from ..json_display import JsonDisplayWidget

if TYPE_CHECKING:
    from .window import ObjectExplorerWindow


class ObjectExplorerLayoutBuilder:
    """Builds and manages the Object Explorer window layout."""

    def __init__(self, explorer_window: "ObjectExplorerWindow") -> None:
        """
        Initialize layout builder.

        Args:
            explorer_window: ObjectExplorerWindow instance that owns the layout
        """
        self.explorer_window = explorer_window
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def setup_layout(self) -> None:
        """
        Setup dock widgets and layout for the Object Explorer window.

        Layout:
        - Top: Selectors (full width)
        - Left: Object Browser
        - Center: Ortho View (docked) + Iso View (docked, under ortho)
        - Right: JSON display docks (tabified)
        """
        self._create_selectors_dock()
        self._create_browser_dock()
        self._create_json_docks()
        self._create_central_views()
        self._connect_signals()

        self.logger.debug("Object Explorer layout created")

    def _create_selectors_dock(self) -> None:
        """Create and setup selectors dock at the top."""
        ew = self.explorer_window

        # Create selectors
        ew.tileset_selector = TsOrthoSelector()
        ew.tileset_iso_selector = TsIsoSelector()
        ew.season_selector = SeasonSelector()
        ew.time_selector = TimeSelector()
        ew.zoom_selector = ZoomSelector()
        ew.weather_selector = WeatherSelector()
        ew.demo_map_selector = DemoMapSelector()

        # Selectors dock (at the TOP)
        ew.selectors_dock = QDockWidget("", ew)
        ew.selectors_dock.setObjectName("oe_selectors_dock")

        # Create horizontal layout for selectors
        selectors_widget = QWidget()
        selectors_layout = QHBoxLayout(selectors_widget)
        selectors_layout.setContentsMargins(4, 4, 4, 4)
        selectors_layout.setSpacing(8)

        # Set size policy for selectors to be compact
        for selector in [  # type: ignore
            ew.tileset_selector,
            ew.tileset_iso_selector,
            ew.season_selector,
            ew.time_selector,
            ew.zoom_selector,
            ew.demo_map_selector,
        ]:  # type: ignore
            selector.setSizePolicy(  # type: ignore
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Minimum,
            )

        selectors_layout.addWidget(ew.demo_map_selector)
        selectors_layout.addWidget(ew.tileset_selector)
        selectors_layout.addWidget(ew.tileset_iso_selector)
        selectors_layout.addWidget(ew.zoom_selector)
        selectors_layout.addStretch()
        selectors_layout.addWidget(ew.season_selector)
        selectors_layout.addWidget(ew.time_selector)
        selectors_layout.addWidget(ew.weather_selector)

        ew.selectors_dock.setWidget(selectors_widget)
        ew.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, ew.selectors_dock)

    def _create_browser_dock(self) -> None:
        """Create and setup object browser dock at the left."""
        ew = self.explorer_window

        # Object browser dock (LEFT side)
        ew.browser_dock = QDockWidget("Objects", ew)
        ew.browser_dock.setObjectName("oe_browser_dock")
        ew.object_browser = ObjectBrowser()
        ew.object_browser.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        ew.browser_dock.setWidget(ew.object_browser)
        ew.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, ew.browser_dock)

    def _create_json_docks(self) -> None:
        """Create and setup JSON display docks at the right."""
        ew = self.explorer_window

        # Game object JSON dock (RIGHT side)
        ew.game_json_dock = QDockWidget("Game Object", ew)
        ew.game_json_dock.setObjectName("oe_game_json_dock")
        ew.game_json_display = JsonDisplayWidget("Game Object JSON")
        ew.game_json_dock.setWidget(ew.game_json_display)
        ew.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, ew.game_json_dock)

        # Tileset JSON dock (RIGHT side, tabified with game json)
        ew.tileset_json_dock = QDockWidget("Ortho Tileset", ew)
        ew.tileset_json_dock.setObjectName("oe_tileset_json_dock")
        ew.tileset_json_display = JsonDisplayWidget("Orthogonal Tileset JSON")
        ew.tileset_json_dock.setWidget(ew.tileset_json_display)
        ew.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, ew.tileset_json_dock)

        # Tileset ISO JSON dock (RIGHT side, tabified with others)
        ew.tileset_iso_json_dock = QDockWidget("ISO Tileset", ew)
        ew.tileset_iso_json_dock.setObjectName("oe_tileset_iso_json_dock")
        ew.tileset_iso_json_display = JsonDisplayWidget("Isometric Tileset JSON")
        ew.tileset_iso_json_dock.setWidget(ew.tileset_iso_json_display)
        ew.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, ew.tileset_iso_json_dock
        )

        # Tabify JSON docks in right area
        ew.tabifyDockWidget(ew.game_json_dock, ew.tileset_json_dock)
        ew.tabifyDockWidget(ew.tileset_json_dock, ew.tileset_iso_json_dock)
        ew.game_json_dock.raise_()  # Raise game_json_dock to be the active tab

    def _create_central_views(self) -> None:
        """Create central widget with both ortho and iso views."""
        ew = self.explorer_window

        # Create central widget with both views in vertical splitter
        # Store splitter in the window for state save/restore
        ew.central_splitter = QSplitter(Qt.Orientation.Vertical)
        ew.central_splitter.setObjectName("oe_central_view_splitter")

        ew.view_ortho = MapView(ew.settings)
        ew.central_splitter.addWidget(ew.view_ortho)

        ew.view_iso = MapView(ew.settings)
        ew.central_splitter.addWidget(ew.view_iso)

        # Set equal sizes by default (50/50 split)
        ew.central_splitter.setSizes([500, 500])

        ew.setCentralWidget(ew.central_splitter)

    def _connect_signals(self) -> None:
        """Connect signals between widgets and action methods."""
        ew = self.explorer_window

        # Connect signals for ortho view
        ew.tileset_selector.ts_ortho_changed.connect(ew.on_tileset_ortho_changed)
        ew.season_selector.seasonChanged.connect(ew.on_season_changed)
        ew.object_browser.object_selected.connect(ew.on_object_selected)
        ew.zoom_selector.zoomChanged.connect(ew.on_zoom_changed)

        # Connect signals for iso view
        ew.tileset_iso_selector.ts_iso_changed.connect(ew.on_tileset_iso_changed)

        # Connect demo map selector
        ew.demo_map_selector.demoMapChanged.connect(ew.on_demo_map_changed)

    def reset_view_proportions(self) -> None:
        """Reset the proportions of the ortho and iso views to 50/50."""
        ew = self.explorer_window
        if hasattr(ew, "central_splitter") and ew.central_splitter:
            ew.central_splitter.setSizes([500, 500])
            self.logger.debug("Reset view proportions to 50/50")

    def reset_widget_layout(self) -> None:
        """Reset all dock widgets to default positions and sizes."""
        ew = self.explorer_window

        # Clear saved state
        ew.restoreState(b"")

        # Remove all dock widgets first
        if hasattr(ew, "selectors_dock"):
            ew.removeDockWidget(ew.selectors_dock)
        if hasattr(ew, "browser_dock"):
            ew.removeDockWidget(ew.browser_dock)
        if hasattr(ew, "game_json_dock"):
            ew.removeDockWidget(ew.game_json_dock)
        if hasattr(ew, "tileset_json_dock"):
            ew.removeDockWidget(ew.tileset_json_dock)
        if hasattr(ew, "tileset_iso_json_dock"):
            ew.removeDockWidget(ew.tileset_iso_json_dock)

        # Re-add dock widgets in default positions
        # Selectors at TOP
        if hasattr(ew, "selectors_dock"):
            ew.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, ew.selectors_dock)
            ew.selectors_dock.setVisible(True)

        # Browser at LEFT
        if hasattr(ew, "browser_dock"):
            ew.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, ew.browser_dock)
            ew.browser_dock.setVisible(True)

        # JSON docks at RIGHT (tabified)
        if hasattr(ew, "game_json_dock"):
            ew.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, ew.game_json_dock)
            ew.game_json_dock.setVisible(True)
        if hasattr(ew, "tileset_json_dock"):
            ew.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, ew.tileset_json_dock
            )
            ew.tileset_json_dock.setVisible(True)
        if hasattr(ew, "tileset_iso_json_dock"):
            ew.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, ew.tileset_iso_json_dock
            )
            ew.tileset_iso_json_dock.setVisible(True)

        # Tabify JSON docks
        if hasattr(ew, "game_json_dock") and hasattr(ew, "tileset_json_dock"):
            ew.tabifyDockWidget(ew.game_json_dock, ew.tileset_json_dock)
        if hasattr(ew, "tileset_json_dock") and hasattr(ew, "tileset_iso_json_dock"):
            ew.tabifyDockWidget(ew.tileset_json_dock, ew.tileset_iso_json_dock)

        # Make game_json_dock the active tab
        if hasattr(ew, "game_json_dock"):
            ew.game_json_dock.raise_()

        # Reset splitter proportions to 50/50
        self.reset_view_proportions()

        self.logger.debug("Reset widget layout and view proportions to defaults")
