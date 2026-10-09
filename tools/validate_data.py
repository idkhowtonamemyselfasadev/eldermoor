#!/usr/bin/env python3
"""Prove the game's data is playable before anyone plays it.

Checks, in order:

* every room loads, is 20x13 and uses legend characters its tileset defines;
* every exit is reciprocal and its doorway is at least two tiles wide
  (water, lava and pits count: gear is the gate, not the wall);
* every sprite, icon, tile, enemy, item and text key a room names exists;
* every enemy attack has a wind-up of at least ENEMY_TELEGRAPH_MIN frames;
* every dialogue line fits the three-line box without being cut off;
* every dungeon is **completable**: a flood fill that respects tile gates
  (webs need the Lantern, pits need the Feather), locked doors and the key
  count reaches the boss room and the Flame, and the dungeon holds at least
  as many small keys as it has small-key doors, so no key can be wasted.

    python tools/validate_data.py [--quiet]
"""
from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eldermoor.config import ENEMY_TELEGRAPH_MIN, PLAY_COLS, PLAY_ROWS  # noqa: E402
from eldermoor.content import Content  # noqa: E402
from eldermoor.objects import KINDS  # noqa: E402
from eldermoor.textbox import DIALOGUE_COLS, paginate  # noqa: E402
from eldermoor.tilemap import BLOCKING, SEALED, Collision, Room, Tileset, list_rooms  # noqa: E402

#: which held item clears which tile interaction
TOOL_FOR = {"cut": "sword", "burn": "lantern", "bomb": "bombs", "lift": "bracelet",
            "smash": "sword", "melt": "fire_boots"}
#: collision classes a held item lets you cross
CROSS_WITH = {Collision.PIT: "feather", Collision.WATER: "fins",
              Collision.LAVA: "fire_boots"}
EDGE_CELLS = {
    "north": [(c, 0) for c in range(PLAY_COLS)],
    "south": [(c, PLAY_ROWS - 1) for c in range(PLAY_COLS)],
    "west": [(0, r) for r in range(PLAY_ROWS)],
    "east": [(PLAY_COLS - 1, r) for r in range(PLAY_ROWS)],
}


class Report:
    """Collects problems so one run prints all of them."""

    def __init__(self, quiet: bool = False) -> None:
        self.problems: list[str] = []
        self.notes: list[str] = []
        self.quiet = quiet

    def fail(self, message: str) -> None:
        """Record a blocking problem."""
        self.problems.append(message)

    def note(self, message: str) -> None:
        """Record something worth printing on success."""
        self.notes.append(message)
        if not self.quiet:
            print("  " + message)


# ----- structural checks -------------------------------------------------
def check_rooms(report: Report, content: Content) -> dict[str, Room]:
    """Load every room and check shape, exits, sprites and references."""
    rooms: dict[str, Room] = {}
    tilesets: dict[str, Tileset] = {}
    for room_id in list_rooms():
        try:
            rooms[room_id] = Room.load(room_id, tilesets=tilesets)
        except (ValueError, KeyError, OSError) as exc:
            report.fail(f"{room_id}: {exc}")
    for room_id, room in rooms.items():
        _check_exits(report, rooms, room_id, room)
        _check_objects(report, content, room_id, room)
        _check_prizes_reachable(report, room_id, room)
    report.note(f"{len(rooms)} rooms, {len(tilesets)} tilesets")
    return rooms


def _check_exits(report: Report, rooms: dict[str, Room], room_id: str, room: Room) -> None:
    opposite = {"north": "south", "south": "north", "east": "west", "west": "east"}
    for direction, target in room.exits.items():
        if target not in rooms:
            report.fail(f"{room_id}: exit {direction} points at missing room {target}")
            continue
        if rooms[target].exits.get(opposite[direction]) != room_id:
            report.fail(f"{room_id}: exit {direction} to {target} is one-way")
        gaps = [cell for cell in EDGE_CELLS[direction]
                if room.collision_at(*cell) not in SEALED]
        if len(gaps) < 2:
            report.fail(f"{room_id}: {direction} doorway is {len(gaps)} tile(s) wide, want 2")
        other = rooms[target]
        back = opposite[direction]
        theirs = [cell for cell in EDGE_CELLS[back]
                  if other.collision_at(*cell) not in SEALED]
        axis = 0 if direction in ("north", "south") else 1
        if gaps and theirs and not {c[axis] for c in gaps} & {c[axis] for c in theirs}:
            report.fail(f"{room_id}: {direction} doorway does not line up with {target}")


