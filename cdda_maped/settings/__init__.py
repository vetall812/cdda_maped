"""
Settings package for CDDA-maped.

This package provides a modular, type-safe configuration management system
using Qt's QSettings for cross-platform storage.

Usage:
    from cdda_maped.settings import AppSettings, ValidationResult

    settings = AppSettings()
    result = settings.validate()
"""

from .core import AppSettings
from .types import ConfigVersion, ConfigError, ValidationResult
from .mods import ModSettings
from .type_slot_mapping import TypeSlotMappingSettings
from .multi_z_level import MultiZLevelSettings

__all__ = [
    "AppSettings",
    "ConfigVersion",
    "ConfigError",
    "ValidationResult",
    "ModSettings",
    "TypeSlotMappingSettings",
    "MultiZLevelSettings",
]
