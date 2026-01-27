"""
CDDA-maped: Visual map editor for Cataclysm: Dark Days Ahead

A cross-platform tool for creating and editing CDDA maps with tileset support.
"""

__version__ = "0.1.0"
__author__ = "CDDA-maped Contributors"

# Core service imports
from .tilesets import TilesetService
from .game_data import GameDataService
from .utils.logging_config import setup_logging

# Main data models
from .tilesets.models import (
    WeightedSprite, TileSource, Tile, TileObject,
    Sheet, FallbackSheet, Tileset
)

__all__ = [
    # Services
    'TilesetService',
    'GameDataService',

    # Logging
    'setup_logging',

    # Data models
    'WeightedSprite',
    'TileSource',
    'Tile',
    'TileObject',
    'Sheet',
    'FallbackSheet',
    'Tileset',
]
