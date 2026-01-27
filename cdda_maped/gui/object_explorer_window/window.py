"""Object Explorer Window.

Secondary window for exploring CDDA game objects and tileset visuals.
Receives references to settings and services upon creation.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING, cast

import qtawesome as qta  # type: ignore

from PySide6.QtWidgets import QMainWindow, QWidget, QDockWidget, QSplitter
from PySide6.QtCore import QTimer, Slot, QByteArray, Qt
from PySide6.QtGui import QCloseEvent, QHideEvent, QAction, QKeySequence, QKeyEvent

from ...settings import AppSettings
from ...game_data.service import GameDataService
from ...tilesets.service import TilesetService
from .menu import ObjectExplorerMenuBuilder
from .layout import ObjectExplorerLayoutBuilder

if TYPE_CHECKING:
    from ..selectors.ts_ortho_selector import TsOrthoSelector
    from ..selectors.ts_iso_selector import TsIsoSelector
    from ..selectors.season_selector import SeasonSelector
    from ..selectors.time_selector import TimeSelector
    from ..selectors.weather_selector import WeatherSelector
    from ..selectors.zoom_selector import ZoomSelector
    from ..selectors.demo_map_selector import DemoMapSelector
    from ..object_browser import ObjectBrowser
    from ..json_display import JsonDisplayWidget
    from ..map_view import MapView
from .actions import ObjectExplorerActions
from ...maps import DemoMap, MapManager


class ObjectExplorerWindow(QMainWindow):
    """Secondary window for object exploration.

    Args:
        settings: Application settings (AppSettings facade).
        game_data_service: Game data service for object access.
        tileset_service: Tileset service for visual resolution.
        parent: Optional parent widget (MainWindow).
    """

    # Dock widgets and selectors
    selectors_dock: QDockWidget
    browser_dock: QDockWidget
    game_json_dock: QDockWidget
    tileset_json_dock: QDockWidget
    tileset_iso_json_dock: QDockWidget
    tileset_selector: TsOrthoSelector
    tileset_iso_selector: TsIsoSelector
    season_selector: SeasonSelector
    time_selector: TimeSelector
    zoom_selector: ZoomSelector
    weather_selector: WeatherSelector
    demo_map_selector: DemoMapSelector
    object_browser: ObjectBrowser
    game_json_display: JsonDisplayWidget
    tileset_json_display: JsonDisplayWidget
    tileset_iso_json_display: JsonDisplayWidget
    view_ortho: MapView
    view_iso: MapView
    map: DemoMap
    action_handler: ObjectExplorerActions
    central_splitter: QSplitter

    def __init__(
        self,
        settings: AppSettings,
        game_data_service: GameDataService,
        tileset_service: TilesetService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self.settings = settings
        self.game_data_service = game_data_service
        self.tileset_service = tileset_service

        # Initialize map manager
        self.map_manager = MapManager()

        # Object pattern state: 9 boolean values for 3x3 grid
        # Index mapping: 0=TL, 1=T, 2=TR, 3=L, 4=C, 5=R, 6=BL, 7=B, 8=BR
        self.object_pattern_state: list[bool] = [False] * 9
        self.current_object_id: Optional[str] = None

        # If an external caller requests a selection before the explorer finishes
        # loading its content, stash it and apply once ready.
        self._pending_select_object_id: Optional[str] = None

        self.setObjectName("object_explorer_window")
        self.setWindowTitle("Object Explorer")
        self.resize(1200, 800)

        # Initialize builders and handlers
        self.menu_builder = ObjectExplorerMenuBuilder(self)
        self.layout_builder = ObjectExplorerLayoutBuilder(self)
        self.action_handler = ObjectExplorerActions(self)

        # Setup UI
        self.layout_builder.setup_layout()
        self.menu_builder.setup_menus()
        self._setup_shortcuts()

        # Restore window geometry and dock state from settings
        if not self.settings.restore_explorer_window_geometry(self):
            # Default size if no saved geometry
            self.resize(1200, 800)

        self._restore_dock_state()
        self._restore_splitter_state()  # Restore after layout is created

        # Setup content
        QTimer.singleShot(100, self.setup_explorer_content) # type: ignore

        self.logger.info("ObjectExplorerWindow initialized")

    def _setup_shortcuts(self) -> None:
        """Setup global shortcuts for iso view rotation."""
        # Rotate CW (Numpad /)
        action_rotate_cw = QAction("Rotate ISO View Clockwise", self)
        action_rotate_cw.setShortcut(QKeySequence("/"))
        action_rotate_cw.triggered.connect(self._on_rotate_iso_cw)
        self.addAction(action_rotate_cw)

        # Center view (Numpad *)
        action_center = QAction("Center ISO View", self)
        action_center.setShortcut(QKeySequence("*"))
        action_center.triggered.connect(self._on_center_iso_view)
        self.addAction(action_center)

        # Rotate CCW (Numpad -)
        action_rotate_ccw = QAction("Rotate ISO View Counter-Clockwise", self)
        action_rotate_ccw.setShortcut(QKeySequence("-"))
        action_rotate_ccw.triggered.connect(self._on_rotate_iso_ccw)
        self.addAction(action_rotate_ccw)

        # Toggle animations (Numpad .)
        action_toggle_animations = QAction("Toggle Animations", self)
        #action_toggle_animations.setShortcut(QKeySequence(Qt.Key_Delete)) # type: ignore[arg-type]
        action_toggle_animations.setShortcut(QKeySequence("."))
        action_toggle_animations.triggered.connect(self._on_toggle_animations)
        self.addAction(action_toggle_animations)

        # Toggle transparency (Numpad 0)
        action_toggle_transparency = QAction("Toggle Transparency", self)
        action_toggle_transparency.setShortcut(QKeySequence("0"))
        action_toggle_transparency.triggered.connect(self._on_toggle_transparency)
        self.addAction(action_toggle_transparency)

        # Z-level controls
        action_increase_z = QAction("Increase Z-Level", self)
        action_increase_z.setShortcut(QKeySequence(Qt.Key.Key_PageUp))  # type: ignore
        action_increase_z.triggered.connect(self._on_increase_z_level)
        self.addAction(action_increase_z)

        action_decrease_z = QAction("Decrease Z-Level", self)
        action_decrease_z.setShortcut(QKeySequence(Qt.Key.Key_PageDown))  # type: ignore
        action_decrease_z.triggered.connect(self._on_decrease_z_level)
        self.addAction(action_decrease_z)

        # Focus controls (Numpad + for ortho, NumPad Enter for iso)
        action_focus_ortho = QAction("Focus Ortho View", self)
        action_focus_ortho.setShortcut(QKeySequence("+"))
        action_focus_ortho.triggered.connect(self._on_focus_ortho_view)
        self.addAction(action_focus_ortho)

        action_focus_iso = QAction("Focus ISO View", self)
        action_focus_iso.setShortcut(QKeySequence(Qt.Key.Key_Enter))  # type: ignore
        action_focus_iso.triggered.connect(self._on_focus_iso_view)
        self.addAction(action_focus_iso)

    def _on_toggle_transparency(self) -> None:
        """Handle toggle transparency shortcut."""
        if hasattr(self, "view_iso") and self.view_iso:
            self.view_iso.toggle_transparency()
        if hasattr(self, "view_ortho") and self.view_ortho:
            self.view_ortho.toggle_transparency()

    def _on_rotate_iso_cw(self) -> None:
        """Handle rotate ISO CW shortcut."""
        if hasattr(self, "view_iso") and self.view_iso:
            self.view_iso.rotate_cw()

    def _on_center_iso_view(self) -> None:
        """Handle center ISO view shortcut."""
        if hasattr(self, "view_iso") and self.view_iso:
            self.view_iso.reset_rotation()

    def _on_rotate_iso_ccw(self) -> None:
        """Handle rotate ISO CCW shortcut."""
        if hasattr(self, "view_iso") and self.view_iso:
            self.view_iso.rotate_ccw()

    def _on_toggle_animations(self) -> None:
        """Handle toggle animations shortcut."""
        if hasattr(self, "view_iso") and self.view_iso:
            self.view_iso.toggle_animation()
        if hasattr(self, "view_ortho") and self.view_ortho:
            self.view_ortho.toggle_animation()

    def _on_increase_z_level(self) -> None:
        """Handle increase z-level shortcut (Page Up)."""
        self.action_handler.increase_z_level()

    def _on_decrease_z_level(self) -> None:
        """Handle decrease z-level shortcut (Page Down)."""
        self.action_handler.decrease_z_level()

    def _on_focus_ortho_view(self) -> None:
        """Handle focus ortho view shortcut (NumPad +)."""
        if hasattr(self, "view_ortho") and self.view_ortho:
            self.view_ortho.setFocus()

    def _on_focus_iso_view(self) -> None:
        """Handle focus iso view shortcut (NumPad Enter)."""
        if hasattr(self, "view_iso") and self.view_iso:
            self.view_iso.setFocus()

    def set_object_placed_in_center(self) -> None:
        """Mark center object as placed and update button icon."""
        self.object_pattern_state[4] = True
        self.current_object_id = self.action_handler.current_object_id
        self.update_button_icons()

    def toggle_object_in_pattern(self, index: int) -> None:
        """Toggle object at given index in the 3x3 pattern.

        Args:
            index: Button index (0-8) representing positions in 3x3 grid
        """
        if not (0 <= index <= 8):
            self.logger.warning(f"Invalid pattern index: {index}")
            return

        if not self.current_object_id:
            self.logger.warning("No object selected to place")
            return

        # Toggle state
        self.object_pattern_state[index] = not self.object_pattern_state[index]
        self.logger.debug(f"Toggled object at index {index}: {self.object_pattern_state[index]}")

        # Update button icons in both views
        self.update_button_icons()

        # Place/remove actual object in map at calculated cell position
        self._place_or_remove_object(index, self.object_pattern_state[index])

        # Redraw both views
        if hasattr(self, "view_ortho") and self.view_ortho:
            self.view_ortho.render_map()
        if hasattr(self, "view_iso") and self.view_iso:
            self.view_iso.render_map()

    def update_button_icons(self) -> None:
        """Update button icons in both map views based on pattern state."""
        # Map index to icon
        for i, is_active in enumerate(self.object_pattern_state):
            icon = "mdi.square" if is_active else "mdi.circle-small"

            if hasattr(self, "view_ortho") and self.view_ortho and hasattr(self.view_ortho, "pattern_buttons"):
                try:
                    button = self.view_ortho.pattern_buttons[i]
                    button.setIcon(qta.icon(icon))  # type: ignore[arg-type]
                except (AttributeError, IndexError):
                    pass

            if hasattr(self, "view_iso") and self.view_iso and hasattr(self.view_iso, "pattern_buttons"):
                try:
                    button = self.view_iso.pattern_buttons[i]
                    button.setIcon(qta.icon(icon))  # type: ignore[arg-type]
                except (AttributeError, IndexError):
                    pass

    def _place_or_remove_object(self, index: int, place: bool) -> None:
        """Place or remove object at pattern position.

        Args:
            index: Pattern index (0-8) representing 3x3 grid position
            place: True to place object, False to remove
        """
        if not self.current_object_id:
            return

        # Convert index to offset from center
        # Index mapping: 0=TL, 1=T, 2=TR, 3=L, 4=C, 5=R, 6=BL, 7=B, 8=BR
        offsets = [
            (-1, -1),  # 0: Top-left
            (0, -1),   # 1: Top
            (1, -1),   # 2: Top-right
            (-1, 0),   # 3: Left
            (0, 0),    # 4: Center
            (1, 0),    # 5: Right
            (-1, 1),   # 6: Bottom-left
            (0, 1),    # 7: Bottom
            (1, 1),    # 8: Bottom-right
        ]

        dx, dy = offsets[index]

        # Calculate absolute cell position
        if hasattr(self, "demo_map"):
            width_in_cells = self.demo_map.sector_width * self.demo_map.num_sectors_x
            height_in_cells = self.demo_map.sector_height * self.demo_map.num_sectors_y
            center_x = width_in_cells // 2
            center_y = height_in_cells // 2
            target_x = center_x + dx
            target_y = center_y + dy
            z = 0

            # Get game object to determine slot
            from cdda_maped.maps import MapCell
            game_object = self.game_data_service.get_resolved_object(self.current_object_id)
            if not game_object:
                return

            object_type = game_object.get("type", "furniture")
            slot = MapCell.get_slot_for_object_type(object_type)

            # Place or remove in the map (shared by both views)
            cell = self.demo_map.get_cell_at(target_x, target_y, z)
            if cell is None:
                cell = MapCell()

            if place:
                cell.set_content(slot, self.current_object_id, quantity=1)
            else:
                cell.clear_slot(slot)

            try:
                self.demo_map.set_cell_at(target_x, target_y, z, cell)
            except ValueError as e:
                self.logger.error(f"Failed to modify cell at ({target_x}, {target_y}): {e}")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle numpad shortcuts for object pattern."""
        # Numpad mapping: numpad keys map to 3x3 grid indices
        numpad_map = {
            Qt.Key.Key_1: 6,  # Bottom-left
            Qt.Key.Key_2: 7,  # Bottom
            Qt.Key.Key_3: 8,  # Bottom-right
            Qt.Key.Key_4: 3,  # Left
            Qt.Key.Key_5: 4,  # Center
            Qt.Key.Key_6: 5,  # Right
            Qt.Key.Key_7: 0,  # Top-left
            Qt.Key.Key_8: 1,  # Top
            Qt.Key.Key_9: 2,  # Top-right
        }

        if event.key() in numpad_map:  # type: ignore[operator]
            idx = numpad_map[event.key()]  # type: ignore[index]
            self.toggle_object_in_pattern(idx)
            event.accept()
            return

        super().keyPressEvent(event)

    def _restore_dock_state(self) -> None:
        """Restore the state of dock widgets from settings."""
        try:
            dock_state_raw = self.settings.settings.value("explorer/dock_state")
            if dock_state_raw:
                dock_state: QByteArray | None = None
                # Ensure it's QByteArray
                if isinstance(dock_state_raw, bytes):
                    dock_state = QByteArray(dock_state_raw)
                elif isinstance(dock_state_raw, QByteArray):
                    dock_state = dock_state_raw
                else:
                    try:
                        dock_state = QByteArray(cast(bytes, dock_state_raw))
                    except (TypeError, ValueError):
                        dock_state = None

                if dock_state:
                    self.restoreState(dock_state)
                    self.logger.debug("Dock state restored from settings")
        except Exception as e:
            self.logger.warning(f"Failed to restore dock state: {e}")

    def _restore_splitter_state(self) -> None:
        """Restore the state of central splitter from settings."""
        try:
            if hasattr(self, "central_splitter") and self.central_splitter:
                splitter_state_raw = self.settings.settings.value("explorer/splitter_state")
                if splitter_state_raw:
                    splitter_state: QByteArray | None = None
                    # Ensure it's QByteArray
                    if isinstance(splitter_state_raw, bytes):
                        splitter_state = QByteArray(splitter_state_raw)
                    elif isinstance(splitter_state_raw, QByteArray):
                        splitter_state = splitter_state_raw
                    else:
                        try:
                            splitter_state = QByteArray(cast(bytes, splitter_state_raw))
                        except (TypeError, ValueError):
                            splitter_state = None

                    if splitter_state:
                        self.central_splitter.restoreState(splitter_state)
                        self.logger.debug("Splitter state restored from settings")
        except Exception as e:
            self.logger.warning(f"Failed to restore splitter state: {e}")

    def _save_dock_state(self) -> None:
        """Save the state of dock widgets to settings."""
        try:
            dock_state = self.saveState()
            self.settings.settings.setValue("explorer/dock_state", dock_state)
            self.settings.settings.sync()
            self.logger.debug("Dock state saved to settings")
        except Exception as e:
            self.logger.warning(f"Failed to save dock state: {e}")

    def _save_splitter_state(self) -> None:
        """Save the state of central splitter to settings."""
        try:
            if hasattr(self, "central_splitter") and self.central_splitter:
                splitter_state = self.central_splitter.saveState()
                self.settings.settings.setValue("explorer/splitter_state", splitter_state)
                self.settings.settings.sync()
                self.logger.debug("Splitter state saved to settings")
        except Exception as e:
            self.logger.warning(f"Failed to save splitter state: {e}")

    @Slot()
    def setup_explorer_content(self) -> None:
        """Setup explorer content (selectors and services)."""
        try:
            self.logger.info("Setting up Object Explorer content...")

            # Read saved selection BEFORE loading the browser list, to avoid it being
            # overwritten by any initial auto-selection during population.
            saved_object_id = self.settings.settings.value("explorer/current_object_id")

            # Configure UI components
            self.view_ortho.set_tileset_service(self.tileset_service)
            self.view_ortho.set_game_data_service(self.game_data_service)
            self.view_iso.set_tileset_service(self.tileset_service)
            self.view_iso.set_game_data_service(self.game_data_service)
            self.object_browser.set_game_data_service(self.game_data_service)

            # Configure selector settings
            self.logger.info("Configuring selector settings...")
            self.tileset_selector.set_settings(self.settings)
            self.tileset_iso_selector.set_settings(self.settings)
            self.season_selector.set_settings(self.settings)
            self.time_selector.set_settings(self.settings)
            self.zoom_selector.set_settings(self.settings)
            self.weather_selector.set_settings(self.settings)
            self.demo_map_selector.set_settings(self.settings)

            # Now load data
            self.tileset_selector.set_tileset_service(self.tileset_service)
            self.tileset_iso_selector.set_tileset_service(self.tileset_service)
            self.weather_selector.set_game_data_service(self.game_data_service)
            self.demo_map_selector.set_map_manager(self.map_manager)

            # Restore states for selectors
            self.season_selector.restore_state()
            self.time_selector.restore_state()
            self.zoom_selector.restore_state()
            self.demo_map_selector.restore_state()

            # Load demo map (shared between ortho and iso views)
            # Use the currently selected demo map from selector
            self.logger.info("Creating maps...")
            current_demo_map_id = self.demo_map_selector.get_current_demo_map_id()
            self.demo_map = self.map_manager.get_demomap(current_demo_map_id)

            # Set same map to both views (different projections)
            self.view_ortho.set_map(self.demo_map)
            self.view_iso.set_map(self.demo_map)

            # Reset z-level to 0 for both views
            self.view_ortho.set_current_z_level(0)
            self.view_iso.set_current_z_level(0)

            # Show rotation buttons only on iso view
            self.view_iso.set_rotation_buttons_visible(True)

            # Apply initial zoom
            self.on_zoom_changed(self.zoom_selector.get_current_zoom())

            # Restore last selected object into center of the map (if any)
            if saved_object_id:
                try:
                    # Select in browser to highlight it
                    self.object_browser.select_object_by_id(str(saved_object_id))
                    # Explicitly trigger rendering (signal may not fire during init)
                    self.action_handler.on_object_selected(str(saved_object_id))
                    self.logger.info("Restored last selected object in Object Explorer")
                except Exception as restore_error:
                    self.logger.warning(
                        "Failed to restore last selected object: %s", restore_error
                    )
            else:
                # If nothing saved yet, keep a reasonable default by using the current
                # browser selection (typically first row).
                try:
                    current_id = self.object_browser.get_selected_object_id()
                    if current_id:
                        self.action_handler.on_object_selected(current_id)
                except Exception as default_error:
                    self.logger.warning("Failed to apply default selection: %s", default_error)

            self.logger.info("Object Explorer content setup complete")

            # Apply any pending selection requested by the main window.
            if self._pending_select_object_id:
                pending = self._pending_select_object_id
                self._pending_select_object_id = None
                try:
                    self.select_object_id(str(pending))
                except Exception as pending_error:
                    self.logger.warning(
                        "Failed to apply pending object selection: %s", pending_error
                    )

            # Set focus to ortho view after all content is loaded
            if hasattr(self, "view_ortho") and self.view_ortho:
                self.view_ortho.setFocus()

        except Exception as e:
            self.logger.error(f"Failed to setup Object Explorer content: {e}")

    def select_object_id(self, object_id: str) -> None:
        """Select and display the given object ID in the explorer.

        This is meant to be called from the MainWindow button.
        If the explorer isn't ready yet, the selection will be applied later.
        """
        if not object_id:
            return

        # Persist selected object for session restore.
        try:
            self.settings.settings.setValue("explorer/current_object_id", object_id)
            self.settings.settings.sync()
        except Exception:
            pass

        # If the browser isn't loaded yet (no service bound), defer.
        try:
            browser_service_ready = bool(
                hasattr(self, "object_browser")
                and getattr(self.object_browser, "game_data_service", None)
            )
        except Exception:
            browser_service_ready = False

        if not browser_service_ready:
            self._pending_select_object_id = object_id
            return

        # Ensure the ObjectBrowser visually selects the item in the tree so the
        # user sees the selection when the explorer is opened from the main window.
        try:
            if hasattr(self, "object_browser") and self.object_browser:
                try:
                    # select_object_by_id will set filters and scroll into view.
                    self.object_browser.select_object_by_id(object_id, set_filters=True)
                except Exception as sel_err:
                    # Don't fail the overall flow if browser selection has an issue.
                    self.logger.debug(f"ObjectBrowser selection failed: {sel_err}")
        except Exception:
            pass

        # Always update the center demo + JSON (signal may not fire if item was already selected)
        try:
            self.action_handler.on_object_selected(object_id)
        except Exception:
            pass

    # Action delegates - forward to actions handler
    def on_tileset_ortho_changed(self, tileset_name: str) -> None:
        """Handle orthogonal tileset change."""
        self.action_handler.on_tileset_ortho_changed(tileset_name)

    def on_tileset_iso_changed(self, tileset_name: str) -> None:
        """Handle isometric tileset change."""
        self.action_handler.on_tileset_iso_changed(tileset_name)

    def on_season_changed(self, season: str) -> None:
        """Handle season change."""
        self.action_handler.on_season_changed(season)

    def on_zoom_changed(self, zoom_factor: float) -> None:
        """Handle zoom change."""
        self.action_handler.on_zoom_changed(zoom_factor)

    def on_demo_map_changed(self, demo_id: str) -> None:
        """Handle demo map change."""
        self.action_handler.on_demo_map_changed(demo_id)

    def on_object_selected(self, object_id: str) -> None:
        """Handle object selection from browser."""
        self.action_handler.on_object_selected(object_id)

    def reset_view_proportions(self) -> None:
        """Reset the proportions of the ortho and iso views to 50/50."""
        self.action_handler.reset_view_proportions()

    def reset_widget_layout(self) -> None:
        """Reset all dock widgets to default positions and sizes."""
        self.action_handler.reset_widget_layout()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event to save settings."""
        # Save window geometry and state
        self.settings.save_explorer_window_geometry(self)
        self._save_dock_state()
        self._save_splitter_state()

        self.logger.info("Object Explorer window geometry and dock state saved")
        super().closeEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:
        """Persist geometry/dock state when window is hidden (e.g., hotkey toggle)."""
        self.settings.save_explorer_window_geometry(self)
        self._save_dock_state()
        self._save_splitter_state()
        super().hideEvent(event)
