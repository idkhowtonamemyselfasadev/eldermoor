"""Juice: the small things that make a hit feel like a hit.

Three of them live here. Sparks are a handful of bright pixels thrown out of
an impact. Hit-stop is a few frames where the whole room holds still, which
is what makes a sword connect rather than pass through. The fanfare is the
moment the item goes over Wren's head and everything else waits.
"""
from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from eldermoor.config import CANVAS_W, PLAY_H, PLAY_W
from eldermoor.entities import Entity

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.world import World

#: how long a spark lives
SPARK_FRAMES = 14
#: frames the room holds still on a solid hit
HIT_STOP = 3
#: how long the item stays over Wren's head
FANFARE_FRAMES = 54


class Spark(Entity):
    """One bright pixel thrown out of an impact and slowing down."""

    blocks_movement = False
    layer = 3
    width = height = 2

    def __init__(self, x: float, y: float, vx: float, vy: float, colour: str = "white") -> None:
        super().__init__(x, y)
        self.vx = vx
        self.vy = vy
        self.colour = colour
        self.timer = 0

    def update(self, world: World) -> None:
        """Fly, slow down, fade out."""
        self.timer += 1
        if self.timer >= SPARK_FRAMES:
            self.alive = False
            return
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.88
        self.vy *= 0.88

    def sprite_name(self) -> str | None:
        """Sparks are drawn as pixels, not sprites."""
        return None

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Two pixels, dimming as they go."""
        if (self.timer // 2) % 2 and self.timer > SPARK_FRAMES // 2:
            return
        size = 2 if self.timer < SPARK_FRAMES // 2 else 1
        target.fill(assets.colour(self.colour),
                    pygame.Rect(round(self.x), round(self.y) + oy, size, size))


def sparks(world: World, x: float, y: float, count: int = 6, colour: str = "white",
           speed: float = 2.2) -> None:
    """Throw a few sparks out of a point."""
    rng: random.Random = world.rng
    for _ in range(count):
        angle = rng.random() * math.tau
        push = speed * (0.5 + rng.random())
        world.spawn(Spark(x, y, math.cos(angle) * push, math.sin(angle) * push, colour))


def dust(world: World, x: float, y: float, count: int = 4) -> None:
    """A low puff of pale pixels, for boots and landings."""
    rng: random.Random = world.rng
    for _ in range(count):
        angle = math.pi + rng.random() * math.pi
        push = 1.0 + rng.random()
        world.spawn(Spark(x, y, math.cos(angle) * push, math.sin(angle) * push * 0.4, "mist"))


def hit_stop(world: World, frames: int = HIT_STOP) -> None:
    """Hold the room still for a few frames."""
    world.freeze = max(world.freeze, frames)


class Fanfare:
    """The item-held-up moment: the room waits, the item rises, a jingle plays."""

    def __init__(self, icon: str, name: str) -> None:
        self.icon = icon
        self.name = name
        self.frame = 0

    @property
    def done(self) -> bool:
        """True once it has had its moment."""
        return self.frame >= FANFARE_FRAMES

    def update(self) -> bool:
        """One frame; True when it is finished."""
        self.frame += 1
        return self.done

    def lift(self) -> int:
        """How far above the hero the item has risen."""
        t = min(1.0, self.frame / 12.0)
        return round(20 * t)

    def draw(self, target: pygame.Surface, assets: Assets, hero: Entity, oy: int = 0) -> None:
        """The item over the hero's head, and its name underneath."""
        if not assets.icons.has(self.icon):
            return
        cx, cy = hero.center
        x = max(4, min(PLAY_W - 12, round(cx) - 4))
        y = max(4, round(cy) - 12 - self.lift())
        glow = assets.colour("gold") if (self.frame // 4) % 2 else assets.colour("white")
        pygame.draw.circle(target, glow, (x + 4, y + 4 + oy), 7, 1)
        target.blit(assets.icons.get(self.icon), (x, y + oy))
        if self.frame > 10:
            label = self.name
            font = assets.font6
            width = font.measure(label)
            font.draw(target, label, (CANVAS_W - width) // 2,
                      min(PLAY_H - 12, round(cy) + 14) + oy, assets.colour("white"))
