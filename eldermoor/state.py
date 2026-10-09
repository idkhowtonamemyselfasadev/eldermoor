"""GameState: everything a save file holds, and the questions the game asks of it."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eldermoor.config import SAVE_VERSION

MAX_HEARTS_CAP = 20
PIECES_PER_CONTAINER = 4
SEASHELLS_TOTAL = 40
HEART_PIECES_TOTAL = 40
FIGURINES_TOTAL = 24
FURNITURE_TOTAL = 12
QUESTS_TOTAL = 30
BESTIARY_TOTAL = 47
RINGS_TOTAL = 12
ITEMS_TOTAL = 40
#: how many rings may be worn at once
RING_SLOTS = 2


@dataclass
class DungeonProgress:
    """What the player has collected inside one dungeon."""

    keys: int = 0
    used_keys: int = 0
    big_key: bool = False
    map: bool = False
    compass: bool = False
    flame: bool = False
    cleared: bool = False
    rooms: list[str] = field(default_factory=list)
    chests: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """Plain-dict form for the save file."""
        return {"keys": self.keys, "used_keys": self.used_keys, "big_key": self.big_key,
                "map": self.map, "compass": self.compass, "flame": self.flame,
                "cleared": self.cleared, "rooms": list(self.rooms), "chests": list(self.chests)}

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> DungeonProgress:
        """Rebuild from the save file, tolerating missing keys."""
        return cls(keys=int(raw.get("keys", 0)), used_keys=int(raw.get("used_keys", 0)),
                   big_key=bool(raw.get("big_key", False)), map=bool(raw.get("map", False)),
                   compass=bool(raw.get("compass", False)), flame=bool(raw.get("flame", False)),
                   cleared=bool(raw.get("cleared", False)),
                   rooms=list(raw.get("rooms", [])), chests=list(raw.get("chests", [])))


@dataclass
class GameState:
    """The save file as a live object. Health is counted in half-hearts."""

    version: int = SAVE_VERSION
    slot: int = 1
    max_hearts: int = 3
    health: int = 6
    heart_pieces: int = 0
    embers: int = 0
    bombs: int = 0
    max_bombs: int = 0
    arrows: int = 0
    max_arrows: int = 0
    magic: int = 0
    max_magic: int = 0
    keys: int = 0                                    # small keys of the dungeon we are in
    sword_level: int = 0
    shield_level: int = 0
    tunic_level: int = 0
    seashells: int = 0
    owned: list[str] = field(default_factory=list)
    slots: list[str | None] = field(default_factory=lambda: [None, None, None])
    slots2: list[str | None] = field(default_factory=lambda: [None, None, None])
    flags: dict[str, int] = field(default_factory=dict)
    dungeons: dict[str, DungeonProgress] = field(default_factory=dict)
    room: str = "ow_1105"
    x: float = 152.0
    y: float = 112.0
    facing: str = "down"
    respawn_room: str = "ow_1105"
    respawn_x: float = 152.0
    respawn_y: float = 112.0
    dungeon: str = ""                                # "" on the overworld
    rooms_visited: list[str] = field(default_factory=list)
    warps: dict[str, str] = field(default_factory=dict)   # region -> room id
    playtime: float = 0.0
    deaths: int = 0
    minutes_of_day: float = 0.0                      # day/night clock
    rings: list[str] = field(default_factory=list)        # rings found
    worn: list[str | None] = field(default_factory=lambda: [None, None])
    figurines: list[str] = field(default_factory=list)
    furniture: list[str] = field(default_factory=list)
    placed: dict[str, str] = field(default_factory=dict)  # furniture id -> spot
    bestiary: dict[str, int] = field(default_factory=dict)  # enemy id -> kills
    quests: list[str] = field(default_factory=list)       # finished side quests
    trade: int = 0                                        # step in the trading chain
    scores: dict[str, int] = field(default_factory=dict)  # minigame -> best

    # ----- items ---------------------------------------------------------
    def has(self, item: str) -> bool:
        """True if the item has been collected."""
        return item in self.owned

    def give(self, item: str) -> bool:
        """Add an item. False if it was already owned."""
        if item in self.owned:
            return False
        self.owned.append(item)
        return True

    def assign(self, index: int, item: str | None, player: int = 0) -> None:
        """Put an item in a HUD slot (B, X, Y), clearing it from that player's others."""
        slots = self.slots2 if player else self.slots
        if not 0 <= index < len(slots):
            raise IndexError(index)
        if item is not None:
            for i, cur in enumerate(slots):
                if cur == item and i != index:
                    slots[i] = None
        slots[index] = item

    # ----- flags ---------------------------------------------------------
    def flag(self, name: str) -> int:
        """Flag value, 0 when never set."""
        return self.flags.get(name, 0)

    def set_flag(self, name: str, value: int = 1) -> None:
        """Set (or clear, with 0) a global flag."""
        if value:
            self.flags[name] = value
        else:
            self.flags.pop(name, None)

    # ----- health --------------------------------------------------------
    def heart_icons(self) -> list[str]:
        """Icon name per heart: heart_full / heart_half / heart_empty."""
        icons: list[str] = []
        for i in range(self.max_hearts):
            halves = max(0, min(2, self.health - 2 * i))
            icons.append(("heart_empty", "heart_half", "heart_full")[halves])
        return icons

    def damage(self, half_hearts: int) -> None:
        """Lose health, never below 0."""
        self.health = max(0, self.health - half_hearts)

    def heal(self, half_hearts: int) -> None:
        """Gain health, never above the maximum."""
        self.health = min(self.max_hearts * 2, self.health + half_hearts)

    def add_heart_container(self) -> None:
        """One more heart, up to the cap, and refill."""
        self.max_hearts = min(MAX_HEARTS_CAP, self.max_hearts + 1)
        self.health = self.max_hearts * 2

    def add_heart_piece(self) -> bool:
        """Collect a piece; returns True when four of them made a container."""
        self.heart_pieces += 1
        if self.heart_pieces % PIECES_PER_CONTAINER == 0:
            self.add_heart_container()
            return True
        return False

    @property
    def low_health(self) -> bool:
        """True when the beep should sound (one heart or less)."""
        return 0 < self.health <= 2

    # ----- dungeons ------------------------------------------------------
    def progress(self, dungeon_id: str) -> DungeonProgress:
        """Progress record for a dungeon, created on first use."""
        if dungeon_id not in self.dungeons:
            self.dungeons[dungeon_id] = DungeonProgress()
        return self.dungeons[dungeon_id]

    def enter_dungeon(self, dungeon_id: str) -> None:
        """Make a dungeon current so the HUD key counter follows it."""
        self.dungeon = dungeon_id
        self.keys = self.progress(dungeon_id).keys if dungeon_id else 0

    def sync_keys(self) -> None:
        """Push the HUD key counter back into the current dungeon's record."""
        if self.dungeon:
            self.progress(self.dungeon).keys = self.keys

    # ----- rings ---------------------------------------------------------
    def find_ring(self, ring_id: str) -> bool:
        """Add a ring to the box. False if it was already in there."""
        if ring_id in self.rings:
            return False
        self.rings.append(ring_id)
        return True

    def wear(self, index: int, ring_id: str | None) -> None:
        """Put a ring on one of the two fingers, taking it off the other."""
        if not 0 <= index < len(self.worn):
            raise IndexError(index)
        if ring_id is not None:
            for i, cur in enumerate(self.worn):
                if cur == ring_id and i != index:
                    self.worn[i] = None
        self.worn[index] = ring_id

    # ----- collections ---------------------------------------------------
    def collect(self, what: str, item_id: str) -> bool:
        """Add to a named collection ("figurines"/"furniture"). False if a duplicate."""
        box: list[str] = getattr(self, what)
        if item_id in box:
            return False
        box.append(item_id)
        return True

    def record_kill(self, enemy_id: str) -> int:
        """Count one kill in the bestiary and hand back the new total."""
        self.bestiary[enemy_id] = self.bestiary.get(enemy_id, 0) + 1
        return self.bestiary[enemy_id]

    def finish_quest(self, quest_id: str) -> bool:
        """Tick a side quest off. False if it was already done."""
        if quest_id in self.quests:
            return False
        self.quests.append(quest_id)
        return True

    def best_score(self, game_id: str, score: int) -> bool:
        """Record a minigame score; True when it beats the stored best."""
        if score <= self.scores.get(game_id, -1):
            return False
        self.scores[game_id] = score
        return True

    # ----- completion ----------------------------------------------------
    def completion(self) -> float:
        """Completion percent over the counters the post-game cares about."""
        parts = [
            (len([d for d in self.dungeons.values() if d.flame]), 8),
            (self.heart_pieces, HEART_PIECES_TOTAL),
            (self.seashells, SEASHELLS_TOTAL),
            (self.max_hearts - 3, MAX_HEARTS_CAP - 3),
            (len(self.owned), ITEMS_TOTAL),
            (len(self.rings), RINGS_TOTAL),
            (len(self.figurines), FIGURINES_TOTAL),
            (len(self.furniture), FURNITURE_TOTAL),
            (len(self.bestiary), BESTIARY_TOTAL),
            (len(self.quests), QUESTS_TOTAL),
        ]
        done = sum(min(got, total) / total for got, total in parts)
        return round(100.0 * done / len(parts), 1)

    # ----- serialisation -------------------------------------------------
    def to_json(self) -> dict[str, Any]:
        """Plain-dict form written to the save file."""
        out: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if key == "dungeons":
                out[key] = {k: v.to_json() for k, v in value.items()}
            else:
                out[key] = value
        out["version"] = SAVE_VERSION
        return out

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> GameState:
        """Rebuild from a (already migrated) save dict, ignoring unknown keys."""
        known = {f for f in cls().__dict__}
        kwargs = {k: v for k, v in raw.items() if k in known and k != "dungeons"}
        state = cls(**kwargs)
        state.dungeons = {k: DungeonProgress.from_json(v)
                          for k, v in raw.get("dungeons", {}).items()}
        for name in ("slots", "slots2"):
            slots = list(raw.get(name, getattr(state, name)))[:3]
            while len(slots) < 3:
                slots.append(None)
            setattr(state, name, slots)
        return state
