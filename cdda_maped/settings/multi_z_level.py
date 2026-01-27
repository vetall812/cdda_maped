"""
Multi-z-level rendering settings for CDDA-maped.
"""

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings

# Type aliases for clarity
BrightnessMethod = Literal["Add", "Magnify", "None"]
BrightnessOperation = Literal["Darken", "Lighten", "None"]
TransparencyMethod = Literal["Add", "Magnify", "None"]


class MultiZLevelSettings:
    """Manages multi-z-level rendering settings."""

    def __init__(self, settings: "QSettings"):
        self.settings = settings

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

    def _get_int(self, key: str, default: int = 0) -> int:
        """Type-safe integer retrieval from settings."""
        value = self.settings.value(key, default)
        try:
            if value is None:
                return default
            return int(value)  # type: ignore
        except (ValueError, TypeError):
            return default

    def _get_float(self, key: str, default: float = 0.0) -> float:
        """Type-safe float retrieval from settings."""
        value = self.settings.value(key, default)
        try:
            if value is None:
                return default
            return float(value)  # type: ignore
        except (ValueError, TypeError):
            return default

    # === Enable Multi-Z-Level Rendering ===

    @property
    def enabled(self) -> bool:
        """Check if multi-z-level rendering is enabled."""
        return self._get_bool("multi_z_level/enabled", False)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set multi-z-level rendering enabled state."""
        self.settings.setValue("multi_z_level/enabled", value)
        self.settings.sync()

    # === Z-Level Range ===

    @property
    def levels_above(self) -> int:
        """Get number of z-levels to render above current (0-10)."""
        value = self._get_int("multi_z_level/levels_above", 1)
        return max(0, min(10, value))

    @levels_above.setter
    def levels_above(self, value: int) -> None:
        """Set number of z-levels to render above current (0-10)."""
        validated = max(0, min(10, value))
        self.settings.setValue("multi_z_level/levels_above", validated)
        self.settings.sync()

    @property
    def levels_below(self) -> int:
        """Get number of z-levels to render below current (0-10)."""
        value = self._get_int("multi_z_level/levels_below", 1)
        return max(0, min(10, value))

    @levels_below.setter
    def levels_below(self, value: int) -> None:
        """Set number of z-levels to render below current (0-10)."""
        validated = max(0, min(10, value))
        self.settings.setValue("multi_z_level/levels_below", validated)
        self.settings.sync()

    # === Brightness Settings ===

    @property
    def brightness_method(self) -> BrightnessMethod:
        """Get brightness adjustment method."""
        value = self._get_str("multi_z_level/brightness_method", "Add")
        if value in ("Add", "Magnify", "None"):
            return value  # type: ignore
        return "Add"

    @brightness_method.setter
    def brightness_method(self, value: BrightnessMethod) -> None:
        """Set brightness adjustment method."""
        if value not in ("Add", "Magnify", "None"):
            raise ValueError(f"Invalid brightness method: {value}")
        self.settings.setValue("multi_z_level/brightness_method", value)
        self.settings.sync()

    @property
    def brightness_step(self) -> float:
        """Get brightness step per z-level (0.0-1.0, stored as 0-100%)."""
        value = self._get_float("multi_z_level/brightness_step", 20.0)
        return max(0.0, min(100.0, value)) / 100.0

    @brightness_step.setter
    def brightness_step(self, value: float) -> None:
        """Set brightness step per z-level (0.0-1.0, stored as 0-100%)."""
        validated = max(0.0, min(1.0, value)) * 100.0
        self.settings.setValue("multi_z_level/brightness_step", validated)
        self.settings.sync()

    @property
    def brightness_operation_above(self) -> BrightnessOperation:
        """Get brightness operation for z-levels above current."""
        value = self._get_str("multi_z_level/brightness_operation_above", "Darken")
        if value in ("Darken", "Lighten", "None"):
            return value  # type: ignore
        return "Darken"

    @brightness_operation_above.setter
    def brightness_operation_above(self, value: BrightnessOperation) -> None:
        """Set brightness operation for z-levels above current."""
        if value not in ("Darken", "Lighten", "None"):
            raise ValueError(f"Invalid brightness operation: {value}")
        self.settings.setValue("multi_z_level/brightness_operation_above", value)
        self.settings.sync()

    @property
    def brightness_operation_below(self) -> BrightnessOperation:
        """Get brightness operation for z-levels below current."""
        value = self._get_str("multi_z_level/brightness_operation_below", "Darken")
        if value in ("Darken", "Lighten", "None"):
            return value  # type: ignore
        return "Darken"

    @brightness_operation_below.setter
    def brightness_operation_below(self, value: BrightnessOperation) -> None:
        """Set brightness operation for z-levels below current."""
        if value not in ("Darken", "Lighten", "None"):
            raise ValueError(f"Invalid brightness operation: {value}")
        self.settings.setValue("multi_z_level/brightness_operation_below", value)
        self.settings.sync()

    # === Transparency Settings ===

    @property
    def transparency_method(self) -> TransparencyMethod:
        """Get transparency adjustment method."""
        value = self._get_str("multi_z_level/transparency_method", "Add")
        if value in ("Add", "Magnify", "None"):
            return value  # type: ignore
        return "Add"

    @transparency_method.setter
    def transparency_method(self, value: TransparencyMethod) -> None:
        """Set transparency adjustment method."""
        if value not in ("Add", "Magnify", "None"):
            raise ValueError(f"Invalid transparency method: {value}")
        self.settings.setValue("multi_z_level/transparency_method", value)
        self.settings.sync()

    @property
    def transparency_step(self) -> float:
        """Get transparency step per z-level (0.0-1.0, stored as 0-100%)."""
        value = self._get_float("multi_z_level/transparency_step", 20.0)
        return max(0.0, min(100.0, value)) / 100.0

    @transparency_step.setter
    def transparency_step(self, value: float) -> None:
        """Set transparency step per z-level (0.0-1.0, stored as 0-100%)."""
        validated = max(0.0, min(1.0, value)) * 100.0
        self.settings.setValue("multi_z_level/transparency_step", validated)
        self.settings.sync()

    # === Utility Methods ===

    def calculate_brightness_factor(
        self, z_offset: int, operation: BrightnessOperation
    ) -> float:
        """Calculate brightness factor for given z-offset.

        Args:
            z_offset: Offset from current z-level (positive = above, negative = below)
            operation: Brightness operation to apply

        Returns:
            Brightness factor (0.0 = black, 1.0 = normal, >1.0 = brighter)
        """
        if operation == "None" or z_offset == 0:
            return 1.0

        abs_offset = abs(z_offset)
        step = self.brightness_step
        method = self.brightness_method

        if method == "None":
            return 1.0
        elif method == "Add":
            adjustment = step * abs_offset
        elif method == "Magnify":
            adjustment = 1.0 - (1.0 - step) ** abs_offset
        else:
            return 1.0

        if operation == "Darken":
            return max(0.0, 1.0 - adjustment)
        else:  # Lighten
            return 1.0 + adjustment

    def calculate_transparency_factor(self, z_offset: int) -> float:
        """Calculate transparency factor for given z-offset.

        Args:
            z_offset: Offset from current z-level (positive = above, negative = below)

        Returns:
            Transparency factor (0.0 = fully transparent, 1.0 = fully opaque)
        """
        if z_offset == 0:
            return 1.0

        abs_offset = abs(z_offset)
        step = self.transparency_step
        method = self.transparency_method

        if method == "None":
            return 1.0
        elif method == "Add":
            return max(0.0, 1.0 - step * abs_offset)
        elif method == "Magnify":
            return (1.0 - step) ** abs_offset
        else:
            return 1.0

    def get_preview_values(
        self, max_levels: int = 3
    ) -> dict[int, tuple[float, float]]:
        """Get preview brightness and transparency values for each z-level offset.

        Args:
            max_levels: Maximum number of levels to preview in each direction

        Returns:
            Dictionary mapping z-offset to (brightness, transparency) tuple
        """
        preview = {0: (1.0, 1.0)}

        for offset in range(-max_levels, max_levels + 1):
            if offset < 0:
                operation = self.brightness_operation_below
            elif offset > 0:
                operation = self.brightness_operation_above
            else:
                operation = "None"

            brightness = self.calculate_brightness_factor(offset, operation)
            transparency = self.calculate_transparency_factor(offset)
            preview[offset] = (brightness, transparency)

        return preview
