"""The three minigames: the shooting gallery, the dig patch and the bells.

Each is a screen of its own, like the shop: ``update`` takes the input and
returns "close" when it is over, ``draw`` paints 320x240. They share the
scoring and the prize payout, which comes out of ``data/minigames.json`` so
the prizes are content rather than code.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pygame

from eldermoor.config import CANVAS_H, CANVAS_W, DATA, FPS, PLAY_W

if TYPE_CHECKING:
    from eldermoor.input import Input
    from eldermoor.world import World


@dataclass(frozen=True)
class GameDef:
    """One minigame: its name, its fee and what it pays for a good score."""

    id: str
    name: str
    greeting: str
    cost: int
    prizes: list[tuple[int, str, str]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def number(self, key: str, fallback: int) -> int:
        """One of the game's own settings."""
        return int(self.raw.get(key, fallback))


class MiniGames:
    """The table of minigames."""

    def __init__(self, games: dict[str, GameDef]) -> None:
        self.games = games

    @classmethod
    def load(cls, root: Path = DATA) -> MiniGames:
        """Read data/minigames.json."""
        path = root / "minigames.json"
        if not path.exists():
            return cls({})
        raw = json.loads(path.read_text(encoding="utf-8"))
        out: dict[str, GameDef] = {}
        for game_id, d in raw["games"].items():
            prizes = [(int(p[0]), str(p[1]), str(p[2])) for p in d.get("prizes", [])]
            out[game_id] = GameDef(id=game_id, name=d["name"], greeting=d["greeting"],
                                   cost=int(d.get("cost", 0)), prizes=prizes, raw=d)
        return cls(out)

    def __len__(self) -> int:
        return len(self.games)

    def get(self, game_id: str) -> GameDef | None:
        """The definition, or None."""
        return self.games.get(game_id)


def pay_prizes(world: World, definition: GameDef, score: int) -> list[str]:
    """Hand over every prize this score has earned for the first time."""
    state = world.state
    won: list[str] = []
    for want, kind, value in definition.prizes:
        if score < want:
            continue
        flag = f"prize:{definition.id}:{want}"
        if state.flag(flag):
            continue
        state.set_flag(flag, 1)
        if kind == "embers":
            state.embers = min(999, state.embers + int(value))
        elif kind == "figurine":
            state.collect("figurines", value)
        elif kind == "furniture":
            state.collect("furniture", value)
        elif kind == "ring":
            state.find_ring(value)
        elif kind == "heart_piece":
            state.add_heart_piece()
        elif kind == "shell":
            state.seashells += 1
        won.append(kind)
    if won:
        world.audio.play("minigame_win")
    return won


class MiniGame:
    """Base: a title, a score, a countdown and the end-of-game payout."""

    def __init__(self, world: World, definition: GameDef) -> None:
        self.world = world
        self.definition = definition
        self.score = 0
        self.frame = 0
        self.over = False
        self.note = ""

    @property
    def best(self) -> int:
        """The stored best score for this game."""
        return self.world.state.scores.get(self.definition.id, 0)

    def finish(self) -> None:
        """Bank the score, pay the prizes and write the note."""
        self.over = True
        state = self.world.state
        record = state.best_score(self.definition.id, self.score)
        pay_prizes(self.world, self.definition, self.score)
        key = "game.record" if record else "game.score"
        self.note = self.world.textdb.get(key, n=self.score)

    def update(self, inp: Input) -> str | None:
        """One frame; returns "close" when the player leaves."""
        self.frame += 1
        if self.over:
            return "close" if inp.pressed("a") or inp.pressed("b") else None
        return self.play(inp)

    def play(self, inp: Input) -> str | None:
        """One frame of the game itself."""
        raise NotImplementedError

    def draw(self, target: pygame.Surface) -> None:
        """Paint the screen: the frame, then the game, then the score."""
        assets = self.world.assets
        target.fill(assets.colour("ink"))
        font = assets.font8
        font.draw(target, self.world.textdb.get(self.definition.name), 10, 8,
                  assets.colour("gold"))
        font.draw(target, f"{self.score:02d}", CANVAS_W - 30, 8, assets.colour("white"))
        self.paint(target)
        if self.note:
            font.draw(target, self.note, 10, CANVAS_H - 18, assets.colour("lime"))
        else:
            assets.font6.draw(target, self.world.textdb.get("game.best", n=self.best),
                              10, CANVAS_H - 16, assets.colour("mist"))

    def paint(self, target: pygame.Surface) -> None:
        """The game's own picture."""


