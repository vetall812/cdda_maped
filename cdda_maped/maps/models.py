"""
Data models for map representation during editing.

This module contains models for the internal representation of map cells,
sectors, and complete maps during editing and visualization. These models are
designed for runtime use and are NOT used for file I/O.

For serialization/deserialization, a separate format is used.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Generic, TypeVar, cast, TYPE_CHECKING
from abc import ABC, abstractmethod
from enum import IntEnum

if TYPE_CHECKING:
    from ..settings import AppSettings


class SlotCapacity(IntEnum):
    """Defines how many objects a slot can contain."""

    SINGLE = 1
    """Slot can contain only one object."""

    MULTIPLE = 2
    """Slot can contain multiple objects."""


class CellSlot(IntEnum):
    """Enumeration of cell slots in render order.

    Each slot represents a layer in the cell that will be rendered in order.
    Lower values render first (further back), higher values render last (on top).

    The render order reflects logical stacking:
    - Terrain is the base layer
    - Furniture sits on terrain
    - Creatures/items sit on furniture
    - Vehicles can interact with multiple layers
    """

    TERRAIN = 1
    """Base terrain/ground layer."""

    GRAFFITI = 2
    """Graffiti/markings on terrain."""

    FIELDS = 3
    """Field effects (fire, blood, smoke, etc.)."""

    FURNITURE = 4
    """Furniture and structures on terrain."""

    WALLFURNITURE = 5
    """Wall-mounted furniture and structures. TBD if separate from FURNITURE."""

    ITEMS = 6
    """Items lying on the ground."""

    CREATURES = 7
    """Monsters, NPCs, and the player."""

    VEHICLES = 8
    """Vehicles (cars, bikes, etc.)."""

    # Future slots can be added here as needed
    UNKNOWN = 9  # For unknown object types


# Slot capacity configuration
SLOT_CAPACITIES: dict[CellSlot, SlotCapacity] = {
    CellSlot.TERRAIN: SlotCapacity.SINGLE,
    CellSlot.GRAFFITI: SlotCapacity.SINGLE,
    CellSlot.FIELDS: SlotCapacity.MULTIPLE,
    CellSlot.FURNITURE: SlotCapacity.SINGLE,
    CellSlot.WALLFURNITURE: SlotCapacity.SINGLE,
    CellSlot.ITEMS: SlotCapacity.MULTIPLE,
    CellSlot.CREATURES: SlotCapacity.SINGLE,
    CellSlot.VEHICLES: SlotCapacity.SINGLE,
    CellSlot.UNKNOWN: SlotCapacity.MULTIPLE,
}


# Default game object type to slot mapping (used as fallback)
# Maps CDDA game data "type" field to appropriate cell slots
# This can be overridden by user settings via TypeSlotMappingSettings
OBJECT_TYPE_TO_SLOT: dict[str, CellSlot] = {
    # Terrain types
    "terrain": CellSlot.TERRAIN,
    # Furniture and structures
    "furniture": CellSlot.FURNITURE,
    "trap": CellSlot.FURNITURE,
    # Items
    "item": CellSlot.ITEMS,
    "ITEM": CellSlot.ITEMS,
    "vehicle_part": CellSlot.ITEMS,
    # Field effects (it seems that fields does not exist as is)
    "field": CellSlot.FIELDS,
    # Creatures
    "MONSTER": CellSlot.CREATURES,
    "npc": CellSlot.CREATURES,
    # Vehicles
    "vehicle": CellSlot.VEHICLES,
    # Map features and overlays (unsure if there are any)
    "graffiti": CellSlot.GRAFFITI,
}


def get_slot_for_object_type(object_type: str, settings: Optional["AppSettings"] = None) -> Optional[CellSlot]:
    """Get the cell slot for a given CDDA object type.

    First tries to get mapping from user settings, falls back to default mapping.

    Args:
        object_type: CDDA object type (e.g., "terrain", "ITEM")
        settings: Optional AppSettings instance. If provided, uses custom mapping.

    Returns:
        CellSlot or None if type is not mapped
    """
    # Try to get from settings if available
    if settings is not None:
        try:
            slot_name = settings.type_slot_mapping.get_slot_for_type(object_type)
            if slot_name:
                # Convert slot name string to CellSlot enum
                return CellSlot[slot_name]
        except (AttributeError, KeyError):
            pass  # Fall through to default mapping

    # Fall back to default mapping
    return OBJECT_TYPE_TO_SLOT.get(object_type)


@dataclass
class CellSlotContent:
    """Content of a single object type within a cell slot.

    Represents one or more copies of a single game object in a slot.
    For stackable items (items, creatures), quantity can be > 1.
    For non-stackable objects (terrain, furniture), quantity is always 1.

    Attributes:
        object_id: The game object identifier (e.g., 't_floor', 'i_rock')
        quantity: Number of this object (default 1). Non-stackable objects always have qty=1.
        extra_data: Optional metadata for the object (rotation, animation state, etc.)
    """

    object_id: str
    quantity: int = 1
    extra_data: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate object_id and quantity."""
        if not self.object_id:
            raise ValueError(f"Invalid object_id: {self.object_id}")

        if self.quantity < 1:
            raise ValueError(f"Invalid quantity: {self.quantity}, must be >= 1")

        if self.extra_data is None:
            self.extra_data = {}


