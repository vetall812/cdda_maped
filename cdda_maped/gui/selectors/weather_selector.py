"""
Weather selector widget for CDDA-maped.

Provides a UI component for selecting weather type.
Minimalist design: icon on the left, selector on the right (Photoshop-style).

Respects mod settings and priorities:
- Shows only weather from core (dda) and user-selected mods
- Deduplicates by ID using active mod priority (0 = highest)
- Emits both weather_id and source mod_id
"""

from typing import Optional, Dict, Tuple, Any, List, cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from ...game_data.service import GameDataService
from ...game_data.models import METADATA_MOD_ID
from ...settings import AppSettings
from .icon_selector import IconSelector


class WeatherSelector(IconSelector):
    """
    Widget for selecting weather type.

    Emits weatherChanged signal when the user selects a different weather.
    Uses minimalist design with fixed Material Design icon.
    """

    # Signal emitted when weather changes (weather_id: str, mod_id: str)
    weatherChanged = Signal(str, str)

    # Fixed icon for weather selector
    ICON_NAME = "mdi.weather-cloudy"
    SETTINGS_KEY = "weather"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.game_data_service: Optional[GameDataService] = None
        self.settings: Optional[AppSettings] = None
        self.current_weather = "clear"
        self.current_mod = "dda"

        # Connect signals
        self.combo.currentTextChanged.connect(self.on_weather_changed)

    def set_game_data_service(self, service: GameDataService):
        """Set game data service and populate weather list."""
        self.game_data_service = service
        # If available, also capture settings from the service
        try:
            self.settings = getattr(service, "settings", None)
        except Exception:
            self.settings = None
        self.load_weathers()

    def set_settings(self, settings: AppSettings):
        """Optionally set settings directly (used to compute mod priorities)."""
        self.settings = settings
        # Enable auto-save via base implementation
        super().set_settings(settings)
        self.load_weathers()

    def load_weathers(self):
        """Load available weather types from game data."""
        if not self.game_data_service:
            return

        try:
            # Determine considered mods and their priority
            considered_mods: List[str] = []
            if self.settings:
                considered_mods = list(self.settings.active_mods)
                if self.settings.always_include_core and "dda" not in considered_mods:
                    # Core is lowest priority: appended at the end
                    considered_mods.append("dda")
            else:
                # Fallback: include only core if no settings info
                considered_mods = ["dda"]

            # Filter weather objects to considered mods only (keeps mod order)
            weathers = self.game_data_service.manager.get_objects_by_type_from_mods(
                "weather_type", considered_mods
            )

            # Block signals while updating
            self.combo.blockSignals(True)
            self.combo.clear()

            # Deduplicate by both ID and display name.
            # When a mod redefines a weather (even with a different ID),
            # the mod's version takes priority and hides the core version.
            # Map: weather_id -> (display_name, source_mod)
            unique: Dict[str, Tuple[str, str]] = {}
            # Map: display_name (normalized) -> weather_id (tracks name-based dedup)
            name_to_id: Dict[str, str] = {}

            def normalize_name(obj: Any, fallback_id: str) -> str:
                """Normalize weather name from object, handling localized dicts."""
                raw_name: Any = obj.get("name", fallback_id)
                if isinstance(raw_name, dict):
                    # Try localized fields in order of preference
                    name_dict = cast(dict[str, Any], raw_name)
                    for key in ("str_sp", "str", "ctxt"):
                        value = name_dict.get(key)
                        if value:
                            return str(value)
                    # Fallback to string representation of dict
                    return str(raw_name) if raw_name else fallback_id
                return str(raw_name)

            # Iterate in mod priority order (active mods first, core last)
            for weather_obj in weathers:
                obj_mod = str(weather_obj.get(METADATA_MOD_ID, ""))
                obj_id: Any = weather_obj.get("id")

                # Skip objects without an explicit id (abstract prototypes)
                if not obj_id:
                    continue

                # Support "id" being either a string or a list of strings
                if isinstance(obj_id, list):
                    ids: List[str] = [str(item) for item in obj_id if isinstance(item, str)]
                else:
                    ids = [str(obj_id)]
                for wid in ids:
                    display_name = normalize_name(weather_obj, wid)
                    normalized_name = display_name.lower()

                    # Check: has this display name been seen in a higher-priority mod?
                    existing_id_with_same_name = name_to_id.get(normalized_name)
                    if existing_id_with_same_name is not None:
                        # This display name was already defined by a higher-priority mod.
                        # Skip this (lower-priority) variant entirely.
                        continue

                    # Check: has this exact ID been seen before?
                    if wid in unique:
                        # Already have this ID from higher-priority mod; skip
                        continue

                    # New weather: add it
                    unique[wid] = (display_name, obj_mod)
                    name_to_id[normalized_name] = wid

            # Convert to (display_name_with_mod, id) pairs and sort by name
            labeled_items: List[Tuple[str, str]] = []
            for wid, (name, src_mod) in unique.items():
                # If the chosen definition comes from a non-core mod, annotate it
                if src_mod and src_mod != "dda":
                    display = f"{name} [{src_mod}]"
                else:
                    display = name
                labeled_items.append((display, wid))

            sorted_items: List[Tuple[str, str]] = sorted(
                labeled_items, key=lambda x: x[0].lower()
            )

            # Add to combo
            for name, wid in sorted_items:
                mod_id = unique.get(wid, (name, "dda"))[1]
                # Store (weather_id, mod_id) tuple in item data
                self.combo.addItem(name, (wid, mod_id))

            self.combo.blockSignals(False)

            # Try to restore saved state, fallback to first item
            if sorted_items:
                if not self.restore_state():
                    # Select first weather if restoration failed
                    self.combo.setCurrentIndex(0)
                    first_name, first_id = sorted_items[0]
                    self.current_weather: str = first_id
                    self.current_mod: str = unique.get(first_id, (first_name, "dda"))[1]
                    self.on_weather_changed(first_name)

            self.logger.info(
                f"Loaded {len(weathers)} weather objects, {len(sorted_items)} unique types"
            )

        except Exception as e:
            self.logger.error(f"Failed to load weather types: {e}")

    def on_weather_changed(self, weather_name: str) -> None:
        """Handle weather selection change."""
        # Get (weather_id, mod_id) from current selection
        data = self.combo.currentData()
        if not isinstance(data, (tuple, list)) or not data or len(data) < 2:
            return
        weather_id, mod_id = str(data[0]), str(data[1])
        if weather_id != self.current_weather or mod_id != self.current_mod:
            self.current_weather = weather_id
            self.current_mod = mod_id
            self.logger.info(
                f"Weather changed to: {weather_id} ({weather_name}) from mod {mod_id}"
            )
            self.weatherChanged.emit(weather_id, mod_id)

    def get_current_weather(self) -> str:
        """Get currently selected weather ID."""
        return self.current_weather

    def get_current_weather_source_mod(self) -> str:
        """Get the source mod ID for the currently selected weather."""
        return self.current_mod

    def set_current_weather(self, weather_id: str) -> None:
        """Set the current weather programmatically."""
        # Find index by weather_id in combo data
        for i in range(self.combo.count()):
            data = self.combo.itemData(i)
            if isinstance(data, (tuple, list)) and data and len(data) >= 2 and str(data[0]) == weather_id:
                self.combo.setCurrentIndex(i)
                self.current_weather = weather_id
                self.current_mod = str(data[1])
                break
        else:
            self.logger.warning(f"Weather ID not found: {weather_id}")

    def _get_save_value(self) -> Optional[str]:
        """Get value to save (weather_id|mod_id format)."""
        return f"{self.current_weather}|{self.current_mod}"

    def _restore_value(self, value: str) -> bool:
        """Restore weather from saved format (weather_id|mod_id)."""
        try:
            if "|" not in value:
                # Old format: just weather_id
                weather_id = value
            else:
                # New format: weather_id|mod_id
                weather_id, _mod_id = value.split("|", 1)

            # Try to find and select this weather
            for i in range(self.combo.count()):
                data = self.combo.itemData(i)
                if isinstance(data, (tuple, list)) and data and len(data) >= 2 and str(data[0]) == weather_id:
                    self.combo.setCurrentIndex(i)
                    self.current_weather = str(data[0])
                    self.current_mod = str(data[1])
                    return True
            return False
        except Exception as e:
            self.logger.warning(f"Failed to restore weather: {e}")
            return False
