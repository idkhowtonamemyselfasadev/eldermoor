"""Tilesets and rooms: JSON in data/, tile collision classes, tile interactions, rendering."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pygame

from eldermoor.config import DATA, PLAY_COLS, PLAY_H, PLAY_ROWS, PLAY_W, TILE

if TYPE_CHECKING:
    from eldermoor.assets import Assets


class Collision(StrEnum):
    """What a tile does to things standing on it."""

    FLOOR = "floor"
    SOLID = "solid"
    GRASS = "grass"          # tall grass: walkable, cuttable
    WATER = "water"
    LAVA = "lava"
    PIT = "pit"
    ICE = "ice"
    LEDGE_DOWN = "ledge_down"
    BOMBABLE = "bombable"
    LIFTABLE = "liftable"


BLOCKING = frozenset({Collision.SOLID, Collision.WATER, Collision.LAVA, Collision.PIT,
                      Collision.BOMBABLE, Collision.LIFTABLE})
#: a doorway is an exit unless solid rock stands in it: water, lava, pits,
#: cracked walls and blocks are all crossable or clearable with the right gear
SEALED = frozenset({Collision.SOLID})
#: classes a hopping entity (Feather) floats over
HOPPABLE = frozenset({Collision.PIT, Collision.WATER})
#: classes that hurt or swallow whatever walks onto them
HAZARD = frozenset({Collision.LAVA, Collision.PIT})

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
#: tile interactions: which tool clears the tile
INTERACTIONS = frozenset({"cut", "lift", "burn", "bomb", "smash", "melt"})


@dataclass(frozen=True)
class TileDef:
    """One tile kind: id, legend character, sprite block, collision and how it is cleared."""

    id: int
    char: str
    sprite: str
    collision: Collision
    interact: str = ""        # "" | cut | lift | burn | bomb | smash
    becomes: str = ""         # legend char of the tile left behind
    drop: str = ""            # drop-table name rolled when cleared
    hook: bool = False        # the Hookshot can bite into it


@dataclass
class Tileset:
    """A tileset JSON: tiles keyed by id, legend char -> id, and the region palette to draw with."""

    name: str
    region: str
    tiles: dict[int, TileDef] = field(default_factory=dict)
    legend: dict[str, int] = field(default_factory=dict)

    @classmethod
    def load(cls, name: str, root: Path = DATA) -> Tileset:
        """Read data/tilesets/<name>.json."""
        raw = json.loads((root / "tilesets" / f"{name}.json").read_text(encoding="utf-8"))
        ts = cls(name=raw.get("name", name), region=raw.get("region", "meadow"))
        for key, t in raw["tiles"].items():
            tid = int(key)
            interact = t.get("interact", "")
            if interact and interact not in INTERACTIONS:
                raise ValueError(f"tileset {name}: unknown interaction {interact!r}")
            td = TileDef(tid, t["char"], t["sprite"], Collision(t.get("collision", "floor")),
                         interact, t.get("becomes", ""), t.get("drop", ""),
                         bool(t.get("hook", False)))
            ts.tiles[tid] = td
            if td.char in ts.legend:
                raise ValueError(f"tileset {name}: legend char {td.char!r} used twice")
            ts.legend[td.char] = tid
        return ts

    def id_of(self, char: str) -> int:
        """Tile id for a legend character."""
        return self.legend[char]


@dataclass
class Room:
    """A single 20x13 screen: tiles, exits, objects and triggers.

    A Room is re-read from JSON every time it is entered, so changes made to
    ``tiles`` during a visit (cut bushes, smashed pots) undo themselves when
    the player leaves and comes back, exactly like the games this follows.
    Anything permanent lives in a global flag instead.
    """

    id: str
    tileset: Tileset
    tiles: list[list[int]]
    exits: dict[str, str] = field(default_factory=dict)
    spawn: tuple[int, int] = (PLAY_W // 2 - 8, PLAY_H // 2 - 8)
    name: str = ""
    objects: list[dict[str, Any]] = field(default_factory=list)
    triggers: list[dict[str, Any]] = field(default_factory=list)
    dungeon: str = ""
    floor: int = 0
    map_pos: tuple[int, int] = (0, 0)
    dark: bool = False
    music: str = ""
    region: str = ""

    # ----- loading -------------------------------------------------------
    @classmethod
    def load(cls, room_id: str, root: Path = DATA, tilesets: dict[str, Tileset] | None = None) -> Room:
        """Build a room: its own JSON file if it has one, else its map sheet."""
        path = root / "rooms" / f"{room_id}.json"
        if not path.exists():
            from eldermoor.mapsheet import find_sheet
            sheet = find_sheet(room_id, root)
            if sheet is None:
                raise FileNotFoundError(f"no room {room_id!r}")
            return sheet.build(room_id, tilesets, root)
        raw = json.loads(path.read_text(encoding="utf-8"))
        ts = cls.tileset_for(raw["tileset"], root, tilesets)
        tiles = cls.parse_tiles(room_id, raw["tiles"], ts)
        spawn = tuple(raw.get("spawn", (PLAY_W // 2 - 8, PLAY_H // 2 - 8)))
        map_pos = tuple(raw.get("map_pos", (0, 0)))
        return cls(
            id=raw.get("id", room_id), tileset=ts, tiles=tiles,
            exits={k: v for k, v in raw.get("exits", {}).items() if k in OPPOSITE},
            spawn=(int(spawn[0]), int(spawn[1])), name=raw.get("name", ""),
            objects=list(raw.get("objects", [])), triggers=list(raw.get("triggers", [])),
            dungeon=raw.get("dungeon", ""), floor=int(raw.get("floor", 0)),
            map_pos=(int(map_pos[0]), int(map_pos[1])), dark=bool(raw.get("dark", False)),
            music=raw.get("music", ""), region=raw.get("region", ""),
        )

    @staticmethod
    def tileset_for(name: str, root: Path, cache: dict[str, Tileset] | None) -> Tileset:
        if cache is not None and name in cache:
            return cache[name]
        ts = Tileset.load(name, root)
        if cache is not None:
            cache[name] = ts
        return ts

    @staticmethod
    def parse_tiles(room_id: str, rows: list[str], ts: Tileset) -> list[list[int]]:
        if len(rows) != PLAY_ROWS:
            raise ValueError(f"room {room_id}: expected {PLAY_ROWS} rows, got {len(rows)}")
        tiles: list[list[int]] = []
        for r, row in enumerate(rows):
            if len(row) != PLAY_COLS:
                raise ValueError(f"room {room_id}: row {r} has {len(row)} columns, want {PLAY_COLS}")
            try:
                tiles.append([ts.legend[ch] for ch in row])
            except KeyError as e:
                raise ValueError(f"room {room_id}: row {r} uses unknown legend char {e}") from e
        return tiles

    # ----- queries -------------------------------------------------------
    @property
    def palette_region(self) -> str:
        """Region palette this room draws with (its own, else the tileset's)."""
        return self.region or self.tileset.region

    @property
    def outdoors(self) -> bool:
        """True for screens the sun and the mist can reach."""
        return not self.dungeon and not self.id.startswith("house")

    def tile_at(self, col: int, row: int) -> TileDef | None:
        """TileDef at grid position, None outside the room."""
        if 0 <= col < PLAY_COLS and 0 <= row < PLAY_ROWS:
            return self.tileset.tiles[self.tiles[row][col]]
        return None

    def collision_at(self, col: int, row: int) -> Collision:
        """Collision class at grid position; outside counts as floor (exits handle edges)."""
        td = self.tile_at(col, row)
        return td.collision if td else Collision.FLOOR

    @staticmethod
    def cells(rect: pygame.Rect) -> list[tuple[int, int]]:
        """Grid cells a rect overlaps, clipped to the room."""
        c0 = max(rect.left // TILE, 0)
        c1 = min((rect.right - 1) // TILE, PLAY_COLS - 1)
        r0 = max(rect.top // TILE, 0)
        r1 = min((rect.bottom - 1) // TILE, PLAY_ROWS - 1)
        return [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]

    def blocked(self, rect: pygame.Rect, passable: frozenset[Collision] = frozenset()) -> bool:
        """True if the rect overlaps a blocking tile that is not in ``passable``."""
        for col, row in self.cells(rect):
            kind = self.collision_at(col, row)
            if kind in BLOCKING and kind not in passable:
                return True
        return False

    def hazard_at(self, rect: pygame.Rect) -> Collision | None:
        """The hazard class under a rect's centre, if any."""
        kind = self.collision_at(rect.centerx // TILE, rect.centery // TILE)
        return kind if kind in HAZARD else None

    def set_tile(self, col: int, row: int, char: str) -> None:
        """Replace one tile by legend character (transient: rooms reload on entry)."""
        if 0 <= col < PLAY_COLS and 0 <= row < PLAY_ROWS:
            self.tiles[row][col] = self.tileset.id_of(char)

    def interactive_cells(self, rect: pygame.Rect, kind: str) -> list[tuple[int, int, TileDef]]:
        """Cells under ``rect`` whose tile is cleared by the given interaction."""
        out: list[tuple[int, int, TileDef]] = []
        for col, row in self.cells(rect):
            td = self.tile_at(col, row)
            if td is not None and td.interact == kind:
                out.append((col, row, td))
        return out

    # ----- drawing -------------------------------------------------------
    def render(self, assets: Assets, region: str | None = None) -> pygame.Surface:
        """Draw the whole tile layer to a new PLAY_W x PLAY_H surface."""
        sheet = assets.region_tiles(region or self.palette_region)
        surf = pygame.Surface((PLAY_W, PLAY_H))
        for r, row in enumerate(self.tiles):
            for c, tid in enumerate(row):
                surf.blit(sheet.get(self.tileset.tiles[tid].sprite), (c * TILE, r * TILE))
        return surf

    def draw_tile(self, surf: pygame.Surface, assets: Assets, col: int, row: int,
                  region: str | None = None) -> None:
        """Repaint one tile onto an already-rendered room surface."""
        td = self.tile_at(col, row)
        if td is None:
            return
        sheet = assets.region_tiles(region or self.palette_region)
        surf.blit(sheet.get(td.sprite), (col * TILE, row * TILE))


def list_rooms(root: Path = DATA) -> list[str]:
    """Every room id: the hand-written JSON rooms plus every map-sheet screen."""
    from eldermoor.mapsheet import sheet_room_ids
    ids = {p.stem for p in (root / "rooms").glob("*.json")}
    ids.update(sheet_room_ids(root))
    return sorted(ids)