@dataclass
class MapCell:
    """A single cell in the map grid.

    Represents one tile/cell on the map with multiple slots for different
    types of objects. Cells are the fundamental building block of maps
    during editing.

    **Important:** MapCell contains only the content (slots), NOT coordinates.
    Coordinates are stored in the container (Map) as dictionary keys:
    `dict[tuple[int, int, int], MapCell]` where tuple is (x, y, z).

    For SINGLE-capacity slots: stores a single CellSlotContent
    For MULTIPLE-capacity slots: stores a list of CellSlotContent

    Empty slots can be None or omitted from the dictionary.

    Example:
        >>> cell = MapCell()
        >>> cell.set_content(CellSlot.TERRAIN, "t_floor")  # 1 tile of floor
        >>> cell.set_content(CellSlot.FURNITURE, "f_table")  # 1 table
        >>> cell.add_content(CellSlot.ITEMS, "i_rock", quantity=10)  # 10 rocks
        >>> cell.add_content(CellSlot.ITEMS, "i_paper", quantity=100)  # 100 papers
        >>> terrain = cell.get_content(CellSlot.TERRAIN)
        >>> all_items = cell.get_all_content_in_slot(CellSlot.ITEMS)  # [10 rocks, 100 papers]
    """

    slots: dict[CellSlot, CellSlotContent | list[CellSlotContent]] = field(
        default_factory=lambda: {}  # type: ignore[return-value]
    )
    """Dictionary of slot -> content mappings.

    For SINGLE slots: CellSlotContent
    For MULTIPLE slots: list[CellSlotContent]
    """

    def _get_slot_capacity(self, slot: CellSlot) -> SlotCapacity:
        """Get the capacity type of a slot.

        Args:
            slot: The slot to check

        Returns:
            SlotCapacity value for the slot
        """
        return SLOT_CAPACITIES.get(slot, SlotCapacity.SINGLE)

    def set_content(
        self, slot: CellSlot, object_id: str, quantity: int = 1, extra_data: Optional[dict[str, Any]] = None
    ) -> None:
        """Set content for a specific slot (overwrites for SINGLE, adds for MULTIPLE).

        For SINGLE slots: overwrites existing content (only one object type allowed)
        For MULTIPLE slots: adds to the list (multiple different object types allowed)

        Args:
            slot: The slot to set content for
            object_id: The game object identifier
            quantity: Number of this object (default 1)
            extra_data: Optional metadata for the object

        Raises:
            ValueError: If object_id or quantity is invalid
        """
        content = CellSlotContent(object_id, quantity, extra_data)
        capacity = self._get_slot_capacity(slot)

        if capacity == SlotCapacity.SINGLE:
            # For single slots, just replace (only one object type allowed)
            self.slots[slot] = content
        else:
            # For multiple slots, add to list (multiple object types allowed)
            if slot not in self.slots:
                self.slots[slot] = []
            current = self.slots[slot]
            if isinstance(current, list):
                current.append(content)

    def add_content(
        self, slot: CellSlot, object_id: str, quantity: int = 1, extra_data: Optional[dict[str, Any]] = None
    ) -> None:
        """Add content to a slot.

        This is an alias for set_content that makes the intent clearer
        for MULTIPLE-capacity slots.

        Args:
            slot: The slot to add content to
            object_id: The game object identifier
            quantity: Number of this object (default 1)
            extra_data: Optional metadata for the object
        """
        self.set_content(slot, object_id, quantity, extra_data)

    def get_content(self, slot: CellSlot) -> Optional[CellSlotContent]:
        """Get content from a SINGLE-capacity slot.

        For MULTIPLE-capacity slots, use get_all_content_in_slot() instead.

        Args:
            slot: The slot to retrieve content from

        Returns:
            CellSlotContent if the slot has content, None otherwise
        """
        content = self.slots.get(slot)
        if content is None:
            return None
        if isinstance(content, CellSlotContent):
            return content
        # If it's a list (MULTIPLE slot), return the first item
        return content[0] if content else None

    def get_all_content_in_slot(
        self, slot: CellSlot
    ) -> list[CellSlotContent]:
        """Get all content from a slot (works for both SINGLE and MULTIPLE).

        For SINGLE slots: returns list with one element or empty list
        For MULTIPLE slots: returns all elements in the slot

        Args:
            slot: The slot to retrieve content from

        Returns:
            List of CellSlotContent objects
        """
        content = self.slots.get(slot)
        if content is None:
            return []
        if isinstance(content, list):
            return content
        # SINGLE slot - return as list
        return [content]

    def clear_slot(self, slot: CellSlot) -> None:
        """Clear content from a specific slot.

        Args:
            slot: The slot to clear
        """
        self.slots.pop(slot, None)

    def remove_content(self, slot: CellSlot, object_id: str, quantity: Optional[int] = None) -> bool:
        """Remove a specific object from a slot.

        For SINGLE slots: removes the content if object_id matches
        For MULTIPLE slots: removes or decreases quantity of the first occurrence

        Args:
            slot: The slot to remove content from
            object_id: The object ID to remove
            quantity: How many to remove. If None, removes all. If more than available, removes all.

        Returns:
            True if something was removed, False if not found
        """
        if slot not in self.slots:
            return False

        content = self.slots[slot]

        if isinstance(content, list):
            # MULTIPLE slot: find and modify/remove first occurrence
            for i, item in enumerate(content):
                if item.object_id == object_id:
                    if quantity is None:
                        # Remove entire entry
                        content.pop(i)
                    else:
                        # Decrease quantity
                        new_qty = item.quantity - quantity
                        if new_qty <= 0:
                            # Remove if quantity exhausted
                            content.pop(i)
                        else:
                            # Update quantity
                            item.quantity = new_qty

                    # Clear slot if list is now empty
                    if not content:
                        self.slots.pop(slot)
                    return True
            return False
        else:
            # SINGLE slot: remove if ID matches
            if content.object_id == object_id:
                self.slots.pop(slot)
                return True
            return False

    def has_content(self, slot: CellSlot) -> bool:
        """Check if a slot has content.

        Args:
            slot: The slot to check

        Returns:
            True if the slot contains content, False otherwise
        """
        return slot in self.slots

    def get_all_content(self) -> dict[CellSlot, CellSlotContent | list[CellSlotContent]]:
        """Get all content in this cell, in render order.

        Returns:
            Dictionary of slot -> content, sorted by slot enum value (render order)
        """
        return dict(sorted(self.slots.items()))

    def get_all_object_ids(self) -> list[str]:
        """Get all object IDs in this cell, in render order.

        Useful for quickly getting all objects without extra data.
        For slots with multiple objects, all are included in order.

        Returns:
            List of object IDs in render order
        """
        result: list[str] = []
        for slot in sorted(self.slots.keys()):
            content = self.slots[slot]
            if isinstance(content, list):
                result.extend([c.object_id for c in content])
            else:
                result.append(content.object_id)
        return result

    def is_empty(self) -> bool:
        """Check if the cell has any content.

        Returns:
            True if the cell has no content, False otherwise
        """
        return len(self.slots) == 0

    @staticmethod
    def get_slot_for_object_type(object_type: str) -> CellSlot:
        """Get the appropriate cell slot for a game object type.

        Args:
            object_type: The game object type (e.g., "terrain", "furniture", "MONSTER")

        Returns:
            CellSlot where this object type should be placed
            Defaults to UNKNOWN if type is unknown
        """
        # Try exact match first, then case-insensitive
        if object_type in OBJECT_TYPE_TO_SLOT:
            return OBJECT_TYPE_TO_SLOT[object_type]

        # Fallback to lowercase for case-insensitive lookup
        normalized_type = object_type.lower()
        return OBJECT_TYPE_TO_SLOT.get(normalized_type, CellSlot.UNKNOWN)


