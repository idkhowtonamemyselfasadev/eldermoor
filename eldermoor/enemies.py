"""Enemies and their projectiles, built from data/enemies/*.json."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pygame

from eldermoor.ai import Brain
from eldermoor.config import DATA, TILE
from eldermoor.entities import DeathPuff, Entity

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.world import World


class EnemyDef:
    """One enemy kind as loaded from JSON."""

    def __init__(self, enemy_id: str, raw: dict[str, Any]) -> None:
        self.id = enemy_id
        self.raw = raw
        self.name = str(raw.get("name", f"enemy.{enemy_id}"))
        self.sprite = str(raw.get("sprite", enemy_id))
        self.frames = int(raw.get("frames", 2))
        self.frame_time = int(raw.get("frame_time", 10))
        self.directional = bool(raw.get("directional", False))
        self.hp = int(raw.get("hp", 2))
        self.damage = int(raw.get("damage", 1))
        self.speed = float(raw.get("speed", 0.5))
        self.drop = str(raw.get("drop", "enemy"))
        self.size = int(raw.get("size", 16))
        self.body = tuple(raw.get("body", (2, 6, 12, 10)))
        self.armour = str(raw.get("armour", ""))      # "front": only hurt from behind
        self.flying = bool(raw.get("flying", False))
        self.ghost = bool(raw.get("ghost", False))    # only visible by lantern light
        self.ai: dict[str, Any] = raw.get("ai", {"start": "idle", "states": {}})
        self.bestiary = str(raw.get("bestiary", f"bestiary.{enemy_id}"))


class EnemyRegistry:
    """All enemy definitions, keyed by id."""

    def __init__(self, defs: dict[str, EnemyDef]) -> None:
        self.defs = defs

    @classmethod
    def load(cls, root: Path = DATA) -> EnemyRegistry:
        """Read every JSON file in data/enemies/."""
        defs: dict[str, EnemyDef] = {}
        for path in sorted((root / "enemies").glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            for enemy_id, entry in raw.items():
                if enemy_id.startswith("_"):
                    continue
                if enemy_id in defs:
                    raise ValueError(f"enemy {enemy_id} defined twice")
                defs[enemy_id] = EnemyDef(enemy_id, entry)
        return cls(defs)

    def __contains__(self, key: object) -> bool:
        return key in self.defs

    def __getitem__(self, key: str) -> EnemyDef:
        return self.defs[key]

    def get(self, key: str) -> EnemyDef | None:
        """Definition or None."""
        return self.defs.get(key)


class Enemy(Entity):
    """An enemy driven by its definition's state machine."""

    team = "enemy"

    def __init__(self, definition: EnemyDef, x: float, y: float,
                 rng: random.Random | None = None) -> None:
        super().__init__(x, y)
        self.definition = definition
        self.width = self.height = definition.size
        self.body = pygame.Rect(*definition.body)
        self.hp = definition.hp
        self.speed = definition.speed
        self.contact_damage = definition.damage
        self.brain = Brain(definition.ai, rng or random.Random())
        self.state_time = 0
        self.heading: tuple[float, float] = (0.0, 0.0)
        self.hop = 0
        self.anim = 0
        self.stun_timer = 0

    # ----- frame ---------------------------------------------------------
    def update(self, world: World) -> None:
        """Knockback, then the state machine, then contact damage."""
        self.tick_timers()
        if self.stun_timer > 0:
            self.stun_timer -= 1
            return
        if self.step_knockback(world):
            return
        self.state_time += 1
        self.brain.step(self, world)
        self.anim = (self.frame // self.definition.frame_time) % self.definition.frames
        self.touch_hero(world)

    def touch_hero(self, world: World) -> None:
        """Hurt the hero on contact."""
        if self.contact_damage <= 0:
            return
        if self.body_rect().colliderect(world.hero.body_rect()):
            world.hero.hurt(world, self.contact_damage, self)

    # ----- damage --------------------------------------------------------
    def vulnerable_from(self, attacker: Entity) -> bool:
        """False when armour covers the side the hit came from.

        A shielded knight is only open from behind: the attacker has to be
        looking the same way the knight is, which means standing at its back.
        """
        if self.definition.armour != "front":
            return True
        return attacker.facing == self.facing

    def take_damage(self, world: World, amount: int, source: Entity | None = None) -> bool:
        """Sword and projectile damage, respecting armour."""
        if source is not None and not self.vulnerable_from(source):
            world.audio.play("block")
            self.stun_timer = 6
            return False
        world.audio.play("enemy_hit")
        return super().take_damage(world, amount, source)

    def die(self, world: World) -> None:
        """Puff, drop, and tell the room an enemy died."""
        super().die(world)
        world.audio.play("enemy_die")
        world.drop_from(self.x, self.y, self.definition.drop)
        world.state.set_flag(f"seen:{self.definition.id}", 1)
        world.trigger("enemy_died", self.definition.id)

    # ----- drawing -------------------------------------------------------
    @property
    def flip(self) -> bool:
        """Side sprites are drawn facing right and mirrored for left."""
        return self.definition.directional and self.facing == "left"

    def sprite_name(self) -> str:
        """Atlas block for the current facing and animation frame."""
        base = self.definition.sprite
        if self.definition.directional:
            side = "side" if self.facing in ("left", "right") else self.facing
            return f"{base}_{side}_{self.anim}"
        return f"{base}_{self.anim}"

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Blit with the hop offset and the telegraph tint applied."""
        if self.definition.ghost and not world_is_lit(self):
            return
        surf = assets.sprites.get(self.sprite_name(), self.flip)
        tinted = self.flash > 0 and (self.flash // 2) % 2 == 0
        if tinted or self.brain.telegraphing:
            surf = surf.copy()
            colour = (180, 180, 180) if tinted else (90, 20, 0)
            surf.fill(colour, special_flags=pygame.BLEND_RGB_ADD)
        target.blit(surf, (round(self.x), round(self.y) + oy - self.hop))


def world_is_lit(enemy: Enemy) -> bool:
    """Ghosts are visible unless the room is dark; set by the world each frame."""
    return getattr(enemy, "visible", True)


class Projectile(Entity):
    """An enemy shot: flies straight, hurts the hero, dies on a wall."""

    team = "enemy"
    body = pygame.Rect(4, 4, 8, 8)
    width = height = 8
    layer = 1

    def __init__(self, x: float, y: float, vx: float, vy: float, sprite: str = "shot_ember",
                 damage: int = 1, life: int = 180, reflectable: bool = True) -> None:
        super().__init__(x, y)
        self.vx = vx
        self.vy = vy
        self.sprite = sprite
        self.damage = damage
        self.life = life
        self.reflectable = reflectable

    def update(self, world: World) -> None:
        """Fly, check the hero and the walls."""
        self.frame += 1
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            return
        self.x += self.vx
        self.y += self.vy
        rect = self.body_rect()
        if world.room.blocked(rect) or not world.play_rect.colliderect(rect):
            self.alive = False
            return
        hero = world.hero
        if rect.colliderect(hero.body_rect()):
            if hero.blocks_from(*self.center) and self.reflectable:
                world.audio.play("block")
                self.vx, self.vy = -self.vx, -self.vy
                self.team = "hero"
                return
            if self.team == "enemy":
                hero.hurt(world, self.damage, self)
                self.alive = False
        elif self.team == "hero":
            for ent in world.enemies():
                if rect.colliderect(ent.body_rect()):
                    ent.take_damage(world, 1, self)
                    self.alive = False
                    return

    def sprite_name(self) -> str:
        """The shot's sprite."""
        return self.sprite


class Thrown(Entity):
    """A rock or pot in the air. Breaks on the first thing it meets."""

    team = "hero"
    body = pygame.Rect(2, 2, 12, 12)
    layer = 2

    def __init__(self, x: float, y: float, vx: float, vy: float, sprite: str,
                 drop: str = "rock", damage: int = 2, life: int = 48) -> None:
        super().__init__(x, y)
        self.vx = vx
        self.vy = vy
        self.sprite = sprite
        self.drop = drop
        self.damage = damage
        self.life = life

    def update(self, world: World) -> None:
        """Fly until something stops it, then break."""
        self.frame += 1
        self.life -= 1
        self.x += self.vx
        self.y += self.vy
        rect = self.body_rect()
        for ent in world.enemies():
            if not rect.colliderect(ent.body_rect()):
                continue
            # a boss that shrugs off the sword is still knocked open by a rock
            if getattr(ent, "weak_states", None) and not getattr(ent, "vulnerable", True):
                ent.stun(world)
            else:
                ent.take_damage(world, self.damage, self)
            self.shatter(world)
            return
        if self.life <= 0 or world.room.blocked(rect) or not world.play_rect.colliderect(rect):
            self.shatter(world)

    def shatter(self, world: World) -> None:
        """Break into a puff and whatever was inside."""
        self.alive = False
        world.audio.play("smash")
        world.spawn(DeathPuff(self.x, self.y))
        if self.drop:
            world.drop_from(self.x, self.y, self.drop)

    def sprite_name(self) -> str:
        """The thing being thrown."""
        return self.sprite


def spawn_enemy(world: World, enemy_id: str, col: int, row: int) -> Enemy | None:
    """Place an enemy at a grid position, or None if the id is unknown."""
    definition = world.enemy_defs.get(enemy_id)
    if definition is None:
        return None
    enemy = Enemy(definition, col * TILE, row * TILE, world.rng)
    world.spawn(enemy)
    return enemy
