"""Animation management for tile animations.

Handles timing and state tracking for animated tiles with weighted frames.
Uses a global animation coordinator to prevent timer conflicts when multiple
MapViews animate simultaneously.
"""

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Set

from PySide6.QtCore import QTimer

from cdda_maped.settings import AppSettings
from cdda_maped.tilesets.models import WeightedSprite

if TYPE_CHECKING:
    # Avoid circular import
    from .map_view import MapView


class GlobalAnimationCoordinator:
    """Singleton coordinator for all animation timers.

    Manages a single QTimer that drives animation for all registered MapViews.
    This prevents timer conflicts and event loop blocking when multiple views
    animate simultaneously.
    """

    _instance: "GlobalAnimationCoordinator | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = True

        # Single repeating timer for all animations
        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._on_global_tick)

        # Set of registered animation controllers
        self._controllers: Set["AnimationController"] = set()

        # Round-robin index for staggering controllers
        self._rr_index: int = 0

        # Current interval
        self._interval = 100  # Default 100ms

        self.logger.debug("Global animation coordinator initialized")

    def register(self, controller: "AnimationController") -> None:
        """Register an animation controller."""
        self._controllers.add(controller)
        self.logger.debug(f"Controller registered, total: {len(self._controllers)}")

    def unregister(self, controller: "AnimationController") -> None:
        """Unregister an animation controller."""
        self._controllers.discard(controller)
        self.logger.debug(f"Controller unregistered, total: {len(self._controllers)}")

        # Stop timer if no controllers left
        if not self._controllers and self.timer.isActive():
            self.timer.stop()
            self.logger.debug("No controllers left, timer stopped")

    def start_timer(self, interval: int) -> None:
        """Start or update the global timer with the given interval.

        Uses the minimum interval of all active controllers.
        """
        # Keep the shortest interval requested
        self._interval = min(self._interval, interval)

        if not self.timer.isActive():
            self.timer.start(self._interval)
            self.logger.debug(f"Global timer started with interval: {self._interval}ms")
        elif self.timer.interval() != self._interval:
            self.timer.setInterval(self._interval)
            self.logger.debug(f"Global timer interval updated to: {self._interval}ms")

    def stop_timer(self) -> None:
        """Stop the global timer if no controllers are active."""
        active_count = sum(1 for c in self._controllers if c.is_active())
        if active_count == 0 and self.timer.isActive():
            self.timer.stop()
            self.logger.debug("All controllers inactive, timer stopped")

    def update_interval(self) -> None:
        """Recalculate optimal interval from all active controllers."""
        if not self._controllers:
            if self.timer.isActive():
                self.timer.stop()
            return

        # Find minimum interval among active controllers
        min_interval = min(
            (
                c.settings.editor.animation_timeout
                for c in self._controllers
                if c.is_active()
            ),
            default=self._interval,
        )

        if min_interval != self._interval:
            self._interval = min_interval
            if self.timer.isActive():
                self.timer.setInterval(self._interval)
                self.logger.debug(f"Global interval updated to: {self._interval}ms")

    def _on_global_tick(self) -> None:
        """Handle global timer tick - notify all active controllers."""
        active_controllers = [c for c in list(self._controllers) if c.is_active()]

        if not active_controllers:
            return

        # Process all active controllers per tick (renders are queued async per controller)
        for controller in active_controllers:
            controller.handle_tick()


@dataclass
class AnimationState:
    """Global animation state for a single tile_id.

    Each animated tile type (e.g., "mon_birb") has one global state that
    tracks which frame is currently active and how many ticks remain.
    Individual tile instances use position-based offsets for variety.
    """

    tile_id: str
    frames: list[WeightedSprite]
    current_frame_index: int = 0
    ticks_remaining: int = 0

    def __post_init__(self):
        """Initialize ticks_remaining from first frame's weight."""
        if self.ticks_remaining == 0 and self.frames:
            self.ticks_remaining = self.frames[0].weight


