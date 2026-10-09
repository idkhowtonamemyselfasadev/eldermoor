#!/usr/bin/env python3
"""Stamp the hand-made overworld blocks into one continuous canvas.

    data/overworld/blocks.txt    the 20x13 screen blocks, drawn by hand
    data/overworld/layout.txt    which block goes on which of the 256 screens
        -> data/overworld/eldermoor.map

The canvas it writes is the committed source of truth: run this to lay the
kingdom out, then edit the .map by hand for anything a block cannot say. Run
it again only when the layout changes, because it overwrites hand edits.

    python tools/build_overworld.py [--check]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "data" / "overworld"
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


def compose(blocks: dict[str, list[str]], grid: list[list[str]]) -> list[str]:
    """Build the canvas lines, one screen row at a time."""
    out: list[str] = []
    for row in grid:
        for line in range(SCREEN_H):
            parts = []
            for name in row:
                if name not in blocks:
                    raise SystemExit(f"layout names unknown block {name!r}")
                parts.append(blocks[name][line])
            out.append("|".join(parts))
    return out


def main(argv: list[str] | None = None) -> int:
    """Write (or check) data/overworld/eldermoor.map."""
    parser = argparse.ArgumentParser(description="lay out the Eldermoor overworld")
    parser.add_argument("--check", action="store_true",
                        help="fail if the canvas on disk differs from the layout")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    blocks = read_blocks(FOLDER / "blocks.txt")
    grid = read_layout(FOLDER / "layout.txt")
    lines = compose(blocks, grid)
    header = (f"# Eldermoor, {len(grid[0])} x {len(grid)} screens, laid out by\n"
              "# tools/build_overworld.py from blocks.txt and layout.txt.\n"
              "# '|' separates screens and is stripped on load.\n")
    text = header + "\n".join(lines) + "\n"
    out = FOLDER / "eldermoor.map"
    if args.check:
        same = out.exists() and out.read_text(encoding="utf-8") == text
        print("canvas matches the layout" if same else "canvas differs from the layout")
        return 0 if same else 1
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}: {len(grid) * len(grid[0])} screens, "
          f"{len(lines)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
