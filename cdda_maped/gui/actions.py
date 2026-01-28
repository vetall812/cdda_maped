"""Action handlers for MainWindow.

Keeps UI action logic separate from window construction/layout.
Mirrors the pattern used in object_explorer_window.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QDialog, QMessageBox

from .. import __version__
from .dialogs import (
    LoggingSettingsDialog,
    ModSelectionDialog,
    show_about_dialog,
    AnimationTimeoutDialog,
)
from ..utils.gui_log_manager import get_gui_log_manager, toggle_gui_log

if TYPE_CHECKING:
    from .main_window import MainWindow


class MainWindowActions:
    """Handles actions and events for the main window."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.main_window = main_window
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def new_map(self) -> None:
        """Create a new map."""
        mw = self.main_window
        mw.logger.info("New map requested")
        mw.status_bar.showMessage("New map feature not yet implemented", 3000)

    def open_map(self) -> None:
        """Open an existing map."""
        mw = self.main_window
        mw.logger.info("Open map requested")
        file_path, _ = QFileDialog.getOpenFileName(
            mw, "Open Map", str(Path.cwd()), "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            mw.logger.info(f"Selected file: {file_path}")
            mw.status_bar.showMessage(
                f"Map opening not yet implemented: {Path(file_path).name}", 3000
            )

    def save_map(self) -> None:
        """Save the current map."""
        mw = self.main_window
        mw.logger.info("Save map requested")
        mw.status_bar.showMessage("Save feature not yet implemented", 3000)

    def save_map_as(self) -> None:
        """Save the current map with a new name."""
        mw = self.main_window
        mw.logger.info("Save as requested")
        file_path, _ = QFileDialog.getSaveFileName(
            mw,
            "Save Map As",
            str(Path.cwd() / "new_map.json"),
            "JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            mw.logger.info(f"Selected save path: {file_path}")
            mw.status_bar.showMessage(
                f"Save as not yet implemented: {Path(file_path).name}", 3000
            )

    def about(self) -> None:
        """Show about dialog."""
        mw = self.main_window
        game_path = str(mw.settings.cdda_path) if mw.settings.cdda_path else None
        show_about_dialog(
            version=__version__,
            game_path=game_path,
            parent=mw,
        )

    def setup_game_path(self) -> None:
        """Show dialog to configure CDDA game directory path."""
        mw = self.main_window

        current_path = mw.settings.cdda_path
        initial_dir = str(current_path) if current_path else str(Path.cwd())

        selected_dir = QFileDialog.getExistingDirectory(
            mw,
            "Select CDDA Game Directory",
            initial_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if not selected_dir:
            return

        game_path = Path(selected_dir).resolve()

        if not self._validate_cdda_path(game_path):
            reply = QMessageBox.question(
                mw,
                "Invalid CDDA Directory",
                "The selected directory doesn't appear to be a valid CDDA installation.\n\n"
                "Expected to find 'data' folder and/or 'gfx' folder.\n\n"
                f"Selected: {game_path}\n\n"
                "Do you want to use it anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                # User rejected invalid path - show path selection dialog again
                self.setup_game_path()
                return

        old_path = mw.settings.cdda_path
        mw.settings.cdda_path = game_path
        mw.settings.sync()

        mw.logger.info(f"CDDA path updated: {old_path} -> {game_path}")
        if hasattr(mw, "status_bar") and mw.status_bar:
            mw.status_bar.showMessage(f"CDDA path set to: {game_path.name}", 3000)

        # Show log window before reloading services
        from ..utils.gui_log_manager import get_gui_log_manager

        gui_log_manager = get_gui_log_manager()
        if gui_log_manager and gui_log_manager.is_available():
            gui_log_manager.show_window()

        try:
            mw.setup_demo_content()
            QMessageBox.information(
                mw,
                "Game Path Updated",
                "CDDA game path has been successfully updated to:\n"
                f"{game_path}\n\n"
                "Game data and tilesets have been reloaded.",
            )

            # TODO: This focus transfer is temporary until main window is no longer a stub.
            # Once main window has a proper map view, focus should remain on main window.
            # Transfer focus to Object Explorer window after reload
            if hasattr(mw, "object_explorer_window") and mw.object_explorer_window:
                mw.object_explorer_window.activateWindow()
                mw.object_explorer_window.raise_()
                if (
                    hasattr(mw.object_explorer_window, "view_ortho")
                    and mw.object_explorer_window.view_ortho
                ):
                    mw.object_explorer_window.view_ortho.setFocus()
        except Exception as e:
            mw.logger.error(f"Failed to reload content with new path: {e}")
            QMessageBox.warning(
                mw,
                "Reload Failed",
                "CDDA path was updated, but failed to reload content:\n"
                f"{e}\n\n"
                "You may need to restart the application.",
            )

    def select_mods(self) -> None:
        """Show mod selection dialog."""
        mw = self.main_window

        if not hasattr(mw, "game_data_service") or not mw.game_data_service:
            QMessageBox.warning(
                mw,
                "No Game Data",
                "Game data must be loaded first. Please configure the CDDA path in settings.",
            )
            return

        try:
            dialog = ModSelectionDialog(mw)

            available_mods = mw.game_data_service.get_available_mods()
            dialog.set_available_mods(available_mods)

            dialog.set_active_mods(mw.settings.active_mods)
            dialog.set_always_include_core(mw.settings.always_include_core)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            new_active_mods = dialog.get_active_mods()
            mw.settings.active_mods = new_active_mods

            new_always_include_core = dialog.get_always_include_core()
            mw.settings.always_include_core = new_always_include_core

            mw.logger.info(
                f"Mod configuration updated: {len(new_active_mods)} active mods"
            )
            mw.status_bar.showMessage(
                f"Mod configuration updated: {len(new_active_mods)} active mods",
                3000,
            )

            if hasattr(mw, "object_browser") and mw.object_browser:
                mw.object_browser.refresh()

            if hasattr(mw, "object_explorer_window") and mw.object_explorer_window:
                try:
                    if hasattr(mw.object_explorer_window, "object_browser"):
                        mw.object_explorer_window.object_browser.refresh()
                except Exception as e:
                    mw.logger.error(f"Failed to refresh Object Explorer browser: {e}")

        except Exception as e:
            mw.logger.error(f"Failed to show mod selection dialog: {e}")
            QMessageBox.critical(
                mw, "Error", f"Failed to update mod configuration:\n{e}"
            )

    def type_slot_mapping_settings(self) -> None:
        """Show type-slot mapping configuration dialog."""
        mw = self.main_window

        if not hasattr(mw, "game_data_service") or not mw.game_data_service:
            QMessageBox.warning(
                mw,
                "No Game Data",
                "Game data must be loaded first. Please configure the CDDA path in settings.",
            )
            return

        try:
            from .dialogs import TypeSlotMappingDialog

            # Get all discovered object types from game data
            available_types = mw.game_data_service.get_types()

            dialog = TypeSlotMappingDialog(mw.settings, available_types, mw)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                mw.logger.info("Type-slot mapping updated")
                mw.status_bar.showMessage("Type-slot mapping updated", 3000)

                # Refresh object browsers to reflect new mapping
                if hasattr(mw, "object_browser") and mw.object_browser:
                    mw.object_browser.refresh()

                if hasattr(mw, "object_explorer_window") and mw.object_explorer_window:
                    try:
                        if hasattr(mw.object_explorer_window, "object_browser"):
                            mw.object_explorer_window.object_browser.refresh()
                    except Exception as e:
                        mw.logger.error(
                            f"Failed to refresh Object Explorer browser: {e}"
                        )

        except Exception as e:
            mw.logger.error(f"Failed to show type-slot mapping dialog: {e}")
            QMessageBox.critical(
                mw, "Error", f"Failed to open type-slot mapping dialog:\n{e}"
            )

    def logging_settings(self) -> None:
        """Show logging settings dialog."""
        mw = self.main_window
        try:
            dialog = LoggingSettingsDialog(mw.settings, mw)
            dialog.exec()
        except Exception as e:
            mw.logger.error(
                f"Error showing logging settings dialog: {e}", exc_info=True
            )

    def animation_timeout_settings(self) -> None:
        """Show animation timeout settings dialog."""
        mw = self.main_window
        try:
            dialog = AnimationTimeoutDialog(mw.settings, mw)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                mw.status_bar.showMessage(
                    f"Animation timeout set to: {mw.settings.editor.animation_timeout} ms",
                    3000,
                )
        except Exception as e:
            mw.logger.error(
                f"Error showing animation timeout dialog: {e}", exc_info=True
            )
            QMessageBox.critical(
                mw, "Error", f"Failed to show logging settings dialog:\n{e}"
            )

    def multi_z_level_settings(self) -> None:
        """Show multi-z-level rendering settings dialog."""
        mw = self.main_window
        try:
            from .dialogs import MultiZLevelDialog

            dialog = MultiZLevelDialog(mw.settings, mw)

            # Connect settings changed signal to refresh views
            dialog.settings_changed.connect(self._on_multi_z_settings_changed)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                mw.status_bar.showMessage("Multi-z-level settings updated", 3000)
        except Exception as e:
            mw.logger.error(
                f"Error showing multi-z-level settings dialog: {e}", exc_info=True
            )
            QMessageBox.critical(
                mw, "Error", f"Failed to show multi-z-level settings dialog:\n{e}"
            )

    def _on_multi_z_settings_changed(self) -> None:
        """Handle multi-z-level settings changes - refresh Object Explorer views."""
        mw = self.main_window
        mw.logger.debug(
            "Multi-z-level settings changed, refreshing Object Explorer views"
        )

        # Refresh Object Explorer views if they exist
        if hasattr(mw, "object_explorer_window") and mw.object_explorer_window:
            ew = mw.object_explorer_window
            try:
                if hasattr(ew, "view_ortho") and ew.view_ortho and ew.view_ortho.map:
                    ew.view_ortho.render_map()
                if hasattr(ew, "view_iso") and ew.view_iso and ew.view_iso.map:
                    ew.view_iso.render_map()
            except Exception as e:
                mw.logger.error(f"Failed to refresh Object Explorer views: {e}")

    def toggle_object_explorer_window(self) -> None:
        """Toggle Object Explorer window visibility."""
        mw = self.main_window
        if not hasattr(mw, "object_explorer_window"):
            mw.show_object_explorer_window_if_ready()
            return

        if mw.object_explorer_window.isVisible():
            mw.object_explorer_window.hide()
            mw.status_bar.showMessage(
                "Object Explorer window hidden (F2 to show)", 2000
            )
        else:
            mw.object_explorer_window.show()
            mw.status_bar.showMessage("Object Explorer window shown (F2 to hide)", 2000)

    def open_object_explorer_with_selected_object(self) -> None:
        """Open Object Explorer and focus it on the currently selected object."""
        mw = self.main_window

        if not hasattr(mw, "object_browser") or not mw.object_browser:
            mw.status_bar.showMessage("Object Browser not available", 2000)
            return

        object_id = mw.object_browser.get_selected_object_id()
        if not object_id:
            mw.status_bar.showMessage("No object selected", 2000)
            return

        # Ensure window exists
        if not hasattr(mw, "object_explorer_window"):
            mw.show_object_explorer_window_if_ready()

        if not hasattr(mw, "object_explorer_window"):
            mw.status_bar.showMessage(
                "Object Explorer not available (services not loaded)",
                3000,
            )
            return

        ew = mw.object_explorer_window

        try:
            ew.show()
            try:
                ew.raise_()
                ew.activateWindow()
            except Exception:
                pass

            # Prefer a dedicated method if present.
            if hasattr(ew, "select_object_id"):
                ew.select_object_id(object_id)
            else:
                # Fallback: persist and call action handler if available.
                try:
                    ew.settings.settings.setValue(
                        "explorer/current_object_id", object_id
                    )
                    ew.settings.settings.sync()
                except Exception:
                    pass
                if hasattr(ew, "action_handler"):
                    ew.action_handler.on_object_selected(object_id)

            mw.status_bar.showMessage(f"Opened in Object Explorer: {object_id}", 2000)
        except Exception as e:
            mw.logger.error(f"Failed to open Object Explorer for '{object_id}': {e}")
            mw.status_bar.showMessage("Failed to open Object Explorer", 3000)

    def set_object_explorer_stay_above_main(self, checked: bool) -> None:
        """Persist/apply whether Object Explorer should stay above the main window."""
        mw = self.main_window

        mw.settings.explorer_stay_above_main = bool(checked)
        mw.logger.info(f"Object Explorer stay_above_main set to: {checked}")

        # If the window exists, recreate it so the parent/ownership is updated.
        if hasattr(mw, "object_explorer_window") and mw.object_explorer_window:
            was_visible = mw.object_explorer_window.isVisible()
            try:
                mw.object_explorer_window.close()
                mw.object_explorer_window.deleteLater()
            except Exception:
                pass

            try:
                delattr(mw, "object_explorer_window")
            except Exception:
                pass

            if was_visible:
                mw.show_object_explorer_window_if_ready()

    def toggle_log_window(self) -> None:
        """Toggle log window visibility."""
        mw = self.main_window
        toggle_gui_log()

        gui_log_manager = get_gui_log_manager()
        if gui_log_manager and gui_log_manager.is_window_visible():
            mw.status_bar.showMessage("Log window shown (press ` to hide)", 2000)
        else:
            mw.status_bar.showMessage("Log window hidden (press ` to show)", 2000)

    def reset_view_proportions(self) -> None:
        """Reset view proportions (if supported by layout)."""
        # Not supported in current minimal layout
        return

    def reset_widget_layout(self) -> None:
        """Reset widget layout to defaults."""
        mw = self.main_window
        if hasattr(mw, "dock_layout_builder"):
            mw.dock_layout_builder.reset_widget_layout()

    @staticmethod
    def _validate_cdda_path(path: Path) -> bool:
        """Validate that the path looks like a CDDA installation."""
        if not path.exists() or not path.is_dir():
            return False

        has_data = (path / "data").exists() and (path / "data").is_dir()
        has_gfx = (path / "gfx").exists() and (path / "gfx").is_dir()
        return has_data or has_gfx
