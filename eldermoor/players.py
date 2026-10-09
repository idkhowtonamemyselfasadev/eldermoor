"""Two lamplighters: who is on screen, who a creature is thinking about.

One-player games have one hero and these questions have obvious answers.
Two-player games have a second hero who drops in beside the first, carries
their own three item slots, and is carried along on every screen change.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.hero import Hero

if TYPE_CHECKING:
    from eldermoor.entities import Entity
    from eldermoor.world import World


def nearest(world: World, ent: Entity) -> Hero:
    """Whichever lamplighter this creature should be thinking about."""
    heroes = world.heroes
    if len(heroes) < 2:
        return world.hero
    ax, ay = ent.center
    return min(heroes, key=lambda h: (h.center[0] - ax) ** 2 + (h.center[1] - ay) ** 2)


def touching(world: World, rect: pygame.Rect) -> Hero | None:
    """The first lamplighter a rect overlaps, if any."""
    for hero in world.heroes:
        if rect.colliderect(hero.body_rect()):
            return hero
    return None


def join(world: World) -> Hero:
    """Drop the second lamplighter in beside the first.

    They start with a copy of player one's item slots, because the first
    thing a second player wants is a sword, not a menu.
    """
    if world.hero2 is None:
        second = Hero(world.hero.x, world.hero.y)
        second.player = 1
        second.facing = world.hero.facing
        world.hero2 = second
        if not any(world.state.slots2):
            world.state.slots2 = list(world.state.slots)
        world.spawn(second)
        world.audio.play("item_get")
    return world.hero2


def drop(world: World) -> None:
    """Take the second lamplighter back out of the game."""
    if world.hero2 is not None:
        world.hero2.alive = False
        world.entities = [e for e in world.entities if e is not world.hero2]
        world.hero2 = None
