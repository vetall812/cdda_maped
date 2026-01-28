"""Map models and utilities for CDDA-maped editor."""

from .models import (
    CellSlot,
    CellSlotContent,
    MapCell,
    SlotCapacity,
    SLOT_CAPACITIES,
    OBJECT_TYPE_TO_SLOT,
    MapSector,
    DemoMapSector,
    BaseMap,
    Map,
    DemoMap,
)
from .map_manager import MapManager
from .demo_map_metadata import DemoMapMetadata, DemoMapSchema
from .demo_map_loader import DemoMapLoader
from .demo_map_registry import DemoMapRegistry

__all__ = [
    "CellSlot",
    "CellSlotContent",
    "MapCell",
    "SlotCapacity",
    "SLOT_CAPACITIES",
    "OBJECT_TYPE_TO_SLOT",
    "MapSector",
    "DemoMapSector",
    "BaseMap",
    "Map",
    "DemoMap",
    "MapManager",
    "DemoMapMetadata",
    "DemoMapSchema",
    "DemoMapLoader",
    "DemoMapRegistry",
]
