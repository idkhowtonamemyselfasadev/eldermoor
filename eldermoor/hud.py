"""The 2-row HUD: hearts, embers, keys, and the B/X/Y item slots."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pygame

from eldermoor.config import CANVAS_W, HUD_H

if TYPE_CHECKING:
    from eldermoor.assets import Assets

MAX_HEARTS = 20
HEARTS_PER_ROW = 10
HEART_X = 8
HEART_Y = 5
HEART_STEP = 9
COUNTER_X = 104
SLOT_X = (202, 240, 278)
SLOT_Y = 7
SLOT_SIZE = 18
SLOT_LABELS = ("B", "X", "Y")


@dataclass
class PlayerState:
    """What the HUD shows. Health is counted in half-hearts."""

    max_hearts: int = 3
    health: int = 6
    embers: int = 0
    keys: int = 0
    items: list[str | None] = field(default_factory=lambda: [None, None, None])

    def heart_icons(self) -> list[str]:
        """Icon name per heart: heart_full / heart_half / heart_empty."""
        icons: list[str] = []
        for i in range(self.max_hearts):
            halves = max(0, min(2, self.health - 2 * i))
            icons.append(("heart_empty", "heart_half", "heart_full")[halves])
        return icons

    def damage(self, half_hearts: int) -> None:
        """Lose health, never below 0."""
        self.health = max(0, self.health - half_hearts)

    def heal(self, half_hearts: int) -> None:
        """Gain health, never above the maximum."""
        self.health = min(self.max_hearts * 2, self.health + half_hearts)


class Hud:
    """Draws the top two tile rows."""

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.bg = assets.colour("ink")
        self.line = assets.colour("slate")
        self.slot_fill = assets.colour("shadow")
        self.slot_edge = assets.colour("stone")
        self.text = assets.colour("white")
        self.label = assets.colour("mist")

    def draw(self, target: pygame.Surface, state: PlayerState) -> None:
        """Render the HUD onto the canvas at y = 0."""
        target.fill(self.bg, pygame.Rect(0, 0, CANVAS_W, HUD_H))
        pygame.draw.line(target, self.line, (0, HUD_H - 1), (CANVAS_W, HUD_H - 1))
        self._draw_hearts(target, state)
        self._draw_counters(target, state)
        self._draw_slots(target, state)

    def _draw_hearts(self, target: pygame.Surface, state: PlayerState) -> None:
        icons = self.assets.icons
        for i, name in enumerate(state.heart_icons()[:MAX_HEARTS]):
            x = HEART_X + (i % HEARTS_PER_ROW) * HEART_STEP
            y = HEART_Y + (i // HEARTS_PER_ROW) * 9
            target.blit(icons.get(name), (x, y))

    def _draw_counters(self, target: pygame.Surface, state: PlayerState) -> None:
        icons = self.assets.icons
        font = self.assets.font6
        target.blit(icons.get("ember"), (COUNTER_X, 4))
        font.draw(target, f"{state.embers:03d}", COUNTER_X + 10, 4, self.text)
        target.blit(icons.get("key"), (COUNTER_X, 16))
        font.draw(target, f"x{state.keys}", COUNTER_X + 10, 16, self.text)

    def _draw_slots(self, target: pygame.Surface, state: PlayerState) -> None:
        font = self.assets.font6
        icons = self.assets.icons
        for i, x in enumerate(SLOT_X):
            box = pygame.Rect(x, SLOT_Y, SLOT_SIZE, SLOT_SIZE)
            target.fill(self.slot_fill, box)
            pygame.draw.rect(target, self.slot_edge, box, 1)
            font.draw(target, SLOT_LABELS[i], x - 7, SLOT_Y + 5, self.label)
            item = state.items[i] if i < len(state.items) else None
            if item and icons.has(item):
                target.blit(icons.get(item), (x + 5, SLOT_Y + 5))
