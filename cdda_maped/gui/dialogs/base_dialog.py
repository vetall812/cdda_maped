"""
Base dialog class for CDDA-maped dialogs.

Provides common functionality:
- Logger initialization
- Standard window flags (dialog, custom, title hint)
- Modal behavior
- Auto-resize on show
"""

import logging
from typing import Optional
from PySide6.QtWidgets import QDialog, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent


class BaseDialog(QDialog):
    """Base class for application dialogs with common functionality."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Dialog",
        modal: bool = True,
    ):
        """
        Initialize the base dialog.

        Args:
            parent: Parent widget
            title: Window title
            modal: Whether dialog is modal (blocks interaction with parent)
        """
        super().__init__(parent)

        # Initialize logger with class name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Set window title
        self.setWindowTitle(title)

        # Standard dialog window flags
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        # Set modal behavior
        self.setModal(modal)

        self.logger.debug(f"{self.__class__.__name__} initialized")

    def showEvent(self, arg__1: QShowEvent) -> None:
        """Auto-adjust dialog size when shown."""
        super().showEvent(arg__1)
        self.adjustSize()
