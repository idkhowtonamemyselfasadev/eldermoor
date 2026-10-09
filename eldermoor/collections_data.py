"""The two display collections: figurines and house furniture.

Both are the same shape — an id, a name key, an icon — so one tiny registry
covers them, and the collection screens read it instead of hard-coding lists.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from eldermoor.config import DATA


@dataclass(frozen=True)
class CollectibleDef:
    """One figurine or one piece of furniture."""

    id: str
    name: str
    icon: str
    spot: str = ""


class Collection:
    """One named collection, in table order."""

    def __init__(self, name: str, entries: dict[str, CollectibleDef]) -> None:
        self.name = name
        self.entries = entries

    @classmethod
    def load(cls, name: str, root: Path = DATA) -> Collection:
        """Read data/collections/<name>.json."""
        path = root / "collections" / f"{name}.json"
        if not path.exists():
            return cls(name, {})
        raw = json.loads(path.read_text(encoding="utf-8"))
        out = {k: CollectibleDef(id=k, name=d["name"], icon=d.get("icon", "icon_empty"),
                                 spot=d.get("spot", ""))
               for k, d in raw[name].items()}
        return cls(name, out)

    def __contains__(self, item_id: object) -> bool:
        return item_id in self.entries

    def __len__(self) -> int:
        return len(self.entries)

    def get(self, item_id: str) -> CollectibleDef | None:
        """The entry, or None."""
        return self.entries.get(item_id)

    def ordered(self) -> list[CollectibleDef]:
        """Every entry in table order."""
        return list(self.entries.values())

    def owned(self, have: list[str]) -> list[CollectibleDef]:
        """The entries the player has, in table order."""
        return [d for d in self.entries.values() if d.id in have]
