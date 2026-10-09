"""Tilesets and rooms: JSON in data/, tile collision classes, room rendering."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from eldermoor.config import DATA, PLAY_COLS, PLAY_H, PLAY_ROWS, PLAY_W, TILE

if TYPE_CHECKING:
    from eldermoor.assets import Assets


class Collision(StrEnum):
    """What a tile does to things standing on it. Only the first three are used in milestone 1."""

    FLOOR = "floor"
    SOLID = "solid"
    GRASS = "grass"          # tall grass: walkable, cuttable later
    WATER = "water"
    LAVA = "lava"
    PIT = "pit"
    ICE = "ice"
    LEDGE_DOWN = "ledge_down"
    BOMBABLE = "bombable"
    LIFTABLE = "liftable"


BLOCKING = frozenset({Collision.SOLID, Collision.WATER, Collision.LAVA, Collision.PIT,
                      Collision.BOMBABLE, Collision.LIFTABLE})

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


@dataclass(frozen=True)
class TileDef:
    """One tile kind: id, legend character, sprite block and collision class."""

    id: int
    char: str
    sprite: str
    collision: Collision


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
            td = TileDef(tid, t["char"], t["sprite"], Collision(t.get("collision", "floor")))
            ts.tiles[tid] = td
            if td.char in ts.legend:
                raise ValueError(f"tileset {name}: legend char {td.char!r} used twice")
            ts.legend[td.char] = tid
        return ts


@dataclass
class Room:
    """A single 20x13 screen of tiles with exits to neighbouring rooms."""

    id: str
    tileset: Tileset
    tiles: list[list[int]]
    exits: dict[str, str] = field(default_factory=dict)
    spawn: tuple[int, int] = (PLAY_W // 2 - 8, PLAY_H // 2 - 8)
    name: str = ""

    @classmethod
    def load(cls, room_id: str, root: Path = DATA, tilesets: dict[str, Tileset] | None = None) -> Room:
        """Read data/rooms/<room_id>.json and validate its size."""
        raw = json.loads((root / "rooms" / f"{room_id}.json").read_text(encoding="utf-8"))
        ts_name = raw["tileset"]
        if tilesets is not None and ts_name in tilesets:
            ts = tilesets[ts_name]
        else:
            ts = Tileset.load(ts_name, root)
            if tilesets is not None:
                tilesets[ts_name] = ts
        rows = raw["tiles"]
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
        exits = {k: v for k, v in raw.get("exits", {}).items() if k in OPPOSITE}
        spawn = tuple(raw.get("spawn", cls.spawn))  # type: ignore[arg-type]
        return cls(raw.get("id", room_id), ts, tiles, exits, (int(spawn[0]), int(spawn[1])),
                   raw.get("name", ""))

    # ----- collision -----------------------------------------------------
    def tile_at(self, col: int, row: int) -> TileDef | None:
        """TileDef at grid position, None outside the room."""
        if 0 <= col < PLAY_COLS and 0 <= row < PLAY_ROWS:
            return self.tileset.tiles[self.tiles[row][col]]
        return None

    def collision_at(self, col: int, row: int) -> Collision:
        """Collision class at grid position; outside the room counts as floor (exits handle edges)."""
        td = self.tile_at(col, row)
        return td.collision if td else Collision.FLOOR

    def blocked(self, rect: pygame.Rect) -> bool:
        """True if the rect (in play-area pixels) overlaps any blocking tile."""
        c0 = max(rect.left // TILE, 0)
        c1 = min((rect.right - 1) // TILE, PLAY_COLS - 1)
        r0 = max(rect.top // TILE, 0)
        r1 = min((rect.bottom - 1) // TILE, PLAY_ROWS - 1)
        for row in range(r0, r1 + 1):
            for col in range(c0, c1 + 1):
                if self.collision_at(col, row) in BLOCKING:
                    return True
        return False

    # ----- drawing -------------------------------------------------------
    def render(self, assets: Assets) -> pygame.Surface:
        """Draw the whole tile layer to a new PLAY_W x PLAY_H surface."""
        sheet = assets.region_tiles(self.tileset.region)
        surf = pygame.Surface((PLAY_W, PLAY_H))
        for r, row in enumerate(self.tiles):
            for c, tid in enumerate(row):
                surf.blit(sheet.get(self.tileset.tiles[tid].sprite), (c * TILE, r * TILE))
        return surf


def list_rooms(root: Path = DATA) -> list[str]:
    """All room ids present in data/rooms/."""
    return sorted(p.stem for p in (root / "rooms").glob("*.json"))
