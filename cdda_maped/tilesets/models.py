"""
Data models for working with CDDA tilesets.

Contains all dataclasses and type definitions used by the tileset system.
Each model is intentionally lightweight: no file-system or service logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, TypedDict, Sequence, cast
from PIL import Image


# =============================================================================
# Tile Models
# =============================================================================

@dataclass
class WeightedSprite:
    """Sprite with weight for weighted random selection.

    A tile definition may specify a list of weighted sprite alternatives.
    If several are present the caller can roll a random choice using the
    weight attribute. This class simply stores the configuration.
    """
    weight: int
    sprite: int | list[int]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WeightedSprite":
        """Create WeightedSprite from JSON dict.

        Args:
            data: Dict with 'weight' and 'sprite' keys

        Returns:
            WeightedSprite instance
        """
        return cls(
            weight=int(data.get("weight", 1)),
            sprite=data["sprite"]  # Can be int or list[int]
        )

    @classmethod
    def from_json_value(
        cls, value: Any
    ) -> "int | list[int] | list[WeightedSprite] | None":
        """Convert JSON value to appropriate type.

        Handles conversion of fg/bg fields which can be:
        - int: single sprite index
        - list[int]: rotation frames
        - list[dict]: weighted sprites

        Args:
            value: Raw JSON value

        Returns:
            Typed value (int, list[int], list[WeightedSprite], or None)
        """
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, list):
            if not value:
                return []  # Empty list

            value_list: list[Any] = list(cast(Sequence[Any], value))
            first = value_list[0]
            if isinstance(first, int):
                # list[int] - rotation frames
                return [int(v) for v in value_list]
            if isinstance(first, dict) and "weight" in first:
                # list[dict] -> list[WeightedSprite]
                sprites: list[WeightedSprite] = []
                for item in value_list:
                    if isinstance(item, dict):
                        sprites.append(cls.from_dict(cast(dict[str, Any], item)))
                return sprites
        # Fallback for unexpected types
        return None


@dataclass
class TileSource:
    """Raw tile definition originating from JSON.

    Fields intentionally mirror the upstream Cataclysm-DDA tileset schema.
    """
    id: str = "unknown"
    fg: int | list[int] | list[WeightedSprite] | None = 0
    bg: int | list[int] | list[WeightedSprite] | None = None
    # Optional object height for 3D stacking within a single cell
    height_3d: int = 0
    animated: bool | None = False
    rotates: bool | None = False
    multitile: bool | None = False
    additional_tiles: list["TileSource"] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TileSource":
        """Create TileSource from JSON dict with proper type conversion.

        Args:
            data: Raw JSON dict

        Returns:
            TileSource with properly typed fields
        """
        # Convert fg/bg fields to proper types
        fg = WeightedSprite.from_json_value(data.get("fg", 0))
        bg = WeightedSprite.from_json_value(data.get("bg"))

        # Handle additional_tiles recursively
        additional_tiles = None
        if "additional_tiles" in data and data["additional_tiles"]:
            raw_tiles: list[Any] | None = data.get("additional_tiles")
            additional_tiles = [
                cls.from_dict(cast(dict[str, Any], tile))
                for tile in (raw_tiles or [])
                if isinstance(tile, dict)
            ]

        return cls(
            id=str(data.get("id", "unknown")),
            fg=fg,
            bg=bg,
            height_3d=int(data.get("height_3d", 0) or 0),
            animated=data.get("animated"),
            rotates=data.get("rotates"),
            multitile=data.get("multitile"),
            additional_tiles=additional_tiles
        )


@dataclass
class Tile:
    """Resolved tile bound to a concrete sprite sheet.

    sheet_id links the tile to a specific `Sheet`. mod_id identifies the
    source mod ("dda" for base game). When several mods override the same
    tile id, the priority resolution happens in the managers layer.
    """
    tileid: str
    source: TileSource
    sheet_id: str = ""  # Уникальный ID листа
    mod_id: str = "dda"  # ID мода, которому принадлежит этот тайл


@dataclass
class SheetInfo:
    """Lightweight information about a sprite sheet.

    Contains metadata needed for rendering without holding the full Sheet object.
    Used as TileObject.style and returned from service methods.
    """
    name: str = "unknown"
    file: str = ""
    sprite_width: int = 32
    sprite_height: int = 32
    mod_id: str = "dda"
    sprite_count: int = 0
    sprite_offset_x: int = 0
    sprite_offset_y: int = 0
    sprite_offset_x_retracted: int = 0
    sprite_offset_y_retracted: int = 0
    pixelscale: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SheetInfo":
        """Create SheetInfo from dict.

        Args:
            data: Dict with sheet information

        Returns:
            SheetInfo instance
        """
        return cls(
            name=str(data.get("name", "unknown")),
            file=str(data.get("file", "")),
            sprite_width=int(data.get("sprite_width", 32)),
            sprite_height=int(data.get("sprite_height", 32)),
            mod_id=str(data.get("mod_id", "dda")),
            sprite_count=int(data.get("sprite_count", 0)),
            sprite_offset_x=int(data.get("sprite_offset_x", 0)),
            sprite_offset_y=int(data.get("sprite_offset_y", 0)),
            sprite_offset_x_retracted=int(data.get("sprite_offset_x_retracted", 0)),
            sprite_offset_y_retracted=int(data.get("sprite_offset_y_retracted", 0)),
            pixelscale=int(data.get("pixelscale", 1))
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for backward compatibility.

        Returns:
            Dict representation
        """
        return {
            "name": self.name,
            "file": self.file,
            "sprite_width": self.sprite_width,
            "sprite_height": self.sprite_height,
            "mod_id": self.mod_id,
            "sprite_count": self.sprite_count,
            "sprite_offset_x": self.sprite_offset_x,
            "sprite_offset_y": self.sprite_offset_y,
            "sprite_offset_x_retracted": self.sprite_offset_x_retracted,
            "sprite_offset_y_retracted": self.sprite_offset_y_retracted,
            "pixelscale": self.pixelscale
        }


