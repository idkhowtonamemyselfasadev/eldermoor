"""What the hero's buttons actually do: talking, opening, cutting, burning, swinging."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import TILE
from eldermoor.enemies import Thrown
from eldermoor.entities import DIRS
from eldermoor.gadgets import fire_hookshot, place_bomb
from eldermoor.objects import PushBlock, Torch
from eldermoor.ranged import shoot_arrow
from eldermoor.tilemap import Collision

if TYPE_CHECKING:
    from eldermoor.hero import Hero
    from eldermoor.world import World

LANTERN_FRAMES = 26


# ----- hero actions ---------------------------------------------------
def lift_tile(world: World, hero: Hero) -> bool:
    """With the Power Bracelet, pick up the rock or pot the hero is facing."""
    if hero.carrying is not None or not world.state.has("bracelet"):
        return False
    front = hero.front_rect()
    for col, row in world.room.cells(front):
        tile = world.room.tile_at(col, row)
        if tile is None or tile.interact not in ("lift", "cut"):
            continue
        if tile.collision not in (Collision.LIFTABLE, Collision.SOLID):
            continue
        world.set_tile(col, row, tile.becomes or ".")
        hero.carrying = tile.sprite
        hero.carry_drop = tile.drop or "rock"
        world.audio.play("lift")
        return True
    return False


def throw_carried(world: World, hero: Hero) -> None:
    """Throw whatever the hero is holding in the direction he faces."""
    if hero.carrying is None:
        return
    dx, dy = DIRS[hero.facing]
    shot = Thrown(hero.x + dx * 8, hero.y + dy * 8, dx * 2.6, dy * 2.6,
                  hero.carrying, hero.carry_drop)
    hero.carrying = None
    hero.carry_drop = ""
    world.audio.play("throw")
    world.spawn(shot)


def try_interact(world: World, hero: Hero) -> bool:
    """A press in front of the hero: talk, read, open, unlock, push or lift."""
    front = hero.front_rect()
    for ent in world.entities:
        if ent is hero or not ent.alive:
            continue
        if ent.body_rect().colliderect(front):
            if isinstance(ent, PushBlock):
                if ent.heavy and not world.state.has("gauntlet"):
                    world.audio.play("error")
                    return True
                dx, dy = DIRS[hero.facing]
                return ent.push(world, dx, dy)
            if ent.interact(world):
                return True
    return lift_tile(world, hero)


def use_item(world: World, hero: Hero, item: str | None) -> None:
    """Use whatever is in a B/X/Y slot."""
    if item is None or not world.state.has(item):
        return
    if item == "lantern":
        _use_lantern(world, hero)
    elif item == "bombs":
        place_bomb(world, hero)
    elif item == "hookshot":
        fire_hookshot(world, hero)
    elif item == "bow":
        shoot_arrow(world, hero)
    elif item == "mirror_cloak":
        pass                       # the cloak works while its button is held
    elif item == "whistle":
        world.blow_whistle()
    elif item == "fire_boots":
        _melt_ice(world, hero)
    elif item == "feather":
        hero.hop()
        world.audio.play("jump")
    elif item.startswith("bottle"):
        _use_bottle(world, item)
    else:
        world.audio.play("error")
    world.trigger("item_used", item)


def _use_lantern(world: World, hero: Hero) -> None:
    if hero.lantern_timer > 0:
        return
    hero.lantern_timer = LANTERN_FRAMES
    world.audio.play("burn")
    front = hero.front_rect()
    world.hit_tiles(front, "burn")
    for ent in world.entities:
        if isinstance(ent, Torch) and ent.body_rect().colliderect(front):
            ent.light(world)


def _melt_ice(world: World, hero: Hero) -> None:
    """The Cinderstep Boots take the ice out of a doorway."""
    if world.hit_tiles(hero.front_rect(), "melt"):
        world.audio.play("burn")


def _use_bottle(world: World, item: str) -> None:
    content = world.state.flag(f"bottle:{item}")
    if not content:
        world.audio.play("error")
        return
    world.state.set_flag(f"bottle:{item}", 0)
    world.state.heal(99)
    world.audio.play("fairy")


def sword_hit(world: World, hero: Hero, rect: pygame.Rect) -> None:
    """Apply a sword rect to enemies, crystals and cuttable tiles."""
    world.hit_tiles(rect, "cut")
    for ent in list(world.entities):
        if ent is hero or not ent.alive or ent.team != "enemy":
            continue
        if id(ent) in hero.hit_this_swing:
            continue
        if ent.body_rect().colliderect(rect):
            hero.hit_this_swing.add(id(ent))
            ent.take_damage(world,
                            max(1, world.state.sword_level) + world.ring_bonus.damage,
                            hero)


def hit_tiles(world: World, rect: pygame.Rect, kind: str) -> int:
    """Clear every tile under ``rect`` that this tool removes. Returns the count."""
    cleared = 0
    for col, row, td in world.room.interactive_cells(rect, kind):
        world.set_tile(col, row, td.becomes or ".")
        world.audio.play({"cut": "cut", "burn": "burn", "smash": "smash"}.get(kind, "cut"))
        if td.drop:
            world.drop_from(col * TILE, row * TILE, td.drop)
        cleared += 1
        world.trigger("tile_cleared", td.sprite)
    return cleared
