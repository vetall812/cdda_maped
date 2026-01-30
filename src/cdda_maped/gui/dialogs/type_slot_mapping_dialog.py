"""
Dialog for configuring object type to cell slot mapping.

Allows users to map CDDA object types to cell slots for rendering and editing.
"""

import logging

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QHeaderView,
    QMessageBox,
    QWidget,
)
from PySide6.QtCore import Qt

from ...settings import AppSettings
from ...maps.models import CellSlot

logger = logging.getLogger(__name__)


class TypeSlotMappingDialog(QDialog):
    """Dialog for configuring type-to-slot mapping."""

    def __init__(
        self,
        settings: AppSettings,
        available_types: list[str],
        parent: QWidget | None = None,
    ):
        """Initialize the dialog.

        Args:
            settings: AppSettings instance
            available_types: List of all available CDDA object types from game data
            parent: Parent widget
        """
        super().__init__(parent)
        self.settings = settings
        self.available_types = sorted(available_types)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self.setWindowTitle("Type to Slot Mapping")
        self.setMinimumSize(600, 500)

        self.setup_ui()
        self.load_current_mapping()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Info label
        info_label = QLabel(
            "Configure which cell slot each CDDA object type is assigned to.\n"
            "Only mapped types will be available in the object browser."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Table for mapping
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Object Type", "Cell Slot"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_mapping)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def load_current_mapping(self):
        """Load current mapping from settings into the table."""
        # Get current mapping
        current_mapping = self.settings.type_slot_mapping.get_mapping()

        # Get all available slots
        available_slots = [slot.name for slot in CellSlot]

        # Populate table with all available types
        self.table.setRowCount(len(self.available_types))

        for row, object_type in enumerate(self.available_types):
            # Type name (read-only)
            type_item = QTableWidgetItem(object_type)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, type_item)

            # Slot combo box
            slot_combo = QComboBox()
            slot_combo.addItem("(none)")  # Option to unmap
            slot_combo.addItems(available_slots)

            # Set current value
            current_slot = current_mapping.get(object_type)
            if current_slot:
                index = slot_combo.findText(current_slot)
                if index >= 0:
                    slot_combo.setCurrentIndex(index)
            else:
                slot_combo.setCurrentIndex(0)  # (none)

            self.table.setCellWidget(row, 1, slot_combo)

    def get_mapping_from_table(self) -> dict[str, str]:
        """Extract mapping from the table.

        Returns:
            Dictionary mapping object type to slot name (excluding unmapped types)
        """
        mapping: dict[str, str] = {}

        for row in range(self.table.rowCount()):
            type_item = self.table.item(row, 0)
            slot_combo_widget = self.table.cellWidget(row, 1)

            if (
                type_item
                and slot_combo_widget
                and isinstance(slot_combo_widget, QComboBox)
            ):
                object_type = type_item.text()
                slot_name = slot_combo_widget.currentText()

                # Only include if not "(none)"
                if slot_name != "(none)":
                    mapping[object_type] = slot_name

        return mapping

    def save_mapping(self):
        """Save the mapping to settings."""
        try:
            mapping = self.get_mapping_from_table()

            # Check if at least one type is mapped
            if not mapping:
                QMessageBox.warning(
                    self,
                    "No Types Mapped",
                    "You must map at least one object type to a slot.\n\n"
                    "Click 'Reset to Defaults' to restore default mappings.",
                )
                return

            # Save to settings
            self.settings.type_slot_mapping.set_mapping(mapping)

            self.logger.info(f"Saved type-slot mapping with {len(mapping)} entries")
            self.accept()

        except Exception as e:
            self.logger.error(f"Failed to save mapping: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save mapping:\n{e}")

    def reset_to_defaults(self):
        """Reset mapping to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset the type-slot mapping to default values?\n\n"
            "This will restore the standard mappings for terrain, furniture, and items.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings.type_slot_mapping.reset_to_defaults()
            self.load_current_mapping()
            self.logger.info("Reset type-slot mapping to defaults")