def _check_objects(report: Report, content: Content, room_id: str, room: Room) -> None:
    for spec in room.objects:
        kind = str(spec.get("kind", ""))
        if kind == "enemy":
            if spec.get("type") not in content.enemies:
                report.fail(f"{room_id}: unknown enemy {spec.get('type')!r}")
            continue
        if kind not in KINDS:
            report.fail(f"{room_id}: unknown object kind {kind!r}")
        item = spec.get("item")
        if item and item not in content.items and item not in ("key", "bigkey", "map",
                                                               "compass", "embers", "heart"):
            report.fail(f"{room_id}: chest holds unknown item {item!r}")
        for key in ("text", "greeting"):
            value = spec.get(key)
            if value and not content.text.has(str(value)):
                report.fail(f"{room_id}: missing text key {value!r}")
        for line in spec.get("lines", []):
            if not content.text.has(str(line.get("text", ""))):
                report.fail(f"{room_id}: missing text key {line.get('text')!r}")
    for trigger in room.triggers:
        for action in trigger.get("do", []):
            if "say" in action and not content.text.has(str(action["say"])):
                report.fail(f"{room_id}: trigger says missing key {action['say']!r}")


def _check_prizes_reachable(report: Report, room_id: str, room: Room) -> None:
    """Every chest and reward must be standable-next-to from the room's own doorways."""
    entries: set[tuple[int, int]] = set()
    for side in room.exits:
        entries |= set(EDGE_CELLS[side])
    for spec in room.objects:
        if spec.get("kind") == "stairs":
            entries.add((int(spec["at"][0]), int(spec["at"][1])))
    if not entries:
        entries.add((room.spawn[0] // 16, room.spawn[1] // 16))
    every_tool = set(TOOL_FOR.values()) | set(CROSS_WITH.values())
    cells = passable_cells(room, every_tool, {"north", "south", "east", "west"})
    reached = flood(room, entries, cells)
    for spec in room.objects + [dict(a["spawn"]) for t in room.triggers
                                for a in t.get("do", []) if "spawn" in a]:
        if spec.get("kind") not in ("chest", "reward"):
            continue
        col, row = int(spec["at"][0]), int(spec["at"][1])
        near = {(col, row), (col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)}
        if not (near & reached):
            report.fail(f"{room_id}: {spec.get('kind')} at {col},{row} is walled in")


def check_enemies(report: Report, content: Content) -> None:
    """Every telegraph must be readable, and every sprite must exist."""
    for enemy_id, definition in content.enemies.defs.items():
        states = definition.ai.get("states", {})
        if definition.ai.get("start") not in states:
            report.fail(f"enemy {enemy_id}: start state {definition.ai.get('start')!r} missing")
        for name, state in states.items():
            target = state.get("next")
            if target and target not in states:
                report.fail(f"enemy {enemy_id}: state {name} -> missing {target!r}")
            for branch in ("if_near", "if_far"):
                go = (state.get(branch) or {}).get("go")
                if go and go not in states:
                    report.fail(f"enemy {enemy_id}: {name}.{branch} -> missing {go!r}")
            if state.get("telegraph") and int(state.get("time", 0)) < ENEMY_TELEGRAPH_MIN:
                report.fail(f"enemy {enemy_id}: telegraph {name} lasts "
                            f"{state.get('time')} frames, want >= {ENEMY_TELEGRAPH_MIN}")
    report.note(f"{len(content.enemies.defs)} enemy kinds")


def check_text(report: Report, content: Content) -> None:
    """Every line must fit the dialogue box."""
    for key, value in content.text.entries.items():
        pages = value if isinstance(value, list) else [value]
        for page in pages:
            if not isinstance(page, str):
                continue
            text = page.replace("{n}", "00").replace("{p}", "00").replace("{f}", "0")
            text = text.replace("{h}", "00").replace("{m}", "00")
            for line in [ln for pg in paginate(text) for ln in pg]:
                if len(line) > DIALOGUE_COLS:
                    report.fail(f"text {key}: line does not fit ({len(line)} chars)")
    report.note(f"{len(content.text.entries)} text keys")


# ----- reachability ------------------------------------------------------
def door_side(spec: dict) -> str:
    """Which exit a door object guards, from where it sits."""
    col, row = spec.get("at", (0, 0))
    if row <= 1:
        return "north"
    if row >= PLAY_ROWS - 2:
        return "south"
    return "west" if col <= 1 else "east"


def passable_cells(room: Room, items: set[str], open_sides: set[str]) -> set[tuple[int, int]]:
    """Cells the hero can stand on given what is in the bag and which doors are open."""
    blocked_by_door = {
        (int(s["at"][0]), int(s["at"][1]))
        for s in room.objects
        if s.get("kind") == "door" and door_side(s) not in open_sides
    }
    solid_objects = {
        (int(s["at"][0]), int(s["at"][1]))
        for s in room.objects
        if s.get("kind") in ("chest", "npc", "sign", "block", "crystal", "torch")
    }
    out: set[tuple[int, int]] = set()
    for row in range(PLAY_ROWS):
        for col in range(PLAY_COLS):
            if (col, row) in blocked_by_door or (col, row) in solid_objects:
                continue
            tile = room.tile_at(col, row)
            if tile is None:
                continue
            if tile.collision in BLOCKING:
                tool = TOOL_FOR.get(tile.interact)
                crossing = CROSS_WITH.get(tile.collision)
                if not ((tool and tool in items) or (crossing and crossing in items)):
                    continue
            out.add((col, row))
    return out


def flood(room: Room, start: set[tuple[int, int]], cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Four-way flood fill from the entry cells."""
    seen = {c for c in start if c in cells}
    queue = deque(seen)
    while queue:
        col, row = queue.popleft()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (col + dc, row + dr)
            if nxt in cells and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


#: a trigger event only fires once the hero holds this item
TRIGGER_NEEDS = {"torches_lit": "lantern", "torch_lit": "lantern"}


def room_gives(room: Room, reached: set[tuple[int, int]],
               items: set[str] | None = None) -> list[dict]:
    """Objects whose cell (or a neighbour of it) the hero can stand on.

    Objects a trigger spawns count only when that trigger can actually fire:
    a chest behind a torch puzzle is not a chest until the Lantern exists.
    """
    held = items if items is not None else set(TRIGGER_NEEDS.values())
    out: list[dict] = []
    specs = list(room.objects)
    for trigger in room.triggers:
        needed = TRIGGER_NEEDS.get(str(trigger.get("on", "")))
        if needed and needed not in held:
            continue
        for action in trigger.get("do", []):
            if "spawn" in action:
                specs.append(dict(action["spawn"]))
    for spec in specs:
        col, row = int(spec.get("at", (0, 0))[0]), int(spec.get("at", (0, 0))[1])
        near = {(col, row), (col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)}
        if near & reached:
            out.append(spec)
    return out


class DungeonRun:
    """A flood fill through a whole dungeon, tracking items, keys and doors."""

    def __init__(self, rooms: dict[str, Room], dungeon_rooms: list[str], entrance: str,
                 start_items: set[str]) -> None:
        self.rooms = rooms
        self.scope = set(dungeon_rooms)
        self.entrance = entrance
        self.items = set(start_items)
        self.keys = 0
        self.big_key = False
        self.small_doors: set[str] = set()
        self.opened: set[str] = set()
        self.reached: dict[str, set[tuple[int, int]]] = {}
        self.entries: dict[str, set[tuple[int, int]]] = {}

    def door_flags(self, room: Room) -> dict[str, tuple[str, str]]:
        """side -> (flag, lock) for the doors in a room."""
        out: dict[str, tuple[str, str]] = {}
        for spec in room.objects:
            if spec.get("kind") == "door":
                out[door_side(spec)] = (str(spec.get("flag", "")), str(spec.get("lock", "")))
        return out

    def open_sides(self, room: Room) -> set[str]:
        """Which of a room's doors are open given the current keys and flags."""
        sides: set[str] = set()
        for side, (flag, lock) in self.door_flags(room).items():
            if flag in self.opened:
                sides.add(side)
            elif lock == "shut":
                sides.add(side)            # triggers open these; assume the room can be cleared
            elif lock == "small" and self.keys > 0:
                sides.add(side)
                self.opened.add(flag)
                self.keys -= 1
            elif lock in ("big", "boss") and self.big_key:
                sides.add(side)
                self.opened.add(flag)
        return sides

    def collect(self, room: Room, reached: set[tuple[int, int]]) -> bool:
        """Take everything standable-next-to in a room. True if anything was new."""
        changed = False
        for spec in room_gives(room, reached, self.items):
            flag = str(spec.get("flag", f"{room.id}:{spec.get('kind')}:{spec.get('at')}"))
            if flag in self.opened:
                continue
            item = str(spec.get("item", ""))
            what = str(spec.get("what", ""))
            if spec.get("kind") == "chest":
                self.opened.add(flag)
                changed = True
                if item == "key":
                    self.keys += 1
                elif item == "bigkey":
                    self.big_key = True
                elif item:
                    self.items.add(item)
            elif spec.get("kind") == "reward":
                self.opened.add(flag)
                self.items.add(what if what != "flame" else "flame")
                changed = True
        return changed

    def run(self) -> None:
        """Flood the dungeon until nothing new is reachable."""
        self.entries = {self.entrance: {(9, 11), (10, 11), (9, 6), (10, 6)}}
        changed = True
        while changed:
            changed = False
            for room_id in list(self.entries):
                room = self.rooms[room_id]
                cells = passable_cells(room, self.items, self.open_sides(room))
                reached = flood(room, self.entries[room_id], cells)
                if reached != self.reached.get(room_id):
                    self.reached[room_id] = reached
                    changed = True
                if self.collect(room, reached):
                    changed = True
                for side, target in room.exits.items():
                    if target not in self.scope:
                        continue
                    if not (set(EDGE_CELLS[side]) & reached):
                        continue
                    back = {"north": "south", "south": "north", "east": "west", "west": "east"}[side]
                    entry = set(EDGE_CELLS[back])
                    if entry - self.entries.get(target, set()):
                        self.entries.setdefault(target, set()).update(entry)
                        changed = True
                for spec in room.objects:
                    if spec.get("kind") != "stairs":
                        continue
                    cell = (int(spec["at"][0]), int(spec["at"][1]))
                    target = str(spec["to"])
                    if cell in reached and target in self.scope:
                        spawn = {(9, 6), (10, 6), (9, 11), (10, 11), (9, 1), (10, 1)}
                        if spawn - self.entries.get(target, set()):
                            self.entries.setdefault(target, set()).update(spawn)
                            changed = True


def check_dungeons(report: Report, content: Content, rooms: dict[str, Room]) -> None:
    """Every dungeon must be completable, with no key able to be wasted."""
    for dungeon in content.dungeons:
        ids = dungeon.all_rooms()
        missing = [r for r in ids if r not in rooms]
        if missing:
            report.fail(f"{dungeon.id}: map names missing rooms {missing}")
            continue
        stray = [r for r, room in rooms.items() if room.dungeon == dungeon.id and r not in ids]
        if stray:
            report.fail(f"{dungeon.id}: rooms not on the map {stray}")
        run = DungeonRun(rooms, ids, dungeon.entrance, {"sword", "shield", "feather"})
        run.run()
        unreached = [r for r in ids if r not in run.reached]
        if unreached:
            report.fail(f"{dungeon.id}: unreachable rooms {unreached}")
        if dungeon.boss_room not in run.reached:
            report.fail(f"{dungeon.id}: boss room {dungeon.boss_room} cannot be reached")
        if dungeon.flame and "flame" not in run.items:
            report.fail(f"{dungeon.id}: the Flame cannot be taken")
        for needed in ("map", "compass", dungeon.item):
            if needed and needed not in run.items:
                report.fail(f"{dungeon.id}: {needed} cannot be collected")
        if dungeon.small_keys and not run.big_key:
            report.fail(f"{dungeon.id}: the Great Key cannot be collected")
        keys, doors = _count_keys_and_doors(rooms, ids)
        if keys < doors:
            report.fail(f"{dungeon.id}: {keys} small keys for {doors} locked doors")
        report.note(f"{dungeon.id}: {len(ids)} rooms, {keys} keys, {doors} locked doors, "
                    f"flame reachable")


def _count_keys_and_doors(rooms: dict[str, Room], ids: list[str]) -> tuple[int, int]:
    keys = 0
    doors: set[str] = set()
    for room_id in ids:
        room = rooms[room_id]
        specs = list(room.objects)
        for trigger in room.triggers:
            for action in trigger.get("do", []):
                if "spawn" in action:
                    specs.append(dict(action["spawn"]))
        for spec in specs:
            if spec.get("kind") == "chest" and spec.get("item") == "key":
                keys += 1
            if spec.get("kind") == "door" and spec.get("lock") == "small":
                doors.add(str(spec.get("flag", "")))
    return keys, len(doors)


def main(argv: list[str] | None = None) -> int:
    """Run every check and print a verdict."""
    parser = argparse.ArgumentParser(description="validate Eldermoor's data")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    report = Report(args.quiet)
    content = Content()
    if not args.quiet:
        print("validating data/ ...")
    rooms = check_rooms(report, content)
    check_enemies(report, content)
    check_text(report, content)
    check_dungeons(report, content, rooms)
    for problem in report.problems:
        print("FAIL", problem, file=sys.stderr)
    print(f"{len(report.problems)} problems")
    return 1 if report.problems else 0


if __name__ == "__main__":
    sys.exit(main())