@dataclass
class TileObject:
    """Fully materialized tile containing rendered sprite images.

    Produced by high-level service methods once sprite indices have been
    collected and converted to actual `Image.Image` objects.
    """
    source: TileSource
    style: SheetInfo
    sprites: dict[int, Image.Image]


# =============================================================================
# Sheet Models
# =============================================================================

class SpriteEntry(TypedDict):
    """Entry describing a single fallback (ASCII) sprite.

    color: Terminal-style color name.
    id:    ASCII character identifier.
    sprite: PIL Image instance.
    """
    color: str
    id: str
    sprite: Image.Image


SpriteIndex = Dict[Tuple[str, str], Image.Image]  # (color, char) -> sprite


@dataclass
class Sheet:
    """Sprite sheet.

    The image is sliced immediately on construction (see `__post_init__`).
    Offsets allow partial shifting of the grid inside the source image.
    """
    name: str  # Уникальное имя листа
    file: str  # Путь к файлу изображения
    image: Image.Image
    sprite_width: int
    sprite_height: int
    mod_id: str = "dda"  # ID мода, которому принадлежит этот лист
    sprite_offset_x: int = 0
    sprite_offset_y: int = 0
    sprite_offset_x_retracted: int = 0
    sprite_offset_y_retracted: int = 0
    pixelscale: int = 1
    tiles_source: List[Dict[str, Any]] = field(default_factory=lambda: [])
    sprites: List[Image.Image] = field(init=False, default_factory=lambda: [])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Sheet":
        """Create Sheet from JSON dict with proper type conversion.

        Args:
            data: Raw JSON dict with sheet configuration

        Returns:
            Sheet with properly typed fields
        """
        tiles_source_raw: list[Any] = data.get("tiles_source", []) if isinstance(
            data.get("tiles_source", []), list
        ) else []
        tiles_source: List[Dict[str, Any]] = [
            cast(Dict[str, Any], item) for item in tiles_source_raw if isinstance(item, dict)
        ]

        return cls(
            name=str(data.get("name", "unknown")),
            file=str(data.get("file", "")),
            image=data["image"],  # Must be pre-loaded PIL Image
            sprite_width=int(data.get("sprite_width", 32)),
            sprite_height=int(data.get("sprite_height", 32)),
            mod_id=str(data.get("mod_id", "dda")),
            sprite_offset_x=int(data.get("sprite_offset_x", 0)),
            sprite_offset_y=int(data.get("sprite_offset_y", 0)),
            sprite_offset_x_retracted=int(data.get("sprite_offset_x_retracted", 0)),
            sprite_offset_y_retracted=int(data.get("sprite_offset_y_retracted", 0)),
            pixelscale=int(data.get("pixelscale", 1)),
            tiles_source=tiles_source,
        )

    def __post_init__(self):
        self.image = self.image.convert("RGBA")
        self._precut_all()

    def _precut_all(self):
        """Slice the sheet image into individual sprites.

        Precomputes all sprites for O(1) indexed access later. Empty or
        missing image results in an empty list.

        NOTE: Sprite offsets (sprite_offset_x/y) are NOT applied here during cropping.
        They are used only for positioning sprites on viewport during rendering.
        This prevents double-offset issues where sprites get offset twice.
        """
        self.sprites = []
        if not self.image:
            return

        img_width, img_height = self.image.size
        cols = img_width // self.sprite_width
        rows = img_height // self.sprite_height

        for y in range(rows):
            for x in range(cols):
                # Crop sprite WITHOUT applying offsets - offsets are for viewport positioning only
                left = x * self.sprite_width
                top = y * self.sprite_height
                right = left + self.sprite_width
                bottom = top + self.sprite_height

                sprite = self.image.crop((left, top, right, bottom))
                self.sprites.append(sprite)

    @property
    def sheet_id(self) -> str:
        """Unique identifier for this sheet.

        Currently we simply reuse `name`. This indirection allows
        evolution later if a different stable key is required.
        """
        return self.name

    def get_sprite_by_index(self, index: int) -> Image.Image | None:
        """Return sprite by local index or None if out of range."""
        if 0 <= index < len(self.sprites):
            return self.sprites[index]
        return None


