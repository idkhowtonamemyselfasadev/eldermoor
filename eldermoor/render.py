"""Painting the play area: the room, its entities, the dark and the shake."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import PLAY_H, PLAY_W, PLAY_Y
from eldermoor.objects import Torch

if TYPE_CHECKING:
    from eldermoor.world import World


# ----- drawing --------------------------------------------------------
def shake_offset(world: World) -> tuple[int, int]:
    """Screen-shake offset for this frame."""
    if world.shake_timer <= 0:
        return 0, 0
    return (world.shake_timer % 3) - 1, (world.shake_timer % 2)


def draw_world(world: World, target: pygame.Surface, oy: int = PLAY_Y) -> None:
    """Draw the play area at vertical offset ``oy``."""
    if world.transition is not None:
        world.transition.draw(target, oy)
        return
    sx, sy = shake_offset(world)
    target.blit(world.room_surface(), (sx, oy + sy))
    for ent in sorted(world.entities, key=lambda e: (e.depth, e.layer)):
        ent.draw(target, world.assets, oy + sy)
    if world.room.dark:
        draw_darkness(world, target, oy + sy)
    if world.boss is not None and world.boss.alive:
        world.boss.draw_bar(target, world.assets, world.textdb.get(world.boss.name_key))
    if world.dialogue is not None:
        world.dialogue.draw(target, world.assets)


def draw_darkness(world: World, target: pygame.Surface, oy: int) -> None:
    """A dark room: black except a circle around Wren, wider with the Lantern lit.

    Lighting the room's torch clears it for good, which is what the
    Lantern is for.
    """
    if any(isinstance(e, Torch) and e.lit for e in world.entities):
        return
    radius = 30
    if world.state.has("lantern"):
        radius = 76 if world.hero.lantern_timer > 0 else 62
    shade = pygame.Surface((PLAY_W, PLAY_H), pygame.SRCALPHA)
    shade.fill((2, 2, 8, 248))
    cx, cy = world.hero.center
    for i in range(6):
        r = radius - i * radius // 7
        alpha = 248 - round(248 * (1.0 - i / 6.0) ** 0.6)
        pygame.draw.circle(shade, (2, 2, 8, alpha), (round(cx), round(cy)), r)
    target.blit(shade, (0, oy))
