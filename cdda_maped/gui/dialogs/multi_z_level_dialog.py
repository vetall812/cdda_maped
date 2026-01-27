"""
Multi-Z-Level Settings Dialog.

Provides UI for configuring multi-z-level rendering with live preview
of brightness and transparency values.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QLabel,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget
)
from PySide6.QtCore import Qt, Signal

from ...settings import AppSettings


class MultiZLevelDialog(QDialog):
    """Dialog for configuring multi-z-level rendering settings."""

    settings_changed = Signal()

    def __init__(self, settings: AppSettings, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.settings = settings
        self.mzl_settings = settings.multi_z_level

        self.setWindowTitle("Multi-Z-Level Rendering Settings")
        self.resize(700, 600)

        self._setup_ui()
        self._load_settings()
        self._connect_signals()
        self._update_preview()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)

        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable Multi-Z-Level Rendering")
        layout.addWidget(self.enable_checkbox)

        # Z-Level Range group
        range_group = QGroupBox("Z-Level Range")
        range_layout = QFormLayout()

        self.levels_above_spin = QSpinBox()
        self.levels_above_spin.setRange(0, 10)
        self.levels_above_spin.setSuffix(" levels")
        range_layout.addRow("Levels above current:", self.levels_above_spin)

        self.levels_below_spin = QSpinBox()
        self.levels_below_spin.setRange(0, 10)
        self.levels_below_spin.setSuffix(" levels")
        range_layout.addRow("Levels below current:", self.levels_below_spin)

        range_group.setLayout(range_layout)
        layout.addWidget(range_group)

        # Brightness group
        brightness_group = QGroupBox("Brightness Settings")
        brightness_layout = QFormLayout()

        self.brightness_method_combo = QComboBox()
        self.brightness_method_combo.addItems(["Add", "Magnify", "None"])
        brightness_layout.addRow("Adjustment method:", self.brightness_method_combo)

        self.brightness_step_spin = QDoubleSpinBox()
        self.brightness_step_spin.setRange(0.0, 100.0)
        self.brightness_step_spin.setSuffix(" %")
        self.brightness_step_spin.setSingleStep(5.0)
        brightness_layout.addRow("Step per level:", self.brightness_step_spin)

        self.brightness_above_combo = QComboBox()
        self.brightness_above_combo.addItems(["Darken", "Lighten", "None"])
        brightness_layout.addRow("Operation above current:", self.brightness_above_combo)

        self.brightness_below_combo = QComboBox()
        self.brightness_below_combo.addItems(["Darken", "Lighten", "None"])
        brightness_layout.addRow("Operation below current:", self.brightness_below_combo)

        brightness_group.setLayout(brightness_layout)
        layout.addWidget(brightness_group)

        # Transparency group
        transparency_group = QGroupBox("Transparency Settings")
        transparency_layout = QFormLayout()

        self.transparency_method_combo = QComboBox()
        self.transparency_method_combo.addItems(["Add", "Magnify", "None"])
        transparency_layout.addRow("Adjustment method:", self.transparency_method_combo)

        self.transparency_step_spin = QDoubleSpinBox()
        self.transparency_step_spin.setRange(0.0, 100.0)
        self.transparency_step_spin.setSuffix(" %")
        self.transparency_step_spin.setSingleStep(5.0)
        transparency_layout.addRow("Step per level:", self.transparency_step_spin)

        transparency_group.setLayout(transparency_layout)
        layout.addWidget(transparency_group)

        # Preview table
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()

        preview_label = QLabel(
            "Preview shows calculated brightness and transparency factors "
            "for each z-level offset from current (0):"
        )
        preview_label.setWordWrap(True)
        preview_layout.addWidget(preview_label)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(
            ["Z-Level Offset", "Brightness Factor", "Transparency Factor"]
        )
        self.preview_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.preview_table.setMaximumHeight(250)
        preview_layout.addWidget(self.preview_table)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _connect_signals(self):
        """Connect widget signals to update preview."""
        self.enable_checkbox.toggled.connect(self._on_settings_changed)
        self.levels_above_spin.valueChanged.connect(self._on_settings_changed)
        self.levels_below_spin.valueChanged.connect(self._on_settings_changed)
        self.brightness_method_combo.currentTextChanged.connect(self._on_settings_changed)
        self.brightness_step_spin.valueChanged.connect(self._on_settings_changed)
        self.brightness_above_combo.currentTextChanged.connect(self._on_settings_changed)
        self.brightness_below_combo.currentTextChanged.connect(self._on_settings_changed)
        self.transparency_method_combo.currentTextChanged.connect(self._on_settings_changed)
        self.transparency_step_spin.valueChanged.connect(self._on_settings_changed)

    def _load_settings(self):
        """Load current settings into UI."""
        self.enable_checkbox.setChecked(self.mzl_settings.enabled)
        self.levels_above_spin.setValue(self.mzl_settings.levels_above)
        self.levels_below_spin.setValue(self.mzl_settings.levels_below)

        self.brightness_method_combo.setCurrentText(self.mzl_settings.brightness_method)
        self.brightness_step_spin.setValue(self.mzl_settings.brightness_step * 100.0)
        self.brightness_above_combo.setCurrentText(
            self.mzl_settings.brightness_operation_above
        )
        self.brightness_below_combo.setCurrentText(
            self.mzl_settings.brightness_operation_below
        )

        self.transparency_method_combo.setCurrentText(self.mzl_settings.transparency_method)
        self.transparency_step_spin.setValue(self.mzl_settings.transparency_step * 100.0)

    def _on_settings_changed(self):
        """Handle any setting change - update preview."""
        self._update_preview()

    def _update_preview(self):
        """Update preview table with current settings."""
        # Always show preview for 3 levels above and 3 levels below
        max_levels = 3

        # Temporarily apply UI values to calculate preview
        # (without saving to settings)
        temp_brightness_method = self.brightness_method_combo.currentText()
        temp_brightness_step = self.brightness_step_spin.value() / 100.0
        temp_brightness_above = self.brightness_above_combo.currentText()
        temp_brightness_below = self.brightness_below_combo.currentText()
        temp_transparency_method = self.transparency_method_combo.currentText()
        temp_transparency_step = self.transparency_step_spin.value() / 100.0

        # Calculate preview values
        preview_data: list[tuple[int, float, float]] = []
        for offset in range(-max_levels, max_levels + 1):
            # Calculate brightness
            # Note: negative offset = below current, positive offset = above current
            if offset < 0:
                operation = temp_brightness_below  # type: ignore
            elif offset > 0:
                operation = temp_brightness_above  # type: ignore
            else:
                operation = "None"  # type: ignore

            brightness = self._calculate_brightness(
                offset, temp_brightness_method, temp_brightness_step, operation  # type: ignore
            )
            transparency = self._calculate_transparency(
                offset, temp_transparency_method, temp_transparency_step
            )

            preview_data.append((offset, brightness, transparency))

        # Reverse order: positive offsets (above) at top, negative (below) at bottom
        preview_data.reverse()

        # Get highlight color from palette (light color for current z-level)
        highlight_color = self.palette().color(self.palette().ColorRole.Light)

        # Update table
        self.preview_table.setRowCount(len(preview_data))
        for row, (offset, brightness, transparency) in enumerate(preview_data):
            # Z-Level offset
            offset_item = QTableWidgetItem(f"{offset:+d}")
            offset_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if offset == 0:
                # Highlight current level
                offset_item.setBackground(highlight_color)
            self.preview_table.setItem(row, 0, offset_item)

            # Brightness factor
            brightness_item = QTableWidgetItem(f"{brightness:.2f}")
            brightness_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if offset == 0:
                brightness_item.setBackground(highlight_color)
            self.preview_table.setItem(row, 1, brightness_item)

            # Transparency factor
            transparency_item = QTableWidgetItem(f"{transparency:.2f}")
            transparency_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if offset == 0:
                transparency_item.setBackground(highlight_color)
            self.preview_table.setItem(row, 2, transparency_item)

    def _calculate_brightness(
        self, z_offset: int, method: str, step: float, operation: str
    ) -> float:
        """Calculate brightness factor (matches MultiZLevelSettings logic)."""
        if operation == "None" or z_offset == 0:
            return 1.0

        abs_offset = abs(z_offset)

        if method == "None":
            return 1.0
        elif method == "Add":
            adjustment = step * abs_offset
        elif method == "Magnify":
            adjustment = 1.0 - (1.0 - step) ** abs_offset
        else:
            return 1.0

        if operation == "Darken":
            return max(0.0, 1.0 - adjustment)
        else:  # Lighten
            return 1.0 + adjustment

    def _calculate_transparency(
        self, z_offset: int, method: str, step: float
    ) -> float:
        """Calculate transparency factor (matches MultiZLevelSettings logic)."""
        if z_offset == 0:
            return 1.0

        abs_offset = abs(z_offset)

        if method == "None":
            return 1.0
        elif method == "Add":
            return max(0.0, 1.0 - step * abs_offset)
        elif method == "Magnify":
            return (1.0 - step) ** abs_offset
        else:
            return 1.0

    def _save_and_accept(self):
        """Save settings and accept dialog."""
        try:
            self.mzl_settings.enabled = self.enable_checkbox.isChecked()
            self.mzl_settings.levels_above = self.levels_above_spin.value()
            self.mzl_settings.levels_below = self.levels_below_spin.value()

            self.mzl_settings.brightness_method = self.brightness_method_combo.currentText()  # type: ignore
            self.mzl_settings.brightness_step = self.brightness_step_spin.value() / 100.0
            self.mzl_settings.brightness_operation_above = self.brightness_above_combo.currentText()  # type: ignore
            self.mzl_settings.brightness_operation_below = self.brightness_below_combo.currentText()  # type: ignore

            self.mzl_settings.transparency_method = self.transparency_method_combo.currentText()  # type: ignore
            self.mzl_settings.transparency_step = self.transparency_step_spin.value() / 100.0

            self.logger.info("Multi-z-level settings saved")
            self.settings_changed.emit()
            self.accept()
        except Exception as e:
            self.logger.error(f"Failed to save multi-z-level settings: {e}")
