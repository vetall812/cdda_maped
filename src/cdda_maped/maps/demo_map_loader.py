"""Loading demo maps from JSON files.

Handles deserialization of demo map JSON files into DemoMap model instances.
"""

import logging
from pathlib import Path
from typing import Any

try:
    import orjson
except ImportError:
    import json as orjson  # type: ignore

from .models import DemoMap, DemoMapSector, MapCell, CellSlot
from .demo_map_metadata import DemoMapMetadata, DemoMapSchema


class DemoMapLoader:
    """Loads demo maps from JSON files.

    Handles deserialization, validation, and conversion to DemoMap instances.
    """

    def __init__(self):
        """Initialize the loader."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def load_from_json(self, path: Path) -> DemoMap:
        """Load a demo map from JSON file.

        Args:
            path: Path to JSON file

        Returns:
            Loaded DemoMap instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or doesn't match schema
        """
        if not path.exists():
            raise FileNotFoundError(f"Demo map file not found: {path}")

        self.logger.info(f"Loading demo map from: {path}")

        # Parse JSON
        try:
            if hasattr(orjson, "loads"):
                data = orjson.loads(path.read_bytes())
            else:
                data = orjson.loads(path.read_text(encoding="utf-8"))  # type: ignore
        except Exception as e:
            raise ValueError(f"Failed to parse JSON from {path}: {e}")

        # Validate schema
        errors = DemoMapSchema.validate_demo_map(data)
        if errors:
            error_msg = "\n  - ".join(errors)
            raise ValueError(f"Invalid demo map JSON in {path}:\n  - {error_msg}")

        # Convert to DemoMap
        demo_map = self._build_demo_map(data)
        self.logger.info(
            f"Loaded demo map '{data['id']}' with {len(demo_map.sectors)} sector(s)"
        )
        return demo_map

    def load_metadata(self, path: Path) -> DemoMapMetadata:
        """Load only metadata from JSON file without building full map.

        Args:
            path: Path to JSON file

        Returns:
            DemoMapMetadata instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"Demo map file not found: {path}")

        try:
            if hasattr(orjson, "loads"):
                data = orjson.loads(path.read_bytes())
            else:
                data = orjson.loads(path.read_text(encoding="utf-8"))  # type: ignore
        except Exception as e:
            raise ValueError(f"Failed to parse JSON from {path}: {e}")

        # Validate only root fields
        errors = DemoMapSchema.validate_root(data)
        if errors:
            error_msg = "\n  - ".join(errors)
            raise ValueError(f"Invalid demo map metadata in {path}:\n  - {error_msg}")

        return DemoMapMetadata(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            version=data["version"],
            sector_width=data["sector_width"],
            sector_height=data["sector_height"],
            file_path=path,
            is_builtin=False,  # Caller should set this
        )

    def _build_demo_map(self, data: dict[str, Any]) -> DemoMap:
        """Convert validated JSON data to DemoMap instance.

        Args:
            data: Validated JSON data

        Returns:
            DemoMap with all sectors populated
        """
        demo_map = DemoMap()

        sector_width = data["sector_width"]
        sector_height = data["sector_height"]

        for sector_data in data["sectors"]:
            sector = self._build_sector(sector_data, sector_width, sector_height)
            x = sector_data["x"]
            y = sector_data["y"]
            z = sector_data["z"]
            demo_map.set_sector(x, y, z, sector)

        return demo_map

    def _build_sector(
        self, sector_data: dict[str, Any], width: int, height: int
    ) -> DemoMapSector:
        """Convert sector JSON data to DemoMapSector instance.

        Args:
            sector_data: Sector dictionary from JSON
            width: Sector width (from root)
            height: Sector height (from root)

        Returns:
            DemoMapSector with cells populated
        """
        sector = DemoMapSector(
            _width=width,
            _height=height,
            sector_id=sector_data["sector_id"],
        )

        layers = sector_data["layers"]

        # Process each layer
        for layer_name, grid in layers.items():
            slot = self._layer_name_to_slot(layer_name)
            self._fill_sector_layer(sector, slot, grid)

        return sector

    def _layer_name_to_slot(self, layer_name: str) -> CellSlot:
        """Convert JSON layer name to CellSlot enum.

        Args:
            layer_name: Layer name from JSON (e.g., "terrain", "furniture")

        Returns:
            Corresponding CellSlot enum value
        """
        mapping = {
            "terrain": CellSlot.TERRAIN,
            "furniture": CellSlot.FURNITURE,
            "items": CellSlot.ITEMS,
            "creatures": CellSlot.CREATURES,
            "graffiti": CellSlot.GRAFFITI,
            "fields": CellSlot.FIELDS,
        }
        return mapping.get(layer_name, CellSlot.UNKNOWN)

    def _fill_sector_layer(
        self, sector: DemoMapSector, slot: CellSlot, grid: list[list[str | None]]
    ) -> None:
        """Fill sector cells with objects from a layer grid.

        Args:
            sector: Target sector to populate
            slot: Which slot to fill in cells
            grid: 2D array of object IDs (height x width)
        """
        for y, row in enumerate(grid):
            for x, object_id in enumerate(row):
                # Skip empty cells
                if not object_id or object_id == "":
                    continue

                # Get or create cell at this position
                cell = sector.get_cell(x, y)
                if cell is None:
                    cell = MapCell()
                    sector.set_cell(x, y, cell)

                # Add object to appropriate slot
                cell.set_content(slot, object_id, quantity=1)
