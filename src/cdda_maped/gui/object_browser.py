"""
Object browser widget for selecting game objects.

Provides a searchable list of CDDA objects filtered by type.
"""

from typing import Optional
import logging

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QPushButton,
    QComboBox,
    QTreeWidget,
    QTreeWidgetItem,
)
from PySide6.QtCore import Qt, Signal

from cdda_maped.game_data.models import GameDataCollection

from ..game_data.service import GameDataService

# Name extraction moved to game_data.collection


class ObjectBrowser(QWidget):
    """
    Widget for browsing and selecting game objects.

    Provides filtering by object type and text search.
    """

    # Signal emitted when an object is selected (object_id: str)
    object_selected = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        emit_selection_signals: bool = True,
    ):
        super().__init__(parent)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self._emit_selection_signals = emit_selection_signals

        self.game_data_service: Optional[GameDataService] = None
        self.app_settings = None  # Will be set when game data service is set
        self.all_objects: GameDataCollection = []
        self.filtered_objects: GameDataCollection = []

        self.setup_ui()

        self.logger.debug(
            f"ObjectBrowser initialized{f' with parent {parent}' if parent else ''}"
        )

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Filter controls
        filter_layout = QHBoxLayout()

        # Object type filter
        filter_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "terrain", "furniture", "item", "monster"])
        self.type_combo.setCurrentText("terrain")  # Default to terrain
        self.type_combo.currentTextChanged.connect(self.filter_objects)
        filter_layout.addWidget(self.type_combo)

        # Search box
        filter_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by ID or name...")
        self.search_edit.textChanged.connect(self.filter_objects)
        filter_layout.addWidget(self.search_edit)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_search)
        filter_layout.addWidget(clear_btn)

        layout.addLayout(filter_layout)

        # Object tree with columns
        self.object_tree = QTreeWidget()
        self.object_tree.setHeaderLabels(["Mod", "Object ID", "Object Name"])
        self.object_tree.setSortingEnabled(True)  # Enable sorting by clicking headers
        self.object_tree.setRootIsDecorated(False)  # Hide tree expansion icons
        self.object_tree.setAlternatingRowColors(
            True
        )  # Alternate row colors for better readability

        # Set column widths
        self.object_tree.setColumnWidth(0, 120)  # Mod column
        self.object_tree.setColumnWidth(1, 200)  # Object ID column
        self.object_tree.setColumnWidth(2, 300)  # Object Name column

        # Connect signals (optional). MainWindow uses this widget only as a browser,
        # without any selection side-effects.
        if self._emit_selection_signals:
            self.object_tree.itemClicked.connect(self.on_object_clicked)
            self.object_tree.itemActivated.connect(self.on_object_activated)
            self.object_tree.currentItemChanged.connect(self.on_current_item_changed)

        # Enable keyboard navigation
        self.object_tree.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.object_tree)

        # Status label
        self.status_label = QLabel("No objects loaded")
        layout.addWidget(self.status_label)

    def set_game_data_service(self, service: GameDataService):
        """Set the game data service and load objects."""
        self.game_data_service = service
        # Try to get settings from service if available
        if hasattr(service, "settings") and service.settings:
            self.app_settings = service.settings  # type: ignore[assignment]
        self.load_objects()

    def _update_type_combo(self, mapped_types: list[str]):
        """Update type combo box with available types.

        Args:
            mapped_types: List of CDDA object types that are mapped to slots
        """
        # Block signals while updating
        self.type_combo.blockSignals(True)
        try:
            current_text = self.type_combo.currentText()
            self.type_combo.clear()

            # Always add "All" option
            self.type_combo.addItem("All")

            # Add mapped types with nice labels
            type_labels = {
                "terrain": "terrain",
                "furniture": "furniture",
                "MONSTER": "monster",
                "ITEM": "item",
            }

            for obj_type in sorted(set(mapped_types)):
                label = type_labels.get(obj_type, obj_type)
                self.type_combo.addItem(label)

            # Restore previous selection if possible
            index = self.type_combo.findText(current_text)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            else:
                self.type_combo.setCurrentText("terrain")  # Default to terrain
        finally:
            self.type_combo.blockSignals(False)

    def refresh(self):
        """Refresh objects from current game data service."""
        if self.game_data_service:
            self.load_objects()

    def load_objects(self):
        """Load objects via shared non-GUI collector."""
        if not self.game_data_service:
            return
        try:
            # Get mapped types from settings or use defaults
            if self.app_settings:
                mapped_types = self.app_settings.type_slot_mapping.get_mapped_types()
            else:
                # Fallback to defaults if no settings available
                mapped_types = ["terrain", "furniture", "MONSTER", "ITEM"]

            if not mapped_types:
                # If user cleared all mappings, use defaults
                mapped_types = ["terrain", "furniture", "ITEM"]

            self.logger.debug(f"Loading objects for types: {mapped_types}")
            self.all_objects = self.game_data_service.collect_resolved_objects(
                mapped_types
            )
            self.logger.info(f"Loaded {len(self.all_objects)} objects.")

            # Update type combo with loaded types
            self._update_type_combo(mapped_types)

            self.filter_objects()
            self.object_tree.setFocus()
        except Exception as e:
            self.logger.error(f"Failed to load objects: {e}")
            self.status_label.setText(f"Error loading objects: {e}")

    def filter_objects(self):
        """Filter objects based on current filters."""
        if not self.all_objects:
            self.logger.debug("No objects to filter")
            return

        selected_type = self.type_combo.currentText()
        search_text = self.search_edit.text().lower()

        self.logger.debug(
            f"Filtering: type='{selected_type}', search='{search_text}'"
        )  # Filter by type
        if selected_type == "All":
            self.filtered_objects = self.all_objects[:]
        else:
            # Map UI type names to actual CDDA type names
            type_mapping = {
                "monster": "MONSTER",
                "terrain": "terrain",
                "furniture": "furniture",
                "item": "ITEM",
            }
            actual_type = type_mapping.get(selected_type.lower(), selected_type)

            self.filtered_objects = [
                obj for obj in self.all_objects if obj.get("type", "") == actual_type
            ]

        # Filter by search text (only if provided) - super fast with pre-resolved names
        if search_text:
            self.filtered_objects = [
                obj
                for obj in self.filtered_objects
                if (
                    search_text in obj.get("id", "").lower()
                    or search_text in obj.get("name", "").lower()
                )
            ]

        # Update list widget
        self.update_object_list()

    def update_object_list(self):
        """Update the object tree widget with pre-resolved objects (instant display)."""
        # Avoid emitting selection signals while rebuilding the list.
        # Otherwise QTreeWidget may emit currentItemChanged during repopulation.
        prev_blocked = self.object_tree.blockSignals(True)
        try:
            self.object_tree.clear()

            self.logger.debug(
                f"Updating tree with {len(self.filtered_objects)} filtered objects"
            )

            # Super fast display: all objects are pre-resolved with computed names
            for obj in self.filtered_objects[:200]:  # Limit display to first 200
                object_id = obj.get("id", "unknown")
                object_name = obj.get("name", "No name")  # Pre-computed name
                mod_id = obj.get("mod_id", "dda")  # Pre-computed mod ID

                # Create tree item with three columns: [Mod] [Object ID] [Object Name]
                item = QTreeWidgetItem([mod_id, object_id, object_name])

                # Store object ID in item data for selection events
                item.setData(0, Qt.ItemDataRole.UserRole, object_id)

                self.object_tree.addTopLevelItem(item)

            # Select the first row by default to keep keyboard navigation usable.
            if (
                self.object_tree.topLevelItemCount() > 0
                and not self.object_tree.currentItem()
            ):
                self.object_tree.setCurrentItem(self.object_tree.topLevelItem(0))
        finally:
            self.object_tree.blockSignals(prev_blocked)

        # Update status
        total_filtered = len(self.filtered_objects)
        displayed = min(total_filtered, 200)

        if total_filtered > 200:
            self.status_label.setText(
                f"Showing {displayed} of {total_filtered} objects (limited)"
            )
        else:
            self.status_label.setText(f"Showing {displayed} objects")

    def on_object_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle object selection by mouse click."""
        if not self._emit_selection_signals:
            return
        self._emit_object_selection(item)

    def on_object_activated(self, item: QTreeWidgetItem, column: int):
        """Handle object activation (Enter key or double-click)."""
        if not self._emit_selection_signals:
            return
        self._emit_object_selection(item)

    def on_current_item_changed(
        self, current: QTreeWidgetItem, previous: QTreeWidgetItem
    ):
        """Handle current item change (keyboard navigation)."""
        if not self._emit_selection_signals:
            return
        # Emit selection immediately when navigating with arrows
        if current:
            self._emit_object_selection(current)

    def _emit_object_selection(self, item: QTreeWidgetItem):
        """Helper method to emit object selection signal."""
        if not item:
            return

        object_id = item.data(0, Qt.ItemDataRole.UserRole)
        if object_id:
            self.logger.debug(f"Object selected: {object_id}")
            self.object_selected.emit(object_id)

    def clear_search(self):
        """Clear search text."""
        self.search_edit.clear()

    def get_selected_object_id(self) -> Optional[str]:
        """Get currently selected object ID."""
        current_item = self.object_tree.currentItem()
        if current_item:
            return current_item.data(0, Qt.ItemDataRole.UserRole)
        return None

    def select_object_by_id(self, object_id: str, *, set_filters: bool = True) -> bool:
        """Select an object in the tree by its ID.

        Args:
            object_id: CDDA object id.
            set_filters: If True, switch type to "All" and set search to object_id
                before selecting (helps ensure the item is visible).

        Returns:
            True if the item was found and selected, False otherwise.
        """
        if not object_id:
            return False

        if set_filters:
            # Avoid cascaded signal emissions while adjusting filters.
            prev_block_type = self.type_combo.blockSignals(True)
            prev_block_search = self.search_edit.blockSignals(True)
            try:
                self.type_combo.setCurrentText("All")
                self.search_edit.setText(object_id)
            finally:
                self.type_combo.blockSignals(prev_block_type)
                self.search_edit.blockSignals(prev_block_search)

            # Rebuild list with updated filters.
            self.filter_objects()

        for idx in range(self.object_tree.topLevelItemCount()):
            item = self.object_tree.topLevelItem(idx)
            if not item:
                continue
            if item.data(0, Qt.ItemDataRole.UserRole) == object_id:
                self.object_tree.setCurrentItem(item)
                try:
                    self.object_tree.scrollToItem(item)
                except Exception:
                    pass
                return True

        return False
