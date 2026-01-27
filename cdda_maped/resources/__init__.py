"""
Resources for CDDA-maped.

Provides helpers to access packaged assets such as the application icon.
"""

from functools import lru_cache
from importlib import resources as importlib_resources

from PySide6.QtGui import QIcon


@lru_cache(maxsize=1)
def get_app_icon() -> QIcon:
    """Return the shared application icon.

    Uses importlib.resources to resolve the packaged ``maped.ico`` file.
    Returns an empty icon if the resource is missing.
    """

    try:
        with importlib_resources.path(__name__, "maped.ico") as icon_path:
            return QIcon(str(icon_path))
    except FileNotFoundError:
        return QIcon()
