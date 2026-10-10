"""The on-screen controls: layout, fingers and the buttons they send."""
from __future__ import annotations

import pygame
import pytest

from eldermoor.app import App, Options
from eldermoor.touch import MIN_RADIUS

#: a spread of screens: two phones, an older phone, a tablet, a small window
SHAPES = ((2340, 1080), (1080, 1920), (1334, 750), (2048, 1536), (960, 540), (640, 480))


def phone(size: tuple[int, int] = (2340, 1080)) -> App:
    """An app laid out for a screen of a given size, with the pad on."""
    pygame.display.set_mode(size)
    app = App(Options(headless=True, no_menu=True, touch="on"))
    app.window = pygame.display.set_mode(size)
    app._relayout()
    return app


def finger(app: App, point: tuple[int, int], index: int = 0) -> None:
    """Put a finger down at a point in window coordinates."""
    app.touch._press(index, point)
    app.touch._apply(app.input)


# ----- layout ------------------------------------------------------------
@pytest.mark.parametrize(("width", "height"), SHAPES)
def test_every_control_fits_on_screen(width, height):
    app = phone((width, height))
    for control in app.touch.controls + [app.touch.stick]:
        cx, cy = control.centre
        assert control.radius - 1 <= cx <= width - control.radius + 1, control.action
        assert control.radius - 1 <= cy <= height - control.radius + 1, control.action
        assert control.radius >= MIN_RADIUS, f"{control.action} is too small to hit"


@pytest.mark.parametrize(("width", "height"), SHAPES)
def test_no_two_controls_sit_on_each_other(width, height):
    app = phone((width, height))
    controls = app.touch.controls + [app.touch.stick]
    for i, a in enumerate(controls):
        for b in controls[i + 1:]:
            gap = (a.centre[0] - b.centre[0]) ** 2 + (a.centre[1] - b.centre[1]) ** 2
            assert gap >= (a.radius + b.radius) ** 2, f"{a.action}/{b.action} overlap"


def test_all_twelve_buttons_are_reachable():
    app = phone()
    actions = {c.action for c in app.touch.controls}
    assert actions == {"a", "b", "x", "y", "l", "r", "start", "select"}
    assert app.touch.stick is not None, "and four more from the pad"


def test_the_controls_keep_off_the_picture_on_a_phone():
    app = phone()
    for control in app.touch.controls + [app.touch.stick]:
        box = pygame.Rect(0, 0, control.radius * 2, control.radius * 2)
        box.center = control.centre
        assert not box.colliderect(app.picture), f"{control.action} covers the game"


# ----- fingers -----------------------------------------------------------
def test_a_button_goes_down_and_comes_up():
    app = phone()
    a = next(c for c in app.touch.controls if c.action == "a")
    app.input.begin_frame()
    finger(app, a.centre)
    assert app.input.is_held("a") and app.input.pressed("a")
    app.input.begin_frame()
    app.touch._lift(0)
    app.touch._apply(app.input)
    assert not app.input.is_held("a") and app.input.released("a")


def test_the_pad_reads_eight_directions():
    app = phone()
    pad = app.touch.stick
    reach = round(pad.radius * 0.8)
    for (dx, dy), wanted in (((0, -1), {"up"}), ((0, 1), {"down"}),
                             ((-1, 0), {"left"}), ((1, 0), {"right"}),
                             ((1, -1), {"up", "right"}), ((-1, 1), {"down", "left"})):
        finger(app, (pad.centre[0] + dx * reach, pad.centre[1] + dy * reach))
        assert app.touch.stick_dirs == wanted, (dx, dy)
    assert app.input.axis() != (0, 0)


def test_the_middle_of_the_pad_is_a_rest():
    app = phone()
    pad = app.touch.stick
    finger(app, pad.centre)
    assert app.touch.stick_dirs == set()
    assert app.input.axis() == (0, 0)


def test_a_thumb_and_a_button_work_at_once():
    app = phone()
    pad = app.touch.stick
    a = next(c for c in app.touch.controls if c.action == "a")
    finger(app, (pad.centre[0], pad.centre[1] + round(pad.radius * 0.8)), index=0)
    finger(app, a.centre, index=1)
    assert app.input.is_held("down") and app.input.is_held("a")
    app.touch._lift(1)
    app.touch._apply(app.input)
    assert app.input.is_held("down") and not app.input.is_held("a")


def test_a_thumb_sliding_round_the_pad_follows_it():
    app = phone()
    pad = app.touch.stick
    reach = round(pad.radius * 0.8)
    finger(app, (pad.centre[0] - reach, pad.centre[1]))
    assert app.input.is_held("left")
    finger(app, (pad.centre[0] + reach, pad.centre[1]))
    assert app.input.is_held("right") and not app.input.is_held("left")


def test_a_touch_on_nothing_does_nothing():
    app = phone()
    finger(app, app.picture.center)
    assert not app.touch.held
    assert not any(app.input.is_held(b) for b in ("a", "b", "up", "down"))


def test_letting_go_of_everything_clears_it():
    app = phone()
    pad = app.touch.stick
    a = next(c for c in app.touch.controls if c.action == "a")
    finger(app, (pad.centre[0], pad.centre[1] - round(pad.radius * 0.8)), index=0)
    finger(app, a.centre, index=1)
    app.touch.release_all(app.input)
    assert not app.touch.held
    assert not app.input.is_held("a") and not app.input.is_held("up")


