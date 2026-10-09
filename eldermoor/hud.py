"""The 2-row HUD: hearts, embers, small keys, the big key and the B/X/Y item slots."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import CANVAS_W, HUD_H
from eldermoor.state import GameState

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.items import ItemRegistry

#: milestone-1 name, kept so older code and tests can keep using it
PlayerState = GameState

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
BEEP_PERIOD = 45


class Hud:
    """Draws the top two tile rows."""

    def __init__(self, assets: Assets, items: ItemRegistry | None = None) -> None:
        self.assets = assets
        self.items = items
        self.bg = assets.colour("ink")
        self.line = assets.colour("slate")
        self.slot_fill = assets.colour("shadow")
        self.slot_edge = assets.colour("stone")
        self.text = assets.colour("white")
        self.label = assets.colour("mist")
        self.beep_timer = 0

    def icon_for(self, item: str | None) -> str:
        """Icon block name for a slot's item."""
        if self.items is not None:
            return self.items.icon(item)
        return item or "icon_empty"

    def tick(self, state: GameState, audio: object | None = None, enabled: bool = True) -> None:
        """Run the low-health beep. Called once per logic frame."""
        if not enabled or not state.low_health:
            self.beep_timer = 0
            return
        self.beep_timer += 1
        if self.beep_timer >= BEEP_PERIOD:
            self.beep_timer = 0
            if audio is not None:
                audio.play("low_health")           # type: ignore[attr-defined]

    def draw(self, target: pygame.Surface, state: GameState) -> None:
        """Render the HUD onto the canvas at y = 0."""
        target.fill(self.bg, pygame.Rect(0, 0, CANVAS_W, HUD_H))
        pygame.draw.line(target, self.line, (0, HUD_H - 1), (CANVAS_W, HUD_H - 1))
        self._draw_hearts(target, state)
        self._draw_counters(target, state)
        self._draw_slots(target, state)

    def _draw_hearts(self, target: pygame.Surface, state: GameState) -> None:
        icons = self.assets.icons
        for i, name in enumerate(state.heart_icons()[:MAX_HEARTS]):
            x = HEART_X + (i % HEARTS_PER_ROW) * HEART_STEP
            y = HEART_Y + (i // HEARTS_PER_ROW) * 9
            target.blit(icons.get(name), (x, y))

    def _draw_counters(self, target: pygame.Surface, state: GameState) -> None:
        icons = self.assets.icons
        font = self.assets.font6
        target.blit(icons.get("ember"), (COUNTER_X, 4))
        font.draw(target, f"{state.embers:03d}", COUNTER_X + 10, 4, self.text)
        target.blit(icons.get("key"), (COUNTER_X, 16))
        font.draw(target, f"x{state.keys}", COUNTER_X + 10, 16, self.text)
        progress = state.dungeons.get(state.dungeon) if state.dungeon else None
        if progress is not None and progress.big_key:
            target.blit(icons.get("icon_bigkey"), (COUNTER_X + 34, 16))
        x = COUNTER_X + 52
        for owned, icon, count in ((state.max_bombs, "icon_bomb", state.bombs),
                                   (state.max_arrows, "icon_bow", state.arrows)):
            if not owned:
                continue
            target.blit(icons.get(icon), (x, 4))
            font.draw(target, f"{count:02d}", x + 9, 4, self.text)
            x += 26

    def _draw_slots(self, target: pygame.Surface, state: GameState) -> None:
        font = self.assets.font6
        icons = self.assets.icons
        for i, x in enumerate(SLOT_X):
            box = pygame.Rect(x, SLOT_Y, SLOT_SIZE, SLOT_SIZE)
            target.fill(self.slot_fill, box)
            pygame.draw.rect(target, self.slot_edge, box, 1)
            font.draw(target, SLOT_LABELS[i], x - 7, SLOT_Y + 5, self.label)
            name = self.icon_for(state.slots[i] if i < len(state.slots) else None)
            if icons.has(name):
                target.blit(icons.get(name), (x + 5, SLOT_Y + 5))
