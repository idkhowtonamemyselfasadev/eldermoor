"""Rings: passive bonuses, two worn at a time, added together.

A ring is a row in ``data/items/rings.json`` and nothing more. The rest of
the game never looks at the worn list: it asks for one :class:`RingBonus`
and reads the field it cares about, so adding a ring is a data change.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path

from eldermoor.config import DATA


@dataclass(frozen=True)
class RingBonus:
    """Everything rings can change, summed over the worn rings."""

    damage: int = 0            # extra half-hearts per sword hit
    defence: int = 0           # half-hearts shaved off a hit (never below one)
    speed: float = 0.0         # fraction added to walking speed
    bombs: int = 0             # extra room in the bomb bag
    arrows: int = 0            # extra room in the quiver
    price: int = 0             # percent off shop prices
    luck: int = 0              # re-roll an empty drop this many times
    embers: int = 0            # extra embers per ember pickup
    roll: int = 0              # frames off the roll cooldown
    reflect: int = 0           # shots bounce off Wren without the cloak
    grip: int = 0              # ice does not carry him
    regen: int = 0             # frames between free half-hearts (0 = never)

    def __add__(self, other: RingBonus) -> RingBonus:
        """Sum two bonuses field by field."""
        return RingBonus(**{f.name: getattr(self, f.name) + getattr(other, f.name)
                            for f in fields(self)})


NO_BONUS = RingBonus()


@dataclass(frozen=True)
class RingDef:
    """One ring: its id, name and description keys, icon and bonus."""

    id: str
    name: str
    icon: str
    desc: str
    bonus: RingBonus


class Rings:
    """Every ring, keyed by id."""

    def __init__(self, rings: dict[str, RingDef]) -> None:
        self.rings = rings

    @classmethod
    def load(cls, root: Path = DATA) -> Rings:
        """Read data/items/rings.json."""
        path = root / "items" / "rings.json"
        if not path.exists():
            return cls({})
        raw = json.loads(path.read_text(encoding="utf-8"))
        known = {f.name for f in fields(RingBonus)}
        out: dict[str, RingDef] = {}
        for ring_id, d in raw["rings"].items():
            bonus = {k: v for k, v in d.get("bonus", {}).items() if k in known}
            unknown = set(d.get("bonus", {})) - known
            if unknown:
                raise ValueError(f"ring {ring_id}: unknown bonus {sorted(unknown)}")
            out[ring_id] = RingDef(id=ring_id, name=d["name"], icon=d.get("icon", "icon_empty"),
                                   desc=d.get("desc", ""), bonus=RingBonus(**bonus))
        return cls(out)

    def __contains__(self, ring_id: object) -> bool:
        return ring_id in self.rings

    def __len__(self) -> int:
        return len(self.rings)

    def get(self, ring_id: str) -> RingDef | None:
        """RingDef or None."""
        return self.rings.get(ring_id)

    def ordered(self, owned: list[str]) -> list[RingDef]:
        """Owned rings in table order."""
        order = list(self.rings)
        return [self.rings[r] for r in sorted(set(owned) & set(order), key=order.index)]

    def bonus(self, worn: list[str | None]) -> RingBonus:
        """The summed bonus of the rings on Wren's fingers."""
        total = NO_BONUS
        for ring_id in worn:
            ring = self.rings.get(ring_id or "")
            if ring is not None:
                total = total + ring.bonus
        return total
