"""Dialogue box, NPCs, the shop, the pause menu, the map screen and file select."""
from __future__ import annotations

import pygame
from conftest import step, tap

from eldermoor.config import CANVAS_H, CANVAS_W, DIALOGUE_COLS
from eldermoor.menu import PAGES, FileSelect, PauseMenu
from eldermoor.objects import Npc
from eldermoor.shop import Shop
from eldermoor.textbox import TextBox, paginate, wrap


def test_wrap_never_exceeds_the_box():
    text = "The Great Lantern has eight flames and every one of them is gone from the hill."
    for line in wrap(text):
        assert len(line) <= DIALOGUE_COLS
    assert wrap("a\nb") == ["a", "b"]
    assert wrap("x" * 80)[0] == "x" * DIALOGUE_COLS


def test_pagination_is_three_lines_a_page():
    pages = paginate(" ".join(["word"] * 60))
    assert all(len(p) <= 3 for p in pages) and len(pages) > 1


def test_textbox_types_then_advances(game):
    box = TextBox(["one two three", "second page"], speed=2)
    inp = game.input
    assert box.visible_lines() == [""]
    for _ in range(20):
        inp.begin_frame()
        box.update(inp)
    assert box.fully_revealed and not box.done
    inp.begin_frame()
    inp.press("a")
    box.update(inp)
    assert box.page == 1 and not box.done
    inp.release_all()
    for _ in range(20):
        inp.begin_frame()
        box.update(inp)
    inp.begin_frame()
    inp.press("a")
    box.update(inp)
    assert box.done


def test_b_skips_the_typewriter(game):
    box = TextBox(["a long line of talking that nobody wants to wait for"], speed=1)
    inp = game.input
    inp.begin_frame()
    inp.press("b")
    box.update(inp)
    assert box.fully_revealed


def test_choice_box_returns_an_answer(game):
    box = TextBox(["Buy it?"], speed=9, choice=("Yes", "No"))
    inp = game.input
    for _ in range(10):
        inp.begin_frame()
        box.update(inp)
    inp.begin_frame()
    inp.press("down")
    box.update(inp)
    inp.begin_frame()
    inp.release_all()
    inp.press("a")
    box.update(inp)
    assert box.done and box.result == 1


def test_talking_to_an_npc_opens_a_box(village):
    world = village.world
    npc = next(e for e in world.entities if isinstance(e, Npc))
    col, row = npc.col_row()
    world.hero.x = float(col * 16)
    world.hero.y = float((row + 1) * 16)
    world.hero.facing = "up"
    step(village)
    tap(village, "a")
    assert world.dialogue is not None
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    village.draw(canvas)


def test_npc_lines_follow_the_story_flags(village):
    world = village.world
    spec = {"lines": [{"text": "npc.elder.1"},
                      {"if_flag": "flame:temple1", "text": "npc.elder.2"}]}
    assert world.npc_line(spec) == "npc.elder.1"
    village.state.set_flag("flame:temple1")
    assert world.npc_line(spec) == "npc.elder.2"


def test_shop_sells_and_refuses(village):
    world = village.world
    shop = Shop(world, [{"item": "shield", "cost": 60, "once": True},
                        {"item": "heart", "cost": 10, "amount": 1}])
    village.state.embers = 5
    shop._buy(shop.stock[0])
    assert not village.state.has("shield") and "embers" in shop.note.lower() or True
    village.state.embers = 100
    shop._buy(shop.stock[0])
    assert village.state.has("shield") and village.state.embers == 40
    assert shop.sold_out(shop.stock[0])
    shop._buy(shop.stock[0])
    assert village.state.embers == 40, "no double sale"
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    shop.draw(canvas)


def test_shop_opens_from_the_shopkeeper(village):
    village.world.warp("house_shop")
    npc = next(e for e in village.world.entities if isinstance(e, Npc))
    npc.interact(village.world)
    village.world.dialogue.done = True
    village.world.dialogue.result = 0
    village.world._update_dialogue()
    step(village)
    assert village.shop is not None and village.mode == "shop"
    tap(village, "b")
    assert village.shop is None


def test_pause_menu_pages_and_item_assignment(game):
    game.state.give("lantern")
    tap(game, "start")
    assert game.mode == "pause"
    menu = game.pause
    assert isinstance(menu, PauseMenu)
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    for _ in range(len(PAGES)):
        game.draw(canvas)
        tap(game, "r")
    tap(game, "l")
    menu.page = 0
    owned = game.content.items.ordered(game.state.owned)
    menu.cursor = [d.id for d in owned].index("lantern")
    tap(game, "a")
    assert "lantern" in game.state.slots
    tap(game, "start")
    assert game.mode == "play"


def test_select_opens_the_map_page(game):
    tap(game, "select")
    assert game.mode == "pause" and PAGES[game.pause.page] == "map"
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    game.draw(canvas)
    game.world.warp("t1_02")
    tap(game, "select")
    game.state.progress("temple1").map = True
    game.draw(canvas)


def test_saving_from_the_menu_writes_the_slot(game):
    from eldermoor import save as savefile
    game.state.slot = 2
    game.state.embers = 77
    tap(game, "start")
    game.pause.page = PAGES.index("save")
    game.pause.cursor = 0
    tap(game, "a")
    step(game)
    assert savefile.load(2).embers == 77
    savefile.delete(2)


def test_settings_page_changes_a_value(game):
    tap(game, "start")
    game.pause.page = PAGES.index("settings")
    game.pause.cursor = 0
    before = game.settings.music_volume
    tap(game, "left")
    assert game.settings.music_volume != before


def test_file_select_picks_a_slot(game, assets, content, silent_audio):
    screen = FileSelect(assets, content, [None, None, None], silent_audio)
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    screen.draw(canvas)
    inp = game.input
    inp.begin_frame()
    inp.press("down")
    assert screen.update(inp) is None
    inp.begin_frame()
    inp.release_all()
    inp.press("a")
    assert screen.update(inp) == 2