class AnimationStateManager:
    """Manages global animation states for all animated tile types.

    This class tracks the animation state for each unique tile_id,
    not for each individual tile instance on the map. Position-based
    offsets provide visual variety while keeping memory usage low.
    """

    def __init__(self):
        """Initialize the animation state manager."""
        # tile_id -> AnimationState
        self._states: dict[str, AnimationState] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def register_animated_tile(
        self, tile_id: str, weighted_sprites: list[WeightedSprite]
    ) -> None:
        """Register an animated tile type for state tracking.

        Should be called when an animated tile is first encountered during
        rendering. Safe to call multiple times for the same tile_id.

        Args:
            tile_id: Unique identifier for the tile (e.g., "mon_birb")
            weighted_sprites: List of weighted sprite frames for animation
        """
        if tile_id not in self._states:
            self._states[tile_id] = AnimationState(
                tile_id=tile_id, frames=weighted_sprites
            )
            self.logger.debug(
                f"Registered animated tile: {tile_id} with {len(weighted_sprites)} frames"
            )

    def get_current_sprite_for_position(self, tile_id: str, x: int, y: int) -> int:
        """Get the current sprite index for a tile at a specific position.

        Uses the global animation state for the tile_id, but applies a
        deterministic position-based offset so tiles at different locations
        show different frames (desynchronized animation).

        Args:
            tile_id: Tile identifier
            x: Grid X coordinate
            y: Grid Y coordinate

        Returns:
            Sprite index to render
        """
        if tile_id not in self._states:
            self.logger.warning(
                f"Attempted to get sprite for unregistered animated tile: {tile_id}"
            )
            return 0

        state = self._states[tile_id]

        if not state.frames:
            return 0

        # Deterministic offset based on position
        # This creates visual variety while remaining predictable
        position_offset = hash((x, y)) % len(state.frames)

        # Current global frame + local offset
        actual_index = (state.current_frame_index + position_offset) % len(state.frames)

        frame = state.frames[actual_index]

        # Handle both int and list[int] sprite values
        if isinstance(frame.sprite, int):
            return frame.sprite
        elif frame.sprite:  # It's a list[int]
            return frame.sprite[0]
        else:
            return 0

    def get_current_frame_for_position(
        self, tile_id: str, x: int, y: int
    ) -> WeightedSprite | None:
        """Get the current WeightedSprite frame for a tile at a position.

        This mirrors get_current_sprite_for_position but returns the full
        WeightedSprite so callers can handle rotation arrays themselves.

        Args:
            tile_id: Tile identifier
            x: Grid X coordinate
            y: Grid Y coordinate

        Returns:
            WeightedSprite for the current frame, or None if unavailable
        """
        if tile_id not in self._states:
            self.logger.warning(
                f"Attempted to get frame for unregistered animated tile: {tile_id}"
            )
            return None

        state = self._states[tile_id]
        if not state.frames:
            return None

        position_offset = hash((x, y)) % len(state.frames)
        actual_index = (state.current_frame_index + position_offset) % len(state.frames)
        return state.frames[actual_index]

    def tick(self) -> None:
        """Advance all animation states by one tick.

        Decrements tick counters and advances to next frames when needed.
        This should be called by AnimationController at the configured interval.
        """
        for state in self._states.values():
            state.ticks_remaining -= 1

            if state.ticks_remaining <= 0:
                # Move to next frame
                state.current_frame_index = (state.current_frame_index + 1) % len(
                    state.frames
                )
                state.ticks_remaining = state.frames[state.current_frame_index].weight

    def clear(self) -> None:
        """Clear all animation states.

        Useful when loading a new map or tileset.
        """
        self._states.clear()
        self.logger.debug("Cleared all animation states")

    def get_registered_count(self) -> int:
        """Get the number of registered animated tile types.

        Returns:
            Count of unique animated tile_ids
        """
        return len(self._states)


