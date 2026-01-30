"""Metadata and schemas for demo maps.

Defines the structure of demo map JSON files and metadata objects.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass
class DemoMapMetadata:
    """Metadata about a demo map.

    Contains display information and file location for a demo map.
    Used by the registry to list available maps without loading full data.

    Attributes:
        id: Unique identifier (must match JSON 'id' field)
        name: Display name for UI
        description: Brief description of the map
        version: Format version string
        sector_width: Width of sectors in this map
        sector_height: Height of sectors in this map
        file_path: Path to the JSON file
        is_builtin: True if from resources/, False if from user config
    """

    id: str
    name: str
    description: str
    version: str
    sector_width: int
    sector_height: int
    file_path: Path
    is_builtin: bool = True

    def __repr__(self) -> str:
        source = "builtin" if self.is_builtin else "user"
        return f"DemoMapMetadata(id={self.id!r}, name={self.name!r}, {source})"


class DemoMapSchema:
    """Validation schemas for demo map JSON structure.

    Provides validation methods to ensure JSON files conform to expected format.
    """

    REQUIRED_ROOT_FIELDS = {
        "id",
        "name",
        "description",
        "version",
        "sector_width",
        "sector_height",
        "sectors",
    }
    REQUIRED_SECTOR_FIELDS = {"sector_id", "x", "y", "z", "layers"}
    VALID_LAYER_NAMES = {
        "terrain",
        "furniture",
        "items",
        "creatures",
        "graffiti",
        "fields",
    }

    @staticmethod
    def validate_root(data: dict[str, Any]) -> list[str]:
        """Validate root-level fields.

        Args:
            data: Parsed JSON data

        Returns:
            List of error messages (empty if valid)
        """
        errors: list[str] = []

        # Check required fields
        missing = DemoMapSchema.REQUIRED_ROOT_FIELDS - data.keys()
        if missing:
            errors.append(f"Missing required fields: {missing}")

        # Validate types
        if not isinstance(data.get("id"), str):
            errors.append("'id' must be a string")
        if not isinstance(data.get("name"), str):
            errors.append("'name' must be a string")
        if not isinstance(data.get("sectors"), list):
            errors.append("'sectors' must be an array")

        # Validate dimensions
        width = data.get("sector_width")
        height = data.get("sector_height")
        if not isinstance(width, int) or not (1 <= width <= 24):
            errors.append(f"'sector_width' must be 1-24, got {width}")
        if not isinstance(height, int) or not (1 <= height <= 24):
            errors.append(f"'sector_height' must be 1-24, got {height}")

        return errors

    @staticmethod
    def validate_sector(
        sector_data: dict[str, Any], expected_width: int, expected_height: int
    ) -> list[str]:
        """Validate a sector object.

        Args:
            sector_data: Sector dictionary from JSON
            expected_width: Expected sector width from root
            expected_height: Expected sector height from root

        Returns:
            List of error messages (empty if valid)
        """
        errors: list[str] = []

        # Check required fields
        missing = DemoMapSchema.REQUIRED_SECTOR_FIELDS - sector_data.keys()
        if missing:
            errors.append(f"Sector missing required fields: {missing}")
            return errors  # Can't continue validation

        # Validate coordinates
        if not isinstance(sector_data.get("x"), int):
            errors.append(f"Sector 'x' must be integer, got {sector_data.get('x')}")
        if not isinstance(sector_data.get("y"), int):
            errors.append(f"Sector 'y' must be integer, got {sector_data.get('y')}")
        if not isinstance(sector_data.get("z"), int):
            errors.append(f"Sector 'z' must be integer, got {sector_data.get('z')}")

        # Validate sector_id is non-empty string (uniqueness checked separately)
        sector_id = sector_data.get("sector_id", "")
        if not isinstance(sector_id, str) or not sector_id:
            errors.append(
                f"Sector 'sector_id' must be a non-empty string, got {sector_id!r}"
            )

        # Validate layers
        layers = sector_data.get("layers")
        if not isinstance(layers, dict):
            errors.append("'layers' must be an object")
            return errors

        layers_dict = cast(dict[str, Any], layers)
        for layer_name, grid in layers_dict.items():
            if layer_name not in DemoMapSchema.VALID_LAYER_NAMES:
                errors.append(
                    f"Unknown layer '{layer_name}', expected one of {DemoMapSchema.VALID_LAYER_NAMES}"
                )
                continue

            # Validate grid dimensions
            if not isinstance(grid, list):
                errors.append(f"Layer '{layer_name}' must be an array")
                continue

            grid_list = cast(list[Any], grid)
            grid_len = len(grid_list)
            if grid_len != expected_height:
                errors.append(
                    f"Layer '{layer_name}' height is {grid_len}, expected {expected_height}"
                )

            for row_idx, row in enumerate(grid_list):
                if not isinstance(row, list):
                    errors.append(f"Layer '{layer_name}' row {row_idx} is not an array")
                    continue
                row_list = cast(list[Any], row)
                row_len = len(row_list)
                if row_len != expected_width:
                    errors.append(
                        f"Layer '{layer_name}' row {row_idx} width is {row_len}, expected {expected_width}"
                    )

        return errors

    @staticmethod
    def validate_demo_map(data: dict[str, Any]) -> list[str]:
        """Validate complete demo map JSON.

        Args:
            data: Parsed JSON data

        Returns:
            List of all validation errors (empty if valid)
        """
        errors = DemoMapSchema.validate_root(data)
        if errors:
            return errors  # Don't continue if root is invalid

        width = data["sector_width"]
        height = data["sector_height"]

        # Track sector_ids to check for uniqueness
        seen_sector_ids: set[str] = set()

        for idx, sector in enumerate(data["sectors"]):
            sector_errors = DemoMapSchema.validate_sector(sector, width, height)
            if sector_errors:
                errors.extend([f"Sector {idx}: {err}" for err in sector_errors])

            # Check sector_id uniqueness
            sector_id = sector.get("sector_id", "")
            if sector_id:
                if sector_id in seen_sector_ids:
                    errors.append(f"Sector {idx}: duplicate 'sector_id' '{sector_id}'")
                else:
                    seen_sector_ids.add(sector_id)

        return errors
