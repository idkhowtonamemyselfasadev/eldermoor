"""The 12-frame flip-scroll between overworld screens."""
from __future__ import annotations

import pygame

from eldermoor.config import FLIP_SCROLL_FRAMES, PLAY_H, PLAY_W, PLAY_Y


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