# ----- events ------------------------------------------------------------
def test_a_finger_event_reaches_the_buttons():
    app = phone()
    a = next(c for c in app.touch.controls if c.action == "a")
    size = app.window.get_size()
    down = pygame.event.Event(pygame.FINGERDOWN, x=a.centre[0] / size[0],
                              y=a.centre[1] / size[1], finger_id=7)
    assert app.touch.handle(down, app.input, size)
    assert app.input.is_held("a")
    up = pygame.event.Event(pygame.FINGERUP, x=a.centre[0] / size[0],
                            y=a.centre[1] / size[1], finger_id=7)
    assert app.touch.handle(up, app.input, size)
    assert not app.input.is_held("a")


def test_a_mouse_click_works_too_for_testing():
    app = phone()
    b = next(c for c in app.touch.controls if c.action == "b")
    size = app.window.get_size()
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=b.centre, button=1)
    assert app.touch.handle(event, app.input, size)
    assert app.input.is_held("b")


def test_other_events_are_left_alone():
    app = phone()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z, mod=0)
    assert not app.touch.handle(event, app.input, app.window.get_size())


# ----- the game behind it ------------------------------------------------
def test_wren_walks_on_a_thumb():
    app = phone()
    app.game.world.warp("glade")
    hero = app.game.world.hero
    start = hero.x
    pad = app.touch.stick
    finger(app, (pad.centre[0] + round(pad.radius * 0.8), pad.centre[1]))
    for _ in range(12):
        app.step()
    assert hero.x > start, "the pad drives the game like any other button"


def test_the_pad_is_off_unless_it_is_wanted():
    pygame.display.set_mode((1280, 720))
    app = App(Options(headless=True, no_menu=True, touch="off"))
    assert not app.touch.visible
    app.game.draw(app.canvas)
    app.present()           # draws nothing extra, and does not fall over


def test_the_setting_decides_when_the_flag_says_auto():
    pygame.display.set_mode((1280, 720))
    app = App(Options(headless=True, no_menu=True, touch="auto"))
    app.game.settings.touch_controls = "on"
    assert app._wants_touch()
    app.game.settings.touch_controls = "off"
    assert not app._wants_touch()


def test_the_pad_draws_without_a_font():
    app = phone()
    app.touch.font = None
    app.present()           # the rings still draw; only the letters go away


# ----- the phone build ---------------------------------------------------
def test_the_staged_web_folder_holds_what_the_game_reads(tmp_path, monkeypatch):
    import build_web
    monkeypatch.setattr(build_web, "STAGE", tmp_path / "web_src")
    staged = build_web.stage()
    for needed in ("main.py", "eldermoor/app.py", "data/text/en.json",
                   "assets/sprites.png", "input_map.json"):
        assert (staged / needed).exists(), needed
    assert not list(staged.rglob("*.wav")), "the uncompressed audio must stay behind"
    assert list(staged.rglob("*.ogg")), "the small audio must come along"
    assert not list(staged.rglob("tests")), "and nothing that is not the game"
    size = sum(p.stat().st_size for p in staged.rglob("*") if p.is_file())
    assert size < 12_000_000, "a phone has to download this"


def test_the_web_entry_point_is_asynchronous(tmp_path, monkeypatch):
    import build_web
    monkeypatch.setattr(build_web, "STAGE", tmp_path / "web_src")
    staged = build_web.stage()
    main = (staged / "main.py").read_text()
    assert "async def main" in main and "asyncio.run" in main
    assert "run_async" in main, "a page cannot run a blocking loop"


def test_the_app_has_an_async_loop():
    import inspect
    assert inspect.iscoroutinefunction(App.run_async)


def test_the_audio_prefers_the_small_files(tmp_path):
    from eldermoor.audio import Audio
    folder = tmp_path / "sfx"
    folder.mkdir()
    (folder / "sword.wav").write_bytes(b"")
    assert Audio._pick(folder, "sword").suffix == ".wav"
    (folder / "sword.ogg").write_bytes(b"")
    assert Audio._pick(folder, "sword").suffix == ".ogg"


def test_the_game_ships_compressed_audio():
    from eldermoor.config import ASSETS
    oggs = list((ASSETS / "audio").rglob("*.ogg"))
    assert len(oggs) > 60, "run tools/build_audio.py --ogg"
    total = sum(p.stat().st_size for p in oggs)
    assert total < 8_000_000, f"{total / 1e6:.1f} MB is too much to send to a phone"


# ----- the cost of drawing them ------------------------------------------
def test_the_drawn_controls_are_kept_between_frames():
    app = phone()
    app.present()
    first = app.touch._layer
    assert first is not None
    app.present()
    assert app.touch._layer is first, "nothing changed, so nothing is redrawn"


def test_pressing_a_button_redraws_them():
    app = phone()
    app.present()
    first = app.touch._layer
    a = next(c for c in app.touch.controls if c.action == "a")
    finger(app, a.centre)
    app.present()
    assert app.touch._layer is not first, "a held button looks different"


def test_a_new_layout_throws_the_old_drawing_away():
    app = phone()
    app.present()
    assert app.touch._layer is not None
    app.window = pygame.display.set_mode((1080, 1920))
    app._relayout()
    assert app.touch._layer is None, "the controls moved, so the picture is stale"


def test_a_frame_is_cheap_at_the_size_a_phone_gets():
    """The browser scales the canvas; Python must not, or the frame is gone."""
    import time
    pygame.display.set_mode((520, 240))
    app = App(Options(headless=True, no_menu=True, touch="on", window=(520, 240)))
    assert app.picture.size == (320, 240), "one pixel per pixel, nothing to scale"
    for _ in range(30):
        app.game.update()
        app.game.draw(app.canvas)
        app.present()
    worst = 0.0
    for _ in range(120):
        start = time.perf_counter()
        app.game.update()
        app.game.draw(app.canvas)
        app.present()
        worst = max(worst, (time.perf_counter() - start) * 1000)
    assert worst < 8.0, f"{worst:.1f} ms of a 16.7 ms frame leaves nothing for a slow device"
