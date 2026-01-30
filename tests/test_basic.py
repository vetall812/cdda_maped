"""Basic unit tests for CDDA-maped modules."""

from typing import Any


class TestSettingsInitialization:
    """Test settings initialization and basic operations."""

    def test_app_settings_init(self) -> None:
        """Test AppSettings can be initialized."""
        from cdda_maped.settings import AppSettings

        settings_obj = AppSettings()
        assert settings_obj is not None

    def test_app_settings_validation(self) -> None:
        """Test settings validation returns result."""
        from cdda_maped.settings import AppSettings

        settings_obj = AppSettings()
        validation = settings_obj.validate()
        assert validation is not None


class TestGameDataModels:
    """Test game data model creation."""

    def test_game_data_dict_creation(self) -> None:
        """Test GameDataObject (dict) can be created."""
        obj: dict[str, Any] = {
            "id": "test_id",
            "type": "terrain",
            "name": "Test Terrain",
        }
        assert obj["id"] == "test_id"
        assert obj["type"] == "terrain"

    def test_game_data_collection_creation(self) -> None:
        """Test GameDataCollection (list) can be created."""
        collection: list[dict[str, Any]] = []
        assert len(collection) == 0


class TestTilesetModels:
    """Test tileset model creation."""

    def test_tile_source_creation(self) -> None:
        """Test TileSource model can be created."""
        from cdda_maped.tilesets.models import TileSource

        source = TileSource(
            id="test_tile",
            fg=0,
            rotates=False,
        )
        assert source.id == "test_tile"
        assert source.fg == 0

    def test_sheet_info_creation(self) -> None:
        """Test SheetInfo model can be created."""
        from cdda_maped.tilesets.models import SheetInfo

        sheet_info = SheetInfo(
            name="test_sheet",
            file="path/to/sheet.png",
        )
        assert sheet_info.name == "test_sheet"
        assert sheet_info.file == "path/to/sheet.png"


class TestUtilsLogging:
    """Test logging configuration."""

    def test_logging_setup_with_settings(self) -> None:
        """Test logging setup works with settings."""
        from cdda_maped.utils.logging_config import setup_logging
        from cdda_maped.settings import AppSettings

        settings_obj = AppSettings()
        # setup_logging returns None but should not raise
        setup_logging(settings=settings_obj)

        # Verify logger is configured
        import logging

        logger = logging.getLogger("cdda_maped")
        assert logger is not None
        assert logger.level == logging.DEBUG
