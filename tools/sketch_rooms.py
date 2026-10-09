#!/usr/bin/env python3
"""(Re)generate the sixteen dungeon room frames in data/dungeons/blocks.txt.

A temple room is a 20x13 box with a doorway on none, some or all of its four
sides. Sixteen walls-and-gaps frames typed out by hand would be 208 lines of
boilerplate with a typo in one of them, so they are emitted here and the
interesting part — the motifs that go inside, and every chest, door, torch
and enemy — stays hand-authored in blocks.txt and the sheet files.

Run this only to recreate the frames; the motifs below the marker in
blocks.txt are preserved.

    python tools/sketch_rooms.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "dungeons" / "blocks.txt"
MARKER = "# --- motifs (hand-drawn; '_' leaves the frame alone) ---"
W, H = 20, 13
#: where a doorway sits: two tiles wide, centred
NS_COLS = (9, 10)
EW_ROWS = (6, 7)

HEADER = """# Temple room frames and motifs, 20x13.
#
# Frames are named r_<sides>: the letters are the doorways, so r_nse has a
# door north, south and east and a wall to the west. The sixteen frames are
# emitted by tools/sketch_rooms.py.
#
# A layout entry may be "frame+motif": the motif is laid over the frame and
# every character except '_' replaces what was there. That is how a room gets
# its pillars, its pit, its lava or its pots without a block per combination.
#
# Legend (data/tilesets/temple.json): . floor  , tiles  M wall  T wall top
#   P pillar  Y statue  0 pit  L lava  w web  u stairs up  > stairs down
#   X cracked wall  R rubble  ~ water  p plate  o pot  b blue barrier
#   r red barrier  = path
"""


def frame(sides: str) -> list[str]:
    """One room box with doorways on the named sides."""
    rows = ["T" * W]
    rows += ["M" + "." * (W - 2) + "M" for _ in range(H - 2)]
    rows.append("M" * W)
    grid = [list(r) for r in rows]
    if "n" in sides:
        for c in NS_COLS:
            grid[0][c] = "."
    if "s" in sides:
        for c in NS_COLS:
            grid[H - 1][c] = "."
    if "w" in sides:
        for r in EW_ROWS:
            grid[r][0] = "."
    if "e" in sides:
        for r in EW_ROWS:
            grid[r][W - 1] = "."
    return ["".join(r) for r in grid]


def main() -> int:
    """Write the frames, keeping any motifs already in the file."""
    tail = ""
    if OUT.exists():
        text = OUT.read_text(encoding="utf-8")
        if MARKER in text:
            tail = text[text.index(MARKER):]
    parts = [HEADER]
    for mask in range(16):
        sides = "".join(letter for bit, letter in enumerate("nsew") if mask & (1 << bit))
        name = f"r_{sides}" if sides else "r_shut"
        parts.append(f"\n@{name} {W} {H}\n" + "\n".join(frame(sides)) + "\n")
    OUT.write_text("".join(parts) + ("\n" + tail if tail else "\n" + MARKER + "\n"),
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: 16 frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