class AnimationController:
    """Controls animation timing and coordinates scene updates.

    Uses GlobalAnimationCoordinator to prevent timer conflicts when multiple
    MapViews animate simultaneously. Each controller registers with the global
    coordinator and receives tick notifications.
    """

    def __init__(
        self,
        map_view: "MapView",
        state_manager: AnimationStateManager,
        settings: AppSettings,
    ):
        """Initialize the animation controller.

        Args:
            map_view: MapView instance that will handle redraws
            state_manager: AnimationStateManager for frame tracking
            settings: Application settings (for animation_timeout)
        """
        self.map_view = map_view
        self.state_manager = state_manager
        self.settings = settings
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Register with global coordinator
        self._coordinator = GlobalAnimationCoordinator()
        self._coordinator.register(self)

        # Active state flag
        self._is_active = False

        # Render overload protection
        self._is_rendering = False
        self._render_pending = False
        self._skipped_ticks = 0

        # Frame timing tracking
        self._last_frame_time: float = 0
        self._frame_delta_ms: float = 0

    def __del__(self):
        """Cleanup: unregister from coordinator."""
        if hasattr(self, "_coordinator"):
            self._coordinator.unregister(self)

    def start(self) -> None:
        """Start animation for this controller.

        Activates this controller and starts the global timer if needed.
        """
        self._is_active = True
        interval = self.settings.editor.animation_timeout
        self._coordinator.start_timer(interval)
        self.logger.debug(f"Animation started with interval: {interval}ms")

    def stop(self) -> None:
        """Stop animation for this controller."""
        self._is_active = False
        self._coordinator.stop_timer()
        self.logger.debug("Animation stopped")

    def pause(self) -> None:
        """Pause animation (alias for stop, for future use)."""
        self.stop()

    def resume(self) -> None:
        """Resume animation (alias for start, for future use)."""
        self.start()

    def is_active(self) -> bool:
        """Check if animation is currently running.

        Returns:
            True if this controller is active
        """
        return self._is_active

    def update_interval(self) -> None:
        """Update timer interval from current settings.

        Recalculates the global coordinator interval if this controller is active.
        """
        if self._is_active:
            self._coordinator.update_interval()
            self.logger.debug("Animation interval update requested")

    def get_skipped_ticks(self) -> int:
        """Get the count of skipped ticks since last successful render.

        Useful for performance monitoring and debugging.

        Returns:
            Number of consecutive skipped ticks
        """
        return self._skipped_ticks

    def get_frame_delta_ms(self) -> int:
        """Get time elapsed since last frame in milliseconds.

        Returns:
            Time in milliseconds between last two frames
        """
        return int(self._frame_delta_ms)

    def handle_tick(self) -> None:
        """Handle animation tick from global coordinator.

        Called by GlobalAnimationCoordinator. Updates animation states
        and triggers a scene redraw. Skips if previous render hasn't completed.
        """
        # Skip if previous render still in progress or already queued
        if self._is_rendering or self._render_pending:
            self._skipped_ticks += 1

            # Log warning if too many consecutive skips
            if self._skipped_ticks == 10:
                self.logger.warning(
                    f"Animation overload: {self._skipped_ticks} consecutive ticks skipped. "
                    f"Consider increasing animation_timeout or optimizing rendering."
                )
            elif self._skipped_ticks > 10 and self._skipped_ticks % 100 == 0:
                # Log every 100 skips after first warning
                self.logger.warning(
                    f"Animation still overloaded: {self._skipped_ticks} skips"
                )

            return

        # Log recovery from overload
        if self._skipped_ticks > 0:
            if self._skipped_ticks > 5:
                self.logger.info(
                    f"Animation recovered after {self._skipped_ticks} skipped ticks"
                )
            self._skipped_ticks = 0

        # Update animation state immediately (lightweight)
        try:
            self.state_manager.tick()
        except Exception as e:
            self.logger.error(f"Error updating animation state: {e}", exc_info=True)
            return

        # Queue render asynchronously to avoid blocking timer slot
        self._render_pending = True
        QTimer.singleShot(0, lambda: self._run_render())  # type: ignore[arg-type]

    def _run_render(self) -> None:
        """Run render_map asynchronously; clears render flags when done."""
        if self._is_rendering:
            # Should not happen, but guard against re-entry
            self._render_pending = False
            return

        self._is_rendering = True
        try:
            self.map_view.render_map()

            # Measure time after render completes
            current_time = time.perf_counter() * 1000  # ms
            if self._last_frame_time > 0:
                delta = current_time - self._last_frame_time

                # Filter tiny deltas (likely coalesced ticks)
                min_delta = max(2.0, self.settings.editor.animation_timeout / 2)
                if delta >= min_delta:
                    # Optional smoothing (EWMA)
                    alpha = 0.2
                    if self._frame_delta_ms > 0:
                        smoothed = alpha * delta + (1 - alpha) * self._frame_delta_ms
                        self._frame_delta_ms = int(smoothed)  # type: ignore[assignment]
                    else:
                        self._frame_delta_ms = int(delta)  # type: ignore[assignment]
            self._last_frame_time = current_time
        except Exception as e:
            self.logger.error(f"Error during animation render: {e}", exc_info=True)
        finally:
            self._is_rendering = False
            self._render_pending = False