class Gallery(MiniGame):
    """Targets slide across; A shoots the lane the cursor is in."""

    LANES = (60, 96, 132)

    def __init__(self, world: World, definition: GameDef) -> None:
        super().__init__(world, definition)
        self.seconds = definition.number("seconds", 30)
        self.left = self.seconds * FPS
        self.lane = 1
        self.flash = 0
        self.targets = [[world.rng.randrange(PLAY_W), 1.4 + i * 0.5, 1] for i in range(3)]

    def play(self, inp: Input) -> str | None:
        """Move the sight, fly the targets, shoot."""
        self.left -= 1
        if inp.pressed("up"):
            self.lane = max(0, self.lane - 1)
        if inp.pressed("down"):
            self.lane = min(len(self.LANES) - 1, self.lane + 1)
        for target in self.targets:
            target[0] += target[1]
            if target[0] > PLAY_W + 16:
                target[0] = -16
                target[1] = 1.2 + self.world.rng.random() * 1.6
                target[2] = 1
        if inp.pressed("a"):
            self.world.audio.play("bow")
            self.flash = 4
            target = self.targets[self.lane]
            if target[2] and 40 <= target[0] <= 220:
                target[2] = 0
                target[0] = PLAY_W + 20
                self.score += 1
                self.world.audio.play("enemy_hit")
        self.flash = max(0, self.flash - 1)
        if self.left <= 0:
            self.finish()
        return None

    def paint(self, target: pygame.Surface) -> None:
        """Three lanes, a sight and whatever is sliding past."""
        assets = self.world.assets
        for i, y in enumerate(self.LANES):
            pygame.draw.line(target, assets.colour("slate"), (8, y + 14), (CANVAS_W - 8, y + 14))
            spec = self.targets[i]
            if spec[2]:
                pygame.draw.circle(target, assets.colour("red"),
                                   (int(spec[0]) + 8, y + 6), 6)
                pygame.draw.circle(target, assets.colour("white"),
                                   (int(spec[0]) + 8, y + 6), 2)
        y = self.LANES[self.lane]
        colour = assets.colour("gold") if not self.flash else assets.colour("white")
        pygame.draw.rect(target, colour, pygame.Rect(10, y + 2, 8, 8), 1)
        assets.font6.draw(target, self.world.textdb.get("game.time", n=self.left // FPS),
                          CANVAS_W - 70, 22, assets.colour("mist"))


class Dig(MiniGame):
    """A patch of mounds; a fixed number of digs finds what it finds."""

    COLS, ROWS = 6, 4

    def __init__(self, world: World, definition: GameDef) -> None:
        super().__init__(world, definition)
        self.digs = definition.number("digs", 10)
        self.cursor = 0
        self.dug: dict[int, bool] = {}
        cells = list(range(self.COLS * self.ROWS))
        world.rng.shuffle(cells)
        self.prizes = set(cells[: self.COLS * self.ROWS // 2])

    def play(self, inp: Input) -> str | None:
        """Move over the patch and dig."""
        if inp.pressed("right"):
            self.cursor = (self.cursor + 1) % (self.COLS * self.ROWS)
        if inp.pressed("left"):
            self.cursor = (self.cursor - 1) % (self.COLS * self.ROWS)
        if inp.pressed("down"):
            self.cursor = (self.cursor + self.COLS) % (self.COLS * self.ROWS)
        if inp.pressed("up"):
            self.cursor = (self.cursor - self.COLS) % (self.COLS * self.ROWS)
        if inp.pressed("a") and self.cursor not in self.dug:
            found = self.cursor in self.prizes
            self.dug[self.cursor] = found
            self.digs -= 1
            self.score += int(found)
            self.world.audio.play("ember" if found else "dig")
            if self.digs <= 0:
                self.finish()
        return None

    def paint(self, target: pygame.Surface) -> None:
        """The patch, the cursor and the digs left."""
        assets = self.world.assets
        for i in range(self.COLS * self.ROWS):
            col, row = i % self.COLS, i // self.COLS
            box = pygame.Rect(40 + col * 40, 50 + row * 36, 30, 26)
            state = self.dug.get(i)
            fill = "shadow" if state is None else ("gold" if state else "slate")
            target.fill(assets.colour(fill), box)
            edge = assets.colour("white") if i == self.cursor else assets.colour("stone")
            pygame.draw.rect(target, edge, box, 1)
        assets.font6.draw(target, self.world.textdb.get("game.digs", n=self.digs),
                          CANVAS_W - 80, 22, assets.colour("mist"))


class Bells(MiniGame):
    """A button is shown; press that one before the bar runs out."""

    BUTTONS = ("a", "b", "l", "r")

    def __init__(self, world: World, definition: GameDef) -> None:
        super().__init__(world, definition)
        self.rounds = definition.number("rounds", 12)
        self.window = 60
        self.timer = self.window
        self.want = world.rng.choice(self.BUTTONS)
        self.result = ""

    def play(self, inp: Input) -> str | None:
        """Watch for the right button, or the bar running out."""
        self.timer -= 1
        pressed = [b for b in self.BUTTONS if inp.pressed(b)]
        if pressed:
            if pressed[0] == self.want:
                self.score += 1
                self.result = "hit"
                self.world.audio.play("menu_select")
            else:
                self.result = "miss"
                self.world.audio.play("error")
            self._next()
        elif self.timer <= 0:
            self.result = "miss"
            self.world.audio.play("error")
            self._next()
        return None

    def _next(self) -> None:
        """Next round, a shade faster, or the end."""
        self.rounds -= 1
        if self.rounds <= 0:
            self.finish()
            return
        self.window = max(22, self.window - 3)
        self.timer = self.window
        self.want = self.world.rng.choice(self.BUTTONS)

    def paint(self, target: pygame.Surface) -> None:
        """The button to press and the bar running down."""
        assets = self.world.assets
        font = assets.font8
        label = self.want.upper()
        font.draw(target, label, CANVAS_W // 2 - 4, 90, assets.colour("gold"))
        width = round(120 * self.timer / max(1, self.window))
        pygame.draw.rect(target, assets.colour("slate"), pygame.Rect(100, 120, 120, 8), 1)
        target.fill(assets.colour("lime"), pygame.Rect(100, 120, width, 8))
        if self.result:
            assets.font6.draw(target, self.world.textdb.get(f"game.{self.result}"),
                              CANVAS_W // 2 - 12, 140, assets.colour("mist"))


KINDS = {"gallery": Gallery, "dig": Dig, "bells": Bells}


def start(world: World, game_id: str) -> MiniGame | None:
    """Build the minigame for an id, or None if there is no such game."""
    definition = world.content.minigames.get(game_id)
    if definition is None:
        return None
    factory = KINDS.get(game_id)
    return factory(world, definition) if factory else None
