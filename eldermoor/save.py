"""Save slots: atomic writes, a backup of the last good file, versioned migrations."""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from eldermoor.config import SAVE_SLOTS, SAVE_VERSION
from eldermoor.settings import ensure_config_dir
from eldermoor.state import GameState

CRASH_SLOT = 0  # slot 0 is the crash slot: written by the top-level handler, never by the menu


def saves_dir() -> Path:
    """The saves/ folder inside the user's config directory."""
    return ensure_config_dir() / "saves"


def slot_path(slot: int) -> Path:
    """Path of one slot's JSON file."""
    return saves_dir() / f"slot{slot}.json"


# ----- migrations --------------------------------------------------------
def _v1_to_v2(raw: dict[str, Any]) -> dict[str, Any]:
    """Milestone-1 saves had no items, flags or dungeons; add the new shape."""
    raw.setdefault("owned", [])
    raw.setdefault("slots", [None, None, None])
    raw.setdefault("flags", {})
    raw.setdefault("dungeons", {})
    raw.setdefault("room", "village_00")
    raw["version"] = 2
    return raw


MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {1: _v1_to_v2}


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    """Bring a save dict up to SAVE_VERSION, one step at a time."""
    version = int(raw.get("version", 1))
    while version < SAVE_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            raise ValueError(f"no migration from save version {version}")
        raw = step(raw)
        new_version = int(raw.get("version", version))
        if new_version <= version:
            raise ValueError(f"migration from {version} did not advance the version")
        version = new_version
    return raw


# ----- read / write ------------------------------------------------------
def save(state: GameState, slot: int | None = None) -> Path:
    """Write a slot atomically, keeping the previous file as .bak."""
    n = state.slot if slot is None else slot
    state.sync_keys()
    path = slot_path(n)
    payload = state.to_json()
    payload["slot"] = n
    payload["saved_at"] = time.time()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    if path.exists():
        path.replace(path.with_suffix(".bak"))
    tmp.replace(path)
    return path


def _read(path: Path) -> GameState | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        return GameState.from_json(migrate(raw))
    except (TypeError, ValueError):
        return None


def load(slot: int) -> GameState | None:
    """Read a slot; falls back to the .bak if the main file is missing or corrupt."""
    for path in (slot_path(slot), slot_path(slot).with_suffix(".bak")):
        if path.exists():
            state = _read(path)
            if state is not None:
                state.slot = slot
                return state
    return None


def delete(slot: int) -> None:
    """Remove a slot and its backup."""
    for suffix in ("", ".bak", ".tmp"):
        p = slot_path(slot).with_suffix(suffix) if suffix else slot_path(slot)
        p.unlink(missing_ok=True)


def summary(slot: int) -> dict[str, Any] | None:
    """Short description of a slot for the file-select screen, or None if empty."""
    state = load(slot)
    if state is None:
        return None
    return {"slot": slot, "hearts": state.max_hearts, "health": state.health,
            "flames": len([d for d in state.dungeons.values() if d.flame]),
            "playtime": state.playtime, "completion": state.completion(),
            "room": state.room, "deaths": state.deaths}


def all_summaries() -> list[dict[str, Any] | None]:
    """Summaries of the three real slots, in order."""
    return [summary(i) for i in range(1, SAVE_SLOTS + 1)]


def crash_save(state: GameState) -> Path:
    """Dump the state to the crash slot so a crash never loses progress."""
    return save(state, CRASH_SLOT)
