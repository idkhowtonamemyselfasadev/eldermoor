"""Entities: the base class and Wren, the hero (walk, idle, sword swing, tile collision)."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from eldermoor.config import (
    HERO_IDLE_FRAME_TIME,
    HERO_SPEED,
    HERO_WALK_FRAME_TIME,
    PLAY_H,
    PLAY_W,
    SWING_FRAME_TIME,
    SWING_FRAMES,
    SWING_TOTAL,
)

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.input import Input
    from eldermoor.tilemap import Room

Facing = str  # "down" | "up" | "left" | "right"
DIAG = math.sqrt(0.5)

# Sword sprite + offset (relative to hero top-left) for each facing and swing frame.
# "left" mirrors "right": the sprite is flipped and the x offset negated.
SWORD_FRAMES: dict[Facing, list[tuple[str, tuple[int, int]]]] = {
    "down": [("sword_h", (8, 2)), ("sword_diag_dr", (12, 9)), ("sword_v_down", (5, 11))],
    "up": [("sword_h", (8, 1)), ("sword_diag_ur", (12, -11)), ("sword_v_up", (4, -8))],
    "right": [("sword_v_up", (5, -6)), ("sword_diag_ur", (12, -4)), ("sword_h", (12, 2))],
}
SWORD_HITBOX: dict[Facing, tuple[int, int, int, int]] = {
    "down": (4, 12, 12, 14),
    "up": (2, -10, 12, 14),
    "right": (12, 2, 14, 12),
    "left": (-10, 2, 14, 12),
}


class Entity:
    """Anything with a position and a sprite. Coordinates are play-area pixels (top-left)."""

    width = 16
    height = 16
    body = pygame.Rect(2, 6, 12, 10)  # collider offset within the sprite

    def __init__(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)
        self.alive = True

    @property
    def rect(self) -> pygame.Rect:
        """Sprite rect (integer pixels)."""
        return pygame.Rect(round(self.x), round(self.y), self.width, self.height)

    def body_rect(self, x: float | None = None, y: float | None = None) -> pygame.Rect:
        """Collider rect at the given (or current) position."""
        bx = round(self.x if x is None else x)
        by = round(self.y if y is None else y)
        return pygame.Rect(bx + self.body.x, by + self.body.y, self.body.w, self.body.h)

    def update(self, inp: Input, room: Room) -> None:
        """Advance one logic frame."""

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Draw to the target surface with a vertical offset (the HUD height)."""


