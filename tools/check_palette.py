#!/usr/bin/env python3
"""Check the 32-colour palette stays readable for colour-blind players.

Three things are checked, and the first two are the ones that actually bite:

* the pairs the game uses to mean *different things* - a full heart against
  an empty one, the red and blue barriers, friendly text against a warning -
  must stay apart in brightness as well as in hue, because brightness is what
  survives every kind of colour blindness;
* the colours the interface is drawn in - text, boxes, cursors, hearts -
  must stay apart under protanopia, deuteranopia and tritanopia. A pair
  whose hues collapse is fine only if their brightness still tells them
  apart, because brightness is the one channel every kind of colour
  blindness keeps. Thirty-two colours cannot all be distinct this way, so
  the sweep over the rest of the palette prints advice rather than failing:
  two shades of green looking alike is a picture, not a puzzle you cannot
  solve;
* the whole palette must span a decent range of brightness, or a greyscale
  screenshot turns to mud.

    python tools/check_palette.py

Exits non-zero and prints what is wrong, so CI and the test suite can
both use it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets_src" / "palette.txt"

#: pairs that carry meaning and so must not look alike. (name, name, min gap)
MEANINGFUL_PAIRS = (
    ("red", "moss", 0.10),          # full heart against the world behind it
    ("red", "sea", 0.10),           # the red and blue barriers
    ("gold", "mist", 0.10),         # a chosen menu row against an unchosen one
    ("lime", "red", 0.10),          # "done" against "danger"
    ("white", "stone", 0.25),       # text against its box
    ("ink", "white", 0.60),         # the two ends of everything
    ("ember", "sky", 0.10),         # enemy shots against friendly ones
)
#: how close two simulated colours may be before their hues count as collapsed
MIN_SEPARATION = 0.045
#: the brightness gap that rescues a collapsed pair
RESCUE_GAP = 0.06
#: the colours the interface is drawn in: these must never be confusable
UI_COLOURS = ("ink", "white", "mist", "stone", "gold", "lime", "red", "sky", "ember")
#: the brightness range the whole palette must cover
MIN_SPREAD = 0.80

#: LMS-space simulation matrices for the three dichromacies
SIMULATIONS = {
    "protanopia": ((0.170556992, 0.829443014, 0.0),
                   (0.170556991, 0.829443008, 0.0),
                   (-0.004517144, 0.004517144, 1.0)),
    "deuteranopia": ((0.33066007, 0.66933993, 0.0),
                     (0.33066007, 0.66933993, 0.0),
                     (-0.02785538, 0.02785538, 1.0)),
    "tritanopia": ((1.0, 0.1273989, -0.1273989),
                   (0.0, 0.8739093, 0.1260907),
                   (0.0, 0.8739093, 0.1260907)),
}


def load_palette() -> list[tuple[str, tuple[float, float, float]]]:
    """Read the palette source into (name, linear rgb) pairs."""
    out: list[tuple[str, tuple[float, float, float]]] = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        _idx, _ch, name, hexv = line.split()
        rgb = tuple(int(hexv[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        out.append((name, (rgb[0], rgb[1], rgb[2])))
    return out


def luminance(rgb: tuple[float, float, float]) -> float:
    """Perceived brightness, 0..1."""
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def simulate(rgb: tuple[float, float, float], kind: str) -> tuple[float, float, float]:
    """The same colour as a dichromat sees it."""
    m = SIMULATIONS[kind]
    return tuple(min(1.0, max(0.0, sum(m[i][j] * rgb[j] for j in range(3))))
                 for i in range(3))  # type: ignore[return-value]


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """Rough perceptual distance between two colours."""
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return (2.0 * dr * dr + 4.0 * dg * dg + 3.0 * db * db) ** 0.5 / 3.0


def check(verbose: bool = True) -> list[str]:
    """Run every check. Returns a list of problems (empty means all well)."""
    palette = load_palette()
    index = {name: rgb for name, rgb in palette}
    problems: list[str] = []

    for first, second, gap in MEANINGFUL_PAIRS:
        if first not in index or second not in index:
            problems.append(f"palette has no colour named {first!r} or {second!r}")
            continue
        delta = abs(luminance(index[first]) - luminance(index[second]))
        if delta < gap:
            problems.append(f"{first} and {second} are only {delta:.3f} apart in "
                            f"brightness, want {gap:.2f}: they mean different things")

    advice: list[str] = []
    for kind in SIMULATIONS:
        seen: list[tuple[str, tuple[float, float, float], float]] = []
        for name, rgb in palette:
            shown = simulate(rgb, kind)
            bright = luminance(rgb)
            for other, other_shown, other_bright in seen:
                if (distance(shown, other_shown) >= MIN_SEPARATION
                        or abs(bright - other_bright) >= RESCUE_GAP):
                    continue
                line = (f"under {kind}, {name} and {other} are indistinguishable: "
                        "same hue, same brightness")
                if name in UI_COLOURS and other in UI_COLOURS:
                    problems.append(line)
                else:
                    advice.append(line)
            seen.append((name, shown, bright))

    spread = max(luminance(c) for _n, c in palette) - min(luminance(c) for _n, c in palette)
    if spread < MIN_SPREAD:
        problems.append(f"the palette only spans {spread:.2f} of brightness, want "
                        f"{MIN_SPREAD:.2f}")

    if verbose:
        print(f"palette: {len(palette)} colours, brightness spread {spread:.2f}")
        for kind in SIMULATIONS:
            worst = min(
                (distance(simulate(a, kind), simulate(b, kind))
                 + abs(luminance(a) - luminance(b)), na, nb)
                for i, (na, a) in enumerate(palette) for nb, b in palette[i + 1:])
            print(f"  {kind}: closest pair {worst[1]}/{worst[2]} at {worst[0]:.3f}")
        for note in advice:
            print(f"  note: {note}")
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"{len(problems)} problems, {len(advice)} notes")
    return problems


def main(argv: list[str]) -> int:
    """Entry point."""
    return 1 if check("--quiet" not in argv) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
