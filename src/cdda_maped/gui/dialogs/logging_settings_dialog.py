"""
Logging settings dialog for CDDA-maped.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QLabel,
    QDialogButtonBox,
    QPushButton,
    QWidget,
)
from PySide6.QtCore import Qt

from cdda_maped.resources.style_manager import apply_style_class

from ...settings import AppSettings
from .base_dialog import BaseDialog


class LoggingSettingsDialog(BaseDialog):
    """Dialog for configuring logging settings."""

    def __init__(self, settings: AppSettings, parent: Optional[QWidget] = None):
        super().__init__(parent, title="Logging Settings")
        self.settings = settings

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup the user interface."""
        main_vbox = QVBoxLayout(self)

        # region Console logging group
        console_group = QGroupBox("Console Logging")
        console_layout = QFormLayout()

        self.console_enabled_check = QCheckBox("Enable console logging")
        console_layout.addRow(self.console_enabled_check)

        self.console_level_combo = QComboBox()
        self.console_level_combo.addItems(
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        console_layout.addRow("Console log level:", self.console_level_combo)

        self.console_colors_check = QCheckBox("Use colors in console")
        console_layout.addRow(self.console_colors_check)

        console_group.setLayout(console_layout)
        main_vbox.addWidget(console_group)

        # region File logging group
        file_group = QGroupBox("File Logging")
        file_layout = QFormLayout()

        self.file_enabled_check = QCheckBox("Enable file logging")
        file_layout.addRow(self.file_enabled_check)

        # Log file path (read-only)
        log_path_layout = QHBoxLayout()
        # self.log_path_field = QLineEdit()
        # self.log_path_field.setReadOnly(True)
        # self.log_path_field.setText(self.settings.log_file_path)
        # log_path_layout.addWidget(self.log_path_field)

        open_button = QPushButton("Open Folder")
        open_button.clicked.connect(self._open_log_folder)
        log_path_layout.addWidget(open_button)

        file_layout.addRow("Log file path:", log_path_layout)

        # Info label
        info_label = QLabel("Note: File logging always captures DEBUG level")
        apply_style_class(info_label, "info")
        info_label.setWordWrap(True)
        file_layout.addRow(info_label)

        file_group.setLayout(file_layout)
        main_vbox.addWidget(file_group)

        # region GUI logging group
        gui_group = QGroupBox("GUI Logging")
        gui_layout = QFormLayout()

        # GUI logging is always enabled
        info_label = QLabel(
            "GUI logging is always enabled with level DEBUG. Setting below will affect only log viewer display."
        )
        apply_style_class(info_label, "info")
        info_label.setWordWrap(True)
        gui_layout.addRow(info_label)

        self.gui_level_combo = QComboBox()
        self.gui_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        gui_layout.addRow("GUI log level:", self.gui_level_combo)

        note_label = QLabel("Note: Press ` to open log viewer")
        apply_style_class(note_label, "info")
        gui_layout.addRow(note_label)

        gui_group.setLayout(gui_layout)
        main_vbox.addWidget(gui_group)

        # region Restart note
        restart_note = QLabel(
            "Note: Changes will take effect after application restart"
        )
        restart_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        apply_style_class(restart_note, "info")
        main_vbox.addWidget(restart_note)

        # region Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        main_vbox.addWidget(button_box)

    def _load_settings(self):
        """Load current settings into UI."""
        # Console settings
        self.console_enabled_check.setChecked(self.settings.console_logging)
        self.console_level_combo.setCurrentText(self.settings.console_log_level)
        self.console_colors_check.setChecked(self.settings.console_use_colors)

        # File settings
        self.file_enabled_check.setChecked(self.settings.file_logging)

        # GUI settings
        self.gui_level_combo.setCurrentText(self.settings.gui_log_level)

    def _save_and_accept(self):
        """Save settings and close dialog."""
        # Save console settings
        self.settings.console_logging = self.console_enabled_check.isChecked()
        self.settings.console_log_level = self.console_level_combo.currentText()
        self.settings.console_use_colors = self.console_colors_check.isChecked()

        # Save file settings
        self.settings.file_logging = self.file_enabled_check.isChecked()

        # Save GUI settings
        self.settings.gui_log_level = self.gui_level_combo.currentText()

        # Sync settings to storage
        self.settings.sync()

        self.logger.info("Logging settings updated")
        self.accept()

    def _open_log_folder(self):
        """Open the folder containing log file."""
        import subprocess
        import sys
        from pathlib import Path

        log_path = Path(self.settings.log_file_path).resolve()
        folder_path = log_path.parent

        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", str(folder_path)])
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder_path)])
            else:
                subprocess.run(["xdg-open", str(folder_path)])
        except Exception as e:
            self.logger.error(f"Failed to open log folder: {e}")
