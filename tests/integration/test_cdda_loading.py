import os
from pathlib import Path
import pytest
from cdda_maped.game_data.service import GameDataService

CDDA_PATH = os.environ.get("CDDA_PATH") or "D:/CDDA"


@pytest.mark.skipif(not Path(CDDA_PATH).exists(), reason="CDDA repo not found")
def test_resolved_object_t_floor():
    service = GameDataService(game_path=CDDA_PATH)
    t_floor = service.manager.get_object_by_id("t_floor")
    assert t_floor is not None, "t_floor not found"
    assert t_floor.get("id") == "t_floor"
    print(f"✓ t_floor loaded: {t_floor}")


@pytest.mark.skipif(not Path(CDDA_PATH).exists(), reason="CDDA repo not found")
def test_resolved_object_t_floor_with_core():
    from cdda_maped.settings.core import AppSettings

    settings = AppSettings()
    settings.always_include_core = True
    service = GameDataService(game_path=CDDA_PATH, settings=settings)
    t_floor = service.get_resolved_object("t_floor")
    print(f"[with always_include_core] t_floor resolved: {t_floor}")
    assert t_floor is not None, "t_floor not found with always_include_core=True"
    assert t_floor.get("id") == "t_floor"
