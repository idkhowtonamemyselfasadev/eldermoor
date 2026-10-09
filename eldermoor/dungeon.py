"""Dungeon definitions: floors, the room grid the map screen draws, and the key graph."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eldermoor.config import DATA


@dataclass
class Floor:
    """One floor of a dungeon: a grid of room ids for the map screen."""

    number: int
    width: int
    height: int
    rooms: dict[str, tuple[int, int]] = field(default_factory=dict)

    def at(self, col: int, row: int) -> str | None:
        """Room id at a map cell, if any."""
        for room_id, (c, r) in self.rooms.items():
            if (c, r) == (col, row):
                return room_id
        return None


@dataclass
class Dungeon:
    """A whole dungeon: floors, entrance, boss room, item and flame.

    An optional cave is the same record with ``optional`` set and the
    ceremony left out: no small keys, no map, no compass and no Flame.
    """

    id: str
    name: str
    music: str
    entrance: str
    boss_room: str
    item: str
    flame: str
    small_keys: int
    floors: list[Floor] = field(default_factory=list)
    tileset: str = ""
    miniboss_room: str = ""
    return_room: str = ""
    entrance_spawn: tuple[int, int] = (152, 160)
    #: an optional cave: no keys, no map, no compass, no Flame, off the main line
    optional: bool = False

    @classmethod
    def load(cls, dungeon_id: str, root: Path = DATA) -> Dungeon:
        """Read data/dungeons/<id>.json."""
        raw = json.loads((root / "dungeons" / f"{dungeon_id}.json").read_text(encoding="utf-8"))
        floors = [Floor(number=int(f.get("n", i + 1)), width=int(f["w"]), height=int(f["h"]),
                        rooms={k: (int(v[0]), int(v[1])) for k, v in f["rooms"].items()})
                  for i, f in enumerate(raw.get("floors", []))]
        return cls(id=raw.get("id", dungeon_id), name=raw.get("name", dungeon_id),
                   music=raw.get("music", ""), entrance=raw["entrance"],
                   boss_room=raw.get("boss_room", ""), item=raw.get("item", ""),
                   flame=raw.get("flame", ""), small_keys=int(raw.get("small_keys", 0)),
                   floors=floors, tileset=raw.get("tileset", ""),
                   miniboss_room=raw.get("miniboss_room", ""),
                   return_room=raw.get("return_room", ""),
                   entrance_spawn=tuple(raw.get("entrance_spawn", (152, 160))),
                   optional=bool(raw.get("optional", False)))

    def floor(self, number: int) -> Floor | None:
        """Floor by number."""
        for f in self.floors:
            if f.number == number:
                return f
        return None

    def all_rooms(self) -> list[str]:
        """Every room id in the dungeon."""
        out: list[str] = []
        for f in self.floors:
            out.extend(f.rooms)
        return out


class Dungeons:
    """Every dungeon definition, keyed by id."""

    def __init__(self, items: dict[str, Dungeon]) -> None:
        self.items = items

    @classmethod
    def load(cls, root: Path = DATA) -> Dungeons:
        """Read every file in data/dungeons/."""
        folder = root / "dungeons"
        if not folder.exists():
            return cls({})
        out: dict[str, Dungeon] = {}
        for path in sorted(folder.glob("*.json")):
            out[path.stem] = Dungeon.load(path.stem, root)
        return cls(out)

    def get(self, dungeon_id: str) -> Dungeon | None:
        """Dungeon or None."""
        return self.items.get(dungeon_id)

    def __iter__(self) -> Any:
        return iter(self.items.values())

    def __len__(self) -> int:
        return len(self.items)
