#!/usr/bin/env python3
"""(Re)generate the small creature pixel-maps in assets_src/sprites/critters.txt.

Twelve more creatures for the caves and the quieter corners of the kingdom.
Each is two 16x16 frames composed from a body shape and a colour, the same
way the bosses are drawn: the output is a plain text pixel-map in
assets_src/ and stays the source of truth, editable by hand afterwards.

    python tools/sketch_critters.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "assets_src" / "sprites" / "critters.txt"

from sketch_bosses import Grid  # noqa: E402  (same drawing primitives)


def blob(frame: int, body: str, eye: str) -> Grid:
    """A round thing that squashes on the second frame."""
    g = Grid(16, 16)
    ry = 5.5 if frame == 0 else 4.6
    g.ellipse(7.5, 10.0, 6.0, ry, body)
    for ex in (5.0, 10.0):
        g.put(int(ex), 8, eye)
        g.put(int(ex), 9, "0")
    return g


def spiky(frame: int, body: str, eye: str) -> Grid:
    """A spined thing; the spines flick out on the second frame."""
    g = Grid(16, 16)
    g.disc(7.5, 9.0, 5.2, body)
    length = 2.4 if frame == 0 else 3.6
    for i in range(8):
        a = math.pi * 2 * i / 8
        g.spike(7.5 + math.cos(a) * 4.4, 9.0 + math.sin(a) * 4.4, a, length, 1.1, body)
    g.disc(7.5, 9.0, 1.6, eye)
    g.put(7, 9, "0")
    return g


def tall(frame: int, body: str, eye: str) -> Grid:
    """Something upright that leans as it walks."""
    g = Grid(16, 16)
    lean = 0 if frame == 0 else 1
    g.ellipse(7.5 + lean, 6.5, 3.6, 3.4, body)
    g.block(5, 9, 10, 14, body)
    g.block(4, 15, 11, 15, "0")
    for ex in (6, 9):
        g.put(ex + lean, 6, eye)
    return g


def flat(frame: int, body: str, eye: str) -> Grid:
    """A low crawler, wider than it is tall."""
    g = Grid(16, 16)
    g.ellipse(7.5, 11.0, 7.0, 3.4, body)
    legs = (2, 5, 10, 13) if frame == 0 else (3, 6, 9, 12)
    for lx in legs:
        g.put(lx, 14, "0")
        g.put(lx, 15, "0")
    for ex in (5, 10):
        g.put(ex, 10, eye)
    return g


def orb(frame: int, body: str, eye: str) -> Grid:
    """A floater with a halo that pulses."""
    g = Grid(16, 16)
    g.disc(7.5, 7.5, 4.4, body)
    g.ring(7.5, 7.5, 5.6 if frame == 0 else 6.4, 6.4 if frame == 0 else 7.0, body)
    g.disc(7.5, 7.5, 1.8, eye)
    g.put(7, 7, "0")
    return g


def crown(frame: int, body: str, eye: str) -> Grid:
    """A spiked crown of a thing that opens and shuts."""
    g = Grid(16, 16)
    g.ellipse(7.5, 9.5, 5.6, 4.6, body)
    spread = 0.0 if frame == 0 else 0.5
    for i in range(5):
        a = -math.pi / 2 + (i - 2) * (0.5 + spread * 0.2)
        g.spike(7.5 + math.cos(a) * 4.0, 9.5 + math.sin(a) * 3.6, a, 3.4, 1.2, body)
    g.put(5, 9, eye)
    g.put(10, 9, eye)
    return g


def kite(frame: int, body: str, eye: str) -> Grid:
    """A diamond that tilts as it flies."""
    g = Grid(16, 16)
    tilt = 0 if frame == 0 else 1
    for y in range(16):
        for x in range(16):
            if abs(x - 7.5) + abs(y - (7.5 + tilt)) <= 5.5:
                g.put(x, y, body)
    for y in range(16):
        for x in range(16):
            if 5.0 <= abs(x - 7.5) + abs(y - (7.5 + tilt)) <= 5.5:
                g.put(x, y, "0")
    g.put(6, 7 + tilt, eye)
    g.put(9, 7 + tilt, eye)
    return g


def coil(frame: int, body: str, eye: str) -> Grid:
    """A spring that compresses on the second frame."""
    g = Grid(16, 16)
    rows = (3, 6, 9, 12) if frame == 0 else (5, 7, 9, 11)
    for y in rows:
        g.block(3, y, 12, y + 1, body)
        g.put(2, y, "0")
        g.put(13, y + 1, "0")
    g.put(6, rows[0], eye)
    g.put(9, rows[0], eye)
    return g


def worm(frame: int, body: str, eye: str) -> Grid:
    """A segmented thing that waves."""
    g = Grid(16, 16)
    for i in range(5):
        wave = math.sin(i * 0.9 + (0 if frame == 0 else 1.6)) * 2.0
        g.disc(3.0 + i * 2.6, 9.0 + wave, 2.2, body)
    g.disc(3.0, 9.0 + math.sin(0 if frame == 0 else 1.6) * 2.0, 1.1, eye)
    return g


SHAPES = {"blob": blob, "spiky": spiky, "tall": tall, "flat": flat, "orb": orb,
          "worm": worm, "crown": crown, "kite": kite, "coil": coil}

#: name, shape, body colour, eye colour
CAST = [
    ("grub", "blob", "i", "f"),
    ("shale", "flat", "3", "e"),
    ("brinelet", "blob", "u", "6"),
    ("thornpup", "spiky", "h", "d"),
    ("dustmite", "flat", "8", "0"),
    ("emberfly", "orb", "e", "6"),
    ("glimmer", "orb", "m", "l"),
    ("reedsnap", "worm", "g", "f"),
    ("stonehand", "tall", "4", "d"),
    ("mistling", "tall", "5", "v"),
    ("cinderworm", "worm", "q", "e"),
    ("glasscrab", "flat", "p", "6"),
    ("bogwisp", "orb", "g", "i"),
    ("saltling", "blob", "7", "k"),
    ("flintback", "spiky", "4", "e"),
    ("gloamfly", "kite", "n", "v"),
    ("chalkcrab", "flat", "6", "3"),
    ("barbthorn", "crown", "h", "d"),
    ("ashgrub", "worm", "1", "e"),
    ("tidecoil", "coil", "k", "u"),
    ("duneskip", "kite", "8", "f"),
    ("slagling", "blob", "c", "e"),
    ("frostnip", "spiky", "m", "6"),
    ("hollowpup", "tall", "2", "d"),
    ("lanternmoth", "kite", "f", "6"),
    ("stillshade", "tall", "1", "5"),
]

HEADER = """# Small creatures, composed by tools/sketch_critters.py and editable by hand.
# Two frames each, 16x16. Palette: 0 ink, 3 stone, 4 ash, 5 mist, 6 white,
# 8 sand, d red, e ember, f gold, g moss, h leaf, i lime, l sky, m ice,
# p pink, q rust, u cyan, v lavender
"""


def main() -> int:
    """Write every critter's two frames. Returns 0."""
    out = [HEADER]
    for name, shape, body, eye in CAST:
        for frame in (0, 1):
            out.append(SHAPES[shape](frame, body, eye).text(f"{name}_{frame}"))
    OUT.write_text("\n".join(out))
    print(f"wrote {len(CAST) * 2} frames to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
