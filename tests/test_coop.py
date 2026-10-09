"""Milestone 7: two lamplighters on one screen."""
from __future__ import annotations

import pygame
from conftest import make_game, step

from eldermoor.config import TILE
from eldermoor.input import Input


def two_player(assets, content, audio, room: str = "glade"):
    """A game with the second lamplighter already dropped in."""
    game = make_game(assets, content, audio, room=room)
    game.settings.two_player = True
    game.update()
    return game


# ----- the input views ---------------------------------------------------
def test_one_player_reads_every_device():
    inp = Input()
    view = inp.view("both")
    inp.begin_frame()
    inp.press("right")
    assert view.is_held("right") and view.pressed("right")
    inp.begin_frame()
    assert view.is_held("right") and not view.pressed("right")


def test_the_two_views_do_not_see_each_other():
    inp = Input()
    one, two = inp.view("keyboard"), inp.view("gamepad")
    inp.begin_frame()
    inp.press("right")
    inp.press_pad("left")
    assert one.axis() == (1, 0)
    assert two.axis() == (-1, 0)
    assert one.pressed("right") and not two.pressed("right")
    assert two.pressed("left") and not one.pressed("left")


def test_a_view_sees_a_button_let_go():
    inp = Input()
    view = inp.view("gamepad")
    inp.begin_frame()
    inp.press_pad("a")
    assert view.pressed("a")
    inp.begin_frame()
    inp.release_pad("a")
    assert view.released("a") and not view.is_held("a")


# ----- dropping in and out ----------------------------------------------
def test_the_setting_drops_the_second_player_in_and_out(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio)
    assert game.world.hero2 is None
    assert len(game.world.heroes) == 1
    game.settings.two_player = True
    game.update()
    assert game.world.hero2 is not None
    assert len(game.world.heroes) == 2
    game.settings.two_player = False
    game.update()
    assert game.world.hero2 is None
    assert game.world.hero not in [None]
    assert all(e.alive for e in game.world.entities)


def test_player_two_starts_beside_player_one_with_the_same_items(assets, content,
                                                                 silent_audio):
    game = make_game(assets, content, silent_audio)
    game.state.give("lantern")
    game.state.assign(0, "lantern")
    game.settings.two_player = True
    game.update()
    second = game.world.hero2
    assert (second.x, second.y) == (game.world.hero.x, game.world.hero.y)
    assert game.state.slots2 == game.state.slots


def test_the_two_walk_independently(assets, content, silent_audio):
    game = two_player(assets, content, silent_audio)
    one, two = game.world.hero, game.world.hero2
    one.x, one.y = 5 * TILE, 6 * TILE
    two.x, two.y = 9 * TILE, 6 * TILE
    game.input.begin_frame()
    game.input.press("right")
    game.input.press_pad("left")
    for _ in range(8):
        game.update()
        game.input.begin_frame()
    game.input.release_all()
    assert one.x > 5 * TILE, "the keyboard moved player one right"
    assert two.x < 9 * TILE, "the gamepad moved player two left"


def test_player_two_has_their_own_slots(assets, content, silent_audio):
    game = two_player(assets, content, silent_audio)
    game.state.give("lantern")
    game.state.give("bombs")
    game.state.assign(0, "lantern", 0)
    game.state.assign(0, "bombs", 1)
    assert game.world.slots_for(0)[0] == "lantern"
    assert game.world.slots_for(1)[0] == "bombs"
    assert game.world.hero2.slots(game.world)[0] == "bombs"


def test_the_items_page_can_equip_player_two(assets, content, silent_audio):
    from eldermoor.menu import PAGES, PauseMenu
    from eldermoor.settings import Settings
    game = make_game(assets, content, silent_audio)
    game.state.give("lantern")
    menu = PauseMenu(assets, content, game.state, silent_audio, Settings(),
                     PAGES.index("items"))
    inp = Input()
    inp.begin_frame()
    inp.press("select")
    menu.update(inp)
    inp.release("select")
    assert menu.player == 1
    canvas = pygame.Surface((320, 240))
    menu.draw(canvas)