@dataclass
class FallbackSheet(Sheet):
    """Fallback sheet containing ASCII glyph sprites.

    A tileset may provide its own `fallback.png`. If absent we inject a
    default sheet (see service logic). This class prepares an index from
    (color, char) -> sprite for fast lookup.
    Layout expectation: the image stacks 16 color layers vertically;
    each layer contains a grid of up to 256 ASCII glyphs.
    """
    sprites_by_char: Dict[Tuple[str, str], Image.Image] = field(init=False, default_factory=lambda: {})
    colors: List[str] = field(init=False, default_factory=lambda: [])
    color_map: Dict[str, int] = field(init=False, default_factory=lambda: {})

    COLOR_ORDER = [
        "black",
        "white",
        "light_gray",
        "dark_gray",
        "red",
        "green",
        "blue",
        "cyan",
        "magenta",
        "brown",
        "light_red",
        "light_green",
        "light_blue",
        "light_cyan",
        "pink",
        "yellow",
    ]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FallbackSheet":
        """Create FallbackSheet from JSON dict with proper type conversion.

        Args:
            data: Raw JSON dict with sheet configuration

        Returns:
            FallbackSheet with properly typed fields
        """
        tiles_source_raw: list[Any] = data.get("tiles_source", []) if isinstance(
            data.get("tiles_source", []), list
        ) else []
        tiles_source: List[Dict[str, Any]] = [
            cast(Dict[str, Any], item) for item in tiles_source_raw if isinstance(item, dict)
        ]

        return cls(
            name=str(data.get("name", "unknown")),
            file=str(data.get("file", "")),
            image=data["image"],  # Must be pre-loaded PIL Image
            sprite_width=int(data.get("sprite_width", 32)),
            sprite_height=int(data.get("sprite_height", 32)),
            mod_id=str(data.get("mod_id", "dda")),
            sprite_offset_x=int(data.get("sprite_offset_x", 0)),
            sprite_offset_y=int(data.get("sprite_offset_y", 0)),
            sprite_offset_x_retracted=int(data.get("sprite_offset_x_retracted", 0)),
            sprite_offset_y_retracted=int(data.get("sprite_offset_y_retracted", 0)),
            pixelscale=int(data.get("pixelscale", 1)),
            tiles_source=tiles_source,
        )

    def __post_init__(self):
        super().__post_init__()
        self.colors = self.COLOR_ORDER
        self.color_map = {name: i for i, name in enumerate(self.colors)}
        self._build_char_index()

    def _build_char_index(self):
        """Build (color, char) -> sprite index for fast lookup.

        Slices the fallback image into 16 color layers. Each layer holds
        256 ASCII glyphs arranged in a grid. The number of columns is
        determined by image width and sprite_width; rows per color are
        computed to fully cover 256 glyphs.
        """
        self.sprites_by_char.clear()
        if not self.image:
            return

        img_w, _ = self.image.size
        if self.sprite_width <= 0:
            return

        cols = max(1, img_w // self.sprite_width)
        # rows per color slab to fit 256 glyphs
        rows_per_color = (256 + cols - 1) // cols

        for layer_index, color in enumerate(self.colors):
            base_y = layer_index * self.sprite_height * rows_per_color
            for ascii_index in range(256):
                row = ascii_index // cols
                col = ascii_index % cols
                left = col * self.sprite_width
                top = base_y + row * self.sprite_height
                right = left + self.sprite_width
                bottom = top + self.sprite_height
                sprite = self.image.crop((left, top, right, bottom))
                char = chr(ascii_index)
                self.sprites_by_char[(color, char)] = sprite

    def get_ascii_sprite(self, color: str, char: str) -> Image.Image | None:
        """Return ASCII sprite by color name and character if present."""
        return self.sprites_by_char.get((color, char))


# =============================================================================
# Tileset Models
# =============================================================================

@dataclass
class Tileset:
    """Tileset metadata descriptor.

    Mirrors fields found in upstream Cataclysm tileset definition files.
    `objects_source` keeps the parsed tiles-new list (already extracted
    from tile_info.json) for direct use without re-parsing.
    """
    short_name: str = "not found"
    view_name: str = "not found"
    folder_name: str = "not found"
    pixelscale: int = 1
    grid_width: int = 32
    grid_height: int = 32
    grid_z_height: int = 0
    is_iso: bool = False
    retract_dist_min: float = 2.5  # deprecated
    retract_dist_max: float = 5.0  # deprecated
    objects_source: list[dict[str, Any]] = field(default_factory=list) # type: ignore

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tileset":
        """Create Tileset from JSON dict with proper type conversion.

        Args:
            data: Raw JSON dict from tile_info.json

        Returns:
            Tileset with properly typed fields
        """
        return cls(
            short_name=str(data.get("short_name", "not found")),
            view_name=str(data.get("view_name", "not found")),
            folder_name=str(data.get("folder_name", "not found")),
            pixelscale=int(data.get("pixelscale", 1)),
            grid_width=int(data.get("width", data.get("grid_width", 32))),
            grid_height=int(data.get("height", data.get("grid_height", 32))),
            grid_z_height=int(data.get("zlevel_height", data.get("grid_z_height", 0))),
            is_iso=bool(data.get("iso", data.get("is_iso", False))),
            retract_dist_min=float(data.get("retract_dist_min", 2.5)),
            retract_dist_max=float(data.get("retract_dist_max", 5.0)),
            objects_source=list(data.get("objects_source", []))
        )
