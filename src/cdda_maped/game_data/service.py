"""
Main service for working with CDDA game data.

Provides high-level API for loading, managing, and querying game data
with support for mods and inheritance resolution.
"""

import logging
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, TYPE_CHECKING, Dict, Any, Mapping

from .loaders import GameDataFileLoader
from .managers import ObjectsManager
from .inheritance import InheritanceResolver
from .models import GameDataObject, GameDataCollection

if TYPE_CHECKING:
    from ..settings import AppSettings


class GameDataService:
    """Service for working with CDDA game data.

    Responsible for reading JSON game data files, grouping objects by type,
    tracking which mod provided each object, and resolving simple inheritance
    (copy-from) chains. Designed to be fast by using a thread pool and
    orjson for parsing.
    """

    def __init__(self, game_path: str | Path, settings: Optional["AppSettings"] = None):
        """Initialize the game data reader.

        Args:
            game_path: Path to the CDDA game folder (should contain `data/` and optional `mods/`).
            settings: App settings for mod configuration and caching.
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.game_path = Path(game_path)
        self.settings = settings

        # Initialize components
        self.loader = GameDataFileLoader()
        self.manager = ObjectsManager()

        # Initialize resolver (will be configured after loading)
        self._resolver: Optional[InheritanceResolver] = None

        self.logger.info(f"Initializing GameDataService with path: {game_path}")
        self._load_data()
        self._setup_resolvers()

    def _setup_resolvers(self) -> None:
        """Setup inheritance resolver with manager lookup function."""
        self._resolver = InheritanceResolver(
            priority_lookup=self.manager.get_object_by_id
        )

    def _load_data(self) -> None:
        """Load and group all JSON data from the game folder, including mods."""
        self.logger.info("Starting game data loading process...")

        # Load core and mod data
        self._load_core_data()
        self._load_mod_data()

        # Finalize type list
        self.manager.finalize_types()

        self.logger.info(
            f"Game data loading completed. Found {len(self.manager.types)} object types "
            f"across {len(self.manager.available_mods)} game mods"
        )
        self.logger.debug(f"Available mods: {self.manager.available_mods}")

    def _load_core_data(self) -> None:
        """Load base (core) game data, excluding mod folders and backup directories."""
        self.logger.debug("Loading core game data...")

        # Exclude files located under certain directories
        mods_path = self.game_path / "data" / "mods"
        previous_version_path = self.game_path / "previous_version"
        json_files: List[Path] = []

        for json_file in self.game_path.rglob("*.json"):
            # Skip files that are part of mods
            if mods_path in json_file.parents:
                continue
            # Skip files that are part of previous_version backups
            if previous_version_path in json_file.parents:
                continue
            json_files.append(json_file)

        if not json_files:
            self.logger.warning("No core JSON files found")
            return

        self.logger.info(f"Found {len(json_files)} core JSON files")

        # Use ThreadPoolExecutor to read files in parallel
        with ThreadPoolExecutor(max_workers=32) as executor:
            future_to_file = {
                executor.submit(
                    self.loader.read_and_group_json_file, json_file, "dda"
                ): json_file
                for json_file in json_files
            }

            processed_count = 0
            total_files = len(future_to_file)

            for future in as_completed(future_to_file):
                try:
                    grouped = future.result()
                    # Add grouped results to manager
                    self.manager.add_objects(grouped, "dda")
                    processed_count += 1

                    # Process GUI events every 250 files to keep UI responsive
                    if processed_count % 250 == 0:
                        self.logger.debug(
                            f"Processed {processed_count}/{total_files} core objects"
                        )
                        # Try to process Qt events if available
                        try:
                            from PySide6.QtWidgets import QApplication

                            app = QApplication.instance()
                            if app:
                                app.processEvents()
                        except ImportError:
                            pass
                except Exception:
                    # ignore failures for individual files
                    pass

    def _load_mod_data(self) -> None:
        """Load data provided by mods (under data/mods/ directory)."""
        self.logger.debug("Loading mod data...")

        mods_path = self.game_path / "data" / "mods"

        if not mods_path.exists() or not mods_path.is_dir():
            self.logger.info("No mods directory found")
            return

        mod_dirs = [d for d in mods_path.iterdir() if d.is_dir()]
        self.logger.info(f"Found {len(mod_dirs)} mod directories")

        for mod_dir in mod_dirs:
            mod_id = mod_dir.name
            json_files = list(mod_dir.rglob("*.json"))

            if not json_files:
                self.logger.debug(f"No JSON files found in mod: {mod_id}")
                continue

            self.logger.debug(
                f"Processing mod '{mod_id}' with {len(json_files)} JSON files"
            )

            # Use ThreadPoolExecutor for parallel reads
            with ThreadPoolExecutor(max_workers=32) as executor:
                future_to_file = {
                    executor.submit(
                        self.loader.read_and_group_json_file, json_file, mod_id
                    ): json_file
                    for json_file in json_files
                }

                processed_count = 0
                total_files = len(future_to_file)

                for future in as_completed(future_to_file):
                    try:
                        grouped = future.result()
                        # Add grouped results to manager
                        self.manager.add_objects(grouped, mod_id)
                        processed_count += 1

                        # Process GUI events every 100 files for mods (smaller batches)
                        if processed_count % 100 == 0:
                            self.logger.debug(
                                f"Processed {processed_count}/{total_files} files in mod '{mod_id}'"
                            )
                            # Try to process Qt events if available
                            try:
                                from PySide6.QtWidgets import QApplication

                                app = QApplication.instance()
                                if app:
                                    app.processEvents()
                            except ImportError:
                                pass
                    except Exception:
                        # ignore failures for individual files
                        pass

            # Process events after each mod
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                if app:
                    app.processEvents()
            except ImportError:
                pass

    # Public API methods - delegate to manager and resolvers

    def get_objects_by_type(self, object_type: str) -> GameDataCollection:
        """Return the list of objects of the specified type from active mods only."""
        if not self.settings:
            # Fallback: return all objects if no settings
            return self.manager.get_objects_by_type(object_type)

        active_mods = self._compute_mod_priority()
        return self.manager.get_objects_by_type_from_mods(object_type, active_mods)

    def get_types(self) -> List[str]:
        """Return a copy of the discovered object types list."""
        return self.manager.get_types()

    def get_available_mods(self) -> List[str]:
        """Return a copy of the list of available mods."""
        return self.manager.get_available_mods()

    def get_resolved_object(self, object_id: str) -> Optional[GameDataObject]:
        """Return the object with resolved 'copy-from' inheritance by ID.

        Uses active_mods from application settings to determine mod priority.
        Core objects are cached, mod objects are resolved on-demand.

        Args:
            object_id: ID of the object to resolve

        Returns:
            Resolved object or None if not found
        """
        if not self._resolver:
            return None

        active_mods = self._compute_mod_priority()
        return self._resolver.resolve_object(object_id, active_mods)

    # High-level collection API (non-GUI)

    @staticmethod
    def _extract_clean_name(name_field: Any) -> str:
        """Extract and clean display name from CDDA name field."""
        if not name_field:
            return "No name"
        if isinstance(name_field, dict):
            str_value = name_field.get("str")  # type: ignore
            if str_value:
                name_str = str(str_value)  # type: ignore
            else:
                return "No name"
        else:
            name_str = str(name_field)
        clean_name = re.sub(r"<[^>]*>", "", name_str)
        return clean_name.strip() or "No name"

    def _compute_mod_priority(self) -> List[str]:
        """Return active mods order, core last if included."""
        if not self.settings:
            return []
        active = self.settings.active_mods.copy()
        if self.settings.always_include_core:
            active = [m for m in active if m != "dda"] + ["dda"]
        return active

    def collect_resolved_objects(
        self,
        types: List[str],
        per_type_limits: Optional[Mapping[str, int]] = None,
    ) -> GameDataCollection:
        """Collect, resolve and deduplicate objects for provided types.

        Returns list of dicts: { id, type, name, mod_id, _resolved_obj }
        """
        collected: GameDataCollection = []

        for object_type in types:
            objects = self.get_objects_by_type(object_type)
            limit = per_type_limits.get(object_type) if per_type_limits else None
            if limit:
                objects = objects[:limit]

            for obj in objects:
                if "abstract" in obj:
                    continue
                obj_id = obj.get("id")
                if not obj_id:
                    continue
                resolved = self.get_resolved_object(str(obj_id))
                if not resolved:
                    continue
                resolved_name = self._extract_clean_name(resolved.get("name"))
                mod_id = resolved.get("_mod_id", "dda")
                collected.append(
                    {
                        "id": str(obj_id),
                        "type": object_type,
                        "name": resolved_name,
                        "mod_id": mod_id,
                        "_resolved_obj": resolved,
                    }
                )

        # Deduplicate by priority (mods override core)
        priority = self._compute_mod_priority()
        if priority:
            dedup: Dict[str, Dict[str, Any]] = {}
            for entry in collected:
                oid = entry["id"]
                current = dedup.get(oid)
                if not current:
                    dedup[oid] = entry
                    continue
                current_mod = str(current.get("mod_id", "dda"))
                new_mod = str(entry.get("mod_id", "dda"))
                try:
                    if priority.index(new_mod) < priority.index(current_mod):
                        dedup[oid] = entry
                except ValueError:
                    # If mod not in list, keep existing
                    pass
            collected = list(dedup.values())

        return collected
