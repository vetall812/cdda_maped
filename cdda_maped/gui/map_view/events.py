"""Event handlers for MapView.

This module provides event handling functionality for MapView,
including mouse panning, keyboard shortcuts, and resize events.
"""

from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QScrollBar


class MapViewEventHandlers:
    """Mixin class for MapView event handling.

    Handles:
    - Mouse panning (middle button or Space+Left button)
    - Keyboard shortcuts (Space for panning cursor)
    - Window resize (repositioning overlay UI)
    """

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize event to reposition overlay UI."""
        super().resizeEvent(event)  # type: ignore

        # Position animation controls in top-right corner
        margin = 10
        button_x = self.width() - self.animation_button.width() - margin  # type: ignore
        button_y = margin

        self.animation_button.move(button_x, button_y)  # type: ignore

        # Position frame stats label below button
        label_x = self.width() - self.frame_stats_label.width() - margin  # type: ignore
        label_y = button_y + self.animation_button.height() + 5  # type: ignore

        self.frame_stats_label.move(label_x, label_y)  # type: ignore

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events for panning."""
        # Middle mouse button or Space+Left mouse button for panning
        if event.button() == Qt.MouseButton.MiddleButton or \
           (event.button() == Qt.MouseButton.LeftButton and self._space_pressed):  # type: ignore
            self._is_panning = True  # type: ignore
            self._pan_start_x = event.position().x()  # type: ignore
            self._pan_start_y = event.position().y()  # type: ignore
            self.setCursor(Qt.CursorShape.ClosedHandCursor)  # type: ignore
            event.accept()
        else:
            super().mousePressEvent(event)  # type: ignore

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move events for panning."""
        if self._is_panning:  # type: ignore
            # Calculate delta movement
            delta_x = event.position().x() - self._pan_start_x  # type: ignore
            delta_y = event.position().y() - self._pan_start_y  # type: ignore

            # Update pan start position
            self._pan_start_x = event.position().x()  # type: ignore
            self._pan_start_y = event.position().y()  # type: ignore

            # Get current scrollbar values and update positions
            h_bar = cast(QScrollBar, self.horizontalScrollBar())  # type: ignore
            v_bar = cast(QScrollBar, self.verticalScrollBar())  # type: ignore
            h_bar.setValue(h_bar.value() - int(delta_x))
            v_bar.setValue(v_bar.value() - int(delta_y))

            event.accept()
        else:
            super().mouseMoveEvent(event)  # type: ignore

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release events for panning."""
        if event.button() == Qt.MouseButton.MiddleButton or \
           (event.button() == Qt.MouseButton.LeftButton and self._is_panning):  # type: ignore
            self._is_panning = False  # type: ignore
            self.setCursor(Qt.CursorShape.ArrowCursor)  # type: ignore
            event.accept()
        else:
            super().mouseReleaseEvent(event)  # type: ignore

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for view control."""
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = True  # type: ignore
            if not self._is_panning:  # type: ignore
                self.setCursor(Qt.CursorShape.OpenHandCursor)  # type: ignore
            event.accept()
        else:
            super().keyPressEvent(event)  # type: ignore

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """Handle key release events for view control."""
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = False  # type: ignore
            if not self._is_panning:  # type: ignore
                self.setCursor(Qt.CursorShape.ArrowCursor)  # type: ignore
            event.accept()
        else:
            super().keyReleaseEvent(event)  # type: ignore
