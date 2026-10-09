"""F1 debug overlay."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import PLAY_Y

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.game import Game


class DebugOverlay:
    """Shows engine stats over the play area. Toggle with the 'debug' action (F1)."""

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.enabled = False
        self.fps = 0.0
        self.show_hitboxes = True

    def toggle(self) -> None:
        """Flip visibility."""
        self.enabled = not self.enabled

    def lines(self, game: Game) -> list[str]:
        """The text lines shown in the overlay."""
        w = game.world
        h = w.hero
        trans = f"{w.transition.direction} {w.transition.frame}/{w.transition.frames}" \
            if w.transition else "-"
        return [
            f"fps {self.fps:5.1f}  frame {game.frame}",
            f"room {w.room.id} ({w.room.name})",
            f"hero {h.x:6.1f},{h.y:6.1f} {h.facing} {h.sprite_name()}",
            f"entities {len(w.entities)}  scroll {trans}",
            f"input {game.input.last_device}  pads {len(game.input.controllers)}",
            f"hp {game.state.health}/{game.state.max_hearts * 2}  embers {game.state.embers}",
        ]

    def draw(self, target: pygame.Surface, game: Game) -> None:
        """Draw the overlay if enabled."""
        if not self.enabled:
            return
        font = self.assets.font6
        lines = self.lines(game)
        box = pygame.Surface((max(font.measure(ln) for ln in lines) + 4, len(lines) * 9 + 3),
                             pygame.SRCALPHA)
        box.fill((0, 0, 0, 160))
        target.blit(box, (2, PLAY_Y + 2))
        font.draw_lines(target, lines, 4, PLAY_Y + 4, self.assets.colour("lime"),
                        outline=self.assets.colour("ink"), spacing=1)
        if self.show_hitboxes:
            self._draw_hitboxes(target, game)

    def _draw_hitboxes(self, target: pygame.Surface, game: Game) -> None:
        w = game.world
        if w.transition:
            return
        for e in w.entities:
            r = e.body_rect().move(0, PLAY_Y)
            pygame.draw.rect(target, self.assets.colour("cyan"), r, 1)
        hb = w.hero.sword_hitbox()
        if hb:
            pygame.draw.rect(target, self.assets.colour("red"), hb.move(0, PLAY_Y), 1)
