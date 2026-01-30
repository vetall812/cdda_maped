"""
Type to slot mapping settings.

Manages the mapping between CDDA object types and cell slots.
"""

import logging
from typing import Dict, Optional, List
from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


# Default mapping for common CDDA types
DEFAULT_TYPE_SLOT_MAPPING: Dict[str, str] = {
    "terrain": "TERRAIN",
    "furniture": "FURNITURE",
    "ITEM": "ITEMS",
    "MONSTER": "CREATURES",
}


class TypeSlotMappingSettings:
    """Settings for mapping CDDA object types to cell slots."""

    def __init__(self, settings: QSettings):
        """Initialize with QSettings instance.

        Args:
            settings: QSettings instance to use for storage
        """
        self.settings = settings
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_mapping(self) -> Dict[str, str]:
        """Get the complete type-to-slot mapping.

        Returns:
            Dictionary mapping object type to slot name (e.g., {"terrain": "TERRAIN"})
            If no custom mapping exists, returns default mapping
        """
        # Try to load from settings
        self.settings.beginGroup("TypeSlotMapping")
        try:
            # Get list of all types that have custom mappings
            all_keys = self.settings.allKeys()

            if not all_keys:
                # No custom mapping, return default
                return DEFAULT_TYPE_SLOT_MAPPING.copy()

            # Load custom mapping
            mapping: Dict[str, str] = {}
            for key in all_keys:
                slot = self.settings.value(key, "")
                if slot:  # Only include if slot is not empty
                    mapping[key] = str(slot)

            return mapping
        finally:
            self.settings.endGroup()

    def set_mapping(self, mapping: Dict[str, str]) -> None:
        """Set the complete type-to-slot mapping.

        Args:
            mapping: Dictionary mapping object type to slot name
        """
        self.settings.beginGroup("TypeSlotMapping")
        try:
            # Clear existing mapping
            self.settings.remove("")

            # Save new mapping
            for object_type, slot in mapping.items():
                if slot:  # Only save if slot is not empty
                    self.settings.setValue(object_type, slot)

            self.logger.debug(f"Saved type-slot mapping with {len(mapping)} entries")
        finally:
            self.settings.endGroup()

    def get_slot_for_type(self, object_type: str) -> Optional[str]:
        """Get the slot assigned to a specific object type.

        Args:
            object_type: CDDA object type (e.g., "terrain", "ITEM")

        Returns:
            Slot name (e.g., "TERRAIN") or None if not mapped
        """
        mapping = self.get_mapping()
        return mapping.get(object_type)

    def set_slot_for_type(self, object_type: str, slot: Optional[str]) -> None:
        """Set the slot for a specific object type.

        Args:
            object_type: CDDA object type
            slot: Slot name or None to unmap
        """
        self.settings.beginGroup("TypeSlotMapping")
        try:
            if slot:
                self.settings.setValue(object_type, slot)
                self.logger.debug(f"Mapped type '{object_type}' to slot '{slot}'")
            else:
                self.settings.remove(object_type)
                self.logger.debug(f"Unmapped type '{object_type}'")
        finally:
            self.settings.endGroup()

    def get_mapped_types(self) -> List[str]:
        """Get list of all object types that are mapped to any slot.

        Returns:
            List of object type names
        """
        mapping = self.get_mapping()
        return list(mapping.keys())

    def get_types_for_slot(self, slot: str) -> List[str]:
        """Get list of object types assigned to a specific slot.

        Args:
            slot: Slot name (e.g., "TERRAIN")

        Returns:
            List of object types mapped to this slot
        """
        mapping = self.get_mapping()
        return [obj_type for obj_type, obj_slot in mapping.items() if obj_slot == slot]

    def reset_to_defaults(self) -> None:
        """Reset mapping to default values."""
        self.set_mapping(DEFAULT_TYPE_SLOT_MAPPING.copy())
        self.logger.info("Reset type-slot mapping to defaults")

    def get_available_slots(self) -> List[str]:
        """Get list of available slot names.

        Returns:
            List of slot names (e.g., ["TERRAIN", "FURNITURE", "ITEMS", ...])
        """
        # Import here to avoid circular dependency
        from ..maps.models import CellSlot

        return [slot.name for slot in CellSlot]
