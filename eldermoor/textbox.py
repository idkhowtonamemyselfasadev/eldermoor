"""The bottom dialogue box: word wrap, typewriter reveal, pages and yes/no choices."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import CANVAS_H, CANVAS_W, DIALOGUE_COLS, DIALOGUE_LINES, TEXT_SPEED_DEFAULT

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.input import Input

BOX_H = DIALOGUE_LINES * 10 + 12
BOX_X = 8
BOX_W = CANVAS_W - 16
BOX_Y = CANVAS_H - BOX_H - 6
PAD = 6


def wrap(text: str, cols: int = DIALOGUE_COLS) -> list[str]:
    """Greedy word wrap. ``\\n`` forces a break, a word longer than a line is split."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            while len(word) > cols:
                if line:
                    lines.append(line)
                    line = ""
                lines.append(word[:cols])
                word = word[cols:]
            if not line:
                line = word
            elif len(line) + 1 + len(word) <= cols:
                line += " " + word
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def paginate(text: str, cols: int = DIALOGUE_COLS, rows: int = DIALOGUE_LINES) -> list[list[str]]:
    """Wrapped text split into pages of at most ``rows`` lines."""
    lines = wrap(text, cols)
    return [lines[i:i + rows] for i in range(0, len(lines), rows)] or [[""]]


class TextBox:
    """One conversation: a list of pages, revealed a glyph at a time."""

    def __init__(self, pages: list[str], speed: int = TEXT_SPEED_DEFAULT,
                 choice: tuple[str, str] | None = None, portrait: str | None = None) -> None:
        self.pages: list[list[str]] = []
        for page in pages:
            self.pages.extend(paginate(page))
        self.speed = max(1, speed)
        self.choice = choice
        self.portrait = portrait
        self.page = 0
        self.revealed = 0
        self.done = False
        self.selected = 0
        self.result: int | None = None

    # ----- state ---------------------------------------------------------
    @property
    def current(self) -> list[str]:
        """Lines of the current page."""
        return self.pages[min(self.page, len(self.pages) - 1)]

    @property
    def page_length(self) -> int:
        """Total glyphs on the current page."""
        return sum(len(line) for line in self.current)

    @property
    def fully_revealed(self) -> bool:
        """True once the whole page is on screen."""
        return self.revealed >= self.page_length

    @property
    def on_last_page(self) -> bool:
        """True on the final page."""
        return self.page >= len(self.pages) - 1

    def visible_lines(self) -> list[str]:
        """The current page clipped to the revealed glyph count."""
        left = self.revealed
        out: list[str] = []
        for line in self.current:
            out.append(line[:left] if left < len(line) else line)
            left = max(0, left - len(line))
        return out

    # ----- input ---------------------------------------------------------
    def update(self, inp: Input) -> str | None:
        """Advance one frame. Returns "typed" on each new glyph, "page" or "done"."""
        if self.done:
            return None
        if inp.is_held("b") and not self.fully_revealed:
            self.revealed = self.page_length
            return "page"
        if not self.fully_revealed:
            before = self.revealed
            self.revealed = min(self.page_length, self.revealed + self.speed)
            return "typed" if self.revealed != before else None
        if self.choice is not None and self.on_last_page:
            return self._update_choice(inp)
        if inp.pressed("a") or inp.pressed("start"):
            if self.on_last_page:
                self.done = True
                return "done"
            self.page += 1
            self.revealed = 0
            return "page"
        return None

    def _update_choice(self, inp: Input) -> str | None:
        if inp.pressed("up") or inp.pressed("down"):
            self.selected = 1 - self.selected
            return "move"
        if inp.pressed("a"):
            self.result = self.selected
            self.done = True
            return "done"
        if inp.pressed("b"):
            self.result = 1
            self.done = True
            return "done"
        return None

    # ----- drawing -------------------------------------------------------
    def draw(self, target: pygame.Surface, assets: Assets) -> None:
        """Draw the box, the revealed text, the choice and the advance arrow."""
        box = pygame.Rect(BOX_X, BOX_Y, BOX_W, BOX_H)
        target.fill(assets.colour("ink"), box)
        pygame.draw.rect(target, assets.colour("bone"), box, 1)
        pygame.draw.rect(target, assets.colour("slate"), box.inflate(-4, -4), 1)
        font = assets.font8
        y = BOX_Y + PAD
        for line in self.visible_lines():
            font.draw(target, line, BOX_X + PAD, y, assets.colour("white"))
            y += 10
        if self.choice is not None and self.on_last_page and self.fully_revealed:
            self._draw_choice(target, assets)
        elif self.fully_revealed:
            font.draw(target, "▼" if assets.font8.has("▼") else "↓",
                      BOX_X + BOX_W - 14, BOX_Y + BOX_H - 12, assets.colour("gold"))

    def _draw_choice(self, target: pygame.Surface, assets: Assets) -> None:
        font = assets.font8
        x = BOX_X + BOX_W - 80
        for i, label in enumerate(self.choice or ()):
            y = BOX_Y + PAD + i * 10
            colour = assets.colour("gold") if i == self.selected else assets.colour("mist")
            font.draw(target, ("→" if i == self.selected else " ") + label, x, y, colour)
