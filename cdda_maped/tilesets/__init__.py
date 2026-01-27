"""
Tilesets package for Cataclysm: DDA.

Provides services for loading, managing, and rendering tilesets,
including support for mods and priority/override rules.
"""

from .service import TilesetService
from .models import (
    Tileset, Sheet, FallbackSheet, Tile, TileSource, WeightedSprite, TileObject,
    SpriteEntry, SpriteIndex, SheetInfo
)
from .managers import TilesetManager, SheetManager, TilesManager

# Public classes intended for external use
__all__ = [
    # Main service
    'TilesetService',

    # Data models
    'FallbackSheet',
    'Sheet',
    'SheetInfo',
    'SpriteEntry',
    'SpriteIndex',
    'Tileset',
    'Tile',
    'TileSource',
    'TileObject',
    'WeightedSprite',

    # Managers (exposed in case they are needed directly)
    'SheetManager',
    'TilesetManager',
    'TilesManager'
]

# Module version
__version__ = '1.0.0'
