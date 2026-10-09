"""Milestone 4 relics: Fins, Cinderstep Boots, Mirror Cloak, Titan Gauntlet, Whistle.

Also the two endings and the screen that rolls them.
"""
from __future__ import annotations

import math

import pygame
from conftest import make_game, step

from eldermoor.config import (
    CLOAK_SPEED_FACTOR,
    HERO_SPEED,
    SWIM_SPEED_FACTOR,
    TILE,
)


def paint(world, char: str, rows: range, cols: range) -> None:
    """Fill a rectangle of the current room with one legend character."""
    tile = world.room.tileset.legend[char]
    for r in rows:
        for c in cols:
            world.room.tiles[r][c] = tile


def tile_rect(col: int, row: int) -> pygame.Rect:
    """The rect of one tile cell."""
    return pygame.Rect(col * TILE, row * TILE, TILE, TILE)


def stand_at(world, col: int, row: int) -> None:
    """Put the hero exactly on a cell and clear anything in flight."""
    world.hero.x, world.hero.y = float(col * TILE), float(row * TILE)
    world.last_safe = (world.hero.x, world.hero.y)


# ----- Fins ---------------------------------------------------------------
def test_water_blocks_until_the_fins_are_found(game):
    w = game.world
    paint(w, "~", range(5, 8), range(2, 18))
    assert w.blocked(tile_rect(10, 6), ignore=w.hero), "no fins, no swimming"
    game.state.give("fins")
    assert not w.blocked(tile_rect(10, 6), ignore=w.hero)


def test_swimming_is_slower_than_walking(game):
    w = game.world
    paint(w, "~", range(4, 9), range(2, 18))
    game.state.give("fins")
    stand_at(w, 6, 6)
    step(game)
    assert w.hero.swimming
    x0 = w.hero.x
    game.input.press("right")
    step(game, 10)
    game.input.release_all()
    assert math.isclose(w.hero.x - x0, HERO_SPEED * SWIM_SPEED_FACTOR * 10, rel_tol=1e-6)


def test_no_sword_swings_in_deep_water(game):
    w = game.world
    paint(w, "~", range(4, 9), range(2, 18))
    game.state.give("fins")
    stand_at(w, 6, 6)
    step(game)
    w.hero.start_swing(w)
    assert not w.hero.swinging


# ----- Cinderstep Boots ---------------------------------------------------
def test_lava_burns_without_the_boots_and_carries_with_them(game):
    w = game.world
    stand_at(w, 4, 6)
    paint(w, "^", range(6, 8), range(8, 14))
    assert w.blocked(tile_rect(10, 6), ignore=w.hero)
    hearts = game.state.health
    w.hero.x, w.hero.y = 10 * TILE, 6 * TILE
    step(game)
    assert game.state.health < hearts, "lava hurts and spits you back out"
    assert (w.hero.x, w.hero.y) == (4 * TILE, 6 * TILE)

    game.state.give("fire_boots")
    assert not w.blocked(tile_rect(10, 6), ignore=w.hero)
    hearts = game.state.health
    w.hero.x, w.hero.y = 10 * TILE, 6 * TILE
    step(game, 4)
    assert game.state.health == hearts, "the boots hold out"


def test_boots_melt_an_ice_wall(game):
    w = game.world
    floor = w.room.tileset.legend["."]
    paint(w, ".", range(5, 8), range(8, 13))
    stand_at(w, 9, 6)
    w.hero.facing = "right"
    paint(w, "J", range(6, 7), range(10, 11))
    game.state.give("fire_boots")
    game.state.assign(0, "fire_boots")
    w.use_item(w.hero, "fire_boots")
    assert w.room.tiles[6][10] == floor, "the ice is gone"


# ----- Mirror Cloak -------------------------------------------------------
def spawn_watcher(game, kind: str = "sentinel", col: int = 10, row: int = 4):
    """Put one enemy of a kind on the board and hand it back."""
    w = game.world
    return w.spawn_from_spec({"kind": "enemy", "type": kind, "at": [col, row]})


def hold_cloak(game) -> None:
    """Own the cloak, slot it in B and hold B down."""
    game.state.give("mirror_cloak")
    game.state.assign(0, "mirror_cloak")
    game.input.press("b")


def test_cloak_hides_wren_from_a_watcher(game):
    from eldermoor.ai import blind_to
    w = game.world
    watcher = spawn_watcher(game)
    stand_at(w, 10, 8)
    step(game)
    assert not blind_to(watcher, w)
    hold_cloak(game)
    step(game)
    assert w.hero.cloaked
    assert blind_to(watcher, w), "the sentinel sees its own reflection"
    game.input.release_all()


def test_cloak_slows_wren_down(game):
    w = game.world
    hold_cloak(game)
    stand_at(w, 6, 6)
    step(game)
    x0 = w.hero.x
    game.input.press("right")
    step(game, 10)
    game.input.release_all()
    assert math.isclose(w.hero.x - x0, HERO_SPEED * CLOAK_SPEED_FACTOR * 10, rel_tol=1e-6)


