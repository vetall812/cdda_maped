"""
File loaders for CDDA game data.

Handles reading and parsing JSON files with parallel processing using
ThreadPoolExecutor and orjson for performance.
"""

import logging
from pathlib import Path
from collections import defaultdict
from typing import List

import orjson

from .models import (
    GameDataObject,
    TypedObjectsMap,
    METADATA_MOD_ID,
    METADATA_SOURCE_FILE,
)


class GameDataFileLoader:
    """Loads and parses game data JSON files with parallel processing."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("GameDataFileLoader initialized")

    @staticmethod
    def read_and_group_json_file(
        json_file: Path, mod_id: str = "dda"
    ) -> TypedObjectsMap:
        """Read a JSON file and group objects by their 'type'.

        Returns a dict mapping type_name -> list of objects. If an object has no
        'type' field it will be placed under the 'unknown' key. Each object
        is annotated with `_mod_id` and `_source_file` to track its origin.

        Args:
            json_file: Path to the JSON file to read
            mod_id: Identifier for the mod/source providing this data

        Returns:
            Dictionary mapping object types to lists of objects
        """
        grouped: TypedObjectsMap = defaultdict(list)

        try:
            with json_file.open("rb") as f:  # orjson works with bytes
                data = orjson.loads(f.read())

            objects: List[GameDataObject] = data if isinstance(data, list) else [data]  # type: ignore

            for obj in objects:
                # Determine object type (fall back to 'unknown')
                obj_type = obj.get("type") if isinstance(obj, dict) else None  # type: ignore
                if not obj_type:
                    obj_type = "unknown"

                # Annotate object with mod/source metadata and copy to avoid mutating
                # shared structures returned by the parser
                obj = obj.copy()  # type: ignore
                obj[METADATA_MOD_ID] = mod_id
                obj[METADATA_SOURCE_FILE] = str(json_file)

                grouped[obj_type].append(obj)

        except Exception as e:
            # Log parse/read errors but do not stop the whole loading process
            logger = logging.getLogger(f"{__name__}.GameDataFileLoader")
            logger.error(f"Error reading JSON file {json_file}: {e}")

        return grouped
