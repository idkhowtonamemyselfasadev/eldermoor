"""The trading chain: ten people, each wanting what the last one gave.

``data/trade.json`` is the chain. ``GameState.trade`` is how far along it is:
step N means Wren is carrying step N's item and is looking for the person who
wants it. Nothing goes in the bag, because the chain is only ever one thing
long, and the last person pays a ring.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eldermoor.config import DATA

if TYPE_CHECKING:
    from eldermoor.world import World


@dataclass(frozen=True)
class TradeStep:
    """One link in the chain: what it hands over and what it says."""

    index: int
    item: str
    icon: str
    ask: str
    take: str
    done: str
    gives: dict[str, Any]


class Trade:
    """The whole chain, in order."""

    def __init__(self, steps: list[TradeStep]) -> None:
        self.steps = steps

    @classmethod
    def load(cls, root: Path = DATA) -> Trade:
        """Read data/trade.json."""
        path = root / "trade.json"
        if not path.exists():
            return cls([])
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls([TradeStep(index=i, item=d["item"], icon=d.get("icon", "icon_empty"),
                              ask=d["ask"], take=d["take"], done=d["done"],
                              gives=dict(d.get("gives", {})))
                    for i, d in enumerate(raw["steps"])])

    def __len__(self) -> int:
        return len(self.steps)

    def step(self, index: int) -> TradeStep | None:
        """One step, or None if the index is off the end."""
        return self.steps[index] if 0 <= index < len(self.steps) else None

    def carrying(self, at: int) -> TradeStep | None:
        """The step whose item Wren is holding, if any."""
        return self.step(at - 1) if at > 0 else None


def talk(world: World, index: int) -> bool:
    """One conversation with the person who serves step ``index``."""
    chain = world.content.trade
    step = chain.step(index)
    if step is None:
        world.say("npc.hello")
        return True
    at = world.state.trade
    if at > index:
        world.say(step.done)
        return True
    if at < index:
        world.say(step.ask if index == 0 else "trade.nothing")
        if index == 0:
            world.state.trade = 1
            world.audio.play("item_get")
        return True
    world.state.trade = index + 1
    world.audio.play("item_get")
    for what, value in step.gives.items():
        if what == "ring":
            world.state.find_ring(str(value))
        elif what == "item":
            world.grant(str(value))
    world.say(step.take)
    world.trigger("traded", index)
    return True
