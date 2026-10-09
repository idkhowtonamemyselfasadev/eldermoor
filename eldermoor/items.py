"""The item registry: data/items/items.json plus the queries menus and the HUD make."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from eldermoor.config import DATA

# kinds that may be put in the B / X / Y slots
ASSIGNABLE = frozenset({"active"})


@dataclass(frozen=True)
class ItemDef:
    """One item: its id, display-name key, 8x8 icon, kind and inventory order."""

    id: str
    name: str
    icon: str
    kind: str                     # active | equip | passive | quest | collect | consumable
    order: int = 0
    desc: str = ""
    cost: int = 0

    @property
    def assignable(self) -> bool:
        """True if this item can sit in a B/X/Y slot."""
        return self.kind in ASSIGNABLE


class ItemRegistry:
    """All items, keyed by id, in inventory order."""

    def __init__(self, items: dict[str, ItemDef]) -> None:
        self.items = items

    @classmethod
    def load(cls, root: Path = DATA) -> ItemRegistry:
        """Read data/items/items.json."""
        raw = json.loads((root / "items" / "items.json").read_text(encoding="utf-8"))
        items: dict[str, ItemDef] = {}
        for i, (item_id, d) in enumerate(raw["items"].items()):
            items[item_id] = ItemDef(id=item_id, name=d["name"], icon=d.get("icon", "icon_empty"),
                                     kind=d.get("kind", "quest"), order=int(d.get("order", i)),
                                     desc=d.get("desc", ""), cost=int(d.get("cost", 0)))
        return cls(items)

    def __contains__(self, item_id: object) -> bool:
        return item_id in self.items

    def __getitem__(self, item_id: str) -> ItemDef:
        return self.items[item_id]

    def get(self, item_id: str) -> ItemDef | None:
        """ItemDef or None."""
        return self.items.get(item_id)

    def icon(self, item_id: str | None) -> str:
        """Icon block name for an item id (icon_empty for None/unknown)."""
        if item_id is None:
            return "icon_empty"
        d = self.items.get(item_id)
        return d.icon if d else "icon_empty"

    def ordered(self, owned: list[str], kind: str | None = None) -> list[ItemDef]:
        """Owned items in inventory order, optionally filtered by kind."""
        defs = [self.items[i] for i in owned if i in self.items]
        if kind is not None:
            defs = [d for d in defs if d.kind == kind]
        return sorted(defs, key=lambda d: d.order)

    def assignable_owned(self, owned: list[str]) -> list[ItemDef]:
        """Owned items that may be bound to B/X/Y."""
        return [d for d in self.ordered(owned) if d.assignable]
