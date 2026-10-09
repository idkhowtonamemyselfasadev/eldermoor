"""Pause menu (items, rings, log, finds, map, settings, save) and file select."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from eldermoor import pages
from eldermoor.config import CANVAS_H, CANVAS_W, SAVE_SLOTS
from eldermoor.state import GameState

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.content import Content
    from eldermoor.input import Input
    from eldermoor.settings import Settings

PAGES = ("items", "rings", "quest", "collect", "map", "settings", "save")
GRID_COLS = 5
GRID_X = 24
GRID_Y = 56
CELL = 24
SETTINGS_ROWS = (
    ("music_volume", "menu.music", "percent"),
    ("sfx_volume", "menu.sfx", "percent"),
    ("text_speed", "menu.text_speed", "steps"),
    ("screen_shake", "menu.shake", "bool"),
    ("low_health_beep", "menu.beep", "bool"),
    ("hints", "menu.hints", "bool"),
    ("stretch", "menu.stretch", "bool"),
)


class PauseMenu:
    """The Start screen. L/R flip pages, A acts, Start or B closes."""

    def __init__(self, assets: Assets, content: Content, state: GameState,
                 audio: Any, settings: Settings, page: int = 0) -> None:
        self.assets = assets
        self.content = content
        self.state = state
        self.audio = audio
        self.settings = settings
        self.page = page
        self.cursor = 0
        self.message = ""
        self.want_save = False
        self.want_warp = ""
        self.tab = 0
        self.ring_slot = 0

    # ----- frame ---------------------------------------------------------
    def update(self, inp: Input) -> str | None:
        """One frame. Returns "close" when the menu should go away."""
        if inp.pressed("start") or inp.pressed("b"):
            self.audio.play("unpause")
            return "close"
        if inp.pressed("r"):
            self.page = (self.page + 1) % len(PAGES)
            self.cursor = 0
            self.audio.play("menu_move")
        elif inp.pressed("l"):
            self.page = (self.page - 1) % len(PAGES)
            self.cursor = 0
            self.audio.play("menu_move")
        handler = getattr(self, f"_update_{PAGES[self.page]}", None)
        return handler(inp) if handler else None

    def _update_items(self, inp: Input) -> None:
        owned = self.content.items.ordered(self.state.owned)
        if not owned:
            return
        self._move_cursor(inp, len(owned), GRID_COLS)
        if inp.pressed("a"):
            item = owned[self.cursor]
            if item.assignable:
                slot = self._next_slot(item.id)
                self.state.assign(slot, item.id)
                self.audio.play("menu_select")
            else:
                self.audio.play("error")

    def _next_slot(self, item_id: str) -> int:
        slots = self.state.slots
        if item_id in slots:
            return (slots.index(item_id) + 1) % 3
        for i, cur in enumerate(slots):
            if cur is None:
                return i
        return 0

    def _update_rings(self, inp: Input) -> None:
        pages.update_rings(self, inp)

    def _update_quest(self, inp: Input) -> None:
        pages.update_quest(self, inp)

    def _update_collect(self, inp: Input) -> None:
        pages.update_collect(self, inp)

    def _update_map(self, inp: Input) -> None:
        """Flip through the lit warp lanterns; A travels to one."""
        regions = sorted(self.state.warps)
        if not regions:
            return
        self._move_cursor(inp, len(regions), 1)
        if inp.pressed("a"):
            self.want_warp = self.state.warps[regions[self.cursor]]
            self.audio.play("warp")

    def _update_settings(self, inp: Input) -> None:
        self._move_cursor(inp, len(SETTINGS_ROWS), 1)
        delta = int(inp.pressed("right")) - int(inp.pressed("left"))
        if not delta:
            return
        field, _label, kind = SETTINGS_ROWS[self.cursor]
        value = getattr(self.settings, field)
        if kind == "bool":
            value = not value
        elif kind == "percent":
            value = min(1.0, max(0.0, round(value + delta * 0.1, 2)))
        else:
            value = min(4, max(1, value + delta))
        setattr(self.settings, field, value)
        self.audio.play("menu_move")

    def _update_save(self, inp: Input) -> None:
        self._move_cursor(inp, 2, 1)
        if inp.pressed("a"):
            if self.cursor == 0:
                self.want_save = True
                self.message = self.content.text.get("menu.saved")
                self.audio.play("save")
            else:
                self.audio.play("menu_back")

    def move_cursor(self, inp: Input, count: int, cols: int) -> None:
        """Move the page cursor within a grid (pages.py calls this too)."""
        self._move_cursor(inp, count, cols)

    def _move_cursor(self, inp: Input, count: int, cols: int) -> None:
        if count <= 0:
            return
        before = self.cursor
        if inp.pressed("right"):
            self.cursor += 1
        if inp.pressed("left"):
            self.cursor -= 1
        if inp.pressed("down"):
            self.cursor += cols
        if inp.pressed("up"):
            self.cursor -= cols
        self.cursor = max(0, min(count - 1, self.cursor))
        if self.cursor != before:
            self.audio.play("select_cursor")

    # ----- drawing -------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        """Paint the whole pause screen."""
        target.fill(self.assets.colour("ink"))
        font = self.assets.font8
        titles = [self.content.text.get(f"menu.{p}") for p in PAGES]
        x = 8
        for i, title in enumerate(titles):
            colour = self.assets.colour("gold") if i == self.page else self.assets.colour("stone")
            font.draw(target, title, x, 8, colour)
            x += font.measure(title) + 8
        pygame.draw.line(target, self.assets.colour("slate"), (0, 22), (CANVAS_W, 22))
        getattr(self, f"_draw_{PAGES[self.page]}")(target)
        if self.message:
            self.assets.font8.draw(target, self.message, 8, CANVAS_H - 14,
                                   self.assets.colour("lime"))

    def _draw_items(self, target: pygame.Surface) -> None:
        owned = self.content.items.ordered(self.state.owned)
        font = self.assets.font6
        for i, item in enumerate(owned):
            col, row = i % GRID_COLS, i // GRID_COLS
            box = pygame.Rect(GRID_X + col * CELL, GRID_Y + row * CELL, 20, 20)
            target.fill(self.assets.colour("shadow"), box)
            edge = self.assets.colour("gold") if i == self.cursor else self.assets.colour("stone")
            pygame.draw.rect(target, edge, box, 1)
            if self.assets.icons.has(item.icon):
                target.blit(self.assets.icons.get(item.icon), (box.x + 6, box.y + 6))
            if item.id in self.state.slots:
                font.draw(target, "BXY"[self.state.slots.index(item.id)],
                          box.right - 6, box.bottom - 8, self.assets.colour("lime"))
        if owned:
            name = self.content.text.get(owned[self.cursor].name)
            self.assets.font8.draw(target, name, 8, 32, self.assets.colour("white"))
            desc = self.content.text.get(owned[self.cursor].desc or "item.nodesc")
            font.draw(target, desc[:52], 8, CANVAS_H - 26, self.assets.colour("mist"))
        else:
            self.assets.font8.draw(target, self.content.text.get("menu.empty"), 8, 40,
                                   self.assets.colour("mist"))

    def _draw_rings(self, target: pygame.Surface) -> None:
        pages.draw_rings(self, target)

    def _draw_quest(self, target: pygame.Surface) -> None:
        pages.draw_quest(self, target)

    def _draw_collect(self, target: pygame.Surface) -> None:
        pages.draw_collect(self, target)

    def _draw_map(self, target: pygame.Surface) -> None:
        font = self.assets.font8
        dungeon = self.content.dungeons.get(self.state.dungeon)
        if dungeon is None:
            font.draw(target, self.content.text.get("map.overworld"), 12, 40,
                      self.assets.colour("white"))
            font.draw(target, self.content.text.get("map.rooms", n=len(self.state.rooms_visited)),
                      12, 56, self.assets.colour("mist"))
            self._draw_warps(target)
            return
        progress = self.state.progress(dungeon.id)
        font.draw(target, self.content.text.get(dungeon.name), 12, 28, self.assets.colour("gold"))
        if not progress.map:
            font.draw(target, self.content.text.get("map.nomap"), 12, 48,
                      self.assets.colour("mist"))
        floor = dungeon.floor(1) or (dungeon.floors[0] if dungeon.floors else None)
        if floor is None:
            return
        size = 12
        ox = (CANVAS_W - floor.width * size) // 2
        oy = 48
        for room_id, (col, row) in floor.rooms.items():
            cell = pygame.Rect(ox + col * size, oy + row * size, size - 1, size - 1)
            seen = room_id in progress.rooms
            if not seen and not progress.map:
                continue
            target.fill(self.assets.colour("slate") if seen else self.assets.colour("shadow"), cell)
            pygame.draw.rect(target, self.assets.colour("stone"), cell, 1)
            if room_id == self.state.room:
                target.fill(self.assets.colour("gold"), cell.inflate(-6, -6))
            elif progress.compass and room_id == dungeon.boss_room:
                target.fill(self.assets.colour("red"), cell.inflate(-6, -6))

    def _draw_warps(self, target: pygame.Surface) -> None:
        """The list of lit warp lanterns on the overworld map page."""
        font = self.assets.font8
        regions = sorted(self.state.warps)
        if not regions:
            font.draw(target, self.content.text.get("map.nowarp"), 12, 76,
                      self.assets.colour("stone"))
            return
        font.draw(target, self.content.text.get("map.warp"), 12, 76,
                  self.assets.colour("mist"))
        for i, region in enumerate(regions):
            colour = self.assets.colour("gold") if i == self.cursor else self.assets.colour("white")
            font.draw(target, self.content.text.get(f"region.{region}"), 24, 92 + i * 12, colour)

    def _draw_settings(self, target: pygame.Surface) -> None:
        font = self.assets.font8
        y = 32
        for i, (field, label, kind) in enumerate(SETTINGS_ROWS):
            value = getattr(self.settings, field)
            if kind == "bool":
                shown = self.content.text.get("menu.on" if value else "menu.off")
            elif kind == "percent":
                shown = f"{round(value * 100):3d}%"
            else:
                shown = str(value)
            colour = self.assets.colour("gold") if i == self.cursor else self.assets.colour("white")
            font.draw(target, self.content.text.get(label), 20, y, colour)
            font.draw(target, shown, 220, y, colour)
            y += 12

    def _draw_save(self, target: pygame.Surface) -> None:
        font = self.assets.font8
        options = [self.content.text.get("menu.save_now"), self.content.text.get("menu.cancel")]
        for i, label in enumerate(options):
            colour = self.assets.colour("gold") if i == self.cursor else self.assets.colour("white")
            font.draw(target, label, 32, 48 + i * 14, colour)
        font.draw(target, self.content.text.get("menu.slot", n=self.state.slot), 32, 28,
                  self.assets.colour("mist"))


class FileSelect:
    """The three save slots at boot."""

    def __init__(self, assets: Assets, content: Content, summaries: list[dict[str, Any] | None],
                 audio: Any) -> None:
        self.assets = assets
        self.content = content
        self.summaries = summaries
        self.audio = audio
        self.cursor = 0

    def update(self, inp: Input) -> int | None:
        """Returns the chosen slot number, or None while still choosing."""
        if inp.pressed("down"):
            self.cursor = (self.cursor + 1) % SAVE_SLOTS
            self.audio.play("select_cursor")
        if inp.pressed("up"):
            self.cursor = (self.cursor - 1) % SAVE_SLOTS
            self.audio.play("select_cursor")
        if inp.pressed("a") or inp.pressed("start"):
            self.audio.play("menu_select")
            return self.cursor + 1
        return None

    def draw(self, target: pygame.Surface) -> None:
        """Title and the three slots."""
        target.fill(self.assets.colour("ink"))
        title = self.content.text.get("title.name")
        font = self.assets.font8
        font.draw(target, title, (CANVAS_W - font.measure(title)) // 2, 36,
                  self.assets.colour("gold"), outline=self.assets.colour("blood"))
        for i in range(SAVE_SLOTS):
            summary = self.summaries[i] if i < len(self.summaries) else None
            y = 96 + i * 30
            box = pygame.Rect(40, y - 6, CANVAS_W - 80, 26)
            pygame.draw.rect(target, self.assets.colour("gold") if i == self.cursor
                             else self.assets.colour("stone"), box, 1)
            if summary is None:
                font.draw(target, self.content.text.get("title.empty", n=i + 1), 52, y,
                          self.assets.colour("mist"))
            else:
                hours = int(summary["playtime"]) // 3600
                minutes = int(summary["playtime"]) // 60 % 60
                font.draw(target, self.content.text.get(
                    "title.slot", n=i + 1, f=summary["flames"], h=hours,
                    m=f"{minutes:02d}", p=summary["completion"]), 52, y,
                    self.assets.colour("white"))
