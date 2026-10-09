"""The flip-scroll between screens, and the geometry of walking off an edge."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import (
    FLIP_SCROLL_FRAMES,
    PLAY_COLS,
    PLAY_H,
    PLAY_ROWS,
    PLAY_W,
    PLAY_Y,
    TILE,
)
from eldermoor.tilemap import BLOCKING

#: how far past an edge the hero walks before the screen flips
EDGE_MARGIN = 6

if TYPE_CHECKING:
    from eldermoor.world import World


class FlipScroll:
    """The old room slides out while the new one slides in; logic pauses meanwhile."""

    def __init__(self, direction: str, old: pygame.Surface, new: pygame.Surface,
                 frames: int = FLIP_SCROLL_FRAMES) -> None:
        self.direction = direction
        self.old = old
        self.new = new
        self.frames = frames
        self.frame = 0

    @property
    def done(self) -> bool:
        """True once the scroll has run its full length."""
        return self.frame >= self.frames

    def update(self) -> None:
        """Advance one frame."""
        self.frame += 1

    def draw(self, target: pygame.Surface, oy: int = PLAY_Y) -> None:
        """Blit both rooms at their interpolated positions."""
        t = min(self.frame, self.frames) / self.frames
        if self.direction in ("east", "west"):
            sign = -1 if self.direction == "east" else 1
            dx = sign * round(PLAY_W * t)
            target.blit(self.old, (dx, oy))
            target.blit(self.new, (dx - sign * PLAY_W, oy))
        else:
            sign = -1 if self.direction == "south" else 1
            dy = sign * round(PLAY_H * t)
            target.blit(self.old, (0, oy + dy))
            target.blit(self.new, (0, oy + dy - sign * PLAY_H))


# ----- walking off an edge -----------------------------------------------
def exit_direction(world: World) -> str | None:
    """Which edge the hero has walked past, if any."""
    hero = world.hero
    cx = hero.x + hero.width / 2
    cy = hero.y + hero.height / 2
    if cx < -EDGE_MARGIN + 8:
        return "west"
    if cx > PLAY_W + EDGE_MARGIN - 8:
        return "east"
    if cy < -EDGE_MARGIN + 8:
        return "north"
    if cy > PLAY_H + EDGE_MARGIN - 8:
        return "south"
    return None


def entry_position(world: World, direction: str) -> tuple[float, float]:
    """Where the hero stands on arriving through a given exit."""
    h = world.hero
    if direction == "east":
        return 0.0, h.y
    if direction == "west":
        return float(PLAY_W - h.width), h.y
    if direction == "south":
        return h.x, 0.0
    return h.x, float(PLAY_H - h.height)


def snap_into_doorway(world: World, side: str) -> None:
    """Line the hero up with the doorway he just stepped through.

    Neighbouring screens do not always put their gap in the same column, so
    arriving with the old x can drop Wren inside a cliff. Slide him to the
    nearest opening on the edge he came in through.
    """
    hero = world.hero
    if side in ("north", "south"):
        row = 0 if side == "south" else PLAY_ROWS - 1
        cols = [c for c in range(PLAY_COLS)
                if world.room.collision_at(c, row) not in BLOCKING]
        if not cols:
            return
        centre = (hero.x + hero.width / 2) / TILE - 0.5
        col = min(cols, key=lambda c: abs(c - centre))
        hero.x = float(col * TILE + (TILE - hero.width) // 2)
    elif side in ("east", "west"):
        col = 0 if side == "east" else PLAY_COLS - 1
        rows = [r for r in range(PLAY_ROWS)
                if world.room.collision_at(col, r) not in BLOCKING]
        if not rows:
            return
        centre = (hero.y + hero.height / 2) / TILE - 0.5
        row = min(rows, key=lambda r: abs(r - centre))
        hero.y = float(row * TILE + (TILE - hero.height) // 2)
    world.last_safe = (hero.x, hero.y)
