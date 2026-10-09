"""Milestone 6: the Temple of Mists, the Boss Rush and the Master Quest."""
from __future__ import annotations

import pygame
from conftest import make_game, step

from eldermoor import postgame
from eldermoor.state import GameState


# ----- the Temple of Mists -----------------------------------------------
def test_the_mist_temple_is_in_the_tables(content):
    mists = content.dungeons.items["mists"]
    assert mists.optional, "it is off the critical path"
    assert mists.small_keys == 4
    assert not mists.flame
    assert content.text.get(mists.name) != mists.name


def test_the_four_wardens_are_bosses(content):
    for boss in ("veilmaw", "duskmaw", "merewarden", "palewarden"):
        definition = content.enemies.get(boss)
        assert definition is not None, boss
        assert definition.raw.get("boss"), boss
        assert definition.hp >= 30, boss
        assert definition.raw.get("phases"), boss


def test_the_mist_door_waits_for_a_finished_run(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio, room="ow_0004")
    assert not [e for e in game.world.entities if type(e).__name__ == "Stairs"]
    game.state.set_flag("cleared", 1)
    game.world.warp("ow_0004")
    assert [e for e in game.world.entities if type(e).__name__ == "Stairs"]


def test_every_mist_room_loads(content):
    from eldermoor.tilemap import Room
    mists = content.dungeons.items["mists"]
    tilesets: dict[str, object] = {}
    for room_id in mists.all_rooms():
        room = Room.load(room_id, tilesets=tilesets)
        assert room.dungeon == "mists"


# ----- the Boss Rush -----------------------------------------------------
def test_the_rush_runs_every_boss(content):
    rush = content.rush
    assert len(rush) >= 20
    for boss in rush.rounds:
        definition = content.enemies.get(boss)
        assert definition is not None and definition.raw.get("boss"), boss
    assert rush.prizes


def test_the_rush_spawns_a_boss_and_counts_rounds(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio)
    w = game.world
    postgame.start(w)
    assert w.room.id == content.rush.room
    assert postgame.running(w)
    assert w.boss is not None, "round one is standing there"
    first = w.boss
    first.hp = 0
    first.die(w)
    assert game.state.flag("rush:round") == 1
    assert game.state.scores["rush"] == 1
    assert w.boss is not None, "and the next one comes on"


def test_the_rush_heals_between_rounds(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio)
    w = game.world
    postgame.start(w)
    game.state.damage(4)
    low = game.state.health
    for _ in range(content.rush.heal_every):
        boss = w.boss
        boss.hp = 0
        boss.die(w)
    assert game.state.health > low, "a breather every few rounds"


def test_the_rush_pays_out_what_was_reached(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio)
    w = game.world
    game.state.set_flag("rush:running", 1)
    game.state.set_flag("rush:round", 12)
    postgame.finish(w)
    assert "fig_hollowking" in game.state.figurines
    assert game.state.embers >= 200
    assert not game.state.flag("rush:running")


def test_the_arena_room_is_walled_and_empty(content):
    from eldermoor.tilemap import Room
    room = Room.load(content.rush.room)
    assert room.objects == []
    assert not room.exits, "no way out but through"


# ----- the Master Quest --------------------------------------------------
def test_master_quest_doubles_damage_and_thickens_hides():
    state = GameState()
    assert postgame.scale_damage(state, 2) == 2
    assert postgame.scale_hp(state, 10) == 10
    state.set_flag("master", 1)
    assert postgame.scale_damage(state, 2) == 4
    assert postgame.scale_hp(state, 10) == 15
    assert postgame.drop_table(state, "enemy") == "enemy_master"


def test_a_master_enemy_hits_harder(assets, content, silent_audio):
    plain = make_game(assets, content, silent_audio)
    easy = plain.world.spawn_from_spec({"kind": "enemy", "type": "crag", "at": [5, 5]})
    hard_game = make_game(assets, content, silent_audio)
    hard_game.state.set_flag("master", 1)
    hard = hard_game.world.spawn_from_spec({"kind": "enemy", "type": "crag", "at": [5, 5]})
    assert hard.contact_damage == easy.contact_damage * 2
    assert hard.hp > easy.hp


def test_the_master_drop_table_is_leaner(content):
    plain = content.drops.tables["enemy"]
    lean = content.drops.tables["enemy_master"]
    assert dict(plain).get("heart", 0) > 0
    plain_share = dict(plain).get("heart", 0) / sum(w for _k, w in plain)
    lean_share = dict(lean).get("heart", 0) / sum(w for _k, w in lean)
    assert lean_share < plain_share


def test_the_file_select_offers_a_master_quest(assets, content, silent_audio):
    from eldermoor.input import Input
    from eldermoor.menu import FileSelect
    inp = Input()
    menu = FileSelect(assets, content, [None, None, None], silent_audio,
                      master_unlocked=True)
    assert not menu.wants_master
    inp.begin_frame()
    inp.press("right")
    menu.update(inp)
    inp.release("right")
    assert menu.wants_master
    canvas = pygame.Surface((320, 240))
    menu.draw(canvas)


def test_a_locked_master_quest_cannot_be_turned_on(assets, content, silent_audio):
    from eldermoor.input import Input
    from eldermoor.menu import FileSelect
    inp = Input()
    menu = FileSelect(assets, content, [None, None, None], silent_audio)
    inp.begin_frame()
    inp.press("right")
    menu.update(inp)
    assert not menu.wants_master


def test_finishing_the_game_unlocks_the_master_quest(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio)
    assert not game.settings.master_unlocked
    game.world.pending_ending = "short"
    game.update()
    assert game.settings.master_unlocked
    assert game.state.flag("cleared") == 1


def test_a_new_master_file_carries_the_flag(assets, content, silent_audio, monkeypatch):
    from eldermoor import save as savefile
    from eldermoor.input import Input
    from eldermoor.menu import FileSelect
    game = make_game(assets, content, silent_audio)
    game.settings.master_unlocked = True
    monkeypatch.setattr(savefile, "load", lambda slot: None)   # an empty slot
    game.file_select = FileSelect(assets, content, [None, None, None], game.audio, True)
    game.input = Input()
    game.input.begin_frame()
    game.input.press("right")
    game.update()
    game.input.release("right")
    game.input.begin_frame()
    game.input.press("a")
    game.update()
    assert game.state.flag("master") == 1
    assert game.mode == "play"


def test_a_master_file_still_plays(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio)
    game.state.set_flag("master", 1)
    game.world.warp("glade")
    step(game, 30)
    assert game.state.health > 0