class Hero(Entity):
    """Wren. 8-direction walking, 4-direction facing, 3-frame sword swing."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self.facing: Facing = "down"
        self.moving = False
        self.anim_frame = 1          # 0, 1, 2 for the walk cycle (1 = standing)
        self.anim_timer = 0
        self.idle_timer = 0
        self.idle_blink = False
        self.swing_timer = 0         # counts up while swinging, 0 when idle
        self.swinging = False

    # ----- logic ---------------------------------------------------------
    def update(self, inp: Input, room: Room) -> None:
        """Read input, swing or move, animate."""
        if self.swinging:
            self._update_swing()
            return
        if inp.pressed("a"):
            self.start_swing()
            return
        dx, dy = inp.axis()
        self._face(dx, dy)
        if dx or dy:
            self.moving = True
            self.idle_timer = 0
            self.idle_blink = False
            speed = HERO_SPEED * (DIAG if dx and dy else 1.0)
            self._move(dx * speed, dy * speed, room)
            self.anim_timer += 1
            if self.anim_timer >= HERO_WALK_FRAME_TIME:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 3
        else:
            self.moving = False
            self.anim_frame = 1
            self.anim_timer = 0
            self.idle_timer += 1
            if self.idle_timer >= HERO_IDLE_FRAME_TIME:
                self.idle_timer = 0
                self.idle_blink = not self.idle_blink

    def start_swing(self) -> None:
        """Begin a sword swing (ignored if one is in progress)."""
        if not self.swinging:
            self.swinging = True
            self.swing_timer = 0
            self.moving = False
            self.anim_frame = 1

    def _update_swing(self) -> None:
        self.swing_timer += 1
        if self.swing_timer >= SWING_TOTAL:
            self.swinging = False
            self.swing_timer = 0

    @property
    def swing_frame(self) -> int:
        """Current swing frame 0..2 (or -1 when not swinging)."""
        if not self.swinging:
            return -1
        return min(self.swing_timer // SWING_FRAME_TIME, SWING_FRAMES - 1)

    def sword_hitbox(self) -> pygame.Rect | None:
        """Active sword rect during frames 1 and 2 of the swing, else None."""
        f = self.swing_frame
        if f < 1:
            return None
        hx, hy, hw, hh = SWORD_HITBOX[self.facing]
        return pygame.Rect(round(self.x) + hx, round(self.y) + hy, hw, hh)

    def _face(self, dx: int, dy: int) -> None:
        if dx and dy:
            horizontal = "right" if dx > 0 else "left"
            vertical = "down" if dy > 0 else "up"
            if self.facing not in (horizontal, vertical):
                self.facing = horizontal
        elif dx:
            self.facing = "right" if dx > 0 else "left"
        elif dy:
            self.facing = "down" if dy > 0 else "up"

    def _move(self, vx: float, vy: float, room: Room) -> None:
        """Axis-separated movement against the room's blocking tiles."""
        if vx:
            nx = self.x + vx
            if room.blocked(self.body_rect(nx, self.y)):
                nx = self._slide_x(vx, room)
            self.x = nx
        if vy:
            ny = self.y + vy
            if room.blocked(self.body_rect(self.x, ny)):
                ny = self._slide_y(vy, room)
            self.y = ny

    def _slide_x(self, vx: float, room: Room) -> float:
        """Move x as far as possible in whole pixels toward vx."""
        step = 1 if vx > 0 else -1
        x = round(self.x)
        for _ in range(int(abs(vx)) + 1):
            if room.blocked(self.body_rect(x + step, self.y)):
                break
            x += step
        return float(x)

    def _slide_y(self, vy: float, room: Room) -> float:
        step = 1 if vy > 0 else -1
        y = round(self.y)
        for _ in range(int(abs(vy)) + 1):
            if room.blocked(self.body_rect(self.x, y + step)):
                break
            y += step
        return float(y)

    def clamp_to_room(self) -> None:
        """Keep the hero inside the play area (used on edges without an exit)."""
        self.x = min(max(self.x, 0.0), float(PLAY_W - self.width))
        self.y = min(max(self.y, 0.0), float(PLAY_H - self.height))

    # ----- drawing -------------------------------------------------------
    @property
    def side(self) -> str:
        """Sprite direction key: 'down', 'up' or 'side'."""
        return "side" if self.facing in ("left", "right") else self.facing

    @property
    def flip(self) -> bool:
        """True when the side sprite must be mirrored (facing left)."""
        return self.facing == "left"

    def sprite_name(self) -> str:
        """Atlas block name for the current pose."""
        if self.swinging:
            return f"wren_swing_{self.side}_{self.swing_frame}"
        if self.moving:
            return f"wren_{self.side}_{self.anim_frame}"
        return f"wren_{self.side}_idle" if self.idle_blink else f"wren_{self.side}_1"

    def sword_sprite(self) -> tuple[str, int, int, bool] | None:
        """(block name, x, y, flip) for the sword in play-area pixels, or None."""
        f = self.swing_frame
        if f < 0:
            return None
        key = "right" if self.facing in ("left", "right") else self.facing
        name, (ox, oy) = SWORD_FRAMES[key][f]
        if self.flip:
            ox = -ox
        return name, round(self.x) + ox, round(self.y) + oy, self.flip

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Draw hero and sword. The sword goes behind the hero when facing up."""
        sword = self.sword_sprite()
        hero = assets.sprites.get(self.sprite_name(), self.flip)
        if sword and self.facing == "up":
            self._draw_sword(target, assets, sword, oy)
        target.blit(hero, (round(self.x), round(self.y) + oy))
        if sword and self.facing != "up":
            self._draw_sword(target, assets, sword, oy)

    @staticmethod
    def _draw_sword(target: pygame.Surface, assets: Assets,
                    sword: tuple[str, int, int, bool], oy: int) -> None:
        name, sx, sy, flip = sword
        target.blit(assets.sprites.get(name, flip), (sx, sy + oy))
