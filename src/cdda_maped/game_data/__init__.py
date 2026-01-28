"""
Module for working with CDDA game data.

Provides services for reading, indexing and managing game objects,
including support for mods and object inheritance. Refactored into
multiple modules for better maintainability and testability.
"""

from .service import GameDataService
from .models import (
    GameDataObject,
    GameDataCollection,
    TypedObjectsMap,
    ModObjectsMap,
    METADATA_MOD_ID,
    METADATA_SOURCE_FILE,
    INHERITANCE_KEY,
)
from .managers import ObjectsManager
from .loaders import GameDataFileLoader
from .inheritance import InheritanceResolver

# Public exports
__all__ = [
    # Main service
    "GameDataService",
    # Type aliases
    "GameDataObject",
    "GameDataCollection",
    "TypedObjectsMap",
    "ModObjectsMap",
    # Constants
    "METADATA_MOD_ID",
    "METADATA_SOURCE_FILE",
    "INHERITANCE_KEY",
    # Component classes (for advanced usage)
    "ObjectsManager",
    "GameDataFileLoader",
    "InheritanceResolver",
]

# Module version
__version__ = "2.0.2"  # Remove deprecated collection module
