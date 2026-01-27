"""Main view widget for map rendering.

This module provides the MapView widget that orchestrates
all rendering components.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Any

import qtawesome as qta  # type: ignore
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QResizeEvent
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QWidget, QPushButton, QLabel, QHBoxLayout, QVBoxLayout

from cdda_maped.game_data.service import GameDataService
from cdda_maped.tilesets.service import TilesetService
from cdda_maped.settings import AppSettings

from .coord_transformer import CoordinateTransformer
from .scene_manager import SceneManager
from .grid_renderer import GridRenderer
from .tile_rendering import TileRenderer
from .animation_manager import AnimationStateManager, AnimationController
from .events import MapViewEventHandlers
from cdda_maped.maps import DemoMap, CellSlot, MapCell

@dataclass
class TileRenderInfo:
    """Information needed to render a single tile in isometric view.

    Attributes:
        sort_key: Tuple of (scene_y, scene_x) for depth sorting in iso view
        x: Grid X coordinate
        y: Grid Y coordinate
        cell: MapCell at this position
    """
    sort_key: tuple[int, int]
    x: int
    y: int
    cell: MapCell


class MapView(MapViewEventHandlers, QGraphicsView):
    """Graphics view for rendering maps with tilesets.

    Displays a grid-based map with sprites from the active tileset.
    """


    # Available seasons
    SEASONS = ["spring", "summer", "autumn", "winter"]

    def __init__(self, settings: AppSettings, parent: Optional[QWidget] = None):
        """Initialize the map view.

        Args:
            settings: Application settings (for animation timeout, etc.)
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.settings = settings

        # Create scene
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Configure view
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Enable panning with mouse
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        self._space_pressed = False

        # Initialize services and data
        self.tileset_service: Optional[TilesetService] = None
        self.game_data_service: Optional[GameDataService] = None

        # Initialize map and iso clone view state
        self.map: Optional[DemoMap] = None
        self.iso_view_map: Optional[DemoMap] = None

        self.current_tileset: Optional[str] = None
        self.current_season: str = "spring"  # Default season
        self._zoom_factor: float = 1.0
        self.current_z_level: int = 0  # Current z-level for multi-z-level rendering

        # Grid display options
        self.grid_visible = True

        # Transparency option
        self.is_transparency_enabled = False

        # Rotation state (0, 1, 2, 3 for 0°, 90°, 180°, 270°)
        self._rotation_state: int = 0

        # Components (initialized when map is set)
        self.transformer: Optional[CoordinateTransformer] = None
        self.scene_manager: Optional[SceneManager] = None
        self.grid_renderer: Optional[GridRenderer] = None
        self.tile_renderer: Optional[TileRenderer] = None

        # Animation components
        self.animation_state_manager = AnimationStateManager()
        self.animation_controller = AnimationController(
            self, self.animation_state_manager, self.settings
        )

        # Animation UI overlay
        self._setup_animation_ui()

        # Objects pattern UI overlay
        self.pattern_buttons: list[QPushButton] = [] # nine buttons will go here
        self._setup_objects_pattern_ui()

        # Rotation and center buttons
        self._setup_rotation_ui()
        # Transparency toggle button
        self._setup_transparency_ui()

        # Timer for updating animation stats
        self._stats_update_timer = QTimer()
        self._stats_update_timer.timeout.connect(self._update_animation_stats)
        self._stats_update_timer.start(100)  # Update every 100ms

        self.logger.debug("Map view initialized")

    def _setup_animation_ui(self) -> None:
        """Setup overlay UI for animation control."""
        # Container for animation ui
        self.animation_ui_container = QWidget(self)
        layout = QHBoxLayout(self.animation_ui_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetFixedSize)
        layout.setSpacing(1)

        # Start/Stop button
        self.animation_button = QPushButton("", self)
        self.animation_button.setFixedSize(32, 32)
        self.animation_button.setIcon(qta.icon("mdi.play")) # type: ignore[arg-type]
        self.animation_button.setFlat(True)
        self.animation_button.clicked.connect(self.toggle_animation)
        self.animation_button.setToolTip("Start animation [ Numpad Del ]")
        self.animation_button.setProperty("class", "map-overlay-button")
        layout.addWidget(self.animation_button)

        # Frame timing label
        self.frame_stats_label = QLabel("0ms / 0fps", self)
        self.frame_stats_label.setFixedSize(100, 32)
        self.frame_stats_label.hide()
        self.frame_stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_stats_label.setProperty("class", "frame-stats")
        layout.addWidget(self.frame_stats_label)

        # Position will be set in resizeEvent
        self.animation_button.raise_()

    def _setup_objects_pattern_ui(self) -> None:

        tooltips = [
            "7", "8", "9",
            "4", "5", "6",
            "1", "2", "3",
        ]

        """Setup overlay UI for objects pattern display."""
        self.objects_pattern_container = QWidget(self)

        # Layout is 3 rows x 3 columns, each cell 10x10 pixels
        # In each cell we add a button with empty square icon
        layout = QVBoxLayout(self.objects_pattern_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        layout.setSpacing(0)

        index = 0
        for _ in range(3):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)
            for _ in range(3):
                button = QPushButton("", self.objects_pattern_container)
                button.setIcon(qta.icon("mdi.square-outline")) # type: ignore[arg-type]
                button.setIconSize(button.size())
                button.setFixedSize(12, 12)
                button.setFlat(True)
                button.setProperty("class", "pattern-button")

                self.pattern_buttons.append(button)
                button.setToolTip(f"[ Numpad {tooltips[index]} ]")
                button.clicked.connect(lambda checked, i=index: self._toggle_object(i)) # type: ignore[arg-type]
                index += 1

                row_layout.addWidget(button)
            layout.addLayout(row_layout)

    def _toggle_object(self, index: int) -> None:
        """Toggle object presence in pattern at given index.

        Args:
            index: Index of the object button (0-8)
        """
        if index < 0 or index >= len(self.pattern_buttons):
            return
        self.logger.debug(f"Toggled object pattern button at index {index}")

        # Find parent ObjectExplorerWindow and call toggle_object_in_pattern
        parent: Any = self.parent()
        while parent:
            if hasattr(parent, 'toggle_object_in_pattern'):
                parent.toggle_object_in_pattern(index)  # type: ignore[attr-defined]
                return
            parent = parent.parent()

    def _setup_transparency_ui(self) -> None:
        """Setup overlay UI for transparency control."""
        # Just one button - toggle transparency on/off
        self.transparency_button = QPushButton("", self)
        self.transparency_button.setIcon(qta.icon("mdi.eye")) # type: ignore[arg-type]
        self.transparency_button.setIconSize(self.transparency_button.size() * 0.8)
        self.transparency_button.setFixedSize(32, 32)
        self.transparency_button.setFlat(True)
        self.transparency_button.setProperty("class", "map-overlay-button")
        self.transparency_button.clicked.connect(self.toggle_transparency)
        self.transparency_button.setToolTip("Toggle transparency [ Numpad 0 ]")

    def toggle_transparency(self) -> None:
        """add or remove _transparent suffix to object_id for all object in scene."""
        self.is_transparency_enabled = not self.is_transparency_enabled
        self.transparency_button.setIcon(qta.icon("mdi.eye{}".format("-off" if self.is_transparency_enabled else ""))) # type: ignore[arg-type]
        self.logger.info(f"Transparency toggled to: {self.is_transparency_enabled}")
        self.render_map()

    def _setup_rotation_ui(self) -> None:
        """Setup rotation and center buttons for isometric view."""
        # Container for rotation buttons
        self.rotation_buttons_container = QWidget(self)
        layout = QHBoxLayout(self.rotation_buttons_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Rotate CW button
        self.rotate_cw_button = QPushButton("", self.rotation_buttons_container)
        self.rotate_cw_button.setIcon(qta.icon("mdi.rotate-right")) # type: ignore[arg-type]
        self.rotate_cw_button.setIconSize(self.rotate_cw_button.size() * 0.8)
        self.rotate_cw_button.setFixedSize(32, 32)
        self.rotate_cw_button.setFlat(True)
        self.rotate_cw_button.setProperty("class", "map-overlay-button")
        self.rotate_cw_button.clicked.connect(self.rotate_cw)
        self.rotate_cw_button.setToolTip("Rotate clockwise [Numpad /]")
        layout.addWidget(self.rotate_cw_button)

        # Center button
        self.center_button = QPushButton("", self.rotation_buttons_container)
        self.center_button.setIcon(qta.icon("mdi.crosshairs-gps")) # type: ignore[arg-type]
        self.center_button.setIconSize(self.center_button.size() * 0.8)
        self.center_button.setFixedSize(32, 32)
        self.center_button.setFlat(True)
        self.center_button.setProperty("class", "map-overlay-button")
        self.center_button.clicked.connect(self.reset_rotation)
        self.center_button.setToolTip("Reset rotation [Numpad *]")
        layout.addWidget(self.center_button)

        # Rotate CCW button
        self.rotate_ccw_button = QPushButton("", self.rotation_buttons_container)
        self.rotate_ccw_button.setIcon(qta.icon("mdi.rotate-left")) # type: ignore[arg-type]
        self.rotate_ccw_button.setIconSize(self.rotate_ccw_button.size() * 0.8)
        self.rotate_ccw_button.setFixedSize(32, 32)
        self.rotate_ccw_button.setFlat(True)
        self.rotate_ccw_button.setProperty("class", "map-overlay-button")
        self.rotate_ccw_button.clicked.connect(self.rotate_ccw)
        self.rotate_ccw_button.setToolTip("Rotate counter-clockwise [Numpad -]")
        layout.addWidget(self.rotate_ccw_button)

        self.rotation_buttons_container.setFixedSize(98, 32)
        # Hide by default - only show for isometric view
        self.rotation_buttons_container.hide()
        self.rotation_buttons_container.raise_()

    def set_rotation_buttons_visible(self, visible: bool) -> None:
        """Show or hide rotation buttons (typically for isometric view only).

        Args:
            visible: True to show buttons, False to hide
        """
        if visible:
            self.rotation_buttons_container.show()
        else:
            self.rotation_buttons_container.hide()

    def toggle_animation(self) -> None:
        """Toggle animation start/stop."""
        if self.animation_controller.is_active():
            self.animation_controller.stop()
            self.animation_button.setIcon(qta.icon("mdi.play")) # type: ignore[arg-type]
            self.animation_button.setToolTip("Start animation [ Numpad Del ]")
            self.animation_button.setFixedSize(32, 32)
            self.frame_stats_label.hide()
            self.logger.debug("Animation paused by user")
        else:
            self.animation_controller.start()
            self.animation_button.setIcon(qta.icon("mdi.pause")) # type: ignore[arg-type]
            self.animation_button.setToolTip("Pause animation [ Numpad Del ]")
            self.animation_button.setFixedSize(32, 32)
            self.frame_stats_label.show()
            self.logger.debug("Animation started by user")

    def _update_animation_stats(self) -> None:
        """Update animation statistics display."""
        frame_delta_ms = self.animation_controller.get_frame_delta_ms()

        # Calculate FPS (avoid division by zero)
        fps = int(1000 / frame_delta_ms) if frame_delta_ms > 0 else 0

        self.frame_stats_label.setText(f"{frame_delta_ms}ms / {fps}fps")

        # Change class based on frame time
        if frame_delta_ms > 100:  # Less than 10 FPS
            self.frame_stats_label.setProperty("class", "frame-stats-red")
        elif frame_delta_ms > 50:  # Less than 20 FPS
            self.frame_stats_label.setProperty("class", "frame-stats-yellow")
        else:
            self.frame_stats_label.setProperty("class", "frame-stats")

        # Force style refresh
        self.frame_stats_label.style().unpolish(self.frame_stats_label)
        self.frame_stats_label.style().polish(self.frame_stats_label)

    def _initialize_components(self):
        """Initialize rendering components based on current map and tileset."""
        if not self.map:
            return

        # Create coordinate transformer from tileset
        self.transformer = CoordinateTransformer.from_tileset(
            self.tileset_service, self.current_tileset
        )

        # Get Z-level height from tileset
        z_level_height = 0
        if self.tileset_service and self.current_tileset:
            tileset = self.tileset_service.get_tileset(self.current_tileset)
            z_level_height = tileset.grid_z_height

        self.iso_view_map = self.map # Reset iso_view_map to original map

        # Create scene manager
        # Compute map dimensions in tiles from sector dimensions and counts
        if self.iso_view_map and self.transformer.is_isometric:
            scene_x_tiles = self.iso_view_map.sector_width * self.iso_view_map.num_sectors_x
            scene_y_tiles = self.iso_view_map.sector_height * self.iso_view_map.num_sectors_y
        else:
            scene_x_tiles = self.map.sector_width * self.map.num_sectors_x
            scene_y_tiles = self.map.sector_height * self.map.num_sectors_y
        scene_z_levels = self.map.num_z_levels

        self.scene_manager = SceneManager(
            scene_x_tiles,
            scene_y_tiles,
            scene_z_levels,
            self.transformer,
            z_level_height,
        )

        # Create grid renderer
        self.grid_renderer = GridRenderer(self._scene, self.transformer, self.scene_manager)

        # Create tile renderer
        self.tile_renderer = TileRenderer(
            self._scene,
            self.transformer,
            self.scene_manager,
            self.tileset_service,
            self.game_data_service,
            self.animation_state_manager,
        )
        if self.current_tileset:
            self.tile_renderer.set_current_tileset(self.current_tileset)
        self.tile_renderer.set_current_season(self.current_season)

        # Update scene rect
        self._scene.setSceneRect(
            0, 0, self.scene_manager.scene_width, self.scene_manager.scene_height
        )

    def set_tileset_service(self, service: TilesetService):
        """Set the tileset service for sprite loading."""
        self.tileset_service = service

        # Set first available tileset as current
        if service:
            available_tilesets = service.get_available_tilesets()
            if available_tilesets:
                self.current_tileset = available_tilesets[0]

        # Redraw if we have a map
        if self.map:
            self._initialize_components()
            self.render_map()

    def set_game_data_service(self, service: GameDataService):
        """Set the game data service for object information."""
        self.game_data_service = service

        # Update renderer if it exists
        if self.tile_renderer:
            self.tile_renderer.set_game_data_service(service)

        # Redraw if we have a map
        if self.map:
            self.render_map()

    def set_current_tileset(self, tileset_name: str):
        """Set the current active tileset."""
        self.current_tileset = tileset_name
        self.logger.debug(f"Current tileset set to: {tileset_name}")

        # Reinitialize components (tile size may have changed)
        if self.map:
            self._initialize_components()
            self.render_map()
            # Center view after tileset change (tile size may have changed)
            self.centerOn(self._scene.sceneRect().center())

    def set_current_season(self, season: str):
        """Set the current season for seasonal sprites."""
        if season not in self.SEASONS:
            self.logger.warning(f"Invalid season '{season}', using 'spring'")
            season = "spring"

        old_season = self.current_season
        self.current_season = season

        # Update renderer if it exists
        if self.tile_renderer:
            self.tile_renderer.set_current_season(season)

        # Refresh the scene if season changed
        if old_season != season:
            self.render_map()

    def set_rotation_state(self, rotation_state: int) -> None:
        """Set the rotation state of the view.

        Args:
            rotation_state: Number of 90° clockwise rotations (0, 1, 2, 3)
        """
        self._rotation_state = rotation_state % 4
        # Update grid renderer if it exists
        if self.grid_renderer:
            self.grid_renderer.set_rotation_state(self._rotation_state)
        self.logger.debug(f"Rotation state set to: {self._rotation_state * 90}°")

    def get_rotation_state(self) -> int:
        """Get the current rotation state.

        Returns:
            Number of 90° clockwise rotations (0, 1, 2, 3)
        """
        return self._rotation_state

    def rotate_cw(self) -> None:
        """Rotate view clockwise by 90°."""
        if self.iso_view_map:
            self.iso_view_map = self.iso_view_map.rotateCW()
        self.logger.info("Rotated view clockwise by 90°")
        self.set_rotation_state(self._rotation_state + 1)
        self.render_map()

    def rotate_ccw(self) -> None:
        """Rotate view counter-clockwise by 90°."""
        if self.iso_view_map:
            self.iso_view_map = self.iso_view_map.rotateCCW()
        self.logger.info("Rotated view counter-clockwise by 90°")
        self.set_rotation_state(self._rotation_state - 1)
        self.render_map()

    def reset_rotation(self) -> None:
        """Reset rotation to initial state (0°)."""
        self.iso_view_map = self.map # Reset iso_view_map to original map
        self.logger.info("Reset view rotation to 0°")
        self.set_rotation_state(0)
        self.centerOn(self._scene.sceneRect().center())
        self.render_map()

    def set_map(self, map: DemoMap):
        """Set the map to display.

        Note: This only initializes the view components. Call render_map()
        explicitly to draw the map content.
        """
        self.map = map
        # Log computed map tile dimensions
        try:
            mx = map.sector_width * map.num_sectors_x
            my = map.sector_height * map.num_sectors_y
            self.logger.debug(f"Map set: tiles {mx}x{my}, z-levels {map.num_z_levels}")
        except Exception:
            self.logger.debug("Map set")

        # Initialize rendering components (transformer, scene_manager, renderers)
        self._initialize_components()

        # Center view on scene (but don't render yet)
        self.centerOn(self._scene.sceneRect().center())

        # rendering here is just for testing purposes. will be removed later.
        #self.render_map()

    def set_grid_visible(self, visible: bool):
        """Set grid visibility."""
        self.grid_visible = visible
        if self.map:
            self.render_map()
        self.logger.debug(f"Grid visibility: {visible}")

    def set_zoom_factor(self, zoom_factor: float) -> None:
        """Set absolute zoom factor for the view."""
        if zoom_factor <= 0:
            self.logger.warning(f"Invalid zoom factor: {zoom_factor}")
            return

        self._zoom_factor = zoom_factor
        self.resetTransform()
        self.scale(zoom_factor, zoom_factor)
        self.centerOn(self._scene.sceneRect().center())

    def get_zoom_factor(self) -> float:
        """Get current zoom factor."""
        return self._zoom_factor

    def set_current_z_level(self, z_level: int) -> None:
        """Set current z-level and refresh view.

        Args:
            z_level: Z-level to set (0-based index)
        """
        if not self.map:
            return

        # Clamp to valid range
        max_z = self.map.num_z_levels - 1
        z_level = max(0, min(max_z, z_level))

        if self.current_z_level != z_level:
            self.current_z_level = z_level
            self.logger.debug(f"Current z-level set to: {z_level}")
            if self.map:
                self.render_map()

    def get_current_z_level(self) -> int:
        """Get current z-level."""
        return self.current_z_level

    def render_map(self):
        """Render the current map."""
        if not self.map:
            return

        # Clear scene
        self._scene.clear()

        # Draw grid if enabled
        if self.grid_visible and self.grid_renderer:
            scene_x_tiles = self.map.sector_width * self.map.num_sectors_x
            scene_y_tiles = self.map.sector_height * self.map.num_sectors_y
            min_z = self.map.min_z_level
            max_z = self.map.max_z_level

            # Get z-level height from tileset
            z_level_height = 0
            if self.tileset_service and self.current_tileset:
                tileset = self.tileset_service.get_tileset(self.current_tileset)
                z_level_height = tileset.grid_z_height

            self.grid_renderer.draw_grid(scene_x_tiles, scene_y_tiles, min_z, max_z, z_level_height, self.current_z_level)

        # Draw map content
        self._draw_map_content()

        self.logger.debug("Map rendered")

    @staticmethod
    def _get_object_id_from_slot(cell: Optional[MapCell], slot: CellSlot) -> Optional[str]:
        """Extract object_id from a specific slot in a cell.

        For MULTIPLE-capacity slots with multiple objects, returns the last one.

        Args:
            cell: The MapCell to extract from (can be None)
            slot: The slot to query

        Returns:
            object_id string, or None if cell is None or slot is empty
        """
        if cell is None:
            return None

        content_list = cell.get_all_content_in_slot(slot)
        if not content_list:
            return None

        # Return last object if multiple
        return content_list[-1].object_id

    def _draw_map_content(self):
        """Draw the actual map content (objects/terrain) in layers.

        Supports multi-z-level rendering with brightness and transparency adjustments.
        """

        if not self.map or not self.iso_view_map or not self.tile_renderer or not self.transformer:
            return

        # Check if multi-z-level rendering is enabled
        mzl_settings = self.settings.multi_z_level if self.settings else None
        multi_z_enabled = mzl_settings.enabled if mzl_settings else False

        self.logger.debug(
            f"Rendering map: multi_z_enabled={multi_z_enabled}, current_z_level={self.current_z_level}"
        )

        if multi_z_enabled and mzl_settings:
            # Multi-z-level rendering
            z_low = max(self.map.min_z_level, self.current_z_level - mzl_settings.levels_below)
            z_high = min(
                self.map.max_z_level,
                self.current_z_level + mzl_settings.levels_above
            )

            self.logger.debug(
                f"Multi-z-level: rendering z-levels {z_low} to {z_high} (current={self.current_z_level})"
            )

            # Get z-level height from tileset
            z_level_height = 0
            if self.tileset_service and self.current_tileset:
                tileset = self.tileset_service.get_tileset(self.current_tileset)
                z_level_height = tileset.grid_z_height

            # Render from bottom to top
            for z in range(z_low, z_high + 1):
                z_offset = z - self.current_z_level

                # Calculate brightness and transparency for this level
                if z_offset < 0:
                    operation = mzl_settings.brightness_operation_below
                elif z_offset > 0:
                    operation = mzl_settings.brightness_operation_above
                else:
                    operation = "None"  # type: ignore

                brightness_factor = mzl_settings.calculate_brightness_factor(
                    z_offset, operation
                )
                transparency_factor = mzl_settings.calculate_transparency_factor(z_offset)

                # Calculate Y offset for this z-level
                y_offset = -z_offset * z_level_height

                self.logger.debug(
                    f"  z={z}: offset={z_offset}, y_offset={y_offset}, "
                    f"brightness={brightness_factor:.2f}, transparency={transparency_factor:.2f}"
                )

                self._render_single_z_level(
                    z, y_offset, brightness_factor, transparency_factor
                )
        else:
            # Single z-level rendering (current level only)
            self._render_single_z_level(self.current_z_level, 0, 1.0, 1.0)

    def _render_single_z_level(
        self, z: int, y_offset: int, brightness_factor: float, transparency_factor: float
    ):
        """Render a single z-level with given adjustments.

        Args:
            z: Z-level to render
            y_offset: Y offset in scene coordinates (for z-level stacking)
            brightness_factor: Brightness adjustment (0.0-2.0+, 1.0 = normal)
            transparency_factor: Transparency factor (0.0 = invisible, 1.0 = opaque)
        """
        if not self.map or not self.iso_view_map or not self.tile_renderer or not self.transformer:
            return

        # Check if z-level is valid
        if z < self.map.min_z_level or z > self.map.max_z_level:
            self.logger.warning(
                f"Invalid z-level {z}, map range is [{self.map.min_z_level}, {self.map.max_z_level}]"
            )
            return

        # Calculate brightness and transparency factors for this z-level
        multi_z_settings = self.settings.multi_z_level
        z_diff = z - self.current_z_level

        # Determine operation based on z-level offset
        if z_diff < 0:
            operation = multi_z_settings.brightness_operation_below
        elif z_diff > 0:
            operation = multi_z_settings.brightness_operation_above
        else:
            operation = "None"  # type: ignore

        brightness_factor = multi_z_settings.calculate_brightness_factor(z_diff, operation)
        transparency_factor = multi_z_settings.calculate_transparency_factor(z_diff)

        if self.transformer.is_isometric:
            width_in_cells = self.iso_view_map.sector_width * self.iso_view_map.num_sectors_x
            height_in_cells = self.iso_view_map.sector_height * self.iso_view_map.num_sectors_y
            # ISO: collect tiles for this layer and sort by scene position
            tiles: list[TileRenderInfo] = []

            for y in range(height_in_cells):
                for x in range(width_in_cells):
                    cell = self.iso_view_map.get_cell_at(x, y, z)

                    if cell:
                        # Sort by scene position (Y first, then X)
                        sort_key = self.transformer.get_iso_sort_key(x, y)
                        tiles.append(TileRenderInfo(sort_key, x, y, cell))

            # Sort by scene position
            tiles.sort(key=lambda tile: tile.sort_key)

            # Render in sorted order
            for tile in tiles:
                # Fetch neighbors for rendering
                neighbor_cells = self.iso_view_map.get_neighbor_cells(tile.x, tile.y, z)
                self.tile_renderer.render_tile(
                    tile.x, tile.y, tile.cell, neighbor_cells,
                    transparency=self.is_transparency_enabled,
                    y_offset_zlevel=y_offset,
                    brightness_factor=brightness_factor,
                    transparency_factor=transparency_factor
                )
        else:
            # Orthogonal: draw row by row (natural order)
            width_in_cells = self.map.sector_width * self.map.num_sectors_x
            height_in_cells = self.map.sector_height * self.map.num_sectors_y
            for y in range(height_in_cells):
                for x in range(width_in_cells):
                    cell = self.map.get_cell_at(x, y, z)

                    if cell:
                        # Get neighbors
                        neighbor_cells = self.map.get_neighbor_cells(x, y, z)
                        self.tile_renderer.render_tile(
                            x, y, cell, neighbor_cells,
                            transparency=self.is_transparency_enabled,
                            y_offset_zlevel=y_offset,
                            brightness_factor=brightness_factor,
                            transparency_factor=transparency_factor
                        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle widget resize to reposition overlay UI elements."""
        super().resizeEvent(event)

        # Position animation button (top-left)
        self.animation_ui_container.move(0, 0)
        self.animation_button.move(0, 0)
        self.frame_stats_label.move(33,0)

        # Position rotation buttons (bottom-center)
        width = self.width()
        x_pos = (width - self.rotation_buttons_container.width()) // 2
        y_pos = self.height() - self.rotation_buttons_container.height() - 15
        self.rotation_buttons_container.move(x_pos, y_pos)

        # now we need to add object pattern buttons (top-right)
        self.objects_pattern_container.move(
            self.width() - 52, # 3*12
            0
        )

        # Position transparency button (bottom-left)
        # Move transparency button only if it was created
        if hasattr(self, "transparency_button"):
            try:
                self.transparency_button.move(0, self.height() - self.transparency_button.height() - 15)
            except Exception:
                # Be defensive: any issue moving the button should not crash the app
                self.logger.exception("Failed to position transparency button")
