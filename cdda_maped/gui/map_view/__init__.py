"""Demo view package for map rendering.

This package provides modular components for rendering CDDA maps:
- CoordinateTransformer: Orthogonal/isometric coordinate conversions
- SceneManager: Scene size and offset calculations
- GridRenderer: Grid line rendering
- TileRenderer: Sprite and tile rendering
- MapView: Main view widget orchestrating all components
- AnimationStateManager: Manages animated tile states
- AnimationController: Controls animation timing
- GlobalAnimationCoordinator: Singleton for coordinating multiple animations
"""

from .map_view import MapView
from .coord_transformer import CoordinateTransformer
from .scene_manager import SceneManager
from .grid_renderer import GridRenderer
from .tile_rendering import TileRenderer
from .animation_manager import (
    AnimationStateManager,
    AnimationController,
    GlobalAnimationCoordinator,
)

__all__ = [
    "MapView",
    "CoordinateTransformer",
    "SceneManager",
    "GridRenderer",
    "TileRenderer",
    "AnimationStateManager",
    "AnimationController",
    "GlobalAnimationCoordinator",
]
