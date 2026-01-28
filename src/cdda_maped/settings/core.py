"""
Core settings management for CDDA-maped.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget, QMainWindow

from .types import ConfigVersion, ValidationResult
from .migration import SettingsMigrator
from .validation import SettingsValidator
from .paths import PathSettings
from .ui import UISettings
from .editor import EditorSettings
from .logging import LoggingSettings
from .mods import ModSettings
from .type_slot_mapping import TypeSlotMappingSettings
from .multi_z_level import MultiZLevelSettings

if TYPE_CHECKING:
    from ..tilesets.service import TilesetService

logger = logging.getLogger(__name__)


class AppSettings:
    """
    Modern configuration management using QSettings.

    Provides type-safe access to application settings with automatic
    cross-platform storage and validation.
    """

    def __init__(self, profile: str = "default"):
        """Initialize settings with organization, application name, and profile.

        Args:
            profile: Settings profile name (default: "default")
        """
        self.settings = QSettings("vetall812", "cdda_maped")
        self.profile = profile

        # Use profile as a group to create hierarchy: vetall812/cdda_maped/default/...
        self.settings.beginGroup(profile)

        # Initialize subsystems
        self._migrator = SettingsMigrator(self.settings)
        self._validator = SettingsValidator(self)
        self._paths = PathSettings(self.settings)
        self._ui = UISettings(self.settings)
        self._editor = EditorSettings(self.settings)
        self._logging = LoggingSettings(self.settings)
        self._mods = ModSettings(self.settings)
        self._type_slot_mapping = TypeSlotMappingSettings(self.settings)
        self._multi_z_level = MultiZLevelSettings(self.settings)

        # Ensure version and migrate if needed
        self._migrator.ensure_version()

        logger.debug(
            f"Settings initialized for profile '{profile}', stored at: {self.settings.fileName()}"
        )

    # === SUBSYSTEM ACCESS ===

    @property
    def paths(self) -> PathSettings:
        """Access path settings subsystem."""
        return self._paths

    @property
    def ui(self) -> UISettings:
        """Access UI settings subsystem."""
        return self._ui

    @property
    def editor(self) -> EditorSettings:
        """Access editor settings subsystem."""
        return self._editor

    @property
    def logging(self) -> LoggingSettings:
        """Access logging settings subsystem."""
        return self._logging

    @property
    def type_slot_mapping(self) -> TypeSlotMappingSettings:
        """Access type-slot mapping settings subsystem."""
        return self._type_slot_mapping

    @property
    def mods(self) -> ModSettings:
        """Access mod settings subsystem."""
        return self._mods

    @property
    def multi_z_level(self) -> MultiZLevelSettings:
        """Access multi-z-level rendering settings subsystem."""
        return self._multi_z_level

    # === VERSION AND FIRST RUN ===

    @property
    def is_first_run(self) -> bool:
        """Check if this is the first run of the application."""
        return self._get_bool("app/first_run", True)

    def set_first_run_complete(self) -> None:
        """Mark first run as complete."""
        self.settings.setValue("app/first_run", False)
        self.settings.sync()

    @property
    def version(self) -> str:
        """Get configuration version."""
        return self._get_str("app/version", ConfigVersion.CURRENT.value)

    # === HELPER METHODS ===

    def _get_str(self, key: str, default: str = "") -> str:
        """Type-safe string retrieval from settings."""
        value = self.settings.value(key, default)
        return str(value) if value is not None else default

    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Type-safe boolean retrieval from settings."""
        value = self.settings.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value) if value is not None else default

    # === PATH SETTINGS (DELEGATED) ===

    @property
    def cdda_path(self) -> Optional[Path]:
        """Get CDDA game directory path."""
        return self._paths.cdda_path

    @cdda_path.setter
    def cdda_path(self, value: Optional[Path]) -> None:
        """Set CDDA game directory path."""
        self._paths.cdda_path = value

    @property
    def cdda_data_path(self) -> Optional[Path]:
        """Get CDDA data directory path (derived from cdda_path)."""
        return self._paths.cdda_data_path

    @property
    def tilesets_path(self) -> Optional[Path]:
        """Get tilesets directory path (derived from cdda_path)."""
        return self._paths.tilesets_path

    @property
    def recent_files(self) -> List[str]:
        """Get list of recently opened files."""
        return self._paths.recent_files

    def add_recent_file(self, file_path: Union[str, Path]) -> None:
        """Add file to recent files list (max 10 items)."""
        self._paths.add_recent_file(file_path)

    def clear_recent_files(self) -> None:
        """Clear recent files list."""
        self._paths.clear_recent_files()

    # === UI SETTINGS (DELEGATED) ===

    def save_window_geometry(self, widget: Union[QWidget, QMainWindow]) -> None:
        """Save window geometry and state."""
        self._ui.save_window_geometry(widget)

    def restore_window_geometry(self, widget: Union[QWidget, QMainWindow]) -> bool:
        """Restore window geometry and state. Returns True if restored."""
        return self._ui.restore_window_geometry(widget)

    def save_explorer_window_geometry(
        self, widget: Union[QWidget, QMainWindow]
    ) -> None:
        """Save object explorer window geometry and state."""
        self._ui.save_explorer_window_geometry(widget)

    def restore_explorer_window_geometry(
        self, widget: Union[QWidget, QMainWindow]
    ) -> bool:
        """Restore object explorer window geometry/state. Returns True if restored."""
        return self._ui.restore_explorer_window_geometry(widget)

    def save_log_window_geometry(self, widget: Union[QWidget, QMainWindow]) -> None:
        """Save log window geometry (separate from main window)."""
        self._ui.save_log_window_geometry(widget)

    def restore_log_window_geometry(self, widget: Union[QWidget, QMainWindow]) -> bool:
        """Restore log window geometry. Returns True if restored."""
        return self._ui.restore_log_window_geometry(widget)

    @property
    def theme(self) -> str:
        """Get UI theme name."""
        return self._ui.theme

    @theme.setter
    def theme(self, value: str) -> None:
        """Set UI theme name."""
        self._ui.theme = value

    @property
    def explorer_stay_above_main(self) -> bool:
        """Whether Object Explorer should stay above the main window."""
        return self._ui.get_explorer_stay_above_main()

    @explorer_stay_above_main.setter
    def explorer_stay_above_main(self, value: bool) -> None:
        """Persist Object Explorer z-order option."""
        self._ui.set_explorer_stay_above_main(value)

    # === EDITOR SETTINGS (DELEGATED) ===

    @property
    def default_tileset(self) -> str:
        """Get default tileset name."""
        return self._editor.default_tileset

    @default_tileset.setter
    def default_tileset(self, value: str) -> None:
        """Set default tileset name."""
        self._editor.default_tileset = value

    @property
    def default_tileset_iso(self) -> str:
        """Get default tileset name for isometric view."""
        return self._editor.default_tileset_iso

    @default_tileset_iso.setter
    def default_tileset_iso(self, value: str) -> None:
        """Set default tileset name for isometric view."""
        self._editor.default_tileset_iso = value

    def get_preferred_tileset(
        self, tileset_service: "TilesetService", is_iso: bool = False
    ) -> str:
        """Get preferred tileset using smart fallback logic.

        Args:
            tileset_service: TilesetService instance to check available tilesets
            is_iso: Whether to prefer isometric (True) or orthogonal (False) tileset

        Returns:
            Name of a suitable tileset
        """
        preferred = self.default_tileset_iso if is_iso else self.default_tileset
        return tileset_service.get_preferred_tileset(preferred, is_iso)

    @property
    def grid_visible(self) -> bool:
        """Check if grid should be visible."""
        return self._editor.grid_visible

    @grid_visible.setter
    def grid_visible(self, value: bool) -> None:
        """Set grid visibility."""
        self._editor.grid_visible = value

    @property
    def zoom_level(self) -> float:
        """Get zoom level."""
        return self._editor.zoom_level

    @zoom_level.setter
    def zoom_level(self, value: float) -> None:
        """Set zoom level."""
        self._editor.zoom_level = value

    @property
    def animation_timeout(self) -> int:
        """Get animation timeout in milliseconds."""
        return self._editor.animation_timeout

    @animation_timeout.setter
    def animation_timeout(self, value: int) -> None:
        """Set animation timeout in milliseconds."""
        self._editor.animation_timeout = value

    # === LOGGING SETTINGS (DELEGATED) ===

    @property
    def console_logging(self) -> bool:
        """Check if console logging is enabled."""
        return self._logging.console_logging

    @console_logging.setter
    def console_logging(self, value: bool) -> None:
        """Set console logging enabled state."""
        self._logging.console_logging = value

    @property
    def console_log_level(self) -> str:
        """Get console logging level."""
        return self._logging.console_log_level

    @console_log_level.setter
    def console_log_level(self, value: str) -> None:
        """Set console logging level."""
        self._logging.console_log_level = value

    @property
    def console_use_colors(self) -> bool:
        """Check if console should use colors."""
        return self._logging.console_use_colors

    @console_use_colors.setter
    def console_use_colors(self, value: bool) -> None:
        """Set console color usage."""
        self._logging.console_use_colors = value

    @property
    def file_logging(self) -> bool:
        """Check if file logging is enabled."""
        return self._logging.file_logging

    @file_logging.setter
    def file_logging(self, value: bool) -> None:
        """Set file logging enabled state."""
        self._logging.file_logging = value

    @property
    def log_file_path(self) -> str:
        """Get log file path (read-only)."""
        return self._logging.log_file_path

    @property
    def log_file_absolute_path(self) -> Path:
        """Get absolute path to log file."""
        return self._logging.log_file_absolute_path

    @property
    def gui_logging(self) -> bool:
        """Check if GUI logging is enabled (always True)."""
        return self._logging.gui_logging

    @property
    def gui_log_level(self) -> str:
        """Get GUI logging level."""
        return self._logging.gui_log_level

    @gui_log_level.setter
    def gui_log_level(self, value: str) -> None:
        """Set GUI logging level."""
        self._logging.gui_log_level = value

    @property
    def gui_show_on_startup(self) -> bool:
        """Check if GUI log window should show on startup."""
        return self._logging.gui_show_on_startup

    @gui_show_on_startup.setter
    def gui_show_on_startup(self, value: bool) -> None:
        """Set GUI log window show on startup."""
        self._logging.gui_show_on_startup = value

    @property
    def gui_show_on_error(self) -> bool:
        """Check if GUI log window should show on errors."""
        return self._logging.gui_show_on_error

    @gui_show_on_error.setter
    def gui_show_on_error(self, value: bool) -> None:
        """Set GUI log window show on error."""
        self._logging.gui_show_on_error = value

    @property
    def gui_focus_on_error(self) -> bool:
        """Check if GUI log window should gain focus on errors."""
        return self._logging.gui_focus_on_error

    @gui_focus_on_error.setter
    def gui_focus_on_error(self, value: bool) -> None:
        """Set GUI log window focus on error."""
        self._logging.gui_focus_on_error = value

    @property
    def gui_max_lines(self) -> int:
        """Get maximum number of lines to keep in GUI log buffer."""
        return self._logging.gui_max_lines

    @gui_max_lines.setter
    def gui_max_lines(self, value: int) -> None:
        """Set maximum number of lines in GUI log buffer."""
        self._logging.gui_max_lines = value

    # === MOD SETTINGS (DELEGATED) ===

    @property
    def active_mods(self) -> List[str]:
        """Get list of active mods in priority order."""
        return self._mods.active_mods

    @active_mods.setter
    def active_mods(self, value: List[str]) -> None:
        """Set list of active mods in priority order."""
        self._mods.active_mods = value

    @property
    def available_mods(self) -> List[str]:
        """Get list of all available mods (cached for UI)."""
        return self._mods.available_mods

    @available_mods.setter
    def available_mods(self, value: List[str]) -> None:
        """Set list of all available mods (cached for UI)."""
        self._mods.available_mods = value

    def add_mod(self, mod_id: str) -> None:
        """Add a mod to the active list if not already present."""
        self._mods.add_mod(mod_id)

    def remove_mod(self, mod_id: str) -> None:
        """Remove a mod from the active list."""
        self._mods.remove_mod(mod_id)

    def move_mod_up(self, mod_id: str) -> bool:
        """Move mod up in priority (towards beginning of list)."""
        return self._mods.move_mod_up(mod_id)

    def move_mod_down(self, mod_id: str) -> bool:
        """Move mod down in priority (towards end of list)."""
        return self._mods.move_mod_down(mod_id)

    def set_mod_priority(self, mod_id: str, new_index: int) -> bool:
        """Set mod to specific priority position."""
        return self._mods.set_mod_priority(mod_id, new_index)

    def clear_active_mods(self) -> None:
        """Clear all active mods."""
        self._mods.clear_active_mods()

    def is_mod_active(self, mod_id: str) -> bool:
        """Check if a mod is active."""
        return self._mods.is_mod_active(mod_id)

    def get_mod_priority(self, mod_id: str) -> int:
        """Get priority index of a mod (-1 if not active)."""
        return self._mods.get_mod_priority(mod_id)

    @property
    def always_include_core(self) -> bool:
        """Whether to always include core data regardless of active mods."""
        return self._mods.always_include_core

    @always_include_core.setter
    def always_include_core(self, value: bool) -> None:
        """Set whether to always include core data."""
        self._mods.always_include_core = value

    # === VALIDATION ===

    def validate(self) -> ValidationResult:
        """Validate current configuration."""
        return self._validator.validate()

    # === UTILITY METHODS ===

    def get_settings_file_path(self) -> str:
        """Get the file path where settings are stored."""
        return self.settings.fileName()

    def sync(self) -> None:
        """Force synchronization of settings to storage."""
        self.settings.sync()
