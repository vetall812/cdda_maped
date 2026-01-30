"""
Style management for CDDA-maped application.

Provides centralized loading and application of Qt stylesheets.
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget


class StyleManager:
    """Manages application stylesheets and themes."""

    def __init__(self):
        """Initialize the style manager."""
        self.styles_dir = Path(__file__).parent / "styles"
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._loaded_styles: dict[str, str] = {}

    def load_style(self, style_name: str) -> Optional[str]:
        """Load a stylesheet from file.

        Args:
            style_name: Name of the style file (without .qss extension)

        Returns:
            Stylesheet content or None if not found
        """
        if style_name in self._loaded_styles:
            return self._loaded_styles[style_name]

        style_file = self.styles_dir / f"{style_name}.qss"

        if not style_file.exists():
            self.logger.warning(f"Style file not found: {style_file}")
            return None

        try:
            with open(style_file, "r", encoding="utf-8") as f:
                content = f.read()
                self._loaded_styles[style_name] = content
                self.logger.debug(f"Loaded stylesheet: {style_name}")
                return content
        except Exception as e:
            self.logger.error(f"Failed to load stylesheet {style_name}: {e}")
            return None

    def apply_style(self, widget: QWidget, style_name: str) -> bool:
        """Apply a stylesheet to a widget.

        Args:
            widget: Widget to apply style to
            style_name: Name of the style file

        Returns:
            True if style was applied successfully
        """
        style_content = self.load_style(style_name)
        if style_content:
            widget.setStyleSheet(style_content)
            return True
        return False

    def apply_app_style(self, app: QApplication, style_name: str = "main") -> bool:
        """Apply a stylesheet to the entire application.

        Args:
            app: QApplication instance
            style_name: Name of the style file (default: "main")

        Returns:
            True if style was applied successfully
        """
        # Load main style
        main_style = self.load_style(style_name)
        if not main_style:
            return False

        # Load additional styles (e.g., map_view)
        additional_styles = ["map_view"]
        combined_style = main_style

        for additional_style_name in additional_styles:
            additional_content = self.load_style(additional_style_name)
            if additional_content:
                combined_style += (
                    f"\n\n/* {additional_style_name}.qss */\n{additional_content}"
                )

        app.setStyleSheet(combined_style)
        self.logger.info(
            f"Applied application stylesheet: {style_name} with {len(additional_styles)} additional styles"
        )
        return True


# Global style manager instance
style_manager = StyleManager()


def apply_style_class(widget: QWidget, class_name: str) -> None:
    """Apply a style class to a widget by setting its 'class' property.

    The actual styling is done via QSS file using selectors like QLabel[class="title"].
    This function only sets the property that QSS selectors will match against.

    Args:
        widget: Widget to apply class to
        class_name: CSS class name (should match selectors in QSS files)
    """
    widget.setProperty("class", class_name)
    # Force style recalculation to apply new property
    widget.style().unpolish(widget)
    widget.style().polish(widget)
