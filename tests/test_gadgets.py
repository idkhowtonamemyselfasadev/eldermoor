"""The Power Bracelet, Bombs, the Hookshot and the Bow."""
from __future__ import annotations

import pygame
from conftest import run_until, step, tap

from eldermoor.gadgets import Bomb, Hookshot, fire_hookshot, place_bomb
from eldermoor.ranged import Arrow, shoot_arrow
from eldermoor.tilemap import Room


def face_tile(game, col: int, row: int, facing: str = "up") -> None:
    """Stand next to a tile and look at it."""
    hero = game.world.hero
    offsets = {"up": (0, 1), "down": (0, -1), "left": (1, 0), "right": (-1, 0)}
    dc, dr = offsets[facing]
    hero.x = float((col + dc) * 16)
    hero.y = float((row + dr) * 16)
    hero.facing = facing
    step(game)


def first_tile(room: Room, interact: str) -> tuple[int, int]:
    """The first cell in a room whose tile answers to a given tool."""
    for r in range(13):
        for c in range(20):
            tile = room.tile_at(c, r)
            if tile is not None and tile.interact == interact:
                return c, r
    raise AssertionError(f"no {interact} tile in {room.id}")


# ----- Power Bracelet ---------------------------------------------------
def test_bracelet_lifts_and_throws_a_boulder(game):
    game.state.give("bracelet")
    game.world.warp("t2_f1_0203")               # the rockfall
    col, row = first_tile(game.world.room, "lift")
    face_tile(game, col, row)
    tap(game, "a")
    step(game)
    hero = game.world.hero
    assert hero.carrying == "rock"
    assert game.world.room.tile_at(col, row).interact != "lift", "the boulder came up"
    tap(game, "a")
    step(game)
    assert hero.carrying is None
    from eldermoor.enemies import Thrown
    assert any(isinstance(e, Thrown) for e in game.world.entities)


def test_no_bracelet_means_no_lifting(game):
    game.world.warp("t2_f1_0203")
    col, row = first_tile(game.world.room, "lift")
    face_tile(game, col, row)
    tap(game, "a")
    step(game)
    assert game.world.hero.carrying is None


def test_thrown_rock_stuns_a_guarded_boss(game, content):
    import random

    from eldermoor.bosses import Boss
    from eldermoor.enemies import Thrown
    boss = Boss(content.enemies["hollowking"], 120.0, 80.0, random.Random(1))
    boss.intro = 0
    boss.brain.state = "shut"
    game.world.spawn(boss)
    assert not boss.vulnerable
    rock = Thrown(boss.x - 10, boss.y + 16, 2.0, 0.0, "rock")
    game.world.spawn(rock)
    assert run_until(game, lambda: boss.brain.state == "stunned", 40)
    assert boss.vulnerable


# ----- Bombs -------------------------------------------------------------
def test_bomb_opens_a_cracked_wall(game):
    game.state.give("bombs")
    game.state.max_bombs = game.state.bombs = 5
    game.world.warp("t3_f1_0400")               # the powder store's back wall
    col, row = first_tile(game.world.room, "bomb")
    hero = game.world.hero
    hero.x, hero.y = float(col * 16), float((row + 1) * 16)
    hero.facing = "up"
    step(game)
    assert place_bomb(game.world, hero)
    assert game.state.bombs == 4
    bomb = next(e for e in game.world.entities if isinstance(e, Bomb))
    hero.x, hero.y = 32.0, 32.0                 # stand well clear
    assert run_until(game, lambda: not bomb.alive, 200)
    assert game.world.room.tile_at(col, row).interact != "bomb", "the wall came down"


def test_bomb_needs_one_in_the_bag(game):
    game.state.give("bombs")
    game.state.bombs = 0
    assert not place_bomb(game.world, game.world.hero)


def test_bomb_hurts_the_hero_too(game, content):
    import random

    from eldermoor.enemies import Enemy
    hero = game.world.hero
    hero.x, hero.y = 150.0, 100.0
    enemy = Enemy(content.enemies["mote"], 150.0, 116.0, random.Random(2))
    enemy.hp = 9
    game.world.spawn(enemy)
    bomb = Bomb(hero.x, hero.y + 8, fuse=1)
    game.world.spawn(bomb)
    health = game.state.health
    step(game, 3)
    assert game.state.health < health and enemy.hp < 9


# ----- Hookshot ----------------------------------------------------------
def test_hookshot_pulls_the_hero_to_a_pillar(game):
    game.state.give("hookshot")
    game.world.warp("t3_f1_0203")               # the washed-out floor
    room = game.world.room
    anchor = next(((c, r) for r in range(13) for c in range(20)
                   if (t := room.tile_at(c, r)) and t.hook), None)
    assert anchor is not None, "the room has a pillar to grab"
    hero = game.world.hero
    hero.x = float((anchor[0] - 4) * 16)
    hero.y = float(anchor[1] * 16)
    hero.facing = "right"
    step(game)
    start_x = hero.x
    assert fire_hookshot(game.world, hero)
    assert hero.hooking and any(isinstance(e, Hookshot) for e in game.world.entities)
    assert run_until(game, lambda: not hero.hooking, 200)
    assert hero.x > start_x, "the chain dragged him over"


def test_hookshot_comes_back_from_a_bare_wall(game):
    game.state.give("hookshot")
    hero = game.world.hero
    hero.facing = "down"
    fire_hookshot(game.world, hero)
    assert run_until(game, lambda: not hero.hooking, 200)
    assert not any(isinstance(e, Hookshot) for e in game.world.entities)


# ----- Bow ---------------------------------------------------------------
def test_arrow_spends_one_and_kills(game, content):
    import random

    from eldermoor.enemies import Enemy
    game.world.give_item("bow")
    game.world.dialogue = None                 # the "you got it" box would pause the world
    assert game.state.arrows == 30 and game.state.max_arrows == 30
    hero = game.world.hero
    hero.x, hero.y = 100.0, 100.0
    hero.facing = "right"
    enemy = Enemy(content.enemies["mote"], 150.0, 100.0, random.Random(3))
    enemy.hp = 2
    game.world.spawn(enemy)
    assert shoot_arrow(game.world, hero)
    assert game.state.arrows == 29
    assert run_until(game, lambda: not enemy.alive, 120)


def test_empty_quiver_refuses(game):
    game.state.give("bow")
    game.state.arrows = 0
    assert not shoot_arrow(game.world, game.world.hero)


def test_arrow_flips_a_crystal(game):
    from eldermoor.objects import Crystal
    crystal = Crystal(game.world, {"kind": "crystal", "at": [10, 6], "id": "x"})
    game.world.spawn(crystal)
    before = crystal.red
    hero = game.world.hero
    hero.x, hero.y = 80.0, 96.0
    arrow = Arrow(hero.x, hero.y, "right")
    game.world.spawn(arrow)
    assert run_until(game, lambda: crystal.red != before, 120)


def test_hud_shows_bombs_and_arrows(game, assets):
    game.world.give_item("bombs")
    game.world.give_item("bow")
    game.world.dialogue = None
    canvas = pygame.Surface((320, 240))
    game.draw(canvas)
    strip = {canvas.get_at((x, y))[:3] for x in range(150, 200) for y in range(2, 14)}
    assert assets.colour("white") in strip, "the counters are on the HUD"
