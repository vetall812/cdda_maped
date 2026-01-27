"""
Mod-related settings for CDDA-maped.
"""

from typing import List, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings


class ModSettings:
    """Manages mod-related settings."""

    def __init__(self, settings: "QSettings"):
        self.settings = settings

    def _get_list(self, key: str, default: List[str] | None = None) -> List[str]:
        """Type-safe list retrieval from settings."""
        if default is None:
            default = []
        value = self.settings.value(key, default)
        if isinstance(value, list):
            return [
                str(item) if item is not None else ""
                for item in cast(list[object], value)
            ]
        return default

    @property
    def active_mods(self) -> List[str]:
        """Get list of active mods in priority order."""
        return self._get_list("mods/active", [])

    @active_mods.setter
    def active_mods(self, value: List[str]) -> None:
        """Set list of active mods in priority order."""
        self.settings.setValue("mods/active", value)
        self.settings.sync()

    @property
    def available_mods(self) -> List[str]:
        """Get list of all available mods (cached for UI)."""
        return self._get_list("mods/available", [])

    @available_mods.setter
    def available_mods(self, value: List[str]) -> None:
        """Set list of all available mods (cached for UI)."""
        self.settings.setValue("mods/available", value)
        self.settings.sync()

    def add_mod(self, mod_id: str) -> None:
        """Add a mod to the active list if not already present."""
        active = self.active_mods
        if mod_id not in active:
            active.append(mod_id)
            self.active_mods = active

    def remove_mod(self, mod_id: str) -> None:
        """Remove a mod from the active list."""
        active = self.active_mods
        if mod_id in active:
            active.remove(mod_id)
            self.active_mods = active

    def move_mod_up(self, mod_id: str) -> bool:
        """Move mod up in priority (towards beginning of list).

        Returns:
            True if mod was moved, False if it was already at the top or not found.
        """
        active = self.active_mods
        try:
            index = active.index(mod_id)
            if index > 0:
                active[index], active[index - 1] = active[index - 1], active[index]
                self.active_mods = active
                return True
        except ValueError:
            pass
        return False

    def move_mod_down(self, mod_id: str) -> bool:
        """Move mod down in priority (towards end of list).

        Returns:
            True if mod was moved, False if it was already at the bottom or not found.
        """
        active = self.active_mods
        try:
            index = active.index(mod_id)
            if index < len(active) - 1:
                active[index], active[index + 1] = active[index + 1], active[index]
                self.active_mods = active
                return True
        except ValueError:
            pass
        return False

    def set_mod_priority(self, mod_id: str, new_index: int) -> bool:
        """Set mod to specific priority position.

        Args:
            mod_id: ID of the mod to move
            new_index: New index position (0 = highest priority)

        Returns:
            True if mod was moved, False if mod not found or index invalid.
        """
        active = self.active_mods
        try:
            old_index = active.index(mod_id)
            if 0 <= new_index < len(active) and old_index != new_index:
                # Remove from old position and insert at new position
                mod = active.pop(old_index)
                active.insert(new_index, mod)
                self.active_mods = active
                return True
        except (ValueError, IndexError):
            pass
        return False

    def clear_active_mods(self) -> None:
        """Clear all active mods."""
        self.active_mods = []

    def is_mod_active(self, mod_id: str) -> bool:
        """Check if a mod is active."""
        return mod_id in self.active_mods

    def get_mod_priority(self, mod_id: str) -> int:
        """Get priority index of a mod (-1 if not active).

        Returns:
            Priority index (0 = highest priority) or -1 if mod is not active.
        """
        try:
            return self.active_mods.index(mod_id)
        except ValueError:
            return -1

    @property
    def always_include_core(self) -> bool:
        """Whether to always include core data regardless of active mods."""
        value = self.settings.value("mods/always_include_core", True, type=bool)
        return bool(value)

    @always_include_core.setter
    def always_include_core(self, value: bool) -> None:
        """Set whether to always include core data."""
        self.settings.sync()
        self.settings.setValue("mods/always_include_core", value)
