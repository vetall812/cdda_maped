"""Tile rendering package for CDDA-maped.

This package contains modular components for rendering tiles:
- TileRenderer: Main orchestrator
- SpriteSelector: Weighted/animated sprite selection
- SpriteTransformer: Rotation, scaling, caching
- PlaceholderRenderer: Fallback shapes for missing sprites
"""

from .tile_renderer import TileRenderer

__all__ = ["TileRenderer"]
