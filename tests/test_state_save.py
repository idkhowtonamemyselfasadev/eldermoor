"""GameState maths, save slots, migrations and the settings file."""
from __future__ import annotations

import json

import pytest

from eldermoor import save as savefile
from eldermoor.config import SAVE_VERSION
from eldermoor.settings import Settings, config_dir
from eldermoor.state import GameState


def test_items_flags_and_slots_round_trip():
    s = GameState()
    assert s.give("lantern") and not s.give("lantern")
    s.assign(0, "lantern")
    s.assign(1, "lantern")                    # moving it clears the old slot
    assert s.slots == [None, "lantern", None]
    s.set_flag("t1_door_a")
    s.set_flag("counter", 3)
    s.set_flag("gone", 0)
    assert s.flag("t1_door_a") == 1 and s.flag("counter") == 3 and s.flag("gone") == 0
    back = GameState.from_json(s.to_json())
    assert back.owned == ["lantern"] and back.slots == [None, "lantern", None]
    assert back.flags == {"t1_door_a": 1, "counter": 3}


def test_heart_maths_and_pieces():
    s = GameState()
    s.damage(3)
    assert s.health == 3 and s.heart_icons() == ["heart_full", "heart_half", "heart_empty"]
    assert s.low_health is False
    s.damage(1)
    assert s.low_health is True
    for _ in range(3):
        assert s.add_heart_piece() is False
    assert s.add_heart_piece() is True
    assert s.max_hearts == 4 and s.health == 8
    s.max_hearts = 20
    s.add_heart_container()
    assert s.max_hearts == 20, "capped at twenty hearts"


def test_dungeon_keys_follow_the_dungeon():
    s = GameState()
    s.enter_dungeon("temple1")
    s.keys = 3
    s.sync_keys()
    s.enter_dungeon("")
    assert s.keys == 0, "the HUD counter empties outside a dungeon"
    s.enter_dungeon("temple1")
    assert s.keys == 3


def test_save_round_trip_backup_and_corruption():
    state = GameState(slot=1, embers=42)
    state.give("sword")
    savefile.save(state, 1)
    state.embers = 99
    savefile.save(state, 1)
    assert savefile.slot_path(1).with_suffix(".bak").exists()
    loaded = savefile.load(1)
    assert loaded is not None and loaded.embers == 99 and loaded.has("sword")
    summary = savefile.summary(1)
    assert summary["slot"] == 1 and summary["hearts"] == 3
    savefile.slot_path(1).write_text("{ not json", encoding="utf-8")
    recovered = savefile.load(1)
    assert recovered is not None and recovered.embers == 42, "falls back to the backup"
    savefile.delete(1)
    assert savefile.load(1) is None


def test_migration_from_version_one():
    raw = {"version": 1, "embers": 5, "health": 4, "max_hearts": 3}
    migrated = savefile.migrate(raw)
    assert migrated["version"] == SAVE_VERSION
    state = GameState.from_json(migrated)
    assert state.embers == 5 and state.owned == [] and state.dungeons == {}


def test_migration_refuses_an_unknown_version():
    with pytest.raises(ValueError):
        savefile.migrate({"version": 0})


def test_completion_grows_with_progress():
    s = GameState()
    before = s.completion()
    s.progress("temple1").flame = True
    s.heart_pieces = 8
    s.seashells = 4
    assert s.completion() > before


def test_settings_file_round_trip_and_clamping(tmp_path):
    path = tmp_path / "settings.json"
    s = Settings(music_volume=2.0, text_speed=99, scale=99)
    s.clamped().save(path)
    back = Settings.load(path)
    assert back.music_volume == 1.0 and back.text_speed == 4 and back.scale == 6
    path.write_text("not json", encoding="utf-8")
    assert Settings.load(path).music_volume == Settings().music_volume


def test_config_dir_is_redirected_for_tests():
    assert "eldermoor-test-" in str(config_dir())


def test_crash_slot_is_written(tmp_path):
    state = GameState(embers=7)
    path = savefile.crash_save(state)
    assert json.loads(path.read_text())["embers"] == 7
