"""Collectibles that fall out of grass, pots and enemies, and the hero's reaction to them."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from eldermoor.drops import PICKUPS
from eldermoor.entities import Entity

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.world import World

LIFETIME = 480           # 8 seconds before it fades
BLINK_FROM = 120         # start blinking this many frames before the end
POP_FRAMES = 14
#: how much each pickup kind is worth
VALUES: dict[str, tuple[str, int]] = {
    "heart": ("health", 2),
    "ember": ("embers", 1),
    "ember5": ("embers", 5),
    "ember20": ("embers", 20),
    "bomb": ("bombs", 3),
    "arrow": ("arrows", 5),
    "magic": ("magic", 8),
    "fairy": ("health", 12),
    "key": ("keys", 1),
    "shell": ("seashells", 1),
}


class Pickup(Entity):
    """A heart, ember, key or fairy lying on the floor. Collected by touching it."""

    body = pygame.Rect(3, 3, 10, 10)
    layer = -1

    def __init__(self, x: float, y: float, kind: str) -> None:
        super().__init__(x, y)
        self.kind = kind
        self.timer = 0
        self.pop = POP_FRAMES
        self.base_y = float(y)

    def update(self, world: World) -> None:
        """Hop out of whatever dropped it, then wait to be picked up."""
        self.timer += 1
        if self.pop > 0:
            self.pop -= 1
        if self.kind == "fairy":
            self.x += math.sin(self.timer / 14.0) * 0.6
            self.y = self.base_y + math.sin(self.timer / 9.0) * 3.0
        if self.timer >= LIFETIME:
            self.alive = False
            return
        if self.body_rect().colliderect(world.hero.body_rect()):
            self.collect(world)

    def collect(self, world: World) -> None:
        """Apply the pickup to the player's state."""
        self.alive = False
        _sprite, sound = PICKUPS.get(self.kind, ("pickup_ember", "ember"))
        world.audio.play(sound)
        field, amount = VALUES.get(self.kind, ("embers", 1))
        state = world.state
        if field == "health":
            state.heal(amount)
        elif field == "keys":
            state.keys += 1
            state.sync_keys()
        elif field == "embers":
            state.embers = min(999, state.embers + amount)
        elif field == "bombs":
            state.bombs = min(state.max_bombs, state.bombs + amount)
        elif field == "arrows":
            state.arrows = min(state.max_arrows, state.arrows + amount)
        elif field == "magic":
            state.magic = min(state.max_magic, state.magic + amount)
        elif field == "seashells":
            state.seashells += 1

    @property
    def hop_offset(self) -> int:
        """A short hop when the pickup first appears."""
        if self.pop <= 0:
            return 0
        t = self.pop / POP_FRAMES
        return -round(6 * math.sin(math.pi * t))

    def sprite_name(self) -> str:
        """Atlas block for this pickup kind."""
        return PICKUPS.get(self.kind, ("pickup_ember", ""))[0]

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Blit the pickup, blinking just before it expires."""
        if self.timer > LIFETIME - BLINK_FROM and (self.timer // 4) % 2 == 0:
            return
        target.blit(assets.sprites.get(self.sprite_name()),
                    (round(self.x), round(self.y) + oy + self.hop_offset))


def spawn_drop(world: World, x: float, y: float, table: str) -> Pickup | None:
    """Roll a drop table at a position and spawn the pickup, if any."""
    kind = world.drops.roll(table, world.rng)
    if kind is None:
        return None
    pickup = Pickup(x, y, kind)
    world.spawn(pickup)
    return pickup
