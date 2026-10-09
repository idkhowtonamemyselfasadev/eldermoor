"""The post-game: the Boss Rush and the Master Quest.

The Boss Rush is a room the game walks you through: one boss at a time out of
``data/bossrush.json``, a little healing between rounds, and prizes for
getting far. The Master Quest is a flag on the save that makes every creature
in the kingdom hit harder and give up less.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from eldermoor.config import DATA

if TYPE_CHECKING:
    from eldermoor.state import GameState
    from eldermoor.world import World

#: how much the Master Quest changes things
MASTER_DAMAGE = 2.0
MASTER_HP = 1.5
#: the leaner drop table the Master Quest rolls instead of ``enemy``
MASTER_DROPS = {"enemy": "enemy_master"}


@dataclass(frozen=True)
class Rush:
    """The Boss Rush: its running order, its arena and its prizes."""

    rounds: list[str] = field(default_factory=list)
    room: str = "rush_arena"
    return_room: str = "ow_1105"
    heal_every: int = 2
    prizes: list[tuple[int, str, str]] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path = DATA) -> Rush:
        """Read data/bossrush.json."""
        path = root / "bossrush.json"
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(rounds=[str(r) for r in raw.get("rounds", [])],
                   room=str(raw.get("room", "rush_arena")),
                   return_room=str(raw.get("return_room", "ow_1105")),
                   heal_every=int(raw.get("heal_every", 2)),
                   prizes=[(int(p[0]), str(p[1]), str(p[2])) for p in raw.get("prizes", [])])

    def __len__(self) -> int:
        return len(self.rounds)

    def boss(self, index: int) -> str:
        """The boss for a round, or "" past the end."""
        return self.rounds[index] if 0 <= index < len(self.rounds) else ""


def master(state: GameState) -> bool:
    """True on a Master Quest file."""
    return bool(state.flag("master"))


def scale_damage(state: GameState, damage: int) -> int:
    """What a creature's hit costs on this file."""
    return round(damage * MASTER_DAMAGE) if master(state) else damage


def scale_hp(state: GameState, hp: int) -> int:
    """How much life a creature has on this file."""
    return max(1, round(hp * MASTER_HP)) if master(state) else hp


def drop_table(state: GameState, table: str) -> str:
    """Which drop table a creature rolls on this file."""
    return MASTER_DROPS.get(table, table) if master(state) else table


# ----- the rush -----------------------------------------------------------
def start(world: World) -> None:
    """Begin the rush: round one, in the arena, at full health."""
    state = world.state
    state.set_flag("rush:round", 0)
    state.set_flag("rush:running", 1)
    state.heal(99)
    world.warp(world.content.rush.room)
    spawn_round(world)


def spawn_round(world: World) -> None:
    """Put the current round's boss in the arena."""
    rush = world.content.rush
    index = world.state.flag("rush:round")
    boss = rush.boss(index)
    if not boss:
        finish(world)
        return
    world.spawn_from_spec({"kind": "enemy", "type": boss, "at": [9, 4]})
    world.audio.play("boss_roar")


def round_done(world: World) -> None:
    """One boss down: heal a little, count it, and bring on the next."""
    state = world.state
    index = state.flag("rush:round") + 1
    state.set_flag("rush:round", index)
    rush = world.content.rush
    if rush.heal_every and index % rush.heal_every == 0:
        state.heal(6)
        world.audio.play("heart")
    state.best_score("rush", index)
    if index >= len(rush):
        finish(world)
        return
    spawn_round(world)


def finish(world: World) -> None:
    """The rush is over, by victory or by falling: pay what was earned."""
    from eldermoor import minigames
    state = world.state
    reached = state.flag("rush:round")
    definition = minigames.GameDef(id="rush", name="rush.title", greeting="rush.hello",
                                   cost=0, prizes=world.content.rush.prizes)
    minigames.pay_prizes(world, definition, reached)
    state.set_flag("rush:round", 0)
    state.set_flag("rush:running", 0)
    world.say("rush.over", after=lambda _r: world.warp(world.content.rush.return_room))


def running(world: World) -> bool:
    """True while a Boss Rush is in progress."""
    return bool(world.state.flag("rush:running")) and world.room.id == world.content.rush.room
