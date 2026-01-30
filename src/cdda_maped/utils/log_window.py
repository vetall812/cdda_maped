"""
Log window for CDDA-maped GUI logging.
"""

import logging
from typing import Optional, List, Tuple

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QComboBox,
    QLineEdit,
    QLabel,
    QApplication,
    QFrame,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QFont,
    QTextCharFormat,
    QColor,
    QKeySequence,
    QShortcut,
    QCloseEvent,
)

from ..settings import AppSettings


class LogWindow(QWidget):
    """
    Standalone log window for displaying application logs.
    Features:
    - Real-time log display with color coding
    - Level filtering (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Text search/filtering
    - Copy to clipboard
    - Window geometry saving/restoring
    """

    # Color scheme for log levels
    LEVEL_COLORS = {
        "DEBUG": QColor(100, 149, 237),  # CornflowerBlue
        "INFO": QColor(50, 205, 50),  # LimeGreen
        "WARNING": QColor(255, 165, 0),  # Orange
        "ERROR": QColor(220, 20, 60),  # Crimson
        "CRITICAL": QColor(139, 0, 139),  # DarkMagenta
    }

    def __init__(self, settings: AppSettings, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.settings = settings
        self.auto_scroll = True
        self.current_filter_level = logging.INFO
        self.search_text = ""

        # Store all log records for filtering/searching
        self.all_log_records: List[Tuple[logging.LogRecord, str]] = []

        self.setup_ui()
        self.setup_window()
        self.setup_shortcuts()

        # Restore window geometry (use separate log window settings)
        if not self.settings.restore_log_window_geometry(self):
            # Default size: 50% of screen
            screen = QApplication.primaryScreen()
            if screen:
                screen_rect = screen.availableGeometry()
                width = int(screen_rect.width() * 0.5)
                height = int(screen_rect.height() * 0.5)
                self.resize(width, height)

                # Center on screen
                x = (screen_rect.width() - width) // 2
                y = (screen_rect.height() - height) // 2
                self.move(x, y)

    def setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Top toolbar
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)

        # Main log display
        self.log_display = QTextEdit()
        self.log_display.setFont(QFont("Consolas", 9))  # Monospace font
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_display)

        # Bottom status bar
        status_bar = self.create_status_bar()
        layout.addWidget(status_bar)

    def create_toolbar(self) -> QFrame:
        """Create the top toolbar with controls."""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.Shape.Box)
        toolbar_layout = QHBoxLayout()
        toolbar.setLayout(toolbar_layout)

        # Level filter
        toolbar_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText(logging.getLevelName(self.current_filter_level))
        self.level_combo.currentTextChanged.connect(self.on_level_filter_changed)
        toolbar_layout.addWidget(self.level_combo)

        toolbar_layout.addWidget(QLabel("  Search:"))

        # Search field
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Filter by text...")
        self.search_field.textChanged.connect(self.on_search_changed)
        toolbar_layout.addWidget(self.search_field)

        # Clear search button
        clear_search_btn = QPushButton("Clear")
        clear_search_btn.clicked.connect(self.clear_search)
        toolbar_layout.addWidget(clear_search_btn)

        toolbar_layout.addStretch()

        # Control buttons
        self.auto_scroll_btn = QPushButton("Auto-scroll: ON")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.clicked.connect(self.toggle_auto_scroll)
        toolbar_layout.addWidget(self.auto_scroll_btn)

        copy_btn = QPushButton("Copy All")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        toolbar_layout.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_logs)
        toolbar_layout.addWidget(clear_btn)

        return toolbar

    def create_status_bar(self) -> QFrame:
        """Create the bottom status bar."""
        status_bar = QFrame()
        status_bar.setFrameStyle(QFrame.Shape.Box)
        status_layout = QHBoxLayout()
        status_bar.setLayout(status_layout)

        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.line_count_label = QLabel("Lines: 0")
        status_layout.addWidget(self.line_count_label)

        return status_bar

    def setup_window(self) -> None:
        """Setup window properties."""
        self.setWindowTitle("CDDA-maped - Log Viewer")
        self.setObjectName("log_window")

    def setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Ctrl+F for search focus
        search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        search_shortcut.activated.connect(self.focus_search)

        # Ctrl+C for copy
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        copy_shortcut.activated.connect(self.copy_to_clipboard)

        # Escape to close window
        close_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        close_shortcut.activated.connect(self.hide)

    def add_log_message(
        self, record: logging.LogRecord, formatted_message: str
    ) -> None:
        """Add a log message to the display."""
        # Always store the message regardless of filters
        self.all_log_records.append((record, formatted_message))

        # Check level filter
        if record.levelno < self.current_filter_level:
            return

        # Check text filter
        if (
            self.search_text
            and self.search_text.lower() not in formatted_message.lower()
        ):
            return

        # Display the message
        self._display_message(record, formatted_message)

    def _display_message(
        self, record: logging.LogRecord, formatted_message: str
    ) -> None:
        """Display a single message in the log widget."""
        # Get color for level
        color = self.LEVEL_COLORS.get(record.levelname, QColor(0, 0, 0))

        # Create formatted text
        cursor = self.log_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        # Set color
        format = QTextCharFormat()
        format.setForeground(color)
        cursor.setCharFormat(format)

        # Insert text
        cursor.insertText(formatted_message + "\n")

        # Auto-scroll if enabled
        if self.auto_scroll:
            self.log_display.verticalScrollBar().setValue(
                self.log_display.verticalScrollBar().maximum()
            )

        # Update line count
        self.update_line_count()

        # Update status
        self.status_label.setText(
            f"Last: {record.levelname} - {record.getMessage()[:50]}..."
        )

    def on_level_filter_changed(self, level_text: str) -> None:
        """Handle level filter change."""
        self.current_filter_level = getattr(logging, level_text)
        self.refresh_display()

    def on_search_changed(self, text: str) -> None:
        """Handle search text change."""
        self.search_text = text
        # Debounce search to avoid too frequent updates
        if hasattr(self, "_search_timer"):
            self._search_timer.stop()
        self._search_timer: QTimer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.refresh_display)
        self._search_timer.start(300)  # 300ms delay

    def clear_search(self) -> None:
        """Clear search field."""
        self.search_field.clear()

    def toggle_auto_scroll(self, checked: bool) -> None:
        """Toggle auto-scroll mode."""
        self.auto_scroll = checked
        self.auto_scroll_btn.setText(f"Auto-scroll: {'ON' if checked else 'OFF'}")

    def copy_to_clipboard(self) -> None:
        """Copy all visible text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_display.toPlainText())
        self.status_label.setText("Copied to clipboard")

    def clear_logs(self) -> None:
        """Clear the log display and all stored records."""
        self.log_display.clear()
        self.all_log_records.clear()
        self.update_line_count()
        self.status_label.setText("Logs cleared")

    def focus_search(self) -> None:
        """Focus the search field."""
        self.search_field.setFocus()
        self.search_field.selectAll()

    def refresh_display(self) -> None:
        """Refresh the entire display (used after filter changes)."""
        # Clear current display
        self.log_display.clear()

        # Re-apply all stored messages through current filters
        for record, formatted_message in self.all_log_records:
            # Check level filter
            if record.levelno < self.current_filter_level:
                continue

            # Check text filter
            if (
                self.search_text
                and self.search_text.lower() not in formatted_message.lower()
            ):
                continue

            # Display the message
            self._display_message(record, formatted_message)

        # Update status
        self.status_label.setText(
            f"Filter: {logging.getLevelName(self.current_filter_level)} "
            + (f"Search: '{self.search_text}'" if self.search_text else "")
        )

    def update_line_count(self) -> None:
        """Update the line count display."""
        line_count = self.log_display.document().lineCount()
        self.line_count_label.setText(f"Lines: {line_count}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        # Save window geometry (use separate log window settings)
        self.settings.save_log_window_geometry(self)

        # Hide instead of close to keep the window available
        event.ignore()
        self.hide()

    def show_and_raise(self) -> None:
        """Show window and bring it to front."""
        self.show()
        self.raise_()
        self.activateWindow()

    def show_and_focus(self) -> None:
        """Show window and give it focus."""
        self.show_and_raise()
        # Small delay to ensure window is shown before focusing
        QTimer.singleShot(50, lambda: self.setFocus())  # type: ignore
