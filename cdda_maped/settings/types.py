"""
Configuration type definitions and exceptions for CDDA-maped.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class ConfigVersion(Enum):
    """Configuration version for migration support."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    CURRENT = V1_1


class ConfigError(Exception):
    """Raised when configuration is invalid or cannot be accessed."""
    pass


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
