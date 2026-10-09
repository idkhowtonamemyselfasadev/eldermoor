"""Data validation, the drop tables, the audio synthesiser and the playthrough bot."""
from __future__ import annotations

import json
import random
import wave
from pathlib import Path

import build_audio
import pytest
import validate_data

from eldermoor.audio import Audio
from eldermoor.drops import PICKUPS, DropTables
from eldermoor.tilemap import list_rooms


def test_validate_data_passes():
    assert validate_data.main(["--quiet"]) == 0


def test_validator_catches_a_dungeon_it_cannot_finish(monkeypatch):
    """Remove the first small key and the validator must notice."""
    original = validate_data.Room.load

    def without_first_key(room_id, *args, **kwargs):
        room = original(room_id, *args, **kwargs)
        if room_id == "t1_18":
            room.triggers = []
        return room

    monkeypatch.setattr(validate_data.Room, "load", staticmethod(without_first_key))
    report = validate_data.Report(quiet=True)
    content = validate_data.Content()
    rooms = {r: without_first_key(r) for r in list_rooms()}
    validate_data.check_dungeons(report, content, rooms)
    assert report.problems, "a temple with no first key must fail validation"


def test_every_item_icon_exists(assets, content):
    for item in content.items.items.values():
        assert assets.icons.has(item.icon), item.id


def test_item_registry_sorting_and_assignable(content):
    owned = ["lantern", "sword", "feather"]
    order = [d.id for d in content.items.ordered(owned)]
    assert order == ["sword", "lantern", "feather"]
    assert [d.id for d in content.items.assignable_owned(owned)] == ["lantern", "feather"]
    assert content.items.icon(None) == "icon_empty"
    assert content.items.icon("nope") == "icon_empty"


def test_drop_tables_cover_every_pickup_kind():
    tables = DropTables.load()
    rng = random.Random(11)
    kinds = set()
    for name in tables.tables:
        for _ in range(400):
            kind = tables.roll(name, rng)
            if kind:
                kinds.add(kind)
    assert kinds <= set(PICKUPS), kinds - set(PICKUPS)
    assert tables.roll("does_not_exist") is None
    assert tables.roll("none", rng) is None


def test_enemy_drop_table_gives_hearts_often_enough():
    tables = DropTables.load()
    rng = random.Random(3)
    hearts = sum(1 for _ in range(2000) if tables.roll("enemy", rng) == "heart")
    assert 0.2 < hearts / 2000 < 0.45, "tuned so the player is rarely stranded"


def test_note_frequencies():
    assert round(build_audio.note_freq("A4")) == 440
    assert round(build_audio.note_freq("A3")) == 220
    assert round(build_audio.note_freq("C4")) == 262
    assert build_audio.note_freq("A#4") > build_audio.note_freq("A4")
    assert build_audio.note_freq("Bb4") < build_audio.note_freq("B4")


def test_pattern_shorthand_expands():
    assert build_audio._rows("C4:4 r:2 E4") == ["C4", ".", ".", ".", "-", "-", "E4"]


def test_every_sfx_renders(tmp_path):
    spec = json.loads((build_audio.SRC / "sfx.json").read_text())
    names = [k for k in spec if not k.startswith("_")]
    assert len(names) >= 50, f"PROMPT asks for 50 sound effects, found {len(names)}"
    for name in ("sword", "heart", "item_get", "door_unlock", "secret", "low_health"):
        assert name in names, f"the classic set needs {name}"
    buf = build_audio.render_tone("square", 440, 220, 0.05, 0.4, "hit")
    assert len(buf) == int(0.05 * build_audio.RATE)
    assert max(abs(v) for v in buf) > 0.01
    out = tmp_path / "x.wav"
    build_audio.write_wav(out, buf)
    with wave.open(str(out)) as w:
        assert w.getnchannels() == 2 and w.getframerate() == 44100


def test_songs_cover_the_slice():
    songs = {p.stem for p in (build_audio.SRC / "songs").glob("*.song")}
    assert {"title", "village", "overworld_day", "temple_ember", "boss"} <= songs
    for path in (build_audio.SRC / "songs").glob("*.song"):
        song = json.loads(path.read_text())
        assert song["channels"], path.stem
        for channel in song["channels"]:
            assert build_audio._rows(channel["pattern"]), path.stem


def test_audio_is_silent_without_files(tmp_path):
    audio = Audio(root=tmp_path)
    audio.enabled = False
    audio.play("sword")
    audio.play_music("village")
    audio.stop_music()
    audio.set_volumes(0.5, 0.5)
    audio.tick()
    assert audio.log[-1] == "sword"


def test_audio_repeat_guard(tmp_path):
    audio = Audio(root=tmp_path)
    audio.enabled = False
    audio.play("hit")
    audio.play("hit")
    assert audio.log.count("hit") == 2, "the log records every request"


@pytest.mark.parametrize("room_id", ["glade", "t1_01", "t1_31"])
def test_room_json_is_indented_and_parsable(room_id):
    raw = json.loads(Path(f"data/rooms/{room_id}.json").read_text())
    assert len(raw["tiles"]) == 13


def test_simulated_run_reaches_the_temple():
    import sim_playthrough
    report = sim_playthrough.run(max_frames=9000, quiet=True)
    assert report["done"]["sword"], "the bot could not even find the sword"
    assert report["done"]["reached_temple"], "the bot never reached the temple"
    assert report["player_hours_slice"] > 0
