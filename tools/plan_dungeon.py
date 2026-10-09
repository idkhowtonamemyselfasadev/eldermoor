#!/usr/bin/env python3
"""Turn a temple's hand-drawn connection map into its layout and check it.

    data/dungeons/<id>/connections.txt   which rooms join which, by hand
        -> data/dungeons/<id>/layout_f1.txt

The connection map is the design: deciding that this room opens east and
that one does not is the dungeon. This tool only works out which of the
sixteen room frames each cell needs, lays the motifs named in
``motifs.txt`` over them, and refuses to write a layout that leaves a room
unreachable from the entrance.

    python tools/plan_dungeon.py temple2
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}


def read_connections(path: Path) -> tuple[list[list[int]], list[list[int]], tuple[int, int]]:
    """Parse the [east], [south] and [entrance] sections."""
    section = ""
    east: list[list[int]] = []
    south: list[list[int]] = []
    entrance = (0, 0)
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            section = line.strip("[]")
            continue
        if section == "east":
            east.append([1 if ch not in ".-" else 0 for ch in line.replace(" ", "")])
        elif section == "south":
            south.append([1 if ch not in ".-" else 0 for ch in line.replace(" ", "")])
        elif section == "entrance":
            r, c = line.split(",")
            entrance = (int(r), int(c))
    return east, south, entrance


def sides_for(east: list[list[int]], south: list[list[int]],
              rows: int, cols: int) -> dict[tuple[int, int], str]:
    """Work out which doorways each room needs."""
    out: dict[tuple[int, int], str] = {}
    for r in range(rows):
        for c in range(cols):
            s = ""
            if r > 0 and south[r - 1][c]:
                s += "n"
            if r < rows - 1 and south[r][c]:
                s += "s"
            if c < cols - 1 and east[r][c]:
                s += "e"
            if c > 0 and east[r][c - 1]:
                s += "w"
            out[(r, c)] = s
    return out


def reachable(sides: dict[tuple[int, int], str], start: tuple[int, int]) -> set[tuple[int, int]]:
    """Every room you can walk to from the entrance, ignoring locks."""
    seen = {start}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for letter, (dr, dc) in DIRS.items():
            nxt = (cell[0] + dr, cell[1] + dc)
            if letter in sides[cell] and nxt in sides and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def frame_name(sides: str) -> str:
    """The frame block for a set of doorways."""
    ordered = "".join(letter for letter in "nsew" if letter in sides)
    return f"r_{ordered}" if ordered else "r_shut"


def main(argv: list[str] | None = None) -> int:
    """Plan one dungeon."""
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    folder = ROOT / "data" / "dungeons" / args[0]
    east, south, entrance = read_connections(folder / "connections.txt")
    rows, cols = len(east), len(east[0]) + 1
    sides = sides_for(east, south, rows, cols)
    seen = reachable(sides, entrance)
    missing = sorted(set(sides) - seen)
    if missing:
        print(f"unreachable rooms: {missing}", file=sys.stderr)
        return 1
    motifs: dict[tuple[int, int], str] = {}
    motif_file = folder / "motifs.txt"
    if motif_file.exists():
        for raw in motif_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            cell, _, names = line.partition(" ")
            r, c = cell.split(",")
            motifs[(int(r), int(c))] = names.strip()
    out = [" ".join(
        frame_name(sides[(r, c)]) + ("+" + motifs[(r, c)].replace(" ", "+")
                                     if motifs.get((r, c)) else "")
        for c in range(cols)) for r in range(rows)]
    header = (f"# {args[0]}, {cols} x {rows} rooms, planned by tools/plan_dungeon.py\n"
              "# from connections.txt and motifs.txt. Every room is reachable.\n")
    (folder / "layout_f1.txt").write_text(header + "\n".join(out) + "\n", encoding="utf-8")
    print(f"{args[0]}: {rows * cols} rooms, all reachable from {entrance}")
    for r in range(rows):
        print("  " + " ".join(f"{sides[(r, c)] or '-':4s}" for c in range(cols)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
