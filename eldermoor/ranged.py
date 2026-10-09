"""The Bow: arrows that hit switches, eyes and things that will not come down."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from eldermoor.entities import DIRS, Entity

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.hero import Hero
    from eldermoor.world import World

ARROW_SPEED = 3.4
ARROW_LIFE = 90
ARROW_DAMAGE = 2


class Arrow(Entity):
    """Flies straight, hits one thing, stops."""

    team = "hero"
    body = pygame.Rect(2, 2, 12, 12)
    layer = 2

    def __init__(self, x: float, y: float, facing: str) -> None:
        super().__init__(x, y)
        dx, dy = DIRS[facing]
        self.vx = dx * ARROW_SPEED
        self.vy = dy * ARROW_SPEED
        self.facing = facing
        self.life = ARROW_LIFE

    def update(self, world: World) -> None:
        """Fly until it hits an enemy, a crystal or a wall."""
        from eldermoor.objects import Crystal
        self.frame += 1
        self.life -= 1
        self.x += self.vx
        self.y += self.vy
        rect = self.body_rect()
        if self.life <= 0 or world.room.blocked(rect) or not world.play_rect.colliderect(rect):
            self.alive = False
            return
        for ent in list(world.entities):
            if ent in world.heroes or not ent.alive:
                continue
            if not rect.colliderect(ent.body_rect()):
                continue
            if isinstance(ent, Crystal):
                ent.take_damage(world, 1, self.owner(world))
                self.alive = False
                return
            if ent.team == "enemy":
                ent.take_damage(world, ARROW_DAMAGE, self.owner(world))
                self.alive = False
                return

    def owner(self, world: World) -> Any:
        """Whoever loosed it; the nearer lamplighter is a good enough guess."""
        return world.nearest_hero(self)

    @property
    def flip(self) -> bool:
        """The arrow sprite points up-right; mirror it for the other side."""
        return self.facing == "left"

    def sprite_name(self) -> str:
        """One arrow sprite, turned by the renderer."""
        return "pickup_arrow"

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Rotate the arrow to point where it is going."""
        angle = {"right": 0, "up": 90, "left": 180, "down": 270}[self.facing]
        surf = pygame.transform.rotate(assets.sprites.get("pickup_arrow"), angle - 45)
        target.blit(surf, (round(self.x) - surf.get_width() // 2 + 8,
                           round(self.y) + oy - surf.get_height() // 2 + 8))


def shoot_arrow(world: World, hero: Hero) -> bool:
    """Loose an arrow. False if the quiver is empty."""
    if world.state.arrows <= 0:
        world.audio.play("error")
        return False
    world.state.arrows -= 1
    cx, cy = hero.center
    world.spawn(Arrow(cx - 8, cy - 8, hero.facing))
    world.audio.play("arrow")
    return True
