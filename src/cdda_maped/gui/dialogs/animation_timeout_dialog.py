"""
Animation timeout settings dialog for CDDA-maped.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QSpinBox,
    QDialogButtonBox,
    QWidget,
)

from cdda_maped.resources.style_manager import apply_style_class

from ...settings import AppSettings
from .base_dialog import BaseDialog


class AnimationTimeoutDialog(BaseDialog):
    """Dialog for configuring animation timeout."""

    def __init__(self, settings: AppSettings, parent: Optional[QWidget] = None):
        super().__init__(parent, title="Animation Timeout Settings")
        self.settings = settings

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup the user interface."""
        main_vbox = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # Animation timeout spinbox
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setMinimum(1)
        self.timeout_spinbox.setMaximum(1000)
        self.timeout_spinbox.setSuffix(" ms")
        self.timeout_spinbox.setToolTip("Animation timeout in milliseconds (1-1000)")
        form_layout.addRow("Animation timeout:", self.timeout_spinbox)

        # Info label
        info_label = QLabel(
            "Controls the speed of tile animations. "
            "Lower values = faster animations, higher values = slower animations."
        )
        apply_style_class(info_label, "info")
        info_label.setWordWrap(True)
        form_layout.addRow(info_label)

        main_vbox.addLayout(form_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        main_vbox.addWidget(button_box)

    def _load_settings(self):
        """Load current settings into UI."""
        self.timeout_spinbox.setValue(self.settings.editor.animation_timeout)

    def _save_and_accept(self):
        """Save settings and close dialog."""
        self.settings.editor.animation_timeout = self.timeout_spinbox.value()
        self.accept()
