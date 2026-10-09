"""Bombs and the Hookshot: the two gadgets that open the middle of the game."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from eldermoor.config import TILE
from eldermoor.entities import DIRS, DeathPuff, Entity

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.hero import Hero
    from eldermoor.world import World

BOMB_FUSE = 96
BOMB_RADIUS = 22
BOMB_DAMAGE = 3
HOOK_SPEED = 5.0
HOOK_RANGE = 6 * TILE
HOOK_PULL = 3.0


class Bomb(Entity):
    """A lit bomb. It does not care whose boots are next to it when it goes off."""

    body = pygame.Rect(3, 4, 10, 10)
    blocks_movement = False
    layer = 1

    def __init__(self, x: float, y: float, fuse: int = BOMB_FUSE) -> None:
        super().__init__(x, y)
        self.fuse = fuse

    def update(self, world: World) -> None:
        """Burn down, then take the room with it."""
        self.frame += 1
        self.fuse -= 1
        if self.fuse <= 0:
            self.explode(world)

    def explode(self, world: World) -> None:
        """Damage everything close, and open anything bombable."""
        self.alive = False
        world.audio.play("bomb_blow")
        world.shake(18)
        world.spawn(DeathPuff(self.x - 4, self.y - 4))
        cx, cy = self.center
        blast = pygame.Rect(int(cx - BOMB_RADIUS), int(cy - BOMB_RADIUS),
                            BOMB_RADIUS * 2, BOMB_RADIUS * 2)
        world.hit_tiles(blast, "bomb")
        for ent in list(world.enemies()):
            if ent.body_rect().colliderect(blast):
                ent.take_damage(world, BOMB_DAMAGE, self)
        caught = world.touching_hero(blast)
        if caught is not None:
            caught.hurt(world, 1, self)

    def sprite_name(self) -> str:
        """Blinks faster as the fuse runs out."""
        rate = 4 if self.fuse < 24 else 10
        return "bomb_lit" if (self.frame // rate) % 2 == 0 else "pickup_bomb"


class Hookshot(Entity):
    """The chain. It goes out, it grabs, and then one of you moves."""

    body = pygame.Rect(2, 2, 12, 12)
    width = height = 8
    layer = 2

    def __init__(self, hero: Hero) -> None:
        dx, dy = DIRS[hero.facing]
        cx, cy = hero.center
        super().__init__(cx - 4, cy - 4)
        self.hero = hero
        self.dir = (dx, dy)
        self.facing = hero.facing
        self.origin = (cx - 4, cy - 4)
        self.length = 0.0
        self.returning = False
        self.anchored = False

    @property
    def horizontal(self) -> bool:
        """True when the chain runs east or west."""
        return self.dir[0] != 0

    def update(self, world: World) -> None:
        """Extend, grab, then either pull the hero or come back."""
        self.frame += 1
        if self.anchored:
            self._pull(world)
            return
        step = -HOOK_SPEED if self.returning else HOOK_SPEED
        self.length += step
        self.x = self.origin[0] + self.dir[0] * self.length
        self.y = self.origin[1] + self.dir[1] * self.length
        if self.returning:
            if self.length <= 0:
                self.alive = False
                self.hero.hooking = False
            return
        rect = self.body_rect()
        for ent in list(world.enemies()):
            if rect.colliderect(ent.body_rect()):
                ent.take_damage(world, 1, self.hero)
                self.returning = True
                return
        col, row = rect.centerx // TILE, rect.centery // TILE
        tile = world.room.tile_at(col, row)
        if tile is not None and tile.hook:
            self.anchored = True
            world.audio.play("block")
            return
        if self.length >= HOOK_RANGE or (tile is not None and tile.collision.name == "SOLID"):
            self.returning = True

    def _pull(self, world: World) -> None:
        """Drag the hero to the anchor, floating over whatever is between."""
        hero = self.hero
        # stop a tile short: the anchor is a pillar, and standing in it is not an option
        tx = self.x - 4 - self.dir[0] * TILE
        ty = self.y - 4 - self.dir[1] * TILE
        dx, dy = tx - hero.x, ty - hero.y
        distance = math.hypot(dx, dy)
        hero.hop_timer = max(hero.hop_timer, 4)       # floats over pits and water
        if distance <= HOOK_PULL:
            hero.x, hero.y = tx, ty
            self.alive = False
            hero.hooking = False
            return
        hero.x += dx / distance * HOOK_PULL
        hero.y += dy / distance * HOOK_PULL

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """The chain, link by link, with the head on the end."""
        link = "chain_h" if self.horizontal else "chain_v"
        steps = max(0, int(self.length) // 8)
        for i in range(steps):
            x = self.origin[0] + self.dir[0] * i * 8
            y = self.origin[1] + self.dir[1] * i * 8
            target.blit(assets.sprites.get(link), (round(x), round(y) + oy))
        target.blit(assets.sprites.get("hook_head"), (round(self.x), round(self.y) + oy))


def place_bomb(world: World, hero: Hero) -> bool:
    """Drop a bomb in front of the hero. False if there are none left."""
    if world.state.bombs <= 0:
        world.audio.play("error")
        return False
    world.state.bombs -= 1
    dx, dy = DIRS[hero.facing]
    world.spawn(Bomb(hero.x + dx * TILE, hero.y + dy * TILE))
    world.audio.play("bomb_place")
    return True


def fire_hookshot(world: World, hero: Hero) -> bool:
    """Throw the chain. False if one is already out."""
    if hero.hooking:
        return False
    hero.hooking = True
    world.audio.play("shoot")
    world.spawn(Hookshot(hero))
    return True