def test_cloak_sends_a_bolt_back(game):
    from eldermoor.enemies import Projectile
    w = game.world
    stand_at(w, 10, 6)
    hold_cloak(game)
    step(game)
    bolt = w.spawn(Projectile(w.hero.x + 24, w.hero.y + 4, -1.5, 0.0, damage=2))
    hearts = game.state.health
    for _ in range(20):
        step(game)
        if bolt.team == "hero":
            break
    game.input.release_all()
    assert bolt.team == "hero", "the mirror turns the shot around"
    assert bolt.vx > 0
    assert game.state.health == hearts


# ----- Titan Gauntlet ----------------------------------------------------
def test_heavy_block_waits_for_the_gauntlet(game):
    w = game.world
    block = w.spawn_from_spec({"kind": "block", "at": [10, 6], "heavy": True})
    stand_at(w, 9, 6)
    w.hero.facing = "right"
    assert w.try_interact(w.hero), "the shove is answered either way"
    assert block.target is None, "too heavy by hand"
    game.state.give("gauntlet")
    assert w.try_interact(w.hero)
    assert block.target is not None, "the gauntlet moves it"


# ----- Whistle of Winds --------------------------------------------------
def test_whistle_needs_a_lantern_lit_somewhere(game):
    w = game.world
    game.state.give("whistle")
    game.state.warps.clear()
    w.blow_whistle()
    assert not w.pending_warp_menu
    assert w.dialogue is not None, "it only answers the wind"
    w.dialogue = None
    game.state.warps["meadow"] = "ow_1105"
    w.blow_whistle()
    assert w.pending_warp_menu


def test_whistle_opens_the_warp_page(game):
    game.state.give("whistle")
    game.state.assign(0, "whistle")
    game.state.warps["meadow"] = "ow_1105"
    game.input.begin_frame()
    game.input.press("b")
    game.update()
    game.input.release("b")
    assert game.mode == "pause"
    assert not game.world.pending_warp_menu


# ----- the endings -------------------------------------------------------
def test_short_ending_for_a_hurried_run(assets, content, silent_audio):
    from eldermoor.ending import Ending
    from eldermoor.state import GameState
    state = GameState()
    ending = Ending(assets, content, state, silent_audio, "short")
    assert not ending.full
    assert ending.pages


def test_full_ending_for_a_finished_run(assets, content, silent_audio):
    from eldermoor.ending import FULL_ENDING_AT, Ending
    from eldermoor.state import GameState
    state = GameState()
    state.heart_pieces = 999
    state.seashells = 999
    state.max_hearts = 99
    state.owned = [f"thing{i}" for i in range(40)]
    state.rings = [f"ring{i}" for i in range(12)]
    state.figurines = [f"fig{i}" for i in range(24)]
    state.furniture = [f"chair{i}" for i in range(12)]
    state.bestiary = {f"beast{i}": 1 for i in range(24)}
    state.quests = [f"quest{i}" for i in range(30)]
    for name in (f"temple{i}" for i in range(1, 10)):
        state.progress(name).flame = True
    assert state.completion() >= FULL_ENDING_AT
    short = Ending(assets, content, state, silent_audio, "short")
    assert short.full, "a complete run earns the long goodbye"


def test_credits_roll_and_finish(assets, content, silent_audio):
    from eldermoor.ending import Ending
    from eldermoor.input import Input
    from eldermoor.state import GameState
    inp = Input()
    ending = Ending(assets, content, GameState(), silent_audio, "short")
    canvas = pygame.Surface((320, 240))
    for _ in range(len(ending.pages)):
        inp.begin_frame()
        inp.press("a")
        ending.update(inp)
        inp.release("a")
    assert ending.rolling
    for _ in range(4000):
        inp.begin_frame()
        ending.draw(canvas)
        if ending.update(inp):
            break
    assert ending.done, "the crawl ends on its own"


def test_the_ending_action_takes_over_the_screen(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio)
    game.world.pending_ending = "short"
    game.update()
    assert game.mode == "ending"
    assert game.state.flag("cleared") == 1
    assert game.state.flag("ending") == 1


# ----- the nine temples ---------------------------------------------------
def test_every_temple_and_its_flame_is_in_the_tables(content):
    names = [f"temple{i}" for i in range(1, 10)]
    assert set(names) <= set(content.dungeons.items)
    flames = {content.dungeons.items[n].flame for n in names[:8]}
    assert len(flames) == 8, "eight flames, no repeats"
    final = content.dungeons.items["temple9"]
    assert final.music == "great_lantern"


def test_the_relics_are_items_with_icons(content, assets):
    for item in ("fins", "fire_boots", "mirror_cloak", "gauntlet", "whistle"):
        assert item in content.items.items, item
        assert assets.icons.has(content.items.items[item].icon), item


def test_the_great_lantern_opens_only_for_eight_flames(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio, room="ow_0906")
    stairs = [e for e in game.world.entities if type(e).__name__ == "Stairs"]
    assert not stairs, "no flames, no way in"
    for i in range(1, 9):
        game.state.progress(f"temple{i}").flame = True
    game.state.set_flag("flames8")
    game.world.warp("ow_0906")
    stairs = [e for e in game.world.entities if type(e).__name__ == "Stairs"]
    assert stairs, "eight flames open the door"
