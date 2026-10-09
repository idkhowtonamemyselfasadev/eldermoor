"""Map sheets: one hand-painted canvas sliced into screens.

A sheet is a directory holding ``sheet.json`` and one or more ``.map`` files.
A ``.map`` file is a plain character canvas: ``rows x PLAY_ROWS`` lines of
``cols x PLAY_COLS`` legend characters, so screen (r, c) is the block at
lines ``r * 13`` and columns ``c * 20``.

Painting the world as one canvas keeps neighbouring screens honest: a road
that leaves one screen is the same row of characters entering the next, and
exits are derived from where both sides are walkable rather than declared
twice.
"""
from __future__ import annotations

import json
import random
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eldermoor.config import DATA, PLAY_COLS, PLAY_ROWS
from eldermoor.tilemap import BLOCKING, OPPOSITE, Room, Tileset

#: a doorway needs this many walkable tiles on both sides to count as an exit
DOORWAY_MIN = 2
EDGE_INDEX = {"north": 0, "south": PLAY_ROWS - 1, "west": 0, "east": PLAY_COLS - 1}


@dataclass
class SheetLayer:
    """One canvas of the sheet (a floor, or the single overworld layer)."""

    name: str
    lines: list[str]
    rows: int
    cols: int
    index: int = 1


class MapSheet:
    """A directory of canvases plus the per-screen extras in sheet.json."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        raw = json.loads((folder / "sheet.json").read_text(encoding="utf-8"))
        self.raw = raw
        self.prefix: str = raw["prefix"]
        self.tileset: str = raw.get("tileset", "meadow")
        self.default_region: str = raw.get("region", "meadow")
        self.default_music: str = raw.get("music", "")
        self.dungeon: str = raw.get("dungeon", "")
        self.screens: dict[str, dict[str, Any]] = raw.get("screens", {})
        self.region_key: dict[str, str] = raw.get("region_names", {})
        self.region_grid: dict[str, list[str]] = raw.get("regions", {})
        self.region_spawns: dict[str, dict[str, Any]] = raw.get("region_spawns", {})
        self.night_music: str = raw.get("night_music", "")
        #: dungeon ids name their floor ("t2_f1_0502"); the overworld does not
        self.id_layer: bool = bool(raw.get("id_layer", len(raw["layers"]) > 1))
        self.layers: dict[str, SheetLayer] = {}
        for entry in raw["layers"]:
            self.layers[entry["name"]] = self._load_layer(entry)

    def _load_layer(self, entry: dict[str, Any]) -> SheetLayer:
        path = self.folder / f"{entry['name']}.map"
        # '|' is an authoring aid: it separates screens so a 320-character line
        # can be read, and is stripped before anything looks at the tiles. A
        # comment is '#' plus a space, because '#' alone paints a fence.
        lines = [ln.replace("|", "") for ln in path.read_text(encoding="utf-8").splitlines()
                 if not (ln.startswith("#") and (len(ln) == 1 or ln[1] == " "))]
        rows, cols = int(entry["rows"]), int(entry["cols"])
        want_lines = rows * PLAY_ROWS
        if len(lines) != want_lines:
            raise ValueError(f"{path.name}: {len(lines)} lines, want {want_lines}")
        width = cols * PLAY_COLS
        for i, line in enumerate(lines):
            if len(line) != width:
                raise ValueError(f"{path.name}: line {i} is {len(line)} wide, want {width}")
        return SheetLayer(entry["name"], lines, rows, cols, int(entry.get("floor", 1)))

    # ----- ids -----------------------------------------------------------
    def room_id(self, layer: SheetLayer, row: int, col: int) -> str:
        """Id of one screen, e.g. ``ow_0713`` or ``t2_f1_0304``."""
        if self.id_layer:
            return f"{self.prefix}_{layer.name}_{row:02d}{col:02d}"
        return f"{self.prefix}_{row:02d}{col:02d}"

    def room_ids(self) -> list[str]:
        """Every screen this sheet can make."""
        out: list[str] = []
        for layer in self.layers.values():
            for row in range(layer.rows):
                for col in range(layer.cols):
                    if self.is_blank(layer, row, col):
                        continue
                    out.append(self.room_id(layer, row, col))
        return out

    def locate(self, room_id: str) -> tuple[SheetLayer, int, int] | None:
        """Find which layer and cell a room id names."""
        if not room_id.startswith(self.prefix + "_"):
            return None
        rest = room_id[len(self.prefix) + 1:]
        layer_name = ""
        if self.id_layer:
            layer_name, _, rest = rest.partition("_")
        if len(rest) != 4 or not rest.isdigit():
            return None
        layer = self.layers.get(layer_name) if layer_name else next(iter(self.layers.values()))
        if layer is None:
            return None
        row, col = int(rest[:2]), int(rest[2:])
        if not (0 <= row < layer.rows and 0 <= col < layer.cols):
            return None
        return layer, row, col

    # ----- tiles ---------------------------------------------------------
    def block(self, layer: SheetLayer, row: int, col: int) -> list[str]:
        """The 13 rows of 20 characters for one screen."""
        top = row * PLAY_ROWS
        left = col * PLAY_COLS
        return [layer.lines[top + r][left:left + PLAY_COLS] for r in range(PLAY_ROWS)]

    def is_blank(self, layer: SheetLayer, row: int, col: int) -> bool:
        """True for a screen painted entirely with the 'nothing here' character."""
        return all(set(line) == {"%"} for line in self.block(layer, row, col))

    def region_of(self, layer: SheetLayer, row: int, col: int) -> str:
        """Region name for a screen, from the regions grid or the sheet default."""
        grid = self.region_grid.get(layer.name)
        if grid and row < len(grid) and col < len(grid[row]):
            return self.region_key.get(grid[row][col], self.default_region)
        return self.default_region

    # ----- rooms ---------------------------------------------------------
    def exits(self, layer: SheetLayer, row: int, col: int, ts: Tileset) -> dict[str, str]:
        """Exits derived from both sides of each edge being walkable."""
        here = self.block(layer, row, col)
        out: dict[str, str] = {}
        for direction, (dr, dc) in (("north", (-1, 0)), ("south", (1, 0)),
                                    ("west", (0, -1)), ("east", (0, 1))):
            nr, nc = row + dr, col + dc
            if not (0 <= nr < layer.rows and 0 <= nc < layer.cols):
                continue
            if self.is_blank(layer, nr, nc):
                continue
            there = self.block(layer, nr, nc)
            mine = self._edge_open(here, direction, ts)
            theirs = self._edge_open(there, OPPOSITE[direction], ts)
            shared = mine & theirs
            if len(shared) >= DOORWAY_MIN:
                out[direction] = self.room_id(layer, nr, nc)
        return out

    @staticmethod
    def _edge_open(block: list[str], direction: str, ts: Tileset) -> set[int]:
        """Indexes along one edge whose tile can be walked on."""
        open_at: set[int] = set()
        if direction in ("north", "south"):
            line = block[EDGE_INDEX[direction]]
            for c, ch in enumerate(line):
                if ts.tiles[ts.legend[ch]].collision not in BLOCKING:
                    open_at.add(c)
        else:
            index = EDGE_INDEX[direction]
            for r, line in enumerate(block):
                if ts.tiles[ts.legend[line[index]]].collision not in BLOCKING:
                    open_at.add(r)
        return open_at

    def wild_spawns(self, room_id: str, region: str, tiles: list[list[int]],
                    ts: Tileset) -> list[dict[str, Any]]:
        """Enemies for a screen with no hand-placed ones.

        256 screens is too many to stock one at a time, so each region names
        the creatures that live in it and how many a screen holds; the places
        they stand come from the room id, so a screen looks the same every
        time you walk back into it. A screen that lists its own objects in
        sheet.json is left alone.
        """
        entry = self.region_spawns.get(region)
        if not entry or not entry.get("types"):
            return []
        # a stable hash: Python's own is salted per process, which would move
        # every creature in the kingdom each time the game is launched
        rng = random.Random(zlib.crc32(room_id.encode()))
        free = [(c, r) for r in range(2, PLAY_ROWS - 2) for c in range(2, PLAY_COLS - 2)
                if ts.tiles[tiles[r][c]].collision not in BLOCKING]
        if not free:
            return []
        out: list[dict[str, Any]] = []
        for when, kinds in (("if_day", entry.get("types", [])),
                            ("if_night", entry.get("night", entry.get("types", [])))):
            if not kinds:
                continue
            for _ in range(int(entry.get("count", 0))):
                col, row = free[rng.randrange(len(free))]
                out.append({"kind": "enemy", "type": kinds[rng.randrange(len(kinds))],
                            "at": [col, row], when: True})
        return out

    def build(self, room_id: str, tilesets: dict[str, Tileset] | None = None,
              root: Path = DATA) -> Room:
        """Make the Room for one screen."""
        found = self.locate(room_id)
        if found is None:
            raise KeyError(room_id)
        layer, row, col = found
        extra = self.screens.get(room_id, {})
        ts_name = extra.get("tileset", self.tileset)
        ts = Room.tileset_for(ts_name, root, tilesets)
        tiles = Room.parse_tiles(room_id, self.block(layer, row, col), ts)
        spawn = tuple(extra.get("spawn", (PLAY_COLS * 8 - 8, PLAY_ROWS * 8 - 8)))
        objects = list(extra.get("objects", []))
        if not objects:
            objects = self.wild_spawns(room_id, extra.get("region", self.region_of(layer, row, col)),
                                       tiles, ts)
        return Room(
            id=room_id, tileset=ts, tiles=tiles,
            exits=self.exits(layer, row, col, ts),
            spawn=(int(spawn[0]), int(spawn[1])),
            name=extra.get("name", ""),
            objects=objects,
            triggers=list(extra.get("triggers", [])),
            dungeon=extra.get("dungeon", self.dungeon),
            floor=int(extra.get("floor", layer.index)),
            map_pos=(col, row),
            dark=bool(extra.get("dark", False)),
            music=extra.get("music", self.default_music),
            region=extra.get("region", self.region_of(layer, row, col)),
        )


_CACHE: dict[Path, list[MapSheet]] = {}


def sheets(root: Path = DATA) -> list[MapSheet]:
    """Every map sheet under data/ (overworld and dungeon floors), loaded once."""
    if root in _CACHE:
        return _CACHE[root]
    found: list[MapSheet] = []
    for config in sorted(root.glob("*/sheet.json")) + sorted(root.glob("*/*/sheet.json")):
        found.append(MapSheet(config.parent))
    _CACHE[root] = found
    return found


def forget_sheets() -> None:
    """Drop the cache (tests that write sheets on the fly)."""
    _CACHE.clear()


def find_sheet(room_id: str, root: Path = DATA) -> MapSheet | None:
    """The sheet that can build this room id, if any."""
    for sheet in sheets(root):
        if sheet.locate(room_id) is not None and not sheet.is_blank(*sheet.locate(room_id)):
            return sheet
    return None


def sheet_room_ids(root: Path = DATA) -> list[str]:
    """Every room id all sheets can make."""
    out: list[str] = []
    for sheet in sheets(root):
        out.extend(sheet.room_ids())
    return out
