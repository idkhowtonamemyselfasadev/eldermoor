#!/usr/bin/env python3
"""Validate every text pixel-map in assets_src/ without building PNGs.

Exits non-zero and prints each problem; used by the test suite and by hand
while drawing. ``python tools/check_art.py`` prints a block count per file.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets_src"
CHARS = "0123456789abcdefghijklmnopqrstuv"


def check_file(path: Path) -> tuple[int, list[str]]:
    """Return (block count, problems) for one source file."""
    problems: list[str] = []
    names: set[str] = set()
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    count = 0
    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        if not line.startswith("@"):
            continue
        parts = line[1:].split()
        if len(parts) != 3:
            problems.append(f"{path.name}: bad header {line!r}")
            continue
        name, w, h = parts[0], int(parts[1]), int(parts[2])
        if name in names:
            problems.append(f"{path.name}: duplicate block {name}")
        names.add(name)
        rows = 0
        while rows < h:
            if i >= len(lines):
                problems.append(f"{path.name}: block {name} truncated")
                break
            row = lines[i]
            i += 1
            if row.startswith("#"):
                continue
            row = row.rstrip()
            if len(row) > w:
                problems.append(f"{path.name}: {name} row {rows} is {len(row)} wide, want {w}")
            for ch in row:
                if ch != "." and ch not in CHARS:
                    problems.append(f"{path.name}: {name} row {rows} bad char {ch!r}")
            rows += 1
        count += 1
    return count, problems


def main() -> int:
    """Check every .txt under assets_src/."""
    total = 0
    problems: list[str] = []
    for path in sorted(SRC.glob("*/*.txt")):
        count, probs = check_file(path)
        total += count
        problems += probs
        print(f"  {path.relative_to(SRC)}: {count} blocks")
    for p in problems:
        print("ERROR", p, file=sys.stderr)
    print(f"{total} blocks, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
