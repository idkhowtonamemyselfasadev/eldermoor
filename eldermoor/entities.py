"""Entity base class, shared movement and hit reactions, and the death puff."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import (
    DEATH_PUFF_FRAMES,
    HIT_FLASH_FRAMES,
    KNOCKBACK_FRAMES,
    PLAY_H,
    PLAY_W,
    TILE,
)

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.world import World

Facing = str  # "down" | "up" | "left" | "right"

DIRS: dict[Facing, tuple[int, int]] = {
    "down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0),
}
FLIP_FACING = {"down": "up", "up": "down", "left": "right", "right": "left"}


def facing_from(dx: float, dy: float, current: Facing = "down") -> Facing:
    """Turn a movement vector into one of the four facings, keeping ``current`` on a tie."""
    if dx and dy:
        horizontal = "right" if dx > 0 else "left"
        vertical = "down" if dy > 0 else "up"
        return current if current in (horizontal, vertical) else horizontal
    if dx:
        return "right" if dx > 0 else "left"
    if dy:
        return "down" if dy > 0 else "up"
    return current


class Entity:
    """Anything in a room. Coordinates are play-area pixels of the sprite's top-left."""

    width = 16
    height = 16
    body = pygame.Rect(2, 6, 12, 10)       # collider inside the sprite cell
    sprite_offset = (0, 0)                 # drawing offset for cells taller than the body
    blocks_movement = False                # other entities cannot walk through it
    team = "neutral"                       # "hero" | "enemy" | "neutral"
    contact_damage = 0                     # half-hearts dealt by touching the hero
    layer = 0                              # draw tiebreak within the same y

    def __init__(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)
        self.alive = True
        self.facing: Facing = "down"
        self.hp = 1
        self.flash = 0
        self.knock = (0.0, 0.0)
        self.knock_timer = 0
        self.frame = 0                     # free-running animation counter

    # ----- geometry ------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        """Sprite cell rect in whole pixels."""
        return pygame.Rect(round(self.x), round(self.y), self.width, self.height)

    def body_rect(self, x: float | None = None, y: float | None = None) -> pygame.Rect:
        """Collider rect at the given (or current) position."""
        bx = round(self.x if x is None else x)
        by = round(self.y if y is None else y)
        return pygame.Rect(bx + self.body.x, by + self.body.y, self.body.w, self.body.h)

    @property
    def center(self) -> tuple[float, float]:
        """Centre of the collider."""
        r = self.body_rect()
        return r.centerx, r.centery

    @property
    def depth(self) -> float:
        """Sort key for drawing: the bottom of the collider."""
        return self.y + self.body.bottom

    def col_row(self) -> tuple[int, int]:
        """Grid cell the collider's centre sits in."""
        r = self.body_rect()
        return r.centerx // TILE, r.centery // TILE

    def distance_to(self, other: Entity) -> float:
        """Straight-line distance between the two colliders' centres."""
        ax, ay = self.center
        bx, by = other.center
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

    # ----- movement ------------------------------------------------------
    def blocked_at(self, world: World, x: float, y: float) -> bool:
        """True if the collider would overlap a blocking tile or a solid entity."""
        return world.blocked(self.body_rect(x, y), ignore=self)

    def move(self, world: World, vx: float, vy: float) -> tuple[bool, bool]:
        """Axis-separated movement. Returns (blocked_x, blocked_y)."""
        hit_x = hit_y = False
        if vx:
            nx = self.x + vx
            if self.blocked_at(world, nx, self.y):
                nx = self._slide(world, vx, horizontal=True)
                hit_x = True
            self.x = nx
        if vy:
            ny = self.y + vy
            if self.blocked_at(world, self.x, ny):
                ny = self._slide(world, vy, horizontal=False)
                hit_y = True
            self.y = ny
        return hit_x, hit_y

    def _slide(self, world: World, v: float, horizontal: bool) -> float:
        step = 1 if v > 0 else -1
        pos = round(self.x if horizontal else self.y)
        for _ in range(int(abs(v)) + 1):
            nxt = pos + step
            blocked = (self.blocked_at(world, nxt, self.y) if horizontal
                       else self.blocked_at(world, self.x, nxt))
            if blocked:
                break
            pos = nxt
        return float(pos)

    def clamp_to_room(self) -> None:
        """Keep the sprite inside the play area."""
        self.x = min(max(self.x, 0.0), float(PLAY_W - self.width))
        self.y = min(max(self.y, 0.0), float(PLAY_H - self.height))

    # ----- reactions -----------------------------------------------------
    def apply_knockback(self, from_x: float, from_y: float, speed: float) -> None:
        """Push away from a point for KNOCKBACK_FRAMES frames."""
        cx, cy = self.center
        dx, dy = cx - from_x, cy - from_y
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        self.knock = (dx / length * speed, dy / length * speed)
        self.knock_timer = KNOCKBACK_FRAMES

    def step_knockback(self, world: World) -> bool:
        """Move along the knockback vector; True while it is still running."""
        if self.knock_timer <= 0:
            return False
        self.knock_timer -= 1
        self.move(world, self.knock[0], self.knock[1])
        return True

    def take_damage(self, world: World, amount: int, source: Entity | None = None) -> bool:
        """Lose hp, flash, get knocked back. True if this killed the entity."""
        if not self.alive:
            return False
        self.hp -= amount
        self.flash = HIT_FLASH_FRAMES
        if source is not None:
            sx, sy = source.center
            self.apply_knockback(sx, sy, 2.0)
        if self.hp <= 0:
            self.die(world)
            return True
        return False

    def die(self, world: World) -> None:
        """Remove the entity and leave a puff."""
        self.alive = False
        world.spawn(DeathPuff(self.x, self.y))

    # ----- hooks ---------------------------------------------------------
    def update(self, world: World) -> None:
        """One logic frame."""
        self.frame += 1

    def interact(self, world: World) -> bool:
        """Called when the hero presses A facing this entity. True if it handled the press."""
        return False

    def sprite_name(self) -> str | None:
        """Atlas block name for the current pose, or None to draw nothing."""
        return None

    @property
    def flip(self) -> bool:
        """True when the sprite must be mirrored horizontally."""
        return False

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Blit the current sprite, white-flashing while ``flash`` is counting down."""
        name = self.sprite_name()
        if name is None:
            return
        surf = assets.sprites.get(name, self.flip)
        if self.flash > 0 and (self.flash // 2) % 2 == 0:
            surf = surf.copy()
            surf.fill((180, 180, 180), special_flags=pygame.BLEND_RGB_ADD)
        ox, oys = self.sprite_offset
        target.blit(surf, (round(self.x) + ox, round(self.y) + oy + oys))

    def tick_timers(self) -> None:
        """Advance the generic per-frame counters."""
        self.frame += 1
        if self.flash > 0:
            self.flash -= 1


class DeathPuff(Entity):
    """The four-frame puff every small enemy leaves behind."""

    blocks_movement = False
    layer = 2

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self.timer = 0

    def update(self, world: World) -> None:
        """Count up and vanish."""
        self.timer += 1
        if self.timer >= DEATH_PUFF_FRAMES:
            self.alive = False

    def sprite_name(self) -> str | None:
        """One of puff_0..puff_3."""
        return f"puff_{min(self.timer // 4, 3)}"
