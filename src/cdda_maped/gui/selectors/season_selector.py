"""
Season selector widget for CDDA-maped.

Provides a UI component for selecting the current season for seasonal sprites.
Minimalist design: icon on the left, selector on the right (Photoshop-style).
"""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from .icon_selector import IconSelector


class SeasonSelector(IconSelector):
    """
    Widget for selecting the current season.

    Emits seasonChanged signal when the user selects a different season.
    Uses minimalist design with fixed Material Design icon.
    """

    # Signal emitted when season changes
    seasonChanged = Signal(str)

    # Available seasons
    SEASONS = [
        ("spring", "Spring"),
        ("summer", "Summer"),
        ("autumn", "Autumn"),
        ("winter", "Winter"),
    ]

    # Fixed icon for season selector (doesn't change with selection)
    ICON_NAME = "mdi.calendar"
    SETTINGS_KEY = "season"

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the season selector."""
        super().__init__(parent)

        self.current_season = "spring"

        # Populate seasons
        for season_id, season_name in self.SEASONS:
            self.combo.addItem(season_name, season_id)

        # Set spring as default
        self.combo.setCurrentIndex(0)

        # Connect signals
        self.combo.currentTextChanged.connect(self.on_season_changed)
        self._enable_auto_save()

    def on_season_changed(self, season_name: str):
        """Handle season selection change."""
        # Find season ID by name
        season_id = None
        for sid, sname in self.SEASONS:
            if sname == season_name:
                season_id = sid
                break

        if season_id and season_id != self.current_season:
            self.current_season = season_id
            self.seasonChanged.emit(season_id)

    def get_current_season(self) -> str:
        """Get the currently selected season ID."""
        return self.current_season

    def set_current_season(self, season_id: str):
        """Set the current season programmatically."""
        # Find index by season ID
        for i, (sid, _) in enumerate(self.SEASONS):
            if sid == season_id:
                self.combo.setCurrentIndex(i)
                self.current_season = season_id
                break
        else:
            self.logger.warning(f"Unknown season ID: {season_id}")
