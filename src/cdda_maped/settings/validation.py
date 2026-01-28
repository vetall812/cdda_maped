"""
Settings validation system for CDDA-maped.
"""

import logging
from pathlib import Path
from typing import List, TYPE_CHECKING

from .types import ValidationResult

if TYPE_CHECKING:
    from .core import AppSettings

logger = logging.getLogger(__name__)


class SettingsValidator:
    """Validates configuration settings."""

    def __init__(self, settings: "AppSettings"):
        self.settings = settings

    def validate(self) -> ValidationResult:
        """Validate current configuration."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate CDDA path
        if self.settings.cdda_path:
            if not self.settings.cdda_path.exists():
                errors.append(f"CDDA path does not exist: {self.settings.cdda_path}")
            elif not (self.settings.cdda_path / "data").exists():
                warnings.append(
                    f"CDDA path might be invalid (no 'data' directory): {self.settings.cdda_path}"
                )
        else:
            warnings.append("CDDA path not set")

        # Validate recent files
        recent_files = self.settings.recent_files
        valid_recent: List[str] = []
        for file_path in recent_files:
            if Path(file_path).exists():
                valid_recent.append(file_path)
            else:
                warnings.append(f"Recent file no longer exists: {file_path}")

        # Clean up invalid recent files
        if len(valid_recent) != len(recent_files):
            self.settings.settings.setValue("paths/recent_files", valid_recent)
            self.settings.settings.sync()

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )
