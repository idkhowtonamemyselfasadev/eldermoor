#!/usr/bin/env python3
"""Compile text pixel-maps in assets_src/ into PNG sheets + JSON atlases in assets/.

Source format (one or more blocks per .txt file)::

    @name W H
    <H rows of W characters>

Characters: '.' = transparent, '0'-'9' = palette 0-9, 'a'-'v' = palette 10-31.
Lines starting with '#' are comments.  Blocks named ``U+0041`` are font glyphs.

Outputs
-------
assets/sprites.png + sprites.json      all sprites (hero, enemies, bosses, pickups)
assets/icons.png + icons.json          8x8 item icons
assets/tiles_<region>.png + tiles.json tiles, one sheet per region palette swap
assets/font8.png / font6.png + .json   bitmap fonts
assets/palette.json                    the master palette
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets_src"
OUT = ROOT / "assets"
CHARS = "0123456789abcdefghijklmnopqrstuv"


def load_palette() -> list[tuple[int, int, int]]:
    """Read assets_src/palette.txt → list of 32 RGB tuples."""
    pal: list[tuple[int, int, int]] = []
    names: list[str] = []
    for line in (SRC / "palette.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        idx, _ch, name, hexv = line.split()
        assert int(idx) == len(pal), f"palette index out of order at {line}"
        pal.append((int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16)))
        names.append(name)
    assert len(pal) == 32, f"palette must have 32 colours, has {len(pal)}"
    (OUT / "palette.json").write_text(
        json.dumps({"names": names, "rgb": pal}, indent=1))
    return pal


def parse_blocks(path: Path) -> list[tuple[str, int, int, list[str]]]:
    """Parse one source file into (name, w, h, rows) blocks."""
    blocks: list[tuple[str, int, int, list[str]]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        if not line.startswith("@"):
            continue
        parts = line[1:].split()
        if len(parts) != 3:
            raise SystemExit(f"{path}:{i}: bad header {line!r}")
        name, w, h = parts[0], int(parts[1]), int(parts[2])
        rows: list[str] = []
        while len(rows) < h:
            if i >= len(lines):
                raise SystemExit(f"{path}: block {name} truncated")
            r = lines[i].rstrip("\n")
            i += 1
            if r.startswith("#"):
                continue
            r = r.rstrip()
            if len(r) < w:
                r = r + "." * (w - len(r))
            if len(r) != w:
                raise SystemExit(f"{path}:{i}: block {name} row {len(rows)} has {len(r)} chars, want {w}")
            for c in r:
                if c != "." and c not in CHARS:
                    raise SystemExit(f"{path}:{i}: bad char {c!r} in {name}")
            rows.append(r)
        blocks.append((name, w, h, rows))
    return blocks


def collect(folder: Path) -> list[tuple[str, int, int, list[str]]]:
    """All blocks from all .txt files in a folder, sorted by file then order."""
    blocks: list[tuple[str, int, int, list[str]]] = []
    seen: set[str] = set()
    for p in sorted(folder.glob("*.txt")):
        for b in parse_blocks(p):
            if b[0] in seen:
                raise SystemExit(f"duplicate block name {b[0]} in {p}")
            seen.add(b[0])
            blocks.append(b)
    return blocks


def pack(blocks: list[tuple[str, int, int, list[str]]], sheet_w: int = 512
         ) -> tuple[dict[str, list[int]], int]:
    """Shelf-pack blocks into a sheet of width sheet_w. Returns atlas and height."""
    atlas: dict[str, list[int]] = {}
    x = y = shelf_h = 0
    for name, w, h, _rows in blocks:
        if x + w > sheet_w:
            x = 0
            y += shelf_h
            shelf_h = 0
        atlas[name] = [x, y, w, h]
        x += w
        shelf_h = max(shelf_h, h)
    return atlas, y + shelf_h


def render_sheet(blocks, atlas, sheet_w: int, sheet_h: int, pal, swap: dict[int, int] | None = None):
    """Rasterise blocks onto an RGBA pygame Surface using the palette (+ optional swap)."""
    import pygame  # noqa: PLC0415  (imported here so --help works without SDL)
    surf = pygame.Surface((sheet_w, max(sheet_h, 1)), pygame.SRCALPHA)
    swap = swap or {}
    for name, w, h, rows in blocks:
        ox, oy, _w, _h = atlas[name]
        for yy, row in enumerate(rows):
            for xx, c in enumerate(row):
                if c == ".":
                    continue
                idx = CHARS.index(c)
                idx = swap.get(idx, idx)
                surf.set_at((ox + xx, oy + yy), (*pal[idx], 255))
    return surf


def build_category(name: str, folder: Path, pal, variants: dict[str, dict[int, int]] | None = None) -> int:
    """Build one sheet (or one per palette variant) for a category. Returns block count."""
    import pygame  # noqa: PLC0415
    blocks = collect(folder)
    if not blocks:
        print(f"  {name}: no blocks")
        return 0
    sheet_w = 512 if name != "fonts" else 256
    atlas, sheet_h = pack(blocks, sheet_w)
    (OUT / f"{name}.json").write_text(json.dumps(atlas, separators=(",", ":")))
    if variants:
        for vname, swap in variants.items():
            surf = render_sheet(blocks, atlas, sheet_w, sheet_h, pal, swap)
            pygame.image.save(surf, str(OUT / f"{name}_{vname}.png"))
    else:
        surf = render_sheet(blocks, atlas, sheet_w, sheet_h, pal)
        pygame.image.save(surf, str(OUT / f"{name}.png"))
    print(f"  {name}: {len(blocks)} blocks, sheet {sheet_w}x{sheet_h}")
    return len(blocks)


def build_fonts(pal) -> None:
    """Fonts are stored per file: font8.txt → font8.png/json, font6.txt → font6.png/json."""
    import pygame  # noqa: PLC0415
    for p in sorted((SRC / "fonts").glob("*.txt")):
        blocks = parse_blocks(p)
        atlas, sheet_h = pack(blocks, 256)
        surf = render_sheet(blocks, atlas, 256, sheet_h, pal)
        pygame.image.save(surf, str(OUT / f"{p.stem}.png"))
        (OUT / f"{p.stem}.json").write_text(json.dumps(atlas, separators=(",", ":")))
        print(f"  {p.stem}: {len(blocks)} glyphs")


def main(argv: list[str]) -> int:
    """Entry point."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    OUT.mkdir(exist_ok=True)
    pal = load_palette()
    swaps_raw = json.loads((SRC / "region_palettes.json").read_text())
    variants = {k: {int(a): int(b) for a, b in v.items()}
                for k, v in swaps_raw.items() if not k.startswith("_")}
    print("building assets →", OUT)
    build_category("sprites", SRC / "sprites", pal)
    build_category("icons", SRC / "icons", pal)
    build_category("tiles", SRC / "tiles", pal, variants)
    build_fonts(pal)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
