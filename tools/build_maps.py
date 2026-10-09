#!/usr/bin/env python3
"""Stamp hand-made 20x13 blocks into the continuous canvas of a map sheet.

A sheet folder holds:

    blocks.txt      the 20x13 screen blocks, drawn by hand (or a shared one)
    layout.txt      which block goes on which screen, one name per screen
        ->          <layer>.map, the canvas eldermoor/mapsheet.py slices

The canvas it writes is the committed source of truth: run this to lay an
area out, then edit the .map by hand for anything a block cannot say. Run it
again only when the layout changes, because it overwrites hand edits.

    python tools/build_maps.py                     # every sheet that has a layout
    python tools/build_maps.py data/overworld      # just this one
    python tools/build_maps.py --check             # fail if a canvas is stale
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCREEN_W, SCREEN_H = 20, 13


def is_comment(line: str) -> bool:
    """A comment is '#' followed by a space or nothing.

    Fences are painted with '#', so a row like ``####.....==.....####`` is
    map data, not a remark.
    """
    return line.startswith("#") and (len(line) == 1 or line[1] == " ")


def read_blocks(path: Path) -> dict[str, list[str]]:
    """Parse blocks.txt into name -> 13 rows of 20 characters."""
    blocks: dict[str, list[str]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.startswith("@"):
            continue
        name, w, h = line[1:].split()
        w, h = int(w), int(h)
        rows: list[str] = []
        while len(rows) < h:
            row = lines[i]
            i += 1
            if is_comment(row):
                continue
            if len(row) != w:
                raise SystemExit(f"block {name} row {len(rows)} is {len(row)} wide, want {w}")
            rows.append(row)
        blocks[name] = rows
    return blocks


def read_layout(path: Path) -> list[list[str]]:
    """Parse layout.txt into a grid of block names."""
    grid = [ln.split() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not is_comment(ln)]
    width = len(grid[0])
    for r, row in enumerate(grid):
        if len(row) != width:
            raise SystemExit(f"layout row {r} names {len(row)} screens, want {width}")
    return grid


def resolve(blocks: dict[str, list[str]], name: str) -> list[str]:
    """A block, or a frame with motifs laid over it: ``r_ns+m_pillars+m_pots``.

    In a motif, '_' means "leave the frame alone"; every other character
    replaces what was underneath.
    """
    parts = name.split("+")
    for part in parts:
        if part not in blocks:
            raise SystemExit(f"layout names unknown block {part!r}")
    rows = list(blocks[parts[0]])
    for motif in parts[1:]:
        over = blocks[motif]
        rows = ["".join(o if o != "_" else b for b, o in zip(base, layer, strict=True))
                for base, layer in zip(rows, over, strict=True)]
    return rows


def compose(blocks: dict[str, list[str]], grid: list[list[str]]) -> list[str]:
    """Build the canvas lines, one screen row at a time."""
    rendered = [[resolve(blocks, name) for name in row] for row in grid]
    out: list[str] = []
    for row in rendered:
        for line in range(SCREEN_H):
            out.append("|".join(block[line] for block in row))
    return out


def blocks_for(folder: Path) -> Path:
    """The block library a sheet uses: its own, else the one beside it."""
    own = folder / "blocks.txt"
    return own if own.exists() else folder.parent / "blocks.txt"


def sheet_folders() -> list[Path]:
    """Every sheet folder under data/ that has a layout to stamp."""
    data = ROOT / "data"
    return sorted(p.parent for p in list(data.glob("*/layout*.txt"))
                  + list(data.glob("*/*/layout*.txt")))


def build_folder(folder: Path, check: bool) -> tuple[int, int]:
    """Stamp (or check) every layout in one sheet folder. Returns (built, stale)."""
    import json
    sheet = json.loads((folder / "sheet.json").read_text(encoding="utf-8"))
    blocks = read_blocks(blocks_for(folder))
    built = stale = 0
    for layer in sheet["layers"]:
        name = layer["name"]
        layout = folder / (f"layout_{name}.txt" if (folder / f"layout_{name}.txt").exists()
                           else "layout.txt")
        grid = read_layout(layout)
        if len(grid) != layer["rows"] or len(grid[0]) != layer["cols"]:
            raise SystemExit(f"{layout}: {len(grid[0])}x{len(grid)} screens, "
                             f"sheet.json says {layer['cols']}x{layer['rows']}")
        lines = compose(blocks, grid)
        header = (f"# {folder.name}/{name}: {len(grid[0])} x {len(grid)} screens, laid out\n"
                  f"# by tools/build_maps.py from {layout.name} and "
                  f"{blocks_for(folder).name}.\n"
                  "# '|' separates screens and is stripped on load.\n")
        text = header + "\n".join(lines) + "\n"
        out = folder / f"{name}.map"
        if check:
            if not (out.exists() and out.read_text(encoding="utf-8") == text):
                print(f"  STALE {out.relative_to(ROOT)}")
                stale += 1
            continue
        out.write_text(text, encoding="utf-8")
        print(f"  wrote {out.relative_to(ROOT)}: {len(grid) * len(grid[0])} screens")
        built += 1
    return built, stale


def main(argv: list[str] | None = None) -> int:
    """Write (or check) every map sheet's canvas."""
    parser = argparse.ArgumentParser(description="lay out Eldermoor's map sheets")
    parser.add_argument("folders", nargs="*", type=Path)
    parser.add_argument("--check", action="store_true",
                        help="fail if a canvas on disk differs from its layout")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    folders = [ROOT / f for f in args.folders] if args.folders else sheet_folders()
    stale = 0
    for folder in folders:
        stale += build_folder(folder, args.check)[1]
    if args.check:
        print("every canvas matches its layout" if not stale else f"{stale} stale canvas(es)")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
