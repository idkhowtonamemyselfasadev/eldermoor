"""F1 debug overlay: engine stats, hitboxes, god mode, warp and give-item."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import PLAY_Y
from eldermoor.tilemap import list_rooms

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.game import Game

#: items the give-item command cycles through
GIVE_CYCLE = ("sword", "shield", "lantern", "feather", "key", "bigkey", "map", "compass")


class DebugOverlay:
    """Shows engine stats over the play area. Toggle with the 'debug' action (F1)."""

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.enabled = False
        self.fps = 0.0
        self.show_hitboxes = True
        self.god = False
        self.give_index = 0
        self.warp_index = 0

    def toggle(self) -> None:
        """Flip visibility."""
        self.enabled = not self.enabled

    # ----- commands ------------------------------------------------------
    def handle_key(self, game: Game, key: int) -> bool:
        """Keyboard commands that only work while the overlay is up."""
        if not self.enabled:
            return False
        if key == pygame.K_g:
            self.god = not self.god
            return True
        if key == pygame.K_i:
            item = GIVE_CYCLE[self.give_index % len(GIVE_CYCLE)]
            self.give_index += 1
            game.world.grant(item)
            return True
        if key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            rooms = list_rooms()
            self.warp_index = (self.warp_index + (1 if key == pygame.K_RIGHTBRACKET else -1)) \
                % max(1, len(rooms))
            game.world.warp(rooms[self.warp_index])
            return True
        if key == pygame.K_h:
            self.show_hitboxes = not self.show_hitboxes
            return True
        return False

    # ----- drawing -------------------------------------------------------
    def lines(self, game: Game) -> list[str]:
        """The text lines shown in the overlay."""
        w = game.world
        h = w.hero
        trans = f"{w.transition.direction} {w.transition.frame}/{w.transition.frames}" \
            if w.transition else "-"
        return [
            f"fps {self.fps:5.1f}  frame {game.frame}  mode {game.mode}",
            f"room {w.room.id} ({w.room.name}) dng {w.room.dungeon or '-'}",
            f"hero {h.x:6.1f},{h.y:6.1f} {h.facing} {h.sprite_name()}",
            f"entities {len(w.entities)}  scroll {trans}  god {int(self.god)}",
            f"input {game.input.last_device}  pads {len(game.input.controllers)}",
            f"hp {game.state.health}/{game.state.max_hearts * 2}  embers {game.state.embers}"
            f"  keys {game.state.keys}",
            f"flags {len(game.state.flags)}  items {len(game.state.owned)}"
            f"  {game.state.completion():.1f}%",
            "g god  i give  h boxes  [ ] warp",
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
            colour = "cyan" if e.team != "enemy" else "pink"
            pygame.draw.rect(target, self.assets.colour(colour),
                             e.body_rect().move(0, PLAY_Y), 1)
        hb = w.hero.sword_hitbox()
        if hb:
            pygame.draw.rect(target, self.assets.colour("red"), hb.move(0, PLAY_Y), 1)
