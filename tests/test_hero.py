"""Wren: movement, facing, collision, sword swing timing."""
from __future__ import annotations

import math

from conftest import step, tap

from eldermoor.config import HERO_SPEED, SWING_TOTAL
from eldermoor.tilemap import Room


def test_hero_spawns_at_room_spawn(game):
    assert (game.world.hero.x, game.world.hero.y) == game.world.room.spawn
    assert game.world.hero.facing == "down"


def test_walks_in_8_directions_with_normalised_diagonals(game):
    h = game.world.hero
    x0, y0 = h.x, h.y
    game.input.press("right")
    step(game, 10)
    assert math.isclose(h.x - x0, HERO_SPEED * 10)
    assert h.facing == "right"
    game.input.press("down")
    step(game, 10)
    d = HERO_SPEED * math.sqrt(0.5) * 10
    assert math.isclose(h.x - x0, HERO_SPEED * 10 + d)
    assert math.isclose(h.y - y0, d)
    assert h.facing == "right", "diagonal keeps the existing facing"
    game.input.release_all()
    game.input.press("up")
    game.input.press("left")
    step(game, 1)
    assert h.facing == "left", "new diagonal with no shared axis prefers horizontal"


def test_walk_animation_cycles_and_idle_blinks(game):
    h = game.world.hero
    assert h.sprite_name() == "wren_down_1"
    game.input.press("down")
    names = set()
    for _ in range(30):
        step(game)
        names.add(h.sprite_name())
    assert names == {"wren_down_0", "wren_down_1", "wren_down_2"}
    game.input.release_all()
    step(game, 31)
    assert h.sprite_name() == "wren_down_idle"
    game.input.press("left")
    step(game)
    assert h.sprite_name().startswith("wren_side_") and h.flip


def test_solid_tiles_block(game):
    h = game.world.hero
    game.input.press("up")
    step(game, 400)
    assert h.body_rect().top >= 16, "stopped by the tree row"
    assert not game.world.room.blocked(h.body_rect())
    game.input.release_all()
    game.input.press("left")
    step(game, 400)
    assert h.body_rect().left >= 16


def test_axis_separated_collision_slides(game):
    h = game.world.hero
    game.input.press("up")
    game.input.press("left")
    step(game, 400)
    assert h.body_rect().top >= 16 and h.body_rect().left >= 16
    # sliding along the wall still made progress on the free axis
    assert h.x <= 16 + 2


def test_sword_swing_timing_and_hitbox(game):
    h = game.world.hero
    assert h.sword_hitbox() is None and h.sword_sprite() is None
    tap(game, "a")
    assert h.swinging and h.swing_frame == 0
    assert h.sprite_name() == "wren_swing_down_0"
    assert h.sword_hitbox() is None, "frame 0 is the wind-up"
    step(game, 4)
    assert h.swing_frame == 1 and h.sword_hitbox() is not None
    name, _x, _y, flip = h.sword_sprite()
    assert name == "sword_diag_dr" and not flip
    step(game, 4)
    assert h.swing_frame == 2
    assert h.sword_hitbox().top >= h.rect.bottom - 4
    step(game, SWING_TOTAL - 8)
    assert not h.swinging and h.sword_hitbox() is None


def test_cannot_move_or_reswing_while_swinging(game):
    h = game.world.hero
    x0 = h.x
    tap(game, "a")
    game.input.press("right")
    step(game, 3)
    assert h.x == x0
    tap(game, "a")
    assert h.swing_timer == 4, "second press ignored"


def test_left_swing_mirrors_right(game):
    h = game.world.hero
    game.input.press("left")
    step(game)
    game.input.release_all()
    tap(game, "a")
    step(game, 8)
    name, sx, _sy, flip = h.sword_sprite()
    assert name == "sword_h" and flip
    assert sx < h.x, "sword is on the left"
    assert h.sword_hitbox().right <= h.rect.left + 4


def test_room_blocked_treats_water_as_blocking(assets):
    room = Room.load("meadow_00")
    import pygame
    assert room.blocked(pygame.Rect(3 * 16, 8 * 16, 4, 4))
    assert not room.blocked(pygame.Rect(2 * 16, 2 * 16, 4, 4))
