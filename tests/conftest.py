"""Headless pytest setup: dummy SDL drivers, built assets, shared fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _pygame_session():
    """Initialise pygame once with a dummy display and make sure assets exist."""
    pygame.init()
    pygame.display.set_mode((320, 240))
    import build_assets
    build_assets.main([])
    yield
    pygame.quit()


@pytest.fixture(scope="session")
def assets():
    """Loaded Assets (session-wide)."""
    from eldermoor.assets import Assets
    return Assets()


@pytest.fixture
def game(assets):
    """A fresh Game with a scriptable Input."""
    from eldermoor.game import Game
    from eldermoor.input import Input
    return Game(assets=assets, inp=Input())


def step(game, n: int = 1) -> None:
    """Run n logic frames (input held state unchanged)."""
    for _ in range(n):
        game.input.begin_frame()
        game.update()


def tap(game, button: str) -> None:
    """Press a button for exactly one frame."""
    game.input.begin_frame()
    game.input.press(button)
    game.update()
    game.input.release(button)
