#!/usr/bin/env python3
"""Put the people, props and cave mouths on the overworld map.

The quest table (``data/quests/quests.json``) says who asks and in which
region; the tokens and quest-item chests are listed here because they are
placement, not content. Every object is keyed by its quest id, so running
this again moves nothing and duplicates nothing: it rewrites its own entries
in ``data/overworld/sheet.json`` and leaves everything else alone.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

SHEET = ROOT / "data" / "overworld" / "sheet.json"

#: quest id -> the screen its giver stands on
GIVERS = {
    "q_cat": "ow_1105", "q_bread": "ow_1106", "q_lamp": "ow_1104", "q_broom": "ow_1107",
    "q_letter": "ow_1204", "q_shells5": "ow_1205", "q_shells20": "ow_1206",
    "q_bestiary": "ow_1207",
    "q_sheep": "ow_1004", "q_flowers": "ow_0805", "q_bridge": "ow_1008", "q_well": "ow_0905",
    "q_honey": "ow_0304", "q_woodcutter": "ow_0305", "q_mushroom": "ow_0302",
    "q_net": "ow_1212", "q_tide": "ow_1213", "q_crab": "ow_1312", "q_gull": "ow_1214",
    "q_water": "ow_0513", "q_dig": "ow_0514", "q_glass": "ow_0512",
    "q_coal": "ow_0112", "q_bellows": "ow_0113",
    "q_skates": "ow_0106", "q_mirror": "ow_0108",
    "q_frogs": "ow_0408", "q_oil": "ow_0407",
    "q_ghost": "ow_0001", "q_quiet": "ow_0002",
}

#: the chests that hold a quest item: item -> screen
QUEST_ITEMS = {
    "q_wheat": "ow_0907", "q_letter": "ow_1203", "q_flowers": "ow_0804",
    "q_wood": "ow_0303", "q_honey": "ow_0301", "q_mushroom": "ow_0300",
    "q_bread": "ow_1208", "q_water": "ow_0006", "q_sand": "ow_0415",
    "q_coal": "ow_0011", "q_shard": "ow_0007", "q_oil": "ow_0406",
}

#: single tokens: id -> (screen, sprite, flag it sets, text key, needs an item?)
TOKENS: dict[str, tuple[str, str, str, str, str]] = {
    "cat": ("ow_1005", "token_cat", "cat_found", "token.cat", ""),
    "well": ("ow_0906", "token_well", "well_bottom", "token.well", ""),
    "net": ("ow_1312", "token_net", "net_found", "token.net", "fins"),
    "boat": ("ow_1213", "token_boat", "boat_free", "token.boat", "gauntlet"),
    "bellows": ("ow_0113", "token_bellows", "bellows_fixed", "token.bellows", ""),
    "ice": ("ow_0107", "token_shard", "ice_crossed", "token.ice", ""),
}

#: the six optional caves: id -> (overworld screen, first room inside)
CAVES = {
    "grotto": ("ow_0306", "cv1_f1_0201"),
    "tidecave": ("ow_1211", "cv2_f1_0201"),
    "vent": ("ow_0114", "cv3_f1_0301"),
    "tarnhollow": ("ow_0109", "cv4_f1_0200"),
    "burrow": ("ow_0511", "cv5_f1_0302"),
    "warren": ("ow_0003", "cv6_f1_0301"),
}

#: counted sets: name -> (flag, sprite, text key, [screens])
SETS: dict[str, tuple[str, str, str, list[str]]] = {
    "sheep": ("sheep_home", "token_sheep", "token.sheep",
              ["ow_1003", "ow_0904", "ow_1006"]),
    "pots": ("pots_broken", "token_pot", "token.pot",
             ["ow_1107", "ow_1207", "ow_1206", "ow_1205", "ow_1204"]),
    "lamps": ("lamps_lit", "token_lamp", "token.lamp",
              ["ow_1104", "ow_1105", "ow_1106", "ow_1107"]),
    "paths": ("paths_cut", "token_bramble", "token.bramble",
              ["ow_0302", "ow_0303", "ow_0304", "ow_0305", "ow_0306", "ow_0307"]),
    "frogs": ("frogs_counted", "token_frog", "token.frog",
              ["ow_0405", "ow_0406", "ow_0407", "ow_0408", "ow_0409",
               "ow_0505", "ow_0506", "ow_0507", "ow_0508"]),
}


#: the doorway lanes. Nothing may stand in them: a screen is entered through
#: them, and a person standing there is a wall across the road.
LANE_COLS = (9, 10)
LANE_ROWS = (6, 7)


def free_cells(room: Any, taken: set[tuple[int, int]]) -> list[tuple[int, int]]:
    """Walkable cells clear of the doorway lanes and the spawn, outermost first."""
    from eldermoor.tilemap import BLOCKING
    spawn = (int(room.spawn[0]) // 16, int(room.spawn[1]) // 16)
    out = []
    for row in range(2, 11):
        for col in range(2, 18):
            if col in LANE_COLS or row in LANE_ROWS:
                continue
            if abs(col - spawn[0]) <= 1 and abs(row - spawn[1]) <= 1:
                continue
            if (col, row) in taken or room.collision_at(col, row) in BLOCKING:
                continue
            out.append((col, row))
    out.sort(key=lambda c: (-(abs(c[0] - 9.5) + abs(c[1] - 6.5)), c[1], c[0]))
    return out


class Placer:
    """Holds the sheet while objects are added, and remembers what is where."""

    def __init__(self) -> None:
        from eldermoor.tilemap import Room
        self.raw = json.loads(SHEET.read_text(encoding="utf-8"))
        self.screens = self.raw.setdefault("screens", {})
        self.room_of = Room.load
        self.tilesets: dict[str, Any] = {}
        self.used: dict[str, set[tuple[int, int]]] = {}

    def entries(self, room_id: str) -> list[dict[str, Any]]:
        """The object list of a screen, created if the screen is new."""
        screen = self.screens.setdefault(room_id, {})
        return screen.setdefault("objects", [])

    def occupied(self, room_id: str) -> set[tuple[int, int]]:
        """Cells already spoken for on a screen."""
        if room_id not in self.used:
            cells = {(int(o["at"][0]), int(o["at"][1]))
                     for o in self.entries(room_id) if "at" in o}
            self.used[room_id] = cells
        return self.used[room_id]

    def forget(self, ids: set[str]) -> None:
        """Drop earlier copies of the objects this tool owns, so they re-place."""
        for screen in self.screens.values():
            objects = screen.get("objects")
            if objects:
                screen["objects"] = [o for o in objects if str(o.get("id", "")) not in ids]

    def place(self, room_id: str, spec: dict[str, Any]) -> None:
        """Drop one object on a free cell, replacing any earlier copy of it."""
        objects = self.entries(room_id)
        key = str(spec.get("id", ""))
        for i, existing in enumerate(objects):
            if str(existing.get("id", "")) == key:
                spec["at"] = existing["at"]
                objects[i] = spec
                return
        room = self.room_of(room_id, tilesets=self.tilesets)
        taken = self.occupied(room_id)
        cells = free_cells(room, taken)
        if not cells:
            raise SystemExit(f"{room_id}: nowhere to put {key}")
        spec["at"] = list(cells[0])
        taken.add(cells[0])
        objects.append(spec)

    def place_wide(self, room_id: str, cave_id: str, target: str) -> None:
        """A two-tile cave mouth: one pair of stairs per tile, side by side."""
        from eldermoor.tilemap import BLOCKING
        objects = self.entries(room_id)
        room = self.room_of(room_id, tilesets=self.tilesets)
        taken = self.occupied(room_id)
        pairs = [(c, r) for c, r in free_cells(room, taken)
                 if (c + 1, r) not in taken and c + 1 < 18
                 and room.collision_at(c + 1, r) not in BLOCKING]
        if not pairs:
            raise SystemExit(f"{room_id}: nowhere to put the mouth of {cave_id}")
        col, row = pairs[0]
        for i in (0, 1):
            taken.add((col + i, row))
            objects.append({"kind": "stairs", "id": f"cave_{cave_id}", "at": [col + i, row],
                            "to": target, "spawn": [152, 160], "sound": "door_open"})

    def write(self) -> None:
        """Save the sheet."""
        SHEET.write_text(json.dumps(self.raw, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    """Place every giver, chest and token. Returns 0."""
    from eldermoor.quests import Quests
    table = Quests.load()
    placer = Placer()
    placer.forget(set(GIVERS) | {f"chest_{i}" for i in QUEST_ITEMS}
                  | {f"cave_{c}" for c in CAVES}
                  | {f"token_{n}" for n in TOKENS}
                  | {f"{n}{i}" for n, spec in SETS.items() for i in range(len(spec[3]))})
    for quest_id, room_id in GIVERS.items():
        quest = table.get(quest_id)
        if quest is None:
            raise SystemExit(f"no such quest: {quest_id}")
        placer.place(room_id, {"kind": "npc", "id": quest_id, "sprite": quest.sprite,
                               "quest": quest_id})
    for item, room_id in QUEST_ITEMS.items():
        placer.place(room_id, {"kind": "chest", "id": f"chest_{item}", "item": item,
                               "flag": f"chest:{item}"})
    for name, (screen, sprite, flag, text, needs) in TOKENS.items():
        spec = {"kind": "token", "id": f"token_{name}", "sprite": sprite,
                "sets": flag, "flag": f"token:{name}", "text": text, "vanish": True}
        if needs:
            spec["needs"] = needs
        placer.place(screen, spec)
    for name, (flag, sprite, text, screens) in SETS.items():
        for i, screen in enumerate(screens):
            placer.place(screen, {"kind": "token", "id": f"{name}{i}", "sprite": sprite,
                                  "count": name, "of": len(screens), "sets": flag,
                                  "flag": f"token:{name}{i}", "text": text, "vanish": True})
    for cave_id, (room_id, target) in CAVES.items():
        placer.place_wide(room_id, cave_id, target)
    placer.write()
    print(f"placed {len(CAVES)} cave mouths, {len(GIVERS)} givers, {len(QUEST_ITEMS)} quest chests, "
          f"{len(TOKENS) + sum(len(s[3]) for s in SETS.values())} tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
