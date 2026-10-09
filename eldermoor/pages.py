"""The pause-menu pages that read the collection tables: rings, log and finds.

These are functions rather than methods so ``menu.py`` stays the frame and
these stay the content. Each takes the live :class:`~eldermoor.menu.PauseMenu`
and does one page's worth of work.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from eldermoor.config import CANVAS_H, CANVAS_W
from eldermoor.state import (
    BESTIARY_TOTAL,
    FIGURINES_TOTAL,
    FURNITURE_TOTAL,
    HEART_PIECES_TOTAL,
    QUESTS_TOTAL,
    RINGS_TOTAL,
    SEASHELLS_TOTAL,
)

if TYPE_CHECKING:
    from eldermoor.input import Input
    from eldermoor.menu import PauseMenu

#: the tabs on the finds page
TABS = ("summary", "figurines", "furniture", "bestiary")
GRID_COLS = 6
CELL = 22


# ----- rings --------------------------------------------------------------
def update_rings(menu: PauseMenu, inp: Input) -> None:
    """Move over the ring box; A puts a ring on, B-less repeats take it off."""
    rings = menu.content.rings.ordered(menu.state.rings)
    if not rings:
        return
    menu.move_cursor(inp, len(rings), GRID_COLS)
    if not inp.pressed("a"):
        return
    ring = rings[menu.cursor]
    worn = menu.state.worn
    if ring.id in worn:
        menu.state.wear(worn.index(ring.id), None)
        menu.audio.play("menu_back")
        return
    slot = 0 if worn[0] is None else (1 if worn[1] is None else menu.ring_slot)
    menu.ring_slot = 1 - slot
    menu.state.wear(slot, ring.id)
    menu.audio.play("menu_select")


def draw_rings(menu: PauseMenu, target: pygame.Surface) -> None:
    """The ring box, with the two worn rings marked."""
    rings = menu.content.rings.ordered(menu.state.rings)
    font6, font8 = menu.assets.font6, menu.assets.font8
    if not rings:
        font8.draw(target, menu.content.text.get("menu.ring_empty"), 8, 40,
                   menu.assets.colour("mist"))
        return
    for i, ring in enumerate(rings):
        col, row = i % GRID_COLS, i // GRID_COLS
        box = pygame.Rect(16 + col * CELL, 56 + row * CELL, 18, 18)
        target.fill(menu.assets.colour("shadow"), box)
        edge = menu.assets.colour("gold") if i == menu.cursor else menu.assets.colour("stone")
        pygame.draw.rect(target, edge, box, 1)
        if menu.assets.icons.has(ring.icon):
            target.blit(menu.assets.icons.get(ring.icon), (box.x + 5, box.y + 5))
        if ring.id in menu.state.worn:
            font6.draw(target, "*", box.right - 5, box.bottom - 8,
                       menu.assets.colour("lime"))
    chosen = rings[min(menu.cursor, len(rings) - 1)]
    font8.draw(target, menu.content.text.get(chosen.name), 8, 32,
               menu.assets.colour("white"))
    font6.draw(target, menu.content.text.get(chosen.desc or "item.nodesc"), 8, CANVAS_H - 26,
               menu.assets.colour("mist"))
    worn = [menu.content.text.get(menu.content.rings.rings[r].name)
            for r in menu.state.worn if r]
    font6.draw(target, f"{menu.content.text.get('menu.worn')}: " + (", ".join(worn) or "-"),
               8, CANVAS_H - 16, menu.assets.colour("lime"))


# ----- the quest log ------------------------------------------------------
def update_quest(menu: PauseMenu, inp: Input) -> None:
    """Scroll the log."""
    menu.move_cursor(inp, max(1, len(_log(menu))), 1)


def _log(menu: PauseMenu) -> list[tuple[str, str, bool]]:
    """(name, hint, done) per quest the player knows about."""
    table = menu.content.quests
    out = [(q.name, q.hint, False) for q in table.open_quests(menu.state)]
    out += [(q.name, q.hint, True) for q in table.done_quests(menu.state)]
    return out


def draw_quest(menu: PauseMenu, target: pygame.Surface) -> None:
    """Open quests with their hints, then the finished ones ticked off."""
    font6, font8 = menu.assets.font6, menu.assets.font8
    rows = _log(menu)
    if not rows:
        font8.draw(target, menu.content.text.get("menu.none_yet"), 8, 40,
                   menu.assets.colour("mist"))
        return
    first = max(0, min(menu.cursor - 3, len(rows) - 7))
    y = 30
    for i in range(first, min(first + 7, len(rows))):
        name, hint, done = rows[i]
        colour = menu.assets.colour("stone") if done else menu.assets.colour("white")
        mark = "+" if done else "-"
        font8.draw(target, f"{mark} {menu.content.text.get(name)}", 10, y, colour)
        if i == menu.cursor and not done:
            font6.draw(target, menu.content.text.get(hint)[:58], 18, y + 10,
                       menu.assets.colour("lime"))
            y += 10
        y += 12


# ----- the finds page -----------------------------------------------------
def update_collect(menu: PauseMenu, inp: Input) -> None:
    """Left/right change tab."""
    if inp.pressed("right"):
        menu.tab = (menu.tab + 1) % len(TABS)
        menu.audio.play("menu_move")
    elif inp.pressed("left"):
        menu.tab = (menu.tab - 1) % len(TABS)
        menu.audio.play("menu_move")


def draw_collect(menu: PauseMenu, target: pygame.Surface) -> None:
    """One tab at a time: the counters, the two cabinets, or the bestiary."""
    font6 = menu.assets.font6
    x = 8
    for i, tab in enumerate(TABS):
        label = menu.content.text.get(f"collect.{tab}" if tab != "summary" else "collect.total")
        colour = menu.assets.colour("gold") if i == menu.tab else menu.assets.colour("stone")
        font6.draw(target, label, x, 26, colour)
        x += font6.measure(label) + 6
    {"summary": _draw_summary, "figurines": _draw_figurines,
     "furniture": _draw_furniture, "bestiary": _draw_bestiary}[TABS[menu.tab]](menu, target)


def _counter(menu: PauseMenu, key: str, got: int, total: int) -> str:
    return f"{menu.content.text.get(key)}  {got}/{total}"


def _draw_summary(menu: PauseMenu, target: pygame.Surface) -> None:
    state = menu.state
    lines = [
        _counter(menu, "collect.pieces", state.heart_pieces, HEART_PIECES_TOTAL),
        _counter(menu, "collect.shells", state.seashells, SEASHELLS_TOTAL),
        _counter(menu, "collect.rings", len(state.rings), RINGS_TOTAL),
        _counter(menu, "collect.figurines", len(state.figurines), FIGURINES_TOTAL),
        _counter(menu, "collect.furniture", len(state.furniture), FURNITURE_TOTAL),
        _counter(menu, "collect.bestiary", len(state.bestiary), BESTIARY_TOTAL),
        _counter(menu, "collect.quests", len(state.quests), QUESTS_TOTAL),
        menu.content.text.get("quest.completion", p=state.completion()),
    ]
    menu.assets.font8.draw_lines(target, lines, 12, 40, menu.assets.colour("white"), spacing=2)


def _draw_cabinet(menu: PauseMenu, target: pygame.Surface, collection, have: list[str]) -> None:
    font6 = menu.assets.font6
    for i, entry in enumerate(collection.ordered()):
        col, row = i % GRID_COLS, i // GRID_COLS
        box = pygame.Rect(16 + col * CELL, 42 + row * CELL, 18, 18)
        target.fill(menu.assets.colour("shadow"), box)
        pygame.draw.rect(target, menu.assets.colour("stone"), box, 1)
        if entry.id in have and menu.assets.icons.has(entry.icon):
            target.blit(menu.assets.icons.get(entry.icon), (box.x + 5, box.y + 5))
        elif entry.id not in have:
            font6.draw(target, "?", box.x + 7, box.y + 6, menu.assets.colour("slate"))
    names = [menu.content.text.get(e.name) for e in collection.owned(have)]
    font6.draw(target, (", ".join(names))[:58] or menu.content.text.get("menu.none_yet"),
               8, CANVAS_H - 18, menu.assets.colour("mist"))


def _draw_figurines(menu: PauseMenu, target: pygame.Surface) -> None:
    _draw_cabinet(menu, target, menu.content.figurines, menu.state.figurines)


def _draw_furniture(menu: PauseMenu, target: pygame.Surface) -> None:
    _draw_cabinet(menu, target, menu.content.furniture, menu.state.furniture)


def _draw_bestiary(menu: PauseMenu, target: pygame.Surface) -> None:
    font6 = menu.assets.font6
    kinds = [e for e in menu.content.enemies.ordered() if not e.raw.get("hidden")]
    y, x = 40, 10
    for definition in kinds:
        kills = menu.state.bestiary.get(definition.id, 0)
        name = menu.content.text.get(definition.name)
        colour = menu.assets.colour("white") if kills else menu.assets.colour("slate")
        font6.draw(target, f"{name if kills else '???'} {kills or ''}".strip(), x, y, colour)
        y += 10
        if y > CANVAS_H - 24:
            y = 40
            x += CANVAS_W // 2 - 12
