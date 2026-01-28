"""
Managers for game data indexing and retrieval.

Provides ObjectsManager class that handles storage, indexing by type/mod,
and efficient lookup operations for game data objects.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional

from .models import GameDataObject, GameDataCollection, TypedObjectsMap, ModObjectsMap


class ObjectsManager:
    """Manager for indexing and retrieving game data objects.

    Maintains two main indices:
    - objects_by_type: global index mapping type -> objects (across all mods)
    - objects_by_mod: mod-scoped index mapping mod_id -> type -> objects

    This dual indexing enables both fast global lookups and mod-specific queries.
    """

    def __init__(self):
        # Global index: type_name -> list of objects (from all mods)
        self.objects_by_type: TypedObjectsMap = defaultdict(list)

        # Mod-scoped index: mod_id -> (type_name -> list of objects)
        self.objects_by_mod: ModObjectsMap = defaultdict(lambda: defaultdict(list))

        # Fast lookup index: object_id, mod -> object (for O(1) access)
        self.objects_by_id: Dict[tuple[str, str], GameDataObject] = {}

        # List of available types and mods (in order of discovery)
        self.types: List[str] = []
        self.available_mods: List[str] = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("ObjectsManager initialized")

    def add_objects(self, grouped_objects: TypedObjectsMap, mod_id: str) -> None:
        """Add a batch of grouped objects from a specific mod.

        Args:
            grouped_objects: Dictionary mapping object types to lists of objects
            mod_id: Identifier for the mod providing these objects
        """
        # Track this mod if it's new
        if mod_id not in self.available_mods:
            self.available_mods.append(mod_id)

        # Add objects to all indices
        for obj_type, objects in grouped_objects.items():
            if objects:
                self.objects_by_type[obj_type].extend(objects)
                self.objects_by_mod[mod_id][obj_type].extend(objects)

                # Build ID index for fast lookup
                for obj in objects:
                    obj_id = obj.get("id")
                    obj_abstract = obj.get("abstract")

                    # Index by (mod_id, id) and (mod_id, abstract)
                    if isinstance(obj_id, str):
                        self.objects_by_id[(mod_id, obj_id)] = obj
                    elif isinstance(obj_id, list):
                        for id_val in obj_id:  # type: ignore
                            self.objects_by_id[(mod_id, id_val)] = obj

                    if isinstance(obj_abstract, str):
                        self.objects_by_id[(mod_id, obj_abstract)] = obj
                    elif isinstance(obj_abstract, list):
                        for abstract_val in obj_abstract:  # type: ignore
                            self.objects_by_id[(mod_id, abstract_val)] = obj

    def finalize_types(self) -> None:
        """Finalize the list of discovered types (sorted)."""
        self.types = sorted(self.objects_by_type.keys())

    def get_objects_by_type(self, object_type: str) -> GameDataCollection:
        """Return all objects of the specified type (across all mods)."""
        return self.objects_by_type.get(object_type, [])

    def get_types(self) -> List[str]:
        """Return a copy of the discovered object types list."""
        return self.types.copy()

    def get_available_mods(self) -> List[str]:
        """Return a copy of the list of available mods."""
        return self.available_mods.copy()

    def get_objects_by_type_from_mod(
        self, object_type: str, mod_id: str
    ) -> GameDataCollection:
        """Return objects of the specified type from a particular mod."""
        return self.objects_by_mod.get(mod_id, {}).get(object_type, [])

    def get_objects_by_type_from_mods(
        self, object_type: str, mod_ids: List[str]
    ) -> GameDataCollection:
        """Return objects of the specified type from specific mods only.

        This is much faster than filtering all objects, as it uses the mod index directly.

        Args:
            object_type: Type of objects to retrieve
            mod_ids: List of mod IDs to include

        Returns:
            Combined list of objects from specified mods
        """
        result: GameDataCollection = []
        for mod_id in mod_ids:
            if mod_id in self.objects_by_mod:
                mod_objects = self.objects_by_mod[mod_id].get(object_type, [])
                result.extend(mod_objects)
        return result

    def get_object_by_id(
        self, object_id: str, preferred_mods: Optional[List[str]] = None
    ) -> Optional[GameDataObject]:
        """Return the object by ID taking mod priority into account.

        Args:
            object_id: ID of the object to find
            preferred_mods: List of mods in priority order. If None, use load order.

        Returns:
            The highest-priority matching object or None if not found
        """
        if preferred_mods is None:
            preferred_mods = self.available_mods

        # Search in preferred order
        for mod_id in preferred_mods:
            if mod_id in self.available_mods:
                obj = self.objects_by_id.get((mod_id, object_id))
                if obj:
                    return obj

        # If not found in preferred mods, search remaining mods
        # for mod_id in self.available_mods:
        #    if mod_id not in preferred_mods:
        #        obj = self.get_object_by_id_from_mod(object_id, mod_id)
        #        if obj:
        #            return obj

        return None
