"""Drop tables: what falls out of grass, pots, chests and dead enemies."""
from __future__ import annotations

import json
import random
from pathlib import Path

from eldermoor.config import DATA

#: pickup kind -> (sprite, sound, how much it gives)
PICKUPS: dict[str, tuple[str, str]] = {
    "heart": ("pickup_heart", "heart"),
    "ember": ("pickup_ember", "ember"),
    "ember5": ("pickup_ember", "ember_big"),
    "ember20": ("pickup_ember", "ember_big"),
    "bomb": ("pickup_bomb", "ember"),
    "arrow": ("pickup_arrow", "ember"),
    "magic": ("pickup_magic", "ember"),
    "fairy": ("pickup_fairy", "fairy"),
    "key": ("pickup_key", "key"),
    "shell": ("pickup_shell", "shell"),
}


class DropTables:
    """Weighted tables loaded from data/items/drops.json."""

    def __init__(self, tables: dict[str, list[tuple[str, int]]]) -> None:
        self.tables = tables

    @classmethod
    def load(cls, root: Path = DATA) -> DropTables:
        """Read data/items/drops.json."""
        raw = json.loads((root / "items" / "drops.json").read_text(encoding="utf-8"))
        tables = {name: [(e["kind"], int(e["weight"])) for e in entries]
                  for name, entries in raw.items() if not name.startswith("_")}
        return cls(tables)

    def roll(self, table: str, rng: random.Random | None = None) -> str | None:
        """Pick one pickup kind from a table, or None for nothing."""
        entries = self.tables.get(table)
        if not entries:
            return None
        rng = rng or random
        total = sum(w for _k, w in entries)
        if total <= 0:
            return None
        pick = rng.randrange(total)
        for kind, weight in entries:
            pick -= weight
            if pick < 0:
                return None if kind == "nothing" else kind
        return None
