"""
Settings migration system for CDDA-maped.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .types import ConfigVersion

if TYPE_CHECKING:
    from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


class SettingsMigrator:
    """Handles configuration migration between versions."""

    def __init__(self, settings: "QSettings"):
        self.settings = settings

    def ensure_version(self) -> None:
        """Ensure configuration version is set and handle migrations."""
        current_version = str(self.settings.value("app/version", ""))

        if not current_version:
            # First run - set current version
            self.settings.setValue("app/version", ConfigVersion.CURRENT.value)
            self.settings.setValue("app/first_run", True)
            self.settings.sync()
            logger.info("First run detected, initializing configuration")
        elif current_version != ConfigVersion.CURRENT.value:
            # Migration needed
            self._migrate_config(current_version, ConfigVersion.CURRENT.value)

    def _migrate_config(self, from_version: str, to_version: str) -> None:
        """Migrate configuration from old version to new version."""
        logger.info(f"Migrating configuration from {from_version} to {to_version}")

        # Migration logic based on versions
        if from_version == "1.0" and to_version == "1.1":
            self._migrate_1_0_to_1_1()
        # elif from_version == "1.1" and to_version == "2.0":
        #     self._migrate_1_1_to_2_0()

        # Update version after successful migration
        self.settings.setValue("app/version", to_version)
        self.settings.setValue("app/migrated_from", from_version)
        self.settings.sync()
        logger.info(f"Migration from {from_version} to {to_version} completed")

    def _migrate_1_0_to_1_1(self) -> None:
        """Migrate from version 1.0 to 1.1 - consolidate paths."""
        logger.debug("Performing migration from 1.0 to 1.1")

        # Migrate from cdda_data_path to cdda_path (parent directory)
        old_data_path = str(self.settings.value("paths/cdda_data", ""))
        if old_data_path:
            data_path = Path(old_data_path)

            # Check if this looks like a CDDA data directory
            if data_path.name == "data":
                # This is a data directory - use parent as CDDA root
                cdda_path = data_path.parent
                self.settings.setValue("paths/cdda", str(cdda_path))
                logger.info(
                    f"Migrated data directory to CDDA root: {data_path} -> {cdda_path}"
                )
            elif (data_path / "data").exists():
                # This already looks like a CDDA root directory
                self.settings.setValue("paths/cdda", str(data_path))
                logger.info(f"Migrated CDDA root directory: {data_path}")
            else:
                # Assume this is the CDDA root even if data directory doesn't exist
                self.settings.setValue("paths/cdda", str(data_path))
                logger.warning(f"Migrated unverified path as CDDA root: {data_path}")

            self.settings.sync()

            # Remove old setting
            self.settings.remove("paths/cdda_data")

        # Remove tilesets_path since it's now derived from cdda_path
        old_tilesets_path = self.settings.value("paths/tilesets", "")
        if old_tilesets_path:
            logger.info(
                f"Removed tilesets_path (now auto-derived): {old_tilesets_path}"
            )
            self.settings.remove("paths/tilesets")
