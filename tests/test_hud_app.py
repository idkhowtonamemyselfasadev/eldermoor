"""HUD maths, debug overlay, the headless app and main.py."""
from __future__ import annotations

import subprocess
import sys

import pygame
from conftest import step, tap

from eldermoor.config import CANVAS_H, CANVAS_W, HUD_H, ROOT
from eldermoor.hud import HEART_X, HEART_Y, PlayerState


def test_heart_icons_half_heart_maths():
    s = PlayerState(max_hearts=3, health=6)
    assert s.heart_icons() == ["heart_full"] * 3
    s.damage(1)
    assert s.heart_icons() == ["heart_full", "heart_full", "heart_half"]
    s.damage(2)
    assert s.heart_icons() == ["heart_full", "heart_half", "heart_empty"]
    s.damage(99)
    assert s.health == 0 and s.heart_icons() == ["heart_empty"] * 3
    s.heal(99)
    assert s.health == 6
    s.max_hearts = 20
    assert len(s.heart_icons()) == 20


def test_hud_draws_hearts_counters_and_slots(game, assets):
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    game.state.give("lantern")
    game.state.assign(0, "lantern")
    game.state.health = 5
    game.state.embers = 42
    game.state.keys = 3
    game.draw(canvas)
    red = assets.colour("red")
    assert canvas.get_at((HEART_X + 2, HEART_Y + 2))[:3] == red
    assert canvas.get_at((HEART_X + 9 * 2 + 2, HEART_Y + 2))[:3] == red
    # third heart is half: its right half is slate, not red
    assert canvas.get_at((HEART_X + 18 + 5, HEART_Y + 2))[:3] == assets.colour("slate")
    # the HUD/play boundary line
    assert canvas.get_at((100, HUD_H - 1))[:3] == assets.colour("slate")
    # item icons in the slots
    slot_pixels = {canvas.get_at((x, y))[:3] for x in range(200, 300) for y in range(8, 24)}
    assert assets.colour("gold") in slot_pixels


def test_debug_overlay_toggles_and_draws(game, assets):
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    assert not game.debug.enabled
    tap(game, "debug")
    assert game.debug.enabled
    game.draw(canvas)
    lines = game.debug.lines(game)
    assert any("glade" in ln for ln in lines) and any("keyboard" in ln for ln in lines)
    assert canvas.get_at((6, HUD_H + 6))[:3] in (assets.colour("lime"), assets.colour("ink"), (0, 0, 0))
    tap(game, "debug")
    assert not game.debug.enabled


def test_fullscreen_request_flag(game):
    tap(game, "fullscreen")
    assert game.want_fullscreen_toggle


def test_game_frame_counter_and_draw(game):
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    step(game, 5)
    assert game.frame == 5
    game.draw(canvas)
    assert canvas.get_at((160, 200))[:3] != (0, 0, 0)


def test_headless_app_runs_fixed_steps():
    from eldermoor.app import App, Options
    app = App(Options(headless=True, frames=20))
    assert app.run() == 0
    assert app.game.frame == 20
    pygame.init()
    pygame.display.set_mode((320, 240))


def test_main_headless_subprocess():
    r = subprocess.run([sys.executable, str(ROOT / "main.py"), "--headless", "--frames", "10"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr


def test_module_size_limits():
    for p in (ROOT / "eldermoor").glob("*.py"):
        assert len(p.read_text().splitlines()) <= 600, p.name
