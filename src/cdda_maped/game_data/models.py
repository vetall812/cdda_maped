"""
Data models for CDDA game data.

Contains type definitions and simple data structures used throughout
the game_data package. Keeps dict-based approach for flexibility while
providing clear type hints.
"""

from typing import Any, Dict, List, TypeAlias

# Type aliases for clarity
GameDataObject: TypeAlias = Dict[str, Any]
"""A single game data object (e.g., monster, item, recipe) as a dict."""

GameDataCollection: TypeAlias = List[GameDataObject]
"""A collection of game data objects."""

TypedObjectsMap: TypeAlias = Dict[str, GameDataCollection]
"""Maps object type (e.g., 'MONSTER', 'item') to list of objects."""

ModObjectsMap: TypeAlias = Dict[str, TypedObjectsMap]
"""Maps mod_id to its typed objects map."""


# Metadata keys added to objects during loading
METADATA_MOD_ID = "_mod_id"
METADATA_SOURCE_FILE = "_source_file"

# Special keys for object inheritance
INHERITANCE_KEY = "copy-from"
EXTEND_KEY = "extend"
DELETE_KEY = "delete"
