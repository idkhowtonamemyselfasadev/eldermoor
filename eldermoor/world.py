"""The world: the current room, the hero, and flip-scroll transitions between rooms."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import FLIP_SCROLL_FRAMES, PLAY_H, PLAY_W, PLAY_Y
from eldermoor.entities import Entity, Hero
from eldermoor.tilemap import OPPOSITE, Room, Tileset

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.input import Input

EDGE_MARGIN = 6  # how far past the edge the hero's centre must go to trigger an exit


class FlipScroll:
    """A 12-frame screen flip: the old room slides out while the new one slides in."""

    def __init__(self, direction: str, old: pygame.Surface, new: pygame.Surface,
                 frames: int = FLIP_SCROLL_FRAMES) -> None:
        self.direction = direction
        self.old = old
        self.new = new
        self.frames = frames
        self.frame = 0

    @property
    def done(self) -> bool:
        """True once the scroll has run its full length."""
        return self.frame >= self.frames

    def update(self) -> None:
        """Advance one frame."""
        self.frame += 1

    def draw(self, target: pygame.Surface, oy: int = PLAY_Y) -> None:
        """Blit both rooms at their interpolated positions."""
        t = min(self.frame, self.frames) / self.frames
        if self.direction == "east":
            dx = -round(PLAY_W * t)
            target.blit(self.old, (dx, oy))
            target.blit(self.new, (dx + PLAY_W, oy))
        elif self.direction == "west":
            dx = round(PLAY_W * t)
            target.blit(self.old, (dx, oy))
            target.blit(self.new, (dx - PLAY_W, oy))
        elif self.direction == "south":
            dy = -round(PLAY_H * t)
            target.blit(self.old, (0, oy + dy))
            target.blit(self.new, (0, oy + dy + PLAY_H))
        else:  # north
            dy = round(PLAY_H * t)
            target.blit(self.old, (0, oy + dy))
            target.blit(self.new, (0, oy + dy - PLAY_H))


class World:
    """Owns the rooms, the hero and the active transition."""

    def __init__(self, assets: Assets, start_room: str = "meadow_00") -> None:
        self.assets = assets
        self.tilesets: dict[str, Tileset] = {}
        self.room = Room.load(start_room, tilesets=self.tilesets)
        self.hero = Hero(*self.room.spawn)
        self.entities: list[Entity] = [self.hero]
        self.transition: FlipScroll | None = None
        self._room_surface: pygame.Surface | None = None
        self.rooms_visited: list[str] = [start_room]

    # ----- rooms ---------------------------------------------------------
    def room_surface(self) -> pygame.Surface:
        """The current room's tile layer, rendered once and cached."""
        if self._room_surface is None:
            self._room_surface = self.room.render(self.assets)
        return self._room_surface

    def warp(self, room_id: str, x: float | None = None, y: float | None = None) -> None:
        """Jump straight to a room (debug / later: stairs, save load)."""
        self.room = Room.load(room_id, tilesets=self.tilesets)
        self._room_surface = None
        self.transition = None
        self.hero.x = self.room.spawn[0] if x is None else x
        self.hero.y = self.room.spawn[1] if y is None else y
        self.entities = [self.hero]
        if room_id not in self.rooms_visited:
            self.rooms_visited.append(room_id)

    def exit_direction(self) -> str | None:
        """Which edge the hero has walked past, if any."""
        cx = self.hero.x + self.hero.width / 2
        cy = self.hero.y + self.hero.height / 2
        if cx < -EDGE_MARGIN + 8:
            return "west"
        if cx > PLAY_W + EDGE_MARGIN - 8:
            return "east"
        if cy < -EDGE_MARGIN + 8:
            return "north"
        if cy > PLAY_H + EDGE_MARGIN - 8:
            return "south"
        return None

    def start_transition(self, direction: str) -> None:
        """Begin a flip-scroll to the room through the given exit."""
        target = self.room.exits[direction]
        old = self.room_surface().copy()
        new_room = Room.load(target, tilesets=self.tilesets)
        self.room = new_room
        self._room_surface = None
        self._place_hero_on_entry(direction)
        new = self.room_surface().copy()
        self.hero.draw(new, self.assets, 0)
        self.transition = FlipScroll(direction, old, new)
        if target not in self.rooms_visited:
            self.rooms_visited.append(target)

    def _place_hero_on_entry(self, direction: str) -> None:
        h = self.hero
        if direction == "east":
            h.x = 0
        elif direction == "west":
            h.x = PLAY_W - h.width
        elif direction == "south":
            h.y = 0
        else:
            h.y = PLAY_H - h.height
        h.moving = False
        h.anim_frame = 1

    # ----- frame ---------------------------------------------------------
    def update(self, inp: Input) -> None:
        """One logic frame: run the transition, or entities + exit checks."""
        if self.transition is not None:
            self.transition.update()
            if self.transition.done:
                self.transition = None
            return
        for e in self.entities:
            e.update(inp, self.room)
        direction = self.exit_direction()
        if direction is None:
            return
        if direction in self.room.exits:
            self.start_transition(direction)
        else:
            self.hero.clamp_to_room()

    def draw(self, target: pygame.Surface, oy: int = PLAY_Y) -> None:
        """Draw the play area at vertical offset ``oy``."""
        if self.transition is not None:
            self.transition.draw(target, oy)
            return
        target.blit(self.room_surface(), (0, oy))
        for e in sorted(self.entities, key=lambda e: e.y):
            e.draw(target, self.assets, oy)

    @property
    def opposite(self) -> dict[str, str]:
        """Exit direction -> opposite, exposed for tools."""
        return OPPOSITE
