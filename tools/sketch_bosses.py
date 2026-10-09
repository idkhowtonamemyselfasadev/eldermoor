#!/usr/bin/env python3
"""(Re)generate the large boss pixel-maps in assets_src/sprites/bosses.txt.

A 48x48 maw drawn by hand one character at a time is a typo farm, so the big
bosses are composed from discs, rings and teeth by this script.  The *output*
is still a plain text pixel-map in assets_src/ and stays the editable source
of truth: run this to start a boss, then tweak the text by hand.

    python tools/sketch_bosses.py
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets_src" / "sprites" / "bosses.txt"


class Grid:
    """A character grid with the few drawing primitives the bosses need."""

    def __init__(self, w: int, h: int) -> None:
        self.w = w
        self.h = h
        self.cells = [["." for _ in range(w)] for _ in range(h)]

    def put(self, x: int, y: int, ch: str) -> None:
        """Set one pixel if it is inside the grid."""
        if 0 <= x < self.w and 0 <= y < self.h:
            self.cells[y][x] = ch

    def disc(self, cx: float, cy: float, r: float, fill: str, outline: str = "0") -> None:
        """A filled ellipse-ish disc with a one-pixel outline."""
        for y in range(self.h):
            for x in range(self.w):
                d = math.hypot(x - cx, y - cy)
                if d <= r:
                    self.cells[y][x] = fill if d <= r - 1.0 else outline

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, fill: str,
                outline: str = "0") -> None:
        """A filled ellipse with a one-pixel outline."""
        for y in range(self.h):
            for x in range(self.w):
                d = math.hypot((x - cx) / rx, (y - cy) / ry)
                if d <= 1.0:
                    self.cells[y][x] = fill if d <= 1.0 - 1.0 / max(rx, ry) else outline

    def ring(self, cx: float, cy: float, r0: float, r1: float, ch: str) -> None:
        """An annulus of one character, drawn over whatever is there."""
        for y in range(self.h):
            for x in range(self.w):
                if r0 <= math.hypot(x - cx, y - cy) <= r1:
                    self.cells[y][x] = ch

    def spike(self, cx: float, cy: float, angle: float, length: float, width: float,
              ch: str) -> None:
        """A tapering tooth pointing from (cx, cy) along ``angle`` radians."""
        steps = int(length * 2)
        for i in range(steps + 1):
            t = i / max(steps, 1)
            px = cx + math.cos(angle) * length * t
            py = cy + math.sin(angle) * length * t
            half = width * (1.0 - t)
            for dy in range(-int(half) - 1, int(half) + 2):
                for dx in range(-int(half) - 1, int(half) + 2):
                    if math.hypot(dx, dy) <= half:
                        self.put(round(px) + dx, round(py) + dy, ch)

    def block(self, x0: int, y0: int, x1: int, y1: int, ch: str) -> None:
        """A filled rectangle (inclusive bounds)."""
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, ch)

    def text(self, name: str) -> str:
        """The block in asset-source form."""
        rows = "\n".join("".join(row).rstrip() or "." * 1 for row in self.cells)
        return f"@{name} {self.w} {self.h}\n{rows}\n"


def cinderjaw(open_jaw: bool) -> Grid:
    """Mini-boss: an ember beetle, 32x32, mandibles closed or spread."""
    g = Grid(32, 32)
    g.ellipse(15.5, 15.0, 14.0, 11.5, "q")
    g.ring(15.5, 15.0, 7.5, 9.0, "e")
    g.ring(15.5, 15.0, 11.0, 11.6, "0")
    for ex in (9.5, 21.5):
        g.disc(ex, 11.0, 3.4, "f")
        g.disc(ex, 11.0, 1.4, "0")
    spread = 0.55 if open_jaw else 0.15
    for side in (-1, 1):
        g.spike(15.5 + side * 5, 24.0, math.pi / 2 + side * spread, 7.0, 2.2, "e")
        g.spike(15.5 + side * 5, 24.0, math.pi / 2 + side * spread, 7.0, 1.0, "f")
    for side in (-1, 1):
        g.block(15 + side * 13, 18, 15 + side * 15, 19, "0")
        g.block(15 + side * 13, 10, 15 + side * 15, 11, "0")
    return g


def ashmaw(open_mouth: bool) -> Grid:
    """Ember Temple boss: the Ashen Maw, 48x48, mouth shut or gaping."""
    g = Grid(48, 48)
    g.disc(23.5, 26.0, 21.0, "q")
    g.ring(23.5, 26.0, 16.5, 18.0, "e")
    mouth_r = 12.0 if open_mouth else 7.0
    g.disc(23.5, 28.0, mouth_r, "c")
    if open_mouth:
        g.disc(23.5, 28.0, 5.5, "e")
        g.disc(23.5, 28.0, 2.5, "f")
        for i in range(8):
            a = math.pi * 2 * i / 8 + math.pi / 8
            tx = 23.5 + math.cos(a) * (mouth_r - 1)
            ty = 28.0 + math.sin(a) * (mouth_r - 1)
            g.spike(tx, ty, a + math.pi, 5.0, 1.8, "6")
    else:
        g.ring(23.5, 28.0, 6.0, 7.0, "0")
        g.block(12, 27, 35, 28, "0")
    for ex in (13.0, 34.0):
        g.disc(ex, 13.0, 4.5, "f")
        g.disc(ex, 13.0, 2.0, "d")
        g.disc(ex, 13.0, 0.9, "0")
    g.ring(23.5, 26.0, 20.2, 21.0, "0")
    return g


HEADER = """# Bosses, composed by tools/sketch_bosses.py and then editable by hand.
#   cinderjaw  32x32 mini-boss of the Ember Temple (mandible slam)
#   ashmaw     48x48 temple boss, the Ashen Maw (shut / gaping)
# Palette: 0 ink, 6 white, c blood, d red, e ember, f gold, q rust
"""


def main() -> int:
    """Write bosses.txt."""
    blocks = [
        cinderjaw(False).text("cinderjaw_0"),
        cinderjaw(True).text("cinderjaw_1"),
        ashmaw(False).text("ashmaw_0"),
        ashmaw(True).text("ashmaw_1"),
    ]
    OUT.write_text(HEADER + "\n" + "\n".join(blocks), encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
