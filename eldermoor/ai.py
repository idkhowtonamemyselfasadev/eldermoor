"""Data-defined AI: a tiny state machine plus the movement modes states can ask for.

A state looks like::

    "dash": {"move": "dash", "speed": 2.2, "time": 20, "next": "rest",
             "if_far": {"dist": 90, "go": "wander"}}

``move`` picks one of the functions in MOVES, ``time`` is how many frames the
state lasts, ``next`` is where it goes afterwards, and ``if_near``/``if_far``
jump early depending on the distance to the hero.  ``telegraph`` marks the
wind-up frames that PROMPT.md requires to be readable.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from eldermoor.entities import DIRS, Entity, facing_from

if TYPE_CHECKING:
    from eldermoor.world import World

MoveFn = Callable[["Entity", "World", dict[str, Any]], None]


def _towards(ent: Entity, world: World) -> tuple[float, float]:
    ax, ay = ent.center
    bx, by = world.hero.center
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy) or 1.0
    return dx / length, dy / length


def move_none(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Stand still."""


def move_chase(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Walk straight at the hero."""
    dx, dy = _towards(ent, world)
    speed = float(params.get("speed", ent.speed))
    ent.facing = facing_from(dx, dy, ent.facing)
    ent.move(world, dx * speed, dy * speed)


def move_flee(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Walk away from the hero."""
    dx, dy = _towards(ent, world)
    speed = float(params.get("speed", ent.speed))
    ent.facing = facing_from(-dx, -dy, ent.facing)
    ent.move(world, -dx * speed, -dy * speed)


def move_wander(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Drift in a direction, picking a new one when blocked or on a timer."""
    speed = float(params.get("speed", ent.speed))
    if ent.heading == (0.0, 0.0) or ent.state_time % int(params.get("turn", 45)) == 0:
        angle = world.rng.uniform(0, math.tau)
        ent.heading = (math.cos(angle), math.sin(angle))
    hit_x, hit_y = ent.move(world, ent.heading[0] * speed, ent.heading[1] * speed)
    if hit_x or hit_y:
        ent.heading = (-ent.heading[0] if hit_x else ent.heading[0],
                       -ent.heading[1] if hit_y else ent.heading[1])
    ent.facing = facing_from(ent.heading[0], ent.heading[1], ent.facing)


def move_patrol(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """March in one of the four directions, reversing at walls."""
    speed = float(params.get("speed", ent.speed))
    if ent.heading == (0.0, 0.0):
        ent.heading = DIRS[ent.facing]
    hit_x, hit_y = ent.move(world, ent.heading[0] * speed, ent.heading[1] * speed)
    if hit_x or hit_y:
        ent.heading = (-ent.heading[0], -ent.heading[1])
    ent.facing = facing_from(ent.heading[0], ent.heading[1], ent.facing)


def move_dash(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Charge in the direction locked in when the state began."""
    speed = float(params.get("speed", ent.speed * 2.5))
    if ent.state_time == 0:
        ent.heading = _towards(ent, world)
        ent.facing = facing_from(ent.heading[0], ent.heading[1], ent.facing)
    hit_x, hit_y = ent.move(world, ent.heading[0] * speed, ent.heading[1] * speed)
    if hit_x or hit_y:
        ent.state_time = 10 ** 6          # a wall ends the charge


def move_hop(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Leap towards the hero in an arc; ``height`` is the drawn hop."""
    period = int(params.get("period", 40))
    speed = float(params.get("speed", ent.speed))
    phase = ent.state_time % period
    if phase == 0:
        ent.heading = _towards(ent, world)
    air = period // 2
    if phase < air:
        ent.move(world, ent.heading[0] * speed, ent.heading[1] * speed)
        ent.hop = round(float(params.get("height", 6)) * math.sin(math.pi * phase / air))
    else:
        ent.hop = 0


def move_float(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Drift at the hero through walls, on a lazy sine."""
    dx, dy = _towards(ent, world)
    speed = float(params.get("speed", ent.speed))
    wobble = math.sin(ent.frame / 20.0) * float(params.get("wobble", 0.4))
    ent.x += dx * speed - dy * wobble
    ent.y += dy * speed + dx * wobble
    ent.clamp_to_room()
    ent.facing = facing_from(dx, dy, ent.facing)


def move_circle(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Orbit the hero at a set radius."""
    ax, ay = ent.center
    bx, by = world.hero.center
    angle = math.atan2(ay - by, ax - bx) + float(params.get("spin", 0.05))
    radius = float(params.get("radius", 48))
    ent.x = bx + math.cos(angle) * radius - ent.width / 2
    ent.y = by + math.sin(angle) * radius - ent.height / 2
    ent.clamp_to_room()


def move_shoot(ent: Entity, world: World, params: dict[str, Any]) -> None:
    """Fire a projectile on the first frame of the state, then hold still."""
    if ent.state_time != 0:
        return
    dx, dy = _towards(ent, world)
    ent.facing = facing_from(dx, dy, ent.facing)
    world.spawn_projectile(ent, dx, dy, params)


MOVES: dict[str, MoveFn] = {
    "none": move_none, "chase": move_chase, "flee": move_flee, "wander": move_wander,
    "patrol": move_patrol, "dash": move_dash, "hop": move_hop, "float": move_float,
    "circle": move_circle, "shoot": move_shoot,
}


class Brain:
    """Runs one entity's state machine. Owned by the entity, driven once per frame."""

    def __init__(self, machine: dict[str, Any], rng: random.Random) -> None:
        self.machine = machine
        self.states: dict[str, dict[str, Any]] = machine.get("states", {})
        self.rng = rng
        self.state: str = machine.get("start", "idle")

    @property
    def current(self) -> dict[str, Any]:
        """The current state's parameters."""
        return self.states.get(self.state, {})

    @property
    def telegraphing(self) -> bool:
        """True while the entity is winding up a readable attack."""
        return bool(self.current.get("telegraph"))

    def go(self, ent: Entity, state: str) -> None:
        """Switch state and reset its timer."""
        if state in self.states:
            self.state = state
            ent.state_time = -1          # about to be incremented to 0

    def step(self, ent: Entity, world: World) -> None:
        """One frame: run the move function, then take any transition."""
        params = self.current
        MOVES.get(str(params.get("move", "none")), move_none)(ent, world, params)
        dist = ent.distance_to(world.hero)
        near = params.get("if_near")
        far = params.get("if_far")
        if near and dist <= float(near.get("dist", 32)):
            self.go(ent, str(near["go"]))
            return
        if far and dist >= float(far.get("dist", 96)):
            self.go(ent, str(far["go"]))
            return
        time = int(params.get("time", 0))
        if time and ent.state_time >= time - 1:
            self.go(ent, str(params.get("next", self.machine.get("start", "idle"))))
