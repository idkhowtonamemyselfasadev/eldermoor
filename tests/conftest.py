"""Headless pytest setup: dummy SDL drivers, a throwaway config dir, shared fixtures."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# saves and settings must never touch the real ~/.config during a test run
os.environ["ELDERMOOR_CONFIG_DIR"] = tempfile.mkdtemp(prefix="eldermoor-test-")

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


@pytest.fixture(scope="session")
def content():
    """Loaded data/ tables (session-wide: the JSON only needs reading once)."""
    from eldermoor.content import Content
    return Content()


@pytest.fixture
def silent_audio():
    """An Audio that records what was asked for without opening a device."""
    from eldermoor.audio import Audio
    audio = Audio(root=Path(tempfile.mkdtemp(prefix="eldermoor-audio-")))
    audio.enabled = False
    return audio


def make_game(assets, content, audio, room: str = "glade", sword: bool = True):
    """A Game in a given room, optionally already holding the sword."""
    from eldermoor.game import Game
    from eldermoor.input import Input
    game = Game(assets=assets, inp=Input(), content=content, audio=audio, start_room=room)
    if sword:
        game.state.give("sword")
        game.state.sword_level = 1
    return game


@pytest.fixture
def game(assets, content, silent_audio):
    """A fresh Game in the Hollow Glade: walled, quiet, and always the same."""
    return make_game(assets, content, silent_audio)


@pytest.fixture
def village(assets, content, silent_audio):
    """A fresh Game standing in Lamplight Village."""
    return make_game(assets, content, silent_audio, room="ow_1105")


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


def run_until(game, predicate, limit: int = 1200) -> bool:
    """Step until the predicate holds or the limit runs out."""
    for _ in range(limit):
        if predicate():
            return True
        step(game)
    return predicate()
