"""The companion in the lantern: a hint, when you have stood still long enough.

She is the game's tutorial. There are no pop-ups: if the player stops for a
few seconds, the first hint in ``data/hints.json`` whose conditions hold gets
said once, in the ordinary dialogue box, and not again in that room. Turning
*Hints* off in the settings turns her off entirely.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eldermoor.config import DATA, FPS

if TYPE_CHECKING:
    from eldermoor.state import GameState
    from eldermoor.world import World


@dataclass(frozen=True)
class Hint:
    """One thing she might say, and when she will say it."""

    text: str
    needs_item: str = ""
    unless_item: str = ""
    needs_flag: str = ""
    unless_flag: str = ""

    def applies(self, state: GameState) -> bool:
        """True when every condition on this hint holds."""
        if self.needs_item and not state.has(self.needs_item):
            return False
        if self.unless_item and state.has(self.unless_item):
            return False
        if self.needs_flag and not state.flag(self.needs_flag):
            return False
        if self.unless_flag and state.flag(self.unless_flag):
            return False
        return True


@dataclass
class Hints:
    """The hint table: the story hints in order, plus one per special room."""

    hints: list[Hint] = field(default_factory=list)
    rooms: dict[str, str] = field(default_factory=dict)
    idle_frames: int = 14 * FPS

    @classmethod
    def load(cls, root: Path = DATA) -> Hints:
        """Read data/hints.json."""
        path = root / "hints.json"
        if not path.exists():
            return cls()
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        hints = [Hint(text=d["text"], needs_item=d.get("needs_item", ""),
                      unless_item=d.get("unless_item", ""), needs_flag=d.get("needs_flag", ""),
                      unless_flag=d.get("unless_flag", ""))
                 for d in raw.get("hints", [])]
        return cls(hints=hints, rooms=dict(raw.get("rooms", {})),
                   idle_frames=round(float(raw.get("idle_seconds", 14)) * FPS))

    def __len__(self) -> int:
        return len(self.hints)

    def for_state(self, state: GameState, room_id: str = "") -> str:
        """The text key she would say right now, or "" if she has nothing."""
        if room_id in self.rooms:
            return self.rooms[room_id]
        for hint in reversed(self.hints):
            if hint.applies(state):
                return hint.text
        return ""


class Companion:
    """Counts how long Wren has stood still and speaks when it is long enough."""

    def __init__(self, table: Hints) -> None:
        self.table = table
        self.idle = 0
        self.said: set[str] = set()
        self.enabled = True

    def reset(self) -> None:
        """New room: forget the idle count, keep what has been said."""
        self.idle = 0

    def update(self, world: World) -> str:
        """One frame. Returns the text key she said, or "" for nothing."""
        if not self.enabled or world.dialogue is not None:
            self.idle = 0
            return ""
        if world.hero.moving or world.hero.busy:
            self.idle = 0
            return ""
        self.idle += 1
        if self.idle < self.table.idle_frames:
            return ""
        self.idle = 0
        key = self.table.for_state(world.state, world.room.id)
        here = f"{world.room.id}:{key}"
        if not key or here in self.said:
            return ""
        self.said.add(here)
        world.audio.play("text")
        world.say(key)
        return key