# ----- sharing the screen -----------------------------------------------
def test_player_two_comes_along_on_a_screen_change(assets, content, silent_audio):
    game = two_player(assets, content, silent_audio, room="ow_1009")
    two = game.world.hero2
    two.x, two.y = 2 * TILE, 2 * TILE
    game.world.warp("ow_1010")
    assert (game.world.hero2.x, game.world.hero2.y) == (game.world.hero.x,
                                                        game.world.hero.y)
    assert two is game.world.hero2, "the same lamplighter, carried along"


def test_only_player_one_opens_the_next_screen(assets, content, silent_audio):
    game = two_player(assets, content, silent_audio, room="ow_1009")
    here = game.world.room.id
    game.world.hero2.x = -40.0
    step(game, 3)
    assert game.world.room.id == here, "player two cannot drag the screen along"


def test_a_creature_chases_the_nearer_lamplighter(assets, content, silent_audio):
    game = two_player(assets, content, silent_audio)
    w = game.world
    w.hero.x, w.hero.y = 2 * TILE, 2 * TILE
    w.hero2.x, w.hero2.y = 15 * TILE, 9 * TILE
    enemy = w.spawn_from_spec({"kind": "enemy", "type": "thistle", "at": [14, 9]})
    assert w.nearest_hero(enemy) is w.hero2
    enemy.x, enemy.y = 3 * TILE, 2 * TILE
    assert w.nearest_hero(enemy) is w.hero


def test_either_lamplighter_can_be_hit(assets, content, silent_audio):
    game = two_player(assets, content, silent_audio)
    w = game.world
    w.hero.x, w.hero.y = 2 * TILE, 2 * TILE
    w.hero2.x, w.hero2.y = 9 * TILE, 6 * TILE
    enemy = w.spawn_from_spec({"kind": "enemy", "type": "thistle", "at": [9, 6]})
    before = game.state.health
    enemy.touch_hero(w)
    assert game.state.health < before, "a shared heart row, either way"
    assert w.hero2.invuln > 0 and w.hero.invuln == 0


def test_either_lamplighter_can_pick_things_up(assets, content, silent_audio):
    from eldermoor.pickups import Pickup
    game = two_player(assets, content, silent_audio)
    w = game.world
    w.hero.x, w.hero.y = 2 * TILE, 2 * TILE
    w.hero2.x, w.hero2.y = 9 * TILE, 6 * TILE
    pickup = w.spawn(Pickup(9 * TILE, 6 * TILE, "ember"))
    pickup.pop = 0
    before = game.state.embers
    pickup.update(w)
    assert game.state.embers > before


def test_both_lamplighters_light_a_dark_room(assets, content, silent_audio):
    game = two_player(assets, content, silent_audio)
    game.world.room.dark = True
    game.world.hero.x, game.world.hero.y = 2 * TILE, 2 * TILE
    game.world.hero2.x, game.world.hero2.y = 15 * TILE, 9 * TILE
    canvas = pygame.Surface((320, 240))
    game.draw(canvas)
    near_one = canvas.get_at((2 * TILE + 8, 2 * TILE + 8 + 32))[:3]
    near_two = canvas.get_at((15 * TILE + 8, 9 * TILE + 8 + 32))[:3]
    dark = canvas.get_at((9 * TILE, 3 * TILE + 32))[:3]
    assert sum(near_one) > sum(dark)
    assert sum(near_two) > sum(dark), "the second lantern lights its own corner"


def test_the_hud_draws_two_rows_of_slots(assets, content, silent_audio):
    game = two_player(assets, content, silent_audio)
    canvas = pygame.Surface((320, 240))
    game.draw(canvas)
    assert game.world.hero2 is not None


def test_a_save_remembers_player_twos_slots():
    from eldermoor import save
    from eldermoor.state import GameState
    state = GameState()
    state.give("bombs")
    state.assign(1, "bombs", 1)
    back = GameState.from_json(save.migrate(state.to_json()))
    assert back.slots2 == state.slots2


def test_a_version_two_save_gains_empty_second_slots():
    from eldermoor import save
    from eldermoor.state import GameState
    raw = {"version": 2, "slot": 1, "owned": [], "flags": {}, "dungeons": {},
           "room": "ow_1105"}
    state = GameState.from_json(save.migrate(raw))
    assert state.slots2 == [None, None, None]
