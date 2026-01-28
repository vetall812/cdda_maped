"""Action handlers for Object Explorer window.

Handles user interactions and state management.
"""

import logging
from typing import TYPE_CHECKING, Any, Optional  # , cast

if TYPE_CHECKING:
    from .window import ObjectExplorerWindow

from cdda_maped.maps import MapCell  # , DemoMap


class ObjectExplorerActions:
    """Handles actions and events for the Object Explorer window."""

    def __init__(self, explorer_window: "ObjectExplorerWindow") -> None:
        """
        Initialize actions handler.

        Args:
            explorer_window: ObjectExplorerWindow instance
        """
        self.explorer_window = explorer_window
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.current_object_id: Optional[str] = None
        # Track resolved IDs for current object (if using looks_like)
        self.current_resolved_ortho_id: Optional[str] = None
        self.current_resolved_iso_id: Optional[str] = None

    def on_tileset_ortho_changed(self, tileset_name: str) -> None:
        """Handle orthogonal tileset change."""
        ew = self.explorer_window
        self.logger.info(f"Ortho tileset changed to: {tileset_name}")
        if hasattr(ew, "view_ortho"):
            ew.view_ortho.set_current_tileset(tileset_name)
        # Update JSON display if object is selected
        if self.current_object_id:
            self.update_json_displays(self.current_object_id)

    def on_tileset_iso_changed(self, tileset_name: str) -> None:
        """Handle isometric tileset change."""
        ew = self.explorer_window
        self.logger.info(f"Iso tileset changed to: {tileset_name}")
        if hasattr(ew, "view_iso"):
            ew.view_iso.set_current_tileset(tileset_name)
        # Update JSON display if object is selected
        if self.current_object_id:
            self.update_json_displays(self.current_object_id)

    def on_season_changed(self, season: str) -> None:
        """Handle season change - syncs both views."""
        ew = self.explorer_window
        self.logger.info(f"Season changed to: {season}")
        # Update both views
        if hasattr(ew, "view_ortho"):
            ew.view_ortho.set_current_season(season)
        if hasattr(ew, "view_iso"):
            ew.view_iso.set_current_season(season)
        # Update JSON displays if object is selected
        if self.current_object_id:
            self.update_json_displays(self.current_object_id)

    def on_zoom_changed(self, zoom_factor: float) -> None:
        """Handle zoom selector changes and apply to both views."""
        ew = self.explorer_window
        self.logger.debug(f"Zoom changed to: {zoom_factor}x")
        if hasattr(ew, "view_ortho"):
            ew.view_ortho.set_zoom_factor(zoom_factor)
        if hasattr(ew, "view_iso"):
            ew.view_iso.set_zoom_factor(zoom_factor)
        if hasattr(ew, "statusBar"):
            ew.statusBar().showMessage(f"Zoom {zoom_factor}x", 1000)

    def on_demo_map_changed(self, demo_id: str) -> None:
        """Handle demo map change - loads new map for both views."""
        ew = self.explorer_window
        self.logger.info(f"Demo map changed to: {demo_id}")

        try:
            # Load new demo map (shared by both views)
            ew.demo_map = ew.map_manager.get_demomap(demo_id)

            # Update both views with new map
            if hasattr(ew, "view_ortho"):
                ew.view_ortho.set_map(ew.demo_map)
            if hasattr(ew, "view_iso"):
                ew.view_iso.set_map(ew.demo_map)

            # Re-render current object if any is selected
            if self.current_object_id:
                self.on_object_selected(self.current_object_id)

            if hasattr(ew, "statusBar"):
                ew.statusBar().showMessage(f"Demo map: {demo_id}", 2000)

        except Exception as e:
            self.logger.error(f"Failed to load demo map '{demo_id}': {e}")
            if hasattr(ew, "statusBar"):
                ew.statusBar().showMessage(f"Error loading demo map: {e}", 5000)

    def on_object_selected(self, object_id: str) -> None:
        """Handle object selection from browser - syncs both views."""
        ew = self.explorer_window
        # Track current object
        self.current_object_id = object_id
        # Persist selected object for next session
        try:
            ew.settings.settings.setValue("explorer/current_object_id", object_id)
            ew.settings.settings.sync()
        except Exception as e:
            self.logger.warning(f"Failed to persist current object id: {e}")

        # Place selected object in center of map (if it exists)
        if hasattr(ew, "demo_map") and hasattr(ew, "game_data_service"):
            try:
                # Calculate map center in world coordinates
                width_in_cells = ew.demo_map.sector_width * ew.demo_map.num_sectors_x
                height_in_cells = ew.demo_map.sector_height * ew.demo_map.num_sectors_y
                center_x = width_in_cells // 2
                center_y = height_in_cells // 2
                z = 0

                # Get game object to determine its type and slot
                game_object = ew.game_data_service.get_resolved_object(object_id)
                if not game_object:
                    self.logger.warning(f"Game object not found: {object_id}")
                    return

                # Determine which slot this object belongs to
                object_type = game_object.get("type", "furniture")
                slot = MapCell.get_slot_for_object_type(object_type)

                # Place object in map (shared by both views)
                cell = ew.demo_map.get_cell_at(center_x, center_y, z)
                if cell is None:
                    cell = MapCell()
                cell.set_content(slot, object_id, quantity=1)
                try:
                    ew.demo_map.set_cell_at(center_x, center_y, z, cell)
                except ValueError as e:
                    self.logger.error(f"Failed to place object on map: {e}")
                    return

                self.logger.debug(
                    f"Object {object_id} placed at ({center_x}, {center_y}) in slot {slot.name}"
                )

                # Update object pattern state: set center button (index 4) as active
                ew.object_pattern_state = [False] * 9  # Reset all
                ew.object_pattern_state[4] = True  # Center is active
                ew.current_object_id = object_id

                # Update button icons in both views using window's method
                ew.update_button_icons()

                # Reset z-level to 0 for both views
                if hasattr(ew, "view_ortho"):
                    ew.view_ortho.set_current_z_level(0)
                if hasattr(ew, "view_iso"):
                    ew.view_iso.set_current_z_level(0)

                # Redraw both maps
                if hasattr(ew, "view_ortho"):
                    ew.view_ortho.render_map()
                    self.logger.debug(f"Ortho view rendered for {object_id}")
                    # Get resolved ID from ortho renderer
                    tile_renderer = ew.view_ortho.tile_renderer
                    if tile_renderer and hasattr(
                        tile_renderer, "get_resolved_object_id"
                    ):
                        self.current_resolved_ortho_id = (
                            tile_renderer.get_resolved_object_id(center_x, center_y)
                        )
                        if self.current_resolved_ortho_id:
                            self.logger.debug(
                                f"Ortho: {object_id} -> {self.current_resolved_ortho_id} via looks_like"
                            )
                    else:
                        self.current_resolved_ortho_id = None

                if hasattr(ew, "view_iso"):
                    ew.view_iso.render_map()
                    self.logger.debug(f"Iso view rendered for {object_id}")
                    # Get resolved ID from iso renderer
                    tile_renderer = ew.view_iso.tile_renderer
                    if tile_renderer and hasattr(
                        tile_renderer, "get_resolved_object_id"
                    ):
                        self.current_resolved_iso_id = (
                            tile_renderer.get_resolved_object_id(center_x, center_y)
                        )
                        if self.current_resolved_iso_id:
                            self.logger.debug(
                                f"Iso: {object_id} -> {self.current_resolved_iso_id} via looks_like"
                            )
                    else:
                        self.current_resolved_iso_id = None

                # Update JSON displays AFTER rendering
                self.update_json_displays(object_id)
            except Exception as e:
                self.logger.error(f"Failed to place object on map: {e}")
                # Still update JSON displays even if map rendering failed
                self.update_json_displays(object_id)
        else:
            self.logger.warning(
                "on_object_selected: demo_map or game_data_service not found"
            )
            # Still update JSON displays even if map rendering failed
            self.update_json_displays(object_id)

    def update_json_displays(self, object_id: str) -> None:
        """Update JSON display panels with object data."""
        ew = self.explorer_window
        try:
            # Get game object data (always use original object_id)
            game_object = None
            if hasattr(ew, "game_data_service"):
                game_object = ew.game_data_service.get_resolved_object(object_id)
                ew.game_json_display.set_json_data(game_object)
            else:
                ew.game_json_display.clear()

            # Get tileset data (ortho) - use stored resolved ID
            if hasattr(ew, "tileset_service") and hasattr(ew, "view_ortho"):
                resolved_ortho_id = self.current_resolved_ortho_id or object_id
                current_season = (
                    ew.view_ortho.current_season
                    if hasattr(ew.view_ortho, "current_season")
                    else "spring"
                )

                self._update_tileset_json_display(
                    tileset_name=ew.view_ortho.current_tileset,
                    original_object_id=object_id,
                    resolved_object_id=resolved_ortho_id,
                    game_object=game_object,
                    target_widget=ew.tileset_json_display,
                    season=current_season,
                )
            else:
                ew.tileset_json_display.clear()

            # Get tileset data (iso) - use stored resolved ID
            if hasattr(ew, "tileset_service") and hasattr(ew, "view_iso"):
                resolved_iso_id = self.current_resolved_iso_id or object_id
                current_season = (
                    ew.view_iso.current_season
                    if hasattr(ew.view_iso, "current_season")
                    else "spring"
                )

                self._update_tileset_json_display(
                    tileset_name=ew.view_iso.current_tileset,
                    original_object_id=object_id,
                    resolved_object_id=resolved_iso_id,
                    game_object=game_object,
                    target_widget=ew.tileset_iso_json_display,
                    season=current_season,
                )
            else:
                ew.tileset_iso_json_display.clear()

        except Exception as e:
            self.logger.error(f"Failed to update JSON displays: {e}")
            ew.game_json_display.set_json_data({"error": str(e)})
            ew.tileset_json_display.set_json_data({"error": str(e)})
            ew.tileset_iso_json_display.set_json_data({"error": str(e)})

    def _update_tileset_json_display(
        self,
        tileset_name: Optional[str],
        original_object_id: str,
        resolved_object_id: str,
        game_object: Optional[dict[str, Any]],
        target_widget: Any,
        season: str = "spring",
    ) -> None:
        """Helper to update tileset JSON display for a given tileset."""
        ew = self.explorer_window
        if not tileset_name:
            target_widget.clear()
            return

        # Get fallback data from game object (use original object for fallback data)
        fallback_color = "white"
        fallback_symbol = "?"
        if game_object:
            raw_color = game_object.get("color", "white")
            raw_symbol = game_object.get("symbol", "?")

            # Ensure fallback values are strings, not lists
            # Handle color (can be string or list)
            if isinstance(raw_color, str):
                fallback_color = raw_color
            elif isinstance(raw_color, list) and raw_color:
                fallback_color = str(raw_color[0])  # type: ignore
            else:
                fallback_color = "white"

            # Handle symbol (can be string or list)
            if isinstance(raw_symbol, str):
                fallback_symbol = raw_symbol
            elif isinstance(raw_symbol, list) and raw_symbol:
                fallback_symbol = str(raw_symbol[0])  # type: ignore
            else:
                fallback_symbol = "?"

        # Get tile object (use resolved_object_id for tileset lookup with season)
        tile_object = ew.tileset_service.get_object_and_sprites_with_priority(
            tileset_name=tileset_name,
            object_id=resolved_object_id,
            fallback_color=fallback_color,
            fallback_symbol=fallback_symbol,
            season=season,
        )

        # Convert TileObject to dict for display (keeping source as-is)
        # Safe conversion of sprite keys (some might be lists)
        try:
            sprite_keys = [
                str(key) if isinstance(key, (list, tuple)) else str(key)
                for key in tile_object.sprites.keys()
            ]
        except Exception:
            sprite_keys = ["<complex_keys>"]

        tileset_data: dict[str, Any] = {
            "source": tile_object.source,
            "style": tile_object.style,
            "sprite_count": len(tile_object.sprites),
            "sprite_indices": sprite_keys,
            "season": season,
        }

        # Add metadata if object was resolved via looks_like
        if resolved_object_id != original_object_id:
            tileset_data = {
                "_original_id": original_object_id,
                "_resolved_via": "looks_like",
                "_actual_id": resolved_object_id,
                **tileset_data,
            }

        target_widget.set_json_data(tileset_data)

    def reset_view_proportions(self) -> None:
        """Reset the proportions of the ortho and iso views to 50/50."""
        ew = self.explorer_window
        ew.layout_builder.reset_view_proportions()

    def reset_widget_layout(self) -> None:
        """Reset all dock widgets to default positions and sizes."""
        ew = self.explorer_window
        ew.layout_builder.reset_widget_layout()

    def increase_z_level(self) -> None:
        """Increase current z-level (move up)."""
        ew = self.explorer_window
        if hasattr(ew, "view_ortho") and ew.view_ortho:
            current_z = ew.view_ortho.current_z_level
            max_z = ew.view_ortho.map.max_z_level if ew.view_ortho.map else 0
            if current_z < max_z:
                new_z = current_z + 1
                ew.view_ortho.current_z_level = new_z
                ew.view_ortho.render_map()
                self.logger.info(f"Z-level increased to {new_z}")
                if hasattr(ew, "statusBar"):
                    ew.statusBar().showMessage(f"Z-level: {new_z}", 1500)

        if hasattr(ew, "view_iso") and ew.view_iso:
            current_z = ew.view_iso.current_z_level
            max_z = ew.view_iso.map.max_z_level if ew.view_iso.map else 0
            if current_z < max_z:
                new_z = current_z + 1
                ew.view_iso.current_z_level = new_z
                ew.view_iso.render_map()

    def decrease_z_level(self) -> None:
        """Decrease current z-level (move down)."""
        ew = self.explorer_window
        if hasattr(ew, "view_ortho") and ew.view_ortho:
            current_z = ew.view_ortho.current_z_level
            min_z = ew.view_ortho.map.min_z_level if ew.view_ortho.map else 0
            if current_z > min_z:
                new_z = current_z - 1
                ew.view_ortho.current_z_level = new_z
                ew.view_ortho.render_map()
                self.logger.info(f"Z-level decreased to {new_z}")
                if hasattr(ew, "statusBar"):
                    ew.statusBar().showMessage(f"Z-level: {new_z}", 1500)

        if hasattr(ew, "view_iso") and ew.view_iso:
            current_z = ew.view_iso.current_z_level
            min_z = ew.view_iso.map.min_z_level if ew.view_iso.map else 0
            if current_z > min_z:
                new_z = current_z - 1
                ew.view_iso.current_z_level = new_z
                ew.view_iso.render_map()
