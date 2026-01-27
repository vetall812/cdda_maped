"""
Dialog for selecting and ordering mods for CDDA-maped.
"""

from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QGroupBox,
    QDialogButtonBox,
    QWidget,
    QCheckBox,
    QHBoxLayout,
    QSizePolicy,
)

from ...resources.style_manager import apply_style_class
from .base_dialog import BaseDialog


class ModSelectionDialog(BaseDialog):
    """Dialog for selecting and ordering active mods."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, title="Configure Active Mods")

        # Lists of mods
        self._available_mods: List[str] = []
        self._active_mods: List[str] = []

        self.setup_ui()

    def setup_ui(self) -> None:
        """Setup the user interface."""
        main_vbox = QVBoxLayout(self)

        # Main content area
        panels_hbox = QHBoxLayout()

        # region Available Mods Panel
        available_group = QGroupBox("Available Mods")
        available_group.setMinimumWidth(200)
        available_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        available_vbox = QVBoxLayout(available_group)

        self.available_list = QListWidget()
        self.available_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        available_vbox.addWidget(self.available_list)

        add_button = QPushButton("Add Selected ->")
        add_button.clicked.connect(self.add_selected_mods)
        available_vbox.addWidget(add_button)

        panels_hbox.addWidget(available_group, stretch=1)

        # endregion

        # region Active Mods Panel
        active_group = QGroupBox("Active Mods (Priority Order)")
        active_group.setMinimumWidth(200)
        active_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        active_vbox = QVBoxLayout(active_group)

        # Control buttons
        control_hbox = QHBoxLayout()

        self.move_up_button = QPushButton("↑ Move Up")
        self.move_up_button.setToolTip("Move selected mod higher in priority")
        self.move_up_button.clicked.connect(self.move_selected_up)
        control_hbox.addWidget(self.move_up_button)

        clear_button = QPushButton("Clear All")
        clear_button.setToolTip("Remove all active mods")
        clear_button.clicked.connect(self.clear_active_mods)
        control_hbox.addWidget(clear_button)

        self.move_down_button = QPushButton("↓ Move Down")
        self.move_down_button.setToolTip("Move selected mod lower in priority")
        self.move_down_button.clicked.connect(self.move_selected_down)
        control_hbox.addWidget(self.move_down_button)

        active_vbox.addLayout(control_hbox)

        priority_label = QLabel("Higher priority (top) ... Lower priority (bottom)")
        apply_style_class(priority_label, "info")
        active_vbox.addWidget(priority_label)

        self.active_list = QListWidget()
        self.active_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.active_list.currentRowChanged.connect(self.update_move_buttons)
        active_vbox.addWidget(self.active_list)

        # Base game inclusion option
        options_hbox = QHBoxLayout()
        self.always_include_core_checkbox = QCheckBox("Include base game files")
        self.always_include_core_checkbox.setToolTip(
            "When checked, base game data is always included with lowest priority. "
            "When unchecked, only objects from explicitly selected mods are shown."
        )
        options_hbox.addWidget(self.always_include_core_checkbox)
        options_hbox.addStretch()
        active_vbox.addLayout(options_hbox)

        remove_button = QPushButton("<- Remove selected")
        remove_button.setToolTip("Remove selected mod from active mods")
        remove_button.clicked.connect(self.remove_selected_mods)
        active_vbox.addWidget(remove_button)

        panels_hbox.addWidget(active_group, stretch=1)

        # endregion

        # Add the panels layout into the dialog's main layout
        main_vbox.addLayout(panels_hbox)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_vbox.addWidget(button_box)

        # Initial state
        self.update_move_buttons()

    def set_available_mods(self, mods: List[str]) -> None:
        """Set the list of available mods."""
        self._available_mods = mods.copy()
        self.refresh_available_list()
        self.logger.debug(f"Set {len(mods)} available mods")

    def set_active_mods(self, mods: List[str]) -> None:
        """Set the list of active mods in priority order."""
        # Filter out base game entries - they're handled by the checkbox
        self._active_mods = [mod for mod in mods if mod != "dda"]
        self.refresh_active_list()
        self.refresh_available_list()  # Update available list to reflect active status
        self.logger.debug(
            f"Set {len(self._active_mods)} active mods (filtered from {len(mods)})"
        )

    def get_active_mods(self) -> List[str]:
        """Get the current list of active mods in priority order."""
        return self._active_mods.copy()

    def set_always_include_core(self, value: bool) -> None:
        """Set the always include core checkbox state."""
        self.always_include_core_checkbox.setChecked(value)

    def get_always_include_core(self) -> bool:
        """Get the always include core checkbox state."""
        return self.always_include_core_checkbox.isChecked()

    def refresh_available_list(self) -> None:
        """Refresh the available mods list."""
        self.available_list.clear()
        for mod_id in self._available_mods:
            # Skip base game entries - they're handled by the checkbox
            if mod_id == "dda":
                continue
            if mod_id not in self._active_mods:
                item = QListWidgetItem(mod_id)
                self.available_list.addItem(item)

    def refresh_active_list(self) -> None:
        """Refresh the active mods list."""
        self.active_list.clear()
        for i, mod_id in enumerate(self._active_mods):
            item = QListWidgetItem(f"{i+1}. {mod_id}")
            item.setData(Qt.ItemDataRole.UserRole, mod_id)
            self.active_list.addItem(item)

    def add_selected_mods(self) -> None:
        """Add selected mods from available to active list."""
        selected_items = self.available_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            mod_id = item.text()
            if mod_id not in self._active_mods:
                self._active_mods.append(mod_id)

        self.refresh_active_list()
        self.refresh_available_list()
        self.logger.debug(f"Added {len(selected_items)} mods to active list")

    def remove_selected_mods(self) -> None:
        """Remove selected mods from active list."""
        current_item = self.active_list.currentItem()
        if not current_item:
            return

        mod_id = current_item.data(Qt.ItemDataRole.UserRole)
        if mod_id in self._active_mods:
            self._active_mods.remove(mod_id)

        self.refresh_active_list()
        self.refresh_available_list()
        self.logger.debug(f"Removed mod '{mod_id}' from active list")

    def move_selected_up(self) -> None:
        """Move selected mod up in priority."""
        current_row = self.active_list.currentRow()
        if current_row <= 0:
            return

        # Swap items in the list
        self._active_mods[current_row], self._active_mods[current_row - 1] = (
            self._active_mods[current_row - 1],
            self._active_mods[current_row],
        )

        self.refresh_active_list()
        self.active_list.setCurrentRow(current_row - 1)
        self.logger.debug(f"Moved mod up in priority")

    def move_selected_down(self) -> None:
        """Move selected mod down in priority."""
        current_row = self.active_list.currentRow()
        if current_row < 0 or current_row >= len(self._active_mods) - 1:
            return

        # Swap items in the list
        self._active_mods[current_row], self._active_mods[current_row + 1] = (
            self._active_mods[current_row + 1],
            self._active_mods[current_row],
        )

        self.refresh_active_list()
        self.active_list.setCurrentRow(current_row + 1)
        self.logger.debug(f"Moved mod down in priority")

    def clear_active_mods(self) -> None:
        """Clear all active mods after confirmation."""
        if not self._active_mods:
            return

        reply = QMessageBox.question(
            self,
            "Clear All Mods",
            "Are you sure you want to remove all active mods?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._active_mods.clear()
            self.refresh_active_list()
            self.refresh_available_list()
            self.logger.debug("Cleared all active mods")

    def update_move_buttons(self) -> None:
        """Update the state of move up/down buttons."""
        current_row = self.active_list.currentRow()
        mod_count = len(self._active_mods)

        self.move_up_button.setEnabled(current_row > 0)
        self.move_down_button.setEnabled(
            current_row >= 0 and current_row < mod_count - 1
        )
