"""The two endings and the credits roll."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import CANVAS_H, CANVAS_W
from eldermoor.textbox import paginate

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.content import Content
    from eldermoor.input import Input
    from eldermoor.state import GameState

#: a run this complete earns the longer ending
FULL_ENDING_AT = 95.0
SCROLL_SPEED = 0.35
CREDITS = (
    "LANTERN OF ELDERMOOR",
    "",
    "design, code, pixels and noise",
    "written for one laptop",
    "",
    "every sprite is a text file",
    "every sound is an oscillator",
    "every room was placed by hand",
    "",
    "thank you for lighting them all",
)


class Ending:
    """Text pages, then a slow credits crawl, then back to the lantern."""

    def __init__(self, assets: Assets, content: Content, state: GameState,
                 audio: object, which: str) -> None:
        self.assets = assets
        self.content = content
        self.state = state
        self.audio = audio
        self.full = state.completion() >= FULL_ENDING_AT or which == "full"
        key = "ending.full" if self.full else "ending.short"
        self.pages: list[list[str]] = []
        for page in content.text.pages(key):
            self.pages.extend(paginate(page, cols=36, rows=6))
        self.page = 0
        self.timer = 0
        self.scroll = 0.0
        self.done = False
        if hasattr(audio, "play_music"):
            audio.play_music("credits")           # falls back to silence if unbuilt

    @property
    def rolling(self) -> bool:
        """True once the text is finished and the credits are moving."""
        return self.page >= len(self.pages)

    def update(self, inp: Input) -> bool:
        """One frame. Returns True when the ending is over."""
        self.timer += 1
        if self.rolling:
            self.scroll += SCROLL_SPEED
            if self.scroll > len(CREDITS) * 12 + CANVAS_H or inp.pressed("start"):
                self.done = True
            return self.done
        if inp.pressed("a") or inp.pressed("start"):
            self.page += 1
        return False

    def draw(self, target: pygame.Surface) -> None:
        """Paint the current page, or the crawl."""
        target.fill(self.assets.colour("ink"))
        font = self.assets.font8
        if not self.rolling:
            lines = self.pages[self.page]
            y = (CANVAS_H - len(lines) * 12) // 2
            for line in lines:
                font.draw(target, line, (CANVAS_W - font.measure(line)) // 2, y,
                          self.assets.colour("white"))
                y += 12
            return
        y = CANVAS_H - round(self.scroll)
        for line in CREDITS:
            if -12 < y < CANVAS_H:
                colour = self.assets.colour("gold") if line.isupper() and line \
                    else self.assets.colour("mist")
                font.draw(target, line, (CANVAS_W - font.measure(line)) // 2, y, colour)
            y += 12