# =============================================================================
# Sector Models
# =============================================================================


class AbstractSector(ABC):
    """Abstract base for map sectors.

    Provides a unified API and shared implementations for sector operations.
    Subclasses must provide `width`/`height` and a factory for constructing
    rotated instances. The `cells`, `sector_id`, and `sector_name` attributes
    are expected to exist in subclasses.
    """

    # Expected subclass attributes (for type checking)
    cells: dict[tuple[int, int], "MapCell"]
    sector_id: str
    sector_name: str

    @property
    @abstractmethod
    def width(self) -> int:
        """Sector width in cells."""

    @property
    @abstractmethod
    def height(self) -> int:
        """Sector height in cells."""

    def get_cell(self, x: int, y: int) -> Optional["MapCell"]:
        """Return cell at (x, y) or None, with bounds validation."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"Sector coordinates out of bounds: ({x}, {y})")
        return self.cells.get((x, y))

    def set_cell(self, x: int, y: int, cell: "MapCell") -> None:
        """Set cell at (x, y) with bounds validation."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"Sector coordinates out of bounds: ({x}, {y})")
        self.cells[(x, y)] = cell

    def clear_cell(self, x: int, y: int) -> None:
        """Remove cell at (x, y) if present, with bounds validation."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"Sector coordinates out of bounds: ({x}, {y})")
        self.cells.pop((x, y), None)

    def rotateCW(self) -> "AbstractSector":
        """Return a new sector rotated 90° clockwise.

        Transformation: (x, y) → (y, width-1-x). Dimensions swap.
        """
        rotated_cells: dict[tuple[int, int], "MapCell"] = {}
        for (x, y), cell in self.cells.items():
            new_x = y
            new_y = self.width - 1 - x
            rotated_cells[(new_x, new_y)] = cell

        return self._make_rotated_sector(rotated_cells, new_width=self.height, new_height=self.width)

    def rotateCCW(self) -> "AbstractSector":
        """Return a new sector rotated 90° counter-clockwise.

        Transformation: (x, y) → (height-1-y, x). Dimensions swap.
        """
        rotated_cells: dict[tuple[int, int], "MapCell"] = {}
        for (x, y), cell in self.cells.items():
            new_x = self.height - 1 - y
            new_y = x
            rotated_cells[(new_x, new_y)] = cell

        return self._make_rotated_sector(rotated_cells, new_width=self.height, new_height=self.width)

    @abstractmethod
    def _make_rotated_sector(
        self,
        rotated_cells: dict[tuple[int, int], "MapCell"],
        new_width: int,
        new_height: int,
    ) -> "AbstractSector":
        """Factory for creating a rotated sector instance of the same concrete type."""

@dataclass
class MapSector(AbstractSector):
    """A 24x24 sector containing MapCells.

    A sector is the standard unit for organizing map data. It always
    contains a 24x24 grid of cells (indexed 0-23 for both x and y).
    Empty cells can be omitted from the dictionary (sparse representation).

    Attributes:
        cells: Dictionary mapping (x, y) to MapCell (x, y in range 0-23)
        sector_id: Unique identifier for this sector (e.g., "0_0_0" or UUID)
        sector_name: Human-readable name for the sector
    """

    cells: dict[tuple[int, int], MapCell] = field(default_factory=lambda: {})  # type: ignore[assignment]
    """Cells indexed by (x, y) where x, y ∈ [0, 23]"""

    sector_id: str = ""
    """Unique identifier for this sector"""

    sector_name: str = ""
    """Human-readable name for this sector"""

    # Class constant
    SIZE = 24

    @property
    def width(self) -> int:
        return self.SIZE

    @property
    def height(self) -> int:
        return self.SIZE

    def _make_rotated_sector(
        self,
        rotated_cells: dict[tuple[int, int], MapCell],
        new_width: int,
        new_height: int,
    ) -> "AbstractSector":
        # MapSector is always square SIZE×SIZE; new dims are ignored
        return MapSector(
            cells=rotated_cells,
            sector_id=self.sector_id,
            sector_name=self.sector_name,
        )


@dataclass
class DemoMapSector(AbstractSector):
    """A variable-sized sector for demo/testing purposes.

    Unlike MapSector which is always 24x24, DemoMapSector can be any size
    (1-24 for both dimensions). Useful for small test maps and demonstrations.

    Attributes:
        width: Width in cells (1-24)
        height: Height in cells (1-24)
        cells: Dictionary mapping (x, y) to MapCell
        sector_id: Unique identifier for this sector
        sector_name: Human-readable name for this sector
    """

    _width: int
    _height: int
    cells: dict[tuple[int, int], MapCell] = field(default_factory=lambda: {})  # type: ignore[assignment]
    sector_id: str = ""
    sector_name: str = ""

    def __post_init__(self) -> None:
        """Validate dimensions."""
        if not (1 <= self._width <= 24 and 1 <= self._height <= 24):
            raise ValueError(f"Invalid sector dimensions: {self._width}x{self._height}")

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def _make_rotated_sector(
        self,
        rotated_cells: dict[tuple[int, int], MapCell],
        new_width: int,
        new_height: int,
    ) -> "AbstractSector":
        return DemoMapSector(
            _width=new_width,
            _height=new_height,
            cells=rotated_cells,
            sector_id=self.sector_id,
            sector_name=self.sector_name,
        )


# =============================================================================
# Map Container Models
# =============================================================================

TSector = TypeVar("TSector", bound=AbstractSector)


@dataclass
class BaseMap(Generic[TSector]):
    """Base class for map containers.

    A map is a 3D grid of sectors, indexed by (x, y, z) coordinates.
    - x, y: Horizontal position in sector grid
    - z: Vertical level (0 = surface, negative = underground)

    Subclasses (Map, DemoMap) specialize TSector to MapSector or DemoMapSector.

    Attributes:
        sectors: Dictionary mapping (x, y, z) to sectors of type TSector
    """

    sectors: dict[tuple[int, int, int], TSector] = field(default_factory=lambda: {})  # type: ignore[assignment]
    """Sectors indexed by (x, y, z) coordinates"""

    @property
    @abstractmethod
    def sector_width(self) -> int:
        """Width of a single sector in cells."""

    @property
    @abstractmethod
    def sector_height(self) -> int:
        """Height of a single sector in cells."""

    @property
    def num_sectors_x(self) -> int:
        """Number of sectors along X axis.

        Returns:
            Count of unique X coordinates, or 0 if no sectors
        """
        if not self.sectors:
            return 0
        x_coords = {x for x, _, _ in self.sectors.keys()}
        return len(x_coords)

    @property
    def num_sectors_y(self) -> int:
        """Number of sectors along Y axis.

        Returns:
            Count of unique Y coordinates, or 0 if no sectors
        """
        if not self.sectors:
            return 0
        y_coords = {y for _, y, _ in self.sectors.keys()}
        return len(y_coords)

    @property
    def num_z_levels(self) -> int:
        """Number of Z levels (vertical layers).

        Returns:
            Count of unique Z coordinates, or 0 if no sectors
        """
        if not self.sectors:
            return 0
        z_coords = {z for _, _, z in self.sectors.keys()}
        return len(z_coords)

    @property
    def min_z_level(self) -> int:
        """Minimum Z level in the map.

        Returns:
            Minimum Z coordinate, or 0 if no sectors
        """
        if not self.sectors:
            return 0
        z_coords = {z for _, _, z in self.sectors.keys()}
        return min(z_coords) if z_coords else 0

    @property
    def max_z_level(self) -> int:
        """Maximum Z level in the map.

        Returns:
            Maximum Z coordinate, or 0 if no sectors
        """
        if not self.sectors:
            return 0
        z_coords = {z for _, _, z in self.sectors.keys()}
        return max(z_coords) if z_coords else 0

    # ---------------------------------------------------------------------
    # World coordinate helpers
    # ---------------------------------------------------------------------
    def get_cell_at(self, x: int, y: int, z: int = 0) -> Optional[MapCell]:
        """Get a `MapCell` by world tile coordinates.

        Translates world (x, y, z) into sector coordinates and intra-sector
        cell coordinates using `sector_width` and `sector_height`.

        Args:
            x: World X in tiles
            y: World Y in tiles
            z: Z level (default 0)

        Returns:
            MapCell if present, None otherwise
        """
        try:
            sw = self.sector_width
            sh = self.sector_height
            if sw <= 0 or sh <= 0:
                return None

            sx = x // sw
            sy = y // sh
            cx = x % sw
            cy = y % sh

            sector = self.sectors.get((sx, sy, z))
            if not sector:
                return None
            return sector.get_cell(cx, cy)
        except Exception:
            return None

    def set_cell_at(self, x: int, y: int, z: int, cell: MapCell) -> None:
        """Set a `MapCell` by world tile coordinates.

        Translates world (x, y, z) into sector coordinates and intra-sector
        cell coordinates using `sector_width` and `sector_height`.
        Creates sectors if they don't exist (for Map only; DemoMap uses single sector).

        Args:
            x: World X in tiles
            y: World Y in tiles
            z: Z level
            cell: MapCell to place

        Raises:
            ValueError: If coordinates are out of sector bounds
        """
        try:
            sw = self.sector_width
            sh = self.sector_height
            if sw <= 0 or sh <= 0:
                raise ValueError(f"Invalid sector dimensions: {sw}x{sh}")

            sx = x // sw
            sy = y // sh
            cx = x % sw
            cy = y % sh

            # Get or create sector
            sector = self.sectors.get((sx, sy, z))
            if not sector:
                # For DemoMap, sector should already exist; for Map, we'd need to create it
                # This is a simple implementation that works for both
                raise ValueError(f"Sector ({sx}, {sy}, {z}) does not exist")

            sector.set_cell(cx, cy, cell)
        except Exception as e:
            raise ValueError(f"Failed to set cell at ({x}, {y}, {z}): {e}")

    def get_neighbor_cells(self, x: int, y: int, z: int = 0) -> list[Optional[MapCell]]:
        """Get neighboring cells in order [N, W, S, E].

        Neighbors are computed by world coordinates:
        - N: (x, y-1)
        - W: (x-1, y)
        - S: (x, y+1)
        - E: (x+1, y)

        Args:
            x: World X in tiles
            y: World Y in tiles
            z: Z level (default 0)

        Returns:
            List of MapCell or None for missing/out-of-bounds
        """
        coords = [(x, y - 1), (x - 1, y), (x, y + 1), (x + 1, y)]
        return [self.get_cell_at(cx, cy, z) for cx, cy in coords]


    def get_sector(
        self, x: int, y: int, z: int
    ) -> Optional[TSector]:
        """Get a sector from the map.

        Args:
            x: X coordinate (horizontal)
            y: Y coordinate (horizontal)
            z: Z coordinate (vertical, 0=surface, <0=underground)

        Returns:
            Sector if found, None otherwise
        """
        return self.sectors.get((x, y, z))

    def set_sector(
        self, x: int, y: int, z: int, sector: TSector
    ) -> None:
        """Set a sector in the map.

        Args:
            x: X coordinate (horizontal)
            y: Y coordinate (horizontal)
            z: Z coordinate (vertical)
            sector: Sector to place
        """
        self.sectors[(x, y, z)] = sector

    def clear_sector(self, x: int, y: int, z: int) -> None:
        """Remove a sector from the map.

        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate
        """
        self.sectors.pop((x, y, z), None)

    def rotateCCW(self) -> "BaseMap[TSector]":
        """Rotate entire map 90 degrees counter-clockwise.

        Rotates all sectors individually and updates their positions:
        - Sector position (sx, sy) → (sy, max_x - sx)
        - Each sector's cells are rotated internally

        Returns:
            New map with rotated sectors at new positions
        """
        if not self.sectors:
            return BaseMap(sectors={})

        # Find bounds
        all_coords = list(self.sectors.keys())
        x_coords = [x for x, _, _ in all_coords]

        max_x = max(x_coords) if x_coords else 0

        rotated_sectors: dict[tuple[int, int, int], TSector] = {}
        for (sx, sy, sz), sector in self.sectors.items():
            # Rotate sector internally
            rotated_sector = cast(TSector, sector.rotateCW())

            # Update sector position: (sx, sy) → (sy, max_x - sx)
            new_sx = sy
            new_sy = max_x - sx

            rotated_sectors[(new_sx, new_sy, sz)] = rotated_sector

        return BaseMap(sectors=rotated_sectors)

    def rotateCW(self) -> "BaseMap[TSector]":
        """Rotate entire map 90 degrees clockwise.

        Rotates all sectors individually and updates their positions:
        - Sector position (sx, sy) → (max_y - sy, sx)
        - Each sector's cells are rotated internally

        Returns:
            New map with rotated sectors at new positions
        """
        if not self.sectors:
            return BaseMap(sectors={})

        # Find bounds
        all_coords = list(self.sectors.keys())
        y_coords = [y for _, y, _ in all_coords]

        max_y = max(y_coords) if y_coords else 0

        rotated_sectors: dict[tuple[int, int, int], TSector] = {}
        for (sx, sy, sz), sector in self.sectors.items():
            # Rotate sector internally
            rotated_sector = cast(TSector, sector.rotateCCW())

            # Update sector position: (sx, sy) → (max_y - sy, sx)
            new_sx = max_y - sy
            new_sy = sx

            rotated_sectors[(new_sx, new_sy, sz)] = rotated_sector

        return BaseMap(sectors=rotated_sectors)


@dataclass
class Map(BaseMap[MapSector]):
    """Complete game map with weather layer.

    Stores standard 24x24 MapSectors organized in 3D grid.
    Includes weather layer (global effects above all sectors).

    Attributes:
        sectors: Dictionary of MapSector objects
        weather: Weather objects by (x, y) coordinate. Applies to all Z levels.
                 Not bound to sectors, exists above everything.
    """

    weather: dict[tuple[int, int], list[str]] = field(default_factory=lambda: {})  # type: ignore[assignment]
    """Weather object IDs indexed by (x, y). List because multiple weather can coexist."""

    @property
    def sector_width(self) -> int:
        """Width of a MapSector (always 24)."""
        return MapSector.SIZE

    @property
    def sector_height(self) -> int:
        """Height of a MapSector (always 24)."""
        return MapSector.SIZE

    def rotateCW(self) -> "Map":  # type: ignore[override]
        """Rotate map 90 degrees clockwise.

        Rotates all sectors and weather layer.

        Returns:
            New Map with rotated sectors and weather
        """
        # Rotate sectors using base class logic
        base_rotated = super().rotateCW()

        # Rotate weather coordinates
        if not self.weather:
            rotated_weather: dict[tuple[int, int], list[str]] = {}
        else:
            all_weather_coords = list(self.weather.keys())
            x_coords = [x for x, _ in all_weather_coords]
            max_x = max(x_coords) if x_coords else 0

            rotated_weather = {}
            for (wx, wy), weather_list in self.weather.items():
                new_wx = wy
                new_wy = max_x - wx
                rotated_weather[(new_wx, new_wy)] = weather_list

        return Map(
            sectors=base_rotated.sectors,
            weather=rotated_weather,
        )

    def rotateCCW(self) -> "Map":  # type: ignore[override]
        """Rotate map 90 degrees counter-clockwise.

        Rotates all sectors and weather layer.

        Returns:
            New Map with rotated sectors and weather
        """
        # Rotate sectors using base class logic
        base_rotated = super().rotateCCW()

        # Rotate weather coordinates
        if not self.weather:
            rotated_weather: dict[tuple[int, int], list[str]] = {}
        else:
            all_weather_coords = list(self.weather.keys())
            y_coords = [y for _, y in all_weather_coords]
            max_y = max(y_coords) if y_coords else 0

            rotated_weather = {}
            for (wx, wy), weather_list in self.weather.items():
                new_wx = max_y - wy
                new_wy = wx
                rotated_weather[(new_wx, new_wy)] = weather_list

        return Map(
            sectors=base_rotated.sectors,
            weather=rotated_weather,
        )


@dataclass
class DemoMap(BaseMap[DemoMapSector]):
    """Demo/test map with single 1x1 sector grid across multiple Z levels.

    By design, DemoMap always has exactly one sector per Z level at position (0, 0).
    Useful for quick testing and demonstrations without managing full sector grids.

    The single sector can be any size (1-24 x 1-24), set at creation.

    Attributes:
        sectors: Dictionary with keys like (0, 0, 0), (0, 0, -1), etc.
                 All have x=0, y=0; z varies.
    """

    @property
    def sector_width(self) -> int:
        """Width of the DemoMapSector.

        Returns:
            Width from the first available sector, or 0 if no sectors
        """
        if not self.sectors:
            return 0
        first_sector = next(iter(self.sectors.values()))
        return first_sector.width

    @property
    def sector_height(self) -> int:
        """Height of the DemoMapSector.

        Returns:
            Height from the first available sector, or 0 if no sectors
        """
        if not self.sectors:
            return 0
        first_sector = next(iter(self.sectors.values()))
        return first_sector.height
    def rotateCW(self) -> "DemoMap":
        """Rotate entire demo map 90 degrees clockwise.

        Rotates all sectors individually and updates their positions.
        Each sector's cells are rotated internally.

        Returns:
            New DemoMap with rotated sectors at new positions
        """
        base_rotated = super().rotateCW()
        return DemoMap(sectors=base_rotated.sectors)

    def rotateCCW(self) -> "DemoMap":
        """Rotate entire demo map 90 degrees counter-clockwise.

        Rotates all sectors individually and updates their positions.
        Each sector's cells are rotated internally.

        Returns:
            New DemoMap with rotated sectors at new positions
        """
        base_rotated = super().rotateCCW()
        return DemoMap(sectors=base_rotated.sectors)
