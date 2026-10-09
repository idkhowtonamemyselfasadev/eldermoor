"""Bosses and mini-bosses: phases, a readable weakness, an intro and a health bar."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from eldermoor.config import PLAY_W
from eldermoor.enemies import Enemy, EnemyDef

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.world import World

INTRO_FRAMES = 90
BAR_X = 60
BAR_W = PLAY_W - 2 * BAR_X
BAR_Y = 6


class Boss(Enemy):
    """An enemy with phases, a named health bar and a vulnerability window.

    ``weak_states`` lists the state-machine states in which the boss can be
    hurt at all; everything else bounces off.  The temple item is what puts
    the boss into one of those states, which is how PROMPT.md 4.5 asks for
    bosses to be beaten.
    """

    def __init__(self, definition: EnemyDef, x: float, y: float, rng: Any = None) -> None:
        super().__init__(definition, x, y, rng)
        raw = definition.raw
        self.phases: list[dict[str, Any]] = list(raw.get("phases", []))
        self.weak_states = set(raw.get("weak_states", []))
        self.max_hp = self.hp
        self.phase = 0
        self.intro = INTRO_FRAMES
        self.name_key = str(raw.get("name", f"boss.{definition.id}"))
        self.reward = str(raw.get("reward", ""))
        self.mini = bool(raw.get("mini", False))

    # ----- frame ---------------------------------------------------------
    def update(self, world: World) -> None:
        """Hold still through the intro, then behave like an enemy with phases."""
        if self.intro > 0:
            self.intro -= 1
            self.frame += 1
            if self.intro == INTRO_FRAMES - 1:
                world.audio.play("boss_roar")
            return
        super().update(world)
        self._check_phase(world)

    def _check_phase(self, world: World) -> None:
        while self.phase < len(self.phases):
            threshold = int(self.phases[self.phase].get("below", 0))
            if self.hp > threshold:
                return
            entry = self.phases[self.phase]
            self.phase += 1
            self.speed *= float(entry.get("speed_mul", 1.0))
            if entry.get("start"):
                self.brain.go(self, str(entry["start"]))
            if entry.get("weak_states"):
                self.weak_states = set(entry["weak_states"])
            world.audio.play("boss_roar")

    # ----- damage --------------------------------------------------------
    @property
    def vulnerable(self) -> bool:
        """True only while the boss is in one of its weak states."""
        return not self.weak_states or self.brain.state in self.weak_states

    def stun(self, world: World, state: str = "stunned") -> None:
        """Put the boss into its vulnerable state (the temple item does this)."""
        self.brain.go(self, state)
        world.audio.play("puzzle")

    def take_damage(self, world: World, amount: int, source: Any = None) -> bool:
        """Only hurt while vulnerable."""
        if not self.vulnerable:
            world.audio.play("block")
            return False
        world.audio.play("boss_hit")
        self.hp -= amount
        self.flash = 12
        if self.hp <= 0:
            self.die(world)
            return True
        return False

    def die(self, world: World) -> None:
        """Explode, hand over the reward and tell the room."""
        self.alive = False
        world.audio.play("boss_die")
        world.state.set_flag(f"seen:{self.definition.id}", 1)
        world.state.record_kill(self.definition.id)
        world.boss_defeated(self)

    # ----- drawing -------------------------------------------------------
    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Blit the boss, flashing white while hurt and shaking during the intro."""
        surf = assets.sprites.get(self.sprite_name(), self.flip)
        if self.flash > 0 and (self.flash // 2) % 2 == 0:
            surf = surf.copy()
            surf.fill((200, 200, 200), special_flags=pygame.BLEND_RGB_ADD)
        shake = 0
        if self.intro > 0:
            shake = (self.intro % 4) - 2
        target.blit(surf, (round(self.x) + shake, round(self.y) + oy - self.hop))

    def draw_bar(self, target: pygame.Surface, assets: Assets, name: str) -> None:
        """The boss health bar with its name, drawn over the play area."""
        frame = pygame.Rect(BAR_X - 1, BAR_Y - 1, BAR_W + 2, 8)
        target.fill(assets.colour("ink"), frame)
        pygame.draw.rect(target, assets.colour("bone"), frame, 1)
        fill = max(0, round(BAR_W * self.hp / max(1, self.max_hp)))
        target.fill(assets.colour("red"), pygame.Rect(BAR_X, BAR_Y, fill, 6))
        assets.font6.draw(target, name, BAR_X, BAR_Y + 9, assets.colour("white"),
                          outline=assets.colour("ink"))
