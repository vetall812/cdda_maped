"""
JSON display widget for showing formatted JSON data.

Provides read-only text display with syntax highlighting and scrolling.
"""

from typing import Optional, Any
import json
import logging
from dataclasses import asdict, is_dataclass

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PySide6.QtGui import QFont

from ..resources.style_manager import apply_style_class


class JsonDisplayWidget(QWidget):
    """
    Widget for displaying formatted JSON data.

    Provides syntax highlighting and scrollable view.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.title = title
        self.setup_ui()
        self.logger.debug(f"JsonDisplayWidget '{title}' initialized")

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Title label
        title_label = QLabel(self.title)
        apply_style_class(title_label, "json-title")
        layout.addWidget(title_label)

        # Text display
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        # Set monospace font for better JSON readability
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.text_edit.setFont(font)

        # Set placeholder text
        self.text_edit.setPlaceholderText("No data selected")

        layout.addWidget(self.text_edit)

    def set_json_data(self, data: Optional[Any]):
        """Set JSON data to display."""
        if data is None:
            self.text_edit.clear()
            self.text_edit.setPlaceholderText("No data available")
            return

        try:
            # Convert dataclass objects to dict recursively
            serializable_data = self._strip_nulls(self._make_serializable(data))

            # Format JSON with indentation
            formatted_json = json.dumps(serializable_data, indent=2, ensure_ascii=False)
            self.text_edit.setPlainText(formatted_json)

        except (TypeError, ValueError) as e:
            self.logger.error(f"Failed to format JSON: {e}")
            self.text_edit.setPlainText(f"Error formatting JSON: {e}")

    def _strip_nulls(self, obj: Any) -> Any:
        """Recursively drop fields and items that are None or height_3d=0 to keep JSON compact."""
        if isinstance(obj, dict):
            return {k: self._strip_nulls(v) for k, v in obj.items() if v is not None and not (k == "height_3d" and v == 0)}  # type: ignore
        if isinstance(obj, list):
            return [self._strip_nulls(v) for v in obj if v is not None]  # type: ignore
        return obj

    def _make_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format."""
        try:
            if is_dataclass(obj) and not isinstance(obj, type):
                return asdict(obj)  # type: ignore
            elif isinstance(obj, dict):
                return {str(key): self._make_serializable(value) for key, value in obj.items()}  # type: ignore
            elif isinstance(obj, (list, tuple)):
                return [self._make_serializable(item) for item in obj]  # type: ignore
            else:
                return obj
        except Exception:
            # If conversion fails, return string representation
            self.logger.error(
                "Failed to serialize object for JSON display", exc_info=True
            )
            return str(obj)  # type: ignore

    def clear(self):
        """Clear the display."""
        self.text_edit.clear()
        self.text_edit.setPlaceholderText("No data selected")
