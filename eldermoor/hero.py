"""Wren: walking, the sword (swing and spin), the shield, the dodge-roll and item use."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from eldermoor.config import (
    HERO_IDLE_FRAME_TIME,
    HERO_INVULN_FRAMES,
    HERO_KNOCKBACK_SPEED,
    HERO_SPEED,
    HERO_WALK_FRAME_TIME,
    ROLL_COOLDOWN,
    ROLL_FRAMES,
    ROLL_IFRAMES,
    ROLL_SPEED,
    SHIELD_SPEED_FACTOR,
    SPIN_CHARGE_FRAMES,
    SPIN_FRAMES,
    SWING_FRAME_TIME,
    SWING_FRAMES,
    SWING_TOTAL,
    TILE,
)
from eldermoor.entities import DIRS, Entity, Facing, facing_from

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.world import World

DIAG = math.sqrt(0.5)

# Sword sprite + offset (relative to the hero's top-left) per facing and swing frame.
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
SPIN_HITBOX = (-8, -8, 32, 32)
SHIELD_SPRITE = {"down": (4, 10), "up": (4, -4), "right": (11, 4), "left": (-9, 4)}


class Hero(Entity):
    """Wren. Eight-direction walking, four-direction sword, shield, roll, items."""

    team = "hero"
    layer = 1

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self.moving = False
        self.anim_frame = 1
        self.anim_timer = 0
        self.idle_timer = 0
        self.idle_blink = False
        self.swing_timer = 0
        self.swinging = False
        self.charge = 0
        self.spin_timer = 0
        self.spinning = False
        self.shielding = False
        self.roll_timer = 0
        self.roll_cooldown = 0
        self.roll_dir = (0.0, 0.0)
        self.invuln = 0
        self.hop_timer = 0
        self.lantern_timer = 0
        self.hit_this_swing: set[int] = set()

    # ----- queries used by the rest of the game --------------------------
    @property
    def busy(self) -> bool:
        """True while an action owns the hero's movement."""
        return self.swinging or self.spinning or self.roll_timer > 0

    @property
    def invulnerable(self) -> bool:
        """True while mercy frames or roll i-frames are running."""
        return self.invuln > 0 or 0 < self.roll_timer <= ROLL_IFRAMES

    @property
    def airborne(self) -> bool:
        """True mid-hop, when pits and water do not block."""
        return self.hop_timer > 0

    def front_tile(self) -> tuple[int, int]:
        """Grid position of the tile the hero faces."""
        dx, dy = DIRS[self.facing]
        r = self.body_rect()
        return (r.centerx + dx * TILE) // TILE, (r.centery + dy * TILE) // TILE

    def front_rect(self) -> pygame.Rect:
        """A 16x16 rect one tile ahead, used for talking, reading and lighting."""
        col, row = self.front_tile()
        return pygame.Rect(col * TILE, row * TILE, TILE, TILE)

    # ----- frame ---------------------------------------------------------
    def update(self, world: World) -> None:
        """Read input and advance one logic frame."""
        self.tick_timers()
        if self.invuln > 0:
            self.invuln -= 1
        if self.roll_cooldown > 0:
            self.roll_cooldown -= 1
        if self.lantern_timer > 0:
            self.lantern_timer -= 1
        if self.hop_timer > 0:
            self.hop_timer -= 1
        if self.step_knockback(world):
            return
        if self.roll_timer > 0:
            self._update_roll(world)
            return
        if self.spinning:
            self._update_spin(world)
            return
        if self.swinging:
            self._update_swing(world)
            return
        self._read_actions(world)
        if not self.busy:
            self._walk(world)

    def _read_actions(self, world: World) -> None:
        inp = world.input
        self.shielding = inp.is_held("l") and world.state.shield_level > 0
        if inp.pressed("r") and self.roll_cooldown == 0:
            self._start_roll(world)
            return
        for index, action in enumerate(("b", "x", "y")):
            if inp.pressed(action):
                world.use_item(self, world.state.slots[index])
                return
        if inp.pressed("a"):
            if world.try_interact(self):
                return
            if world.state.sword_level > 0:
                self.start_swing(world)
        if inp.is_held("a") and world.state.sword_level >= 2 and not self.swinging:
            self.charge = min(self.charge + 1, SPIN_CHARGE_FRAMES)
        elif inp.released("a") and self.charge >= SPIN_CHARGE_FRAMES:
            self._start_spin(world)
        elif not inp.is_held("a"):
            self.charge = 0

    def _walk(self, world: World) -> None:
        dx, dy = world.input.axis()
        self.facing = facing_from(dx, dy, self.facing)
        if dx or dy:
            self.moving = True
            self.idle_timer = 0
            self.idle_blink = False
            speed = HERO_SPEED * (DIAG if dx and dy else 1.0)
            if self.shielding:
                speed *= SHIELD_SPEED_FACTOR
            self.move(world, dx * speed, dy * speed)
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

    # ----- sword ---------------------------------------------------------
    def start_swing(self, world: World | None = None) -> None:
        """Begin a sword swing (ignored if one is in progress)."""
        if self.swinging or self.spinning:
            return
        self.swinging = True
        self.swing_timer = 0
        self.moving = False
        self.anim_frame = 1
        self.hit_this_swing.clear()
        if world is not None:
            world.audio.play("sword")

    def _update_swing(self, world: World) -> None:
        self.swing_timer += 1
        box = self.sword_hitbox()
        if box is not None:
            world.sword_hit(self, box)
        if self.swing_timer >= SWING_TOTAL:
            self.swinging = False
            self.swing_timer = 0

    def _start_spin(self, world: World) -> None:
        self.spinning = True
        self.spin_timer = 0
        self.charge = 0
        self.hit_this_swing.clear()
        world.audio.play("spin")

    def _update_spin(self, world: World) -> None:
        self.spin_timer += 1
        hx, hy, hw, hh = SPIN_HITBOX
        world.sword_hit(self, pygame.Rect(round(self.x) + hx, round(self.y) + hy, hw, hh))
        if self.spin_timer >= SPIN_FRAMES:
            self.spinning = False
            self.spin_timer = 0

    @property
    def swing_frame(self) -> int:
        """Current swing frame 0..2, or -1 when not swinging."""
        if not self.swinging:
            return -1
        return min(self.swing_timer // SWING_FRAME_TIME, SWING_FRAMES - 1)

    def sword_hitbox(self) -> pygame.Rect | None:
        """Active sword rect during frames 1 and 2 of the swing, else None."""
        if self.spinning:
            hx, hy, hw, hh = SPIN_HITBOX
            return pygame.Rect(round(self.x) + hx, round(self.y) + hy, hw, hh)
        if self.swing_frame < 1:
            return None
        hx, hy, hw, hh = SWORD_HITBOX[self.facing]
        return pygame.Rect(round(self.x) + hx, round(self.y) + hy, hw, hh)

    # ----- roll ----------------------------------------------------------
    def _start_roll(self, world: World) -> None:
        dx, dy = world.input.axis()
        if not dx and not dy:
            dx, dy = DIRS[self.facing]
        length = math.hypot(dx, dy) or 1.0
        self.roll_dir = (dx / length, dy / length)
        self.roll_timer = ROLL_FRAMES
        self.facing = facing_from(dx, dy, self.facing)
        self.roll_cooldown = ROLL_FRAMES + ROLL_COOLDOWN
        world.audio.play("roll")

    def _update_roll(self, world: World) -> None:
        self.roll_timer -= 1
        t = self.roll_timer / ROLL_FRAMES
        speed = ROLL_SPEED * (0.35 + 0.65 * t)
        self.move(world, self.roll_dir[0] * speed, self.roll_dir[1] * speed)

    # ----- damage --------------------------------------------------------
    def blocks_from(self, source_x: float, source_y: float) -> bool:
        """True if a raised shield covers the direction the hit comes from."""
        if not self.shielding:
            return False
        cx, cy = self.center
        dx, dy = source_x - cx, source_y - cy
        want = facing_from(dx, dy, self.facing)
        return want == self.facing

    def hurt(self, world: World, half_hearts: int, source: Entity | None = None) -> bool:
        """Take damage unless invulnerable or shielding. True if the hit landed."""
        if self.invulnerable or half_hearts <= 0 or world.god_mode:
            return False
        if source is not None:
            sx, sy = source.center
            if self.blocks_from(sx, sy):
                world.audio.play("block")
                self.apply_knockback(sx, sy, 1.5)
                return False
            self.apply_knockback(sx, sy, HERO_KNOCKBACK_SPEED)
        self.invuln = HERO_INVULN_FRAMES
        world.state.damage(half_hearts)
        world.audio.play("hurt")
        self.swinging = False
        self.spinning = False
        self.roll_timer = 0
        if world.state.health <= 0:
            world.on_hero_death()
        return True

    def hop(self) -> None:
        """Start a feather jump."""
        if self.hop_timer == 0:
            self.hop_timer = 26

    @property
    def hop_height(self) -> int:
        """How far above the ground the sprite is drawn during a hop."""
        if self.hop_timer <= 0:
            return 0
        t = 1.0 - abs(self.hop_timer - 13) / 13.0
        return round(10 * t)

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
        if self.spinning:
            return f"wren_swing_{self.side}_{min(self.spin_timer // 6, 2)}"
        if self.swinging:
            return f"wren_swing_{self.side}_{self.swing_frame}"
        if self.roll_timer > 0:
            return f"wren_{self.side}_{(ROLL_FRAMES - self.roll_timer) // 5 % 3}"
        if self.moving:
            return f"wren_{self.side}_{self.anim_frame}"
        return f"wren_{self.side}_idle" if self.idle_blink else f"wren_{self.side}_1"

    def sword_sprite(self) -> tuple[str, int, int, bool] | None:
        """(block name, x, y, flip) for the sword in play-area pixels, or None."""
        if self.spinning:
            key = ("right", "down", "left", "up")[(self.spin_timer // 6) % 4]
            name, (ox, oy) = SWORD_FRAMES["right" if key in ("right", "left") else key][2]
            flip = key == "left"
            return name, round(self.x) + (-ox if flip else ox), round(self.y) + oy, flip
        f = self.swing_frame
        if f < 0:
            return None
        key = "right" if self.facing in ("left", "right") else self.facing
        name, (ox, oy) = SWORD_FRAMES[key][f]
        if self.flip:
            ox = -ox
        return name, round(self.x) + ox, round(self.y) + oy, self.flip

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Draw hero, shield and sword; the sword goes behind the hero when facing up."""
        if self.invuln > 0 and (self.invuln // 3) % 2 == 1:
            return
        oy -= self.hop_height
        sword = self.sword_sprite()
        hero = assets.sprites.get(self.sprite_name(), self.flip)
        if sword and self.facing == "up":
            self._blit(target, assets, sword, oy)
        target.blit(hero, (round(self.x), round(self.y) + oy))
        if sword and self.facing != "up":
            self._blit(target, assets, sword, oy)
        if self.shielding and assets.sprites.has("shield_block"):
            sx, sy = SHIELD_SPRITE[self.facing]
            target.blit(assets.sprites.get("shield_block", self.facing == "left"),
                        (round(self.x) + sx, round(self.y) + sy + oy))

    @staticmethod
    def _blit(target: pygame.Surface, assets: Assets,
              sword: tuple[str, int, int, bool], oy: int) -> None:
        name, sx, sy, flip = sword
        target.blit(assets.sprites.get(name, flip), (sx, sy + oy))
