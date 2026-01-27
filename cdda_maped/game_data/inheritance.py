"""
Inheritance resolution for CDDA game data.

Handles resolving 'copy-from' inheritance chains, merging parent and child
object definitions according to CDDA's inheritance rules. Single resolver
supports mod priority during lookups.
"""

from typing import Optional, List, Callable, Any, cast

from .models import (
    GameDataObject,
    INHERITANCE_KEY,
    EXTEND_KEY,
    DELETE_KEY,
    METADATA_MOD_ID,
    METADATA_SOURCE_FILE,
)


class InheritanceResolver:
    """Inheritance resolver that respects mod priority when looking up objects.

    Supports specifying a preferred mod order, which is useful when multiple
    mods define objects with the same ID.
    """

    def __init__(
        self,
        priority_lookup: Callable[[str, Optional[List[str]]], Optional[GameDataObject]],
    ):
        """Initialize the resolver with a priority-aware lookup function.

        Args:
            priority_lookup: Function that takes (object_id, preferred_mods)
                             and returns the object respecting mod priority
        """
        self._priority_lookup = priority_lookup

    def resolve_object(
        self, object_id: str, preferred_mods: Optional[List[str]] = None
    ) -> Optional[GameDataObject]:
        """Resolve an object with inheritance and mod priority.

        Args:
            object_id: ID of the object to resolve
            preferred_mods: List of mods in priority order

        Returns:
            The resolved object with inherited fields merged, or None if not found
        """
        visited: set[str] = set()
        result = self._merge_recursive_priority(object_id, preferred_mods, visited)
        return result if result else None

    def _merge_recursive_priority(
        self, object_id: str, preferred_mods: Optional[List[str]], visited: set[str]
    ) -> GameDataObject:
        """Recursively merge object with parent lookup.

        Args:
            object_id: ID of the object to merge
            preferred_mods: List of mods in priority order
            visited: Set of already visited object IDs to prevent cycles

        Returns:
            Merged object dictionary (empty dict if not found)
        """
        # Check for cycles
        if object_id in visited:
            return {}  # Return empty dict to break the cycle

        # Add to visited set
        visited.add(object_id)

        # Lookup object with priority
        obj = self._priority_lookup(object_id, preferred_mods)
        if not obj:
            visited.remove(object_id)  # Remove from visited on failure
            return {}

        # Check for parent
        parent_id = obj.get(INHERITANCE_KEY)
        if parent_id:
            parent = self._merge_recursive_priority(parent_id, preferred_mods, visited)
        else:
            parent = {}

        # Remove from visited (backtrack)
        visited.remove(object_id)

        # Merge with extend/delete support
        merged = self._merge_with_extend_delete(parent, obj)

        return merged

    def _merge_with_extend_delete(
        self, parent: GameDataObject, child: GameDataObject
    ) -> GameDataObject:
        """Merge parent and child objects with extend/delete directive support.

        Args:
            parent: Parent object dictionary
            child: Child object dictionary

        Returns:
            Merged object with extended/deleted fields applied
        """
        merged = parent.copy()

        # Process delete directive first (removes items from inherited lists/dicts)
        delete_data = child.get(DELETE_KEY, {})
        for delete_key, delete_value in delete_data.items():
            if delete_key in merged:
                merged[delete_key] = self._apply_delete(
                    merged[delete_key], delete_value
                )

        # Process extend directive (adds items to inherited lists/dicts)
        extend_data = child.get(EXTEND_KEY, {})
        for extend_key, extend_value in extend_data.items():
            if extend_key in merged:
                merged[extend_key] = self._apply_extend(
                    merged[extend_key], extend_value
                )
            else:
                # Field doesn't exist in parent, just set it
                merged[extend_key] = extend_value

        # Apply regular overwrites from child (excluding special keys)
        for key, value in child.items():
            if key not in (
                INHERITANCE_KEY,
                EXTEND_KEY,
                DELETE_KEY,
                METADATA_MOD_ID,
                METADATA_SOURCE_FILE,
            ):
                merged[key] = value

        # Preserve source mod/file metadata from the most specific object
        merged[METADATA_MOD_ID] = child.get(METADATA_MOD_ID)
        merged[METADATA_SOURCE_FILE] = child.get(METADATA_SOURCE_FILE)

        return merged

    def _apply_extend(self, parent_value: Any, extend_value: Any) -> Any:
        """Apply extend operation to a field value.

        Args:
            parent_value: Value from parent object
            extend_value: Value to extend with

        Returns:
            Extended value
        """
        # For lists, concatenate
        if isinstance(parent_value, list) and isinstance(extend_value, list):
            return cast(list[Any], parent_value) + cast(list[Any], extend_value)
        # For dicts, merge (extend_value overrides parent_value for same keys)
        elif isinstance(parent_value, dict) and isinstance(extend_value, dict):
            result = cast(dict[str, Any], parent_value).copy()
            result.update(cast(dict[str, Any], extend_value))
            return result
        else:
            # For other types, replace
            return extend_value

    def _apply_delete(self, parent_value: Any, delete_value: Any) -> Any:
        """Apply delete operation to a field value.

        Args:
            parent_value: Value from parent object
            delete_value: Value containing items to delete

        Returns:
            Value with items deleted
        """
        # For lists, remove items that match delete_value elements
        if isinstance(parent_value, list) and isinstance(delete_value, list):
            result: list[Any] = cast(list[Any], parent_value).copy()
            for item_to_delete in cast(list[Any], delete_value):
                # For complex objects (dicts), match by content
                if isinstance(item_to_delete, dict):
                    result = [
                        item
                        for item in result
                        if not self._dict_matches(item, cast(dict[str, Any], item_to_delete))
                    ]
                else:
                    # For simple values, direct removal
                    while item_to_delete in result:
                        result.remove(item_to_delete)
            return result
        # For dicts, remove keys specified in delete_value
        elif isinstance(parent_value, dict) and isinstance(delete_value, dict):
            result_dict: dict[str, Any] = cast(dict[str, Any], parent_value).copy()
            for key in cast(dict[str, Any], delete_value).keys():
                result_dict.pop(key, None)
            return result_dict
        else:
            # For other types, return parent unchanged
            return parent_value # type: ignore

    def _dict_matches(self, item: Any, pattern: dict[str, Any]) -> bool:
        """Check if a dict item matches a pattern (for delete operations).

        Args:
            item: Dict to check
            pattern: Pattern dict with fields to match

        Returns:
            True if all pattern fields match item fields
        """
        if not isinstance(item, dict):
            return False
        for key, value in pattern.items():
            if key not in item or item[key] != value:
                return False
        return True
