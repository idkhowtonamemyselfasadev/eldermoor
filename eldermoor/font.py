"""Bitmap fonts: glyph blocks named U+XXXX in a sheet, tinted and optionally outlined."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from eldermoor.assets import Sheet

Colour = tuple[int, int, int]
WHITE: Colour = (244, 242, 248)
BLACK: Colour = (11, 10, 18)

OUTLINE_OFFSETS = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1))


class BitmapFont:
    """Fixed-width bitmap font. Glyphs in the sheet are white and get tinted on draw."""

    def __init__(self, sheet: Sheet, width: int, height: int) -> None:
        self.sheet = sheet
        self.width = width
        self.height = height
        self._tinted: dict[tuple[str, Colour], pygame.Surface] = {}

    @staticmethod
    def glyph_name(ch: str) -> str:
        """Atlas block name for a character."""
        return f"U+{ord(ch):04X}"

    def has(self, ch: str) -> bool:
        """True if the font contains a glyph for the character."""
        return self.sheet.has(self.glyph_name(ch))

    def glyph(self, ch: str, colour: Colour = WHITE) -> pygame.Surface:
        """Tinted glyph surface; unknown characters render as '?'."""
        if not self.has(ch):
            ch = "?"
        key = (ch, colour)
        surf = self._tinted.get(key)
        if surf is None:
            surf = self.sheet.get(self.glyph_name(ch)).copy()
            # glyph pixels are palette white (not pure); force RGB to 255 (alpha untouched), then tint
            surf.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
            surf.fill(colour, special_flags=pygame.BLEND_RGB_MULT)
            self._tinted[key] = surf
        return surf

    def measure(self, text: str) -> int:
        """Pixel width of a single line of text."""
        return len(text) * self.width

    def draw(self, target: pygame.Surface, text: str, x: int, y: int,
             colour: Colour = WHITE, outline: Colour | None = None) -> int:
        """Draw one line of text. Returns the x after the last glyph."""
        if outline is not None:
            for ox, oy in OUTLINE_OFFSETS:
                self._draw_plain(target, text, x + ox, y + oy, outline)
        return self._draw_plain(target, text, x, y, colour)

    def _draw_plain(self, target: pygame.Surface, text: str, x: int, y: int, colour: Colour) -> int:
        for ch in text:
            target.blit(self.glyph(ch, colour), (x, y))
            x += self.width
        return x

    def draw_lines(self, target: pygame.Surface, lines: list[str], x: int, y: int,
                   colour: Colour = WHITE, outline: Colour | None = None, spacing: int = 1) -> None:
        """Draw several lines top to bottom."""
        for line in lines:
            self.draw(target, line, x, y, colour, outline)
            y += self.height + spacing
