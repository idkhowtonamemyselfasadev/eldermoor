"""Side quests: a table in data/quests/quests.json and the questions asked of it.

A quest is a giver and a condition. The giver is an NPC carrying
``{"quest": "<id>"}``; the condition is the ``needs`` row in the table and the
payment is the ``gives`` row. Nothing else in the game knows what a quest is,
so the thirty of them are thirty rows rather than thirty special cases.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eldermoor.config import DATA

if TYPE_CHECKING:
    from eldermoor.state import GameState
    from eldermoor.world import World

#: what a quest can ask for
NEEDS = ("item", "flag", "shells", "bestiary", "rooms", "pieces", "score")
#: what a quest can pay
GIVES = ("item", "ring", "figurine", "furniture", "heart_piece", "embers")


@dataclass(frozen=True)
class QuestDef:
    """One side quest: who asks, what for, and what they hand over."""

    id: str
    name: str
    hint: str
    region: str
    sprite: str
    needs: dict[str, Any]
    gives: dict[str, Any]

    @property
    def short(self) -> str:
        """The quest id without its ``q_`` prefix, which the strings use."""
        return self.id[2:] if self.id.startswith("q_") else self.id

    def line(self, which: str) -> str:
        """Text key for one of the giver's four lines."""
        return f"quest.{self.short}.{which}"

    @property
    def start_flag(self) -> str:
        """Flag set the first time the giver is spoken to."""
        return f"{self.id}:asked"


class Quests:
    """Every quest, keyed by id, with the state questions the menu asks."""

    def __init__(self, quests: dict[str, QuestDef]) -> None:
        self.quests = quests

    @classmethod
    def load(cls, root: Path = DATA) -> Quests:
        """Read data/quests/quests.json."""
        path = root / "quests" / "quests.json"
        if not path.exists():
            return cls({})
        raw = json.loads(path.read_text(encoding="utf-8"))
        out: dict[str, QuestDef] = {}
        for quest_id, d in raw["quests"].items():
            needs = dict(d.get("needs", {}))
            gives = dict(d.get("gives", {}))
            for table, allowed, label in ((needs, NEEDS, "needs"), (gives, GIVES, "gives")):
                unknown = set(table) - set(allowed)
                if unknown:
                    raise ValueError(f"quest {quest_id}: unknown {label} {sorted(unknown)}")
            out[quest_id] = QuestDef(id=quest_id, name=d["name"], hint=d["hint"],
                                     region=d.get("region", ""),
                                     sprite=d.get("sprite", "npc_elder"),
                                     needs=needs, gives=gives)
        return cls(out)

    def __contains__(self, quest_id: object) -> bool:
        return quest_id in self.quests

    def __len__(self) -> int:
        return len(self.quests)

    def get(self, quest_id: str) -> QuestDef | None:
        """QuestDef or None."""
        return self.quests.get(quest_id)

    def status(self, state: GameState, quest_id: str) -> str:
        """"done", "open" (asked, not finished) or "unknown" (never spoken to)."""
        quest = self.quests.get(quest_id)
        if quest is None:
            return "unknown"
        if quest_id in state.quests:
            return "done"
        return "open" if state.flag(quest.start_flag) else "unknown"

    def open_quests(self, state: GameState) -> list[QuestDef]:
        """Quests the player has been asked for and not yet finished."""
        return [q for q in self.quests.values() if self.status(state, q.id) == "open"]

    def done_quests(self, state: GameState) -> list[QuestDef]:
        """Quests the player has finished, in table order."""
        return [q for q in self.quests.values() if q.id in state.quests]


def satisfied(world: World, quest: QuestDef) -> bool:
    """True when the player is carrying or has done whatever the quest asks."""
    state = world.state
    for need, value in quest.needs.items():
        if need == "item" and not state.has(str(value)):
            return False
        if need == "flag" and not state.flag(str(value)):
            return False
        if need == "shells" and state.seashells < int(value):
            return False
        if need == "bestiary" and len(state.bestiary) < int(value):
            return False
        if need == "rooms" and len(state.rooms_visited) < int(value):
            return False
        if need == "pieces" and state.heart_pieces < int(value):
            return False
        if need == "score":
            game_id, want = str(value[0]), int(value[1])
            if state.scores.get(game_id, 0) < want:
                return False
    return True


def pay(world: World, quest: QuestDef) -> None:
    """Hand over a quest's reward and tick it off the log."""
    state = world.state
    state.finish_quest(quest.id)
    for gives, value in quest.gives.items():
        if gives == "item":
            world.grant(str(value))
        elif gives == "ring":
            state.find_ring(str(value))
        elif gives in ("figurine", "furniture"):
            state.collect(f"{gives}s" if gives == "figurine" else gives, str(value))
        elif gives == "heart_piece":
            state.add_heart_piece()
        elif gives == "embers":
            state.embers = min(999, state.embers + int(value))
    world.audio.play("quest_done")
    world.trigger("quest_done", quest.id)
