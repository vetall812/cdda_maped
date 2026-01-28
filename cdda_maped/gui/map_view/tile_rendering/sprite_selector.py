"""Sprite selection for weighted and animated tiles.

Handles selection of sprites from weighted lists with support for
deterministic pseudo-random selection and animation state management.
"""

from typing import Sequence, Optional

from cdda_maped.tilesets.models import WeightedSprite
from ..animation_manager import AnimationStateManager


class SpriteSelector:
    """Selects sprites from weighted lists for tiles.

    Supports both static (deterministic hash-based) and animated
    (time-based frame selection) tiles.
    """

    def __init__(self, animation_state_manager: Optional[AnimationStateManager] = None):
        """Initialize the sprite selector.

        Args:
            animation_state_manager: Manager for animated tile states (optional)
        """
        self.animation_state_manager = animation_state_manager

    def select_weighted_frame(
        self,
        weighted_list: Sequence[WeightedSprite],
        x: int,
        y: int,
        object_id: str,
        is_animated: bool = False,
    ) -> WeightedSprite:
        """Select WeightedSprite frame from weighted list.

        Used when caller needs the full WeightedSprite (e.g., to extract orientation).
        Delegates to AnimationStateManager for animated tiles or uses hash-based selection.

        Args:
            weighted_list: List of WeightedSprite objects
            x: Grid X coordinate
            y: Grid Y coordinate
            object_id: Object identifier
            is_animated: If True, treat as animated tile (uses animation state)

        Returns:
            Selected WeightedSprite frame
        """
        if not weighted_list:
            return WeightedSprite(weight=1, sprite=0)

        # If animated and we have animation state manager
        if is_animated and self.animation_state_manager:
            self.animation_state_manager.register_animated_tile(
                object_id, list(weighted_list)
            )
            frame = self.animation_state_manager.get_current_frame_for_position(
                object_id, x, y
            )
            if frame is not None:
                return frame

        # Create deterministic seed from coordinates and object
        seed = hash((x, y, object_id))

        # Calculate total weight
        total_weight = sum(ws.weight for ws in weighted_list)
        if total_weight <= 0:
            total_weight = len(weighted_list)

        # Pick index based on seed
        selection = abs(seed) % total_weight

        # Find frame by accumulated weight
        accumulated = 0
        for ws in weighted_list:
            accumulated += ws.weight
            if selection < accumulated:
                return ws

        return weighted_list[0]

    def select_weighted_sprite(
        self,
        weighted_list: Sequence[WeightedSprite],
        x: int,
        y: int,
        object_id: str,
        is_animated: bool = False,
    ) -> int:
        """Select sprite index from weighted list.

        Delegates to select_weighted_frame and extracts the sprite index.
        Handles both int and list[int] sprite values.

        Args:
            weighted_list: List of WeightedSprite objects
            x: Grid X coordinate
            y: Grid Y coordinate
            object_id: Object identifier
            is_animated: If True, treat as animated tile (uses animation state)

        Returns:
            Selected sprite index
        """
        # Get selected frame and extract its sprite index
        frame = self.select_weighted_frame(weighted_list, x, y, object_id, is_animated)

        # Handle sprite as int or list[int]
        sprite_val = frame.sprite
        if isinstance(sprite_val, list):
            return sprite_val[0] if sprite_val else 0
        return sprite_val
