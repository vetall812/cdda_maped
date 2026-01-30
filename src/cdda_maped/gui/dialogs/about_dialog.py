"""
About dialog for CDDA-maped.
"""

from typing import Optional
from PySide6.QtWidgets import QMessageBox, QWidget, QApplication
from PySide6.QtCore import Qt


def show_about_dialog(
    version: str,
    game_path: Optional[str] = None,
    parent: Optional[QWidget] = None,
) -> None:
    """
    Show about dialog with application information.

    Args:
        version: Application version string
        game_path: Path to CDDA game directory (optional)
        parent: Parent widget
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle("")  # No title

    game_path_display = game_path if game_path else "Not configured"

    msg.setText(
        f"<h3>CDDA-maped v{version}</h3>"
        "<p>Visual map editor for Cataclysm: Dark Days Ahead</p>"
        "<p>A cross-platform tool for creating and editing CDDA maps with tileset support.</p>"
        f"<p><b>Configuration:</b><br>"
        f"game path: {game_path_display}<br>"
    )

    # Set application icon inside dialog
    msg.setIconPixmap(QApplication.windowIcon().pixmap(64, 64))

    # Apply custom window flags for fixed size dialog
    msg.setWindowFlags(
        Qt.WindowType.Dialog
        | Qt.WindowType.CustomizeWindowHint
        | Qt.WindowType.MSWindowsFixedSizeDialogHint
    )

    msg.exec()
