"""Input map: all 12 buttons mapped, edge detection, keyboard + gamepad events."""
from __future__ import annotations

import json

import pygame

from eldermoor.config import BUTTONS, INPUT_MAP_FILE
from eldermoor.input import Input


def test_input_map_file_maps_all_12_buttons_on_both_devices():
    raw = json.loads(INPUT_MAP_FILE.read_text())
    for b in BUTTONS:
        assert raw["keyboard"].get(b), f"keyboard missing {b}"
        assert raw["gamepad"].get(b), f"gamepad missing {b}"
    assert raw["keyboard"]["fullscreen"] and raw["keyboard"]["debug"]
    inp = Input()
    assert inp.unmapped_buttons() == []
    assert len(inp.pad_to_action) >= 12


def test_keyboard_events_and_edges():
    inp = Input()
    inp.begin_frame()
    inp.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z, mod=0))
    assert inp.is_held("a") and inp.pressed("a")
    inp.begin_frame()
    assert inp.is_held("a") and not inp.pressed("a")
    inp.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_z, mod=0))
    assert inp.released("a") and not inp.is_held("a")
    inp.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w, mod=0))
    inp.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, mod=0))
    assert inp.axis() == (1, -1)
    assert inp.last_device == "keyboard"


def test_gamepad_buttons_and_stick():
    inp = Input()
    inp.begin_frame()
    inp.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=pygame.CONTROLLER_BUTTON_A))
    assert inp.pressed("a") and inp.last_device == "gamepad"
    inp.handle_event(pygame.event.Event(pygame.CONTROLLERAXISMOTION,
                                        axis=pygame.CONTROLLER_AXIS_LEFTX, value=-30000))
    assert inp.axis() == (-1, 0)
    inp.handle_event(pygame.event.Event(pygame.CONTROLLERAXISMOTION,
                                        axis=pygame.CONTROLLER_AXIS_LEFTX, value=2000))
    assert inp.axis() == (0, 0), "inside the deadzone"
    inp.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONUP, button=pygame.CONTROLLER_BUTTON_A))
    assert not inp.is_held("a")


def test_alt_enter_is_fullscreen():
    inp = Input()
    inp.begin_frame()
    inp.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=pygame.KMOD_LALT))
    assert inp.pressed("fullscreen") and not inp.is_held("start")
    inp.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN, mod=0))
    assert not inp.is_held("fullscreen")


def test_remap_and_save(tmp_path):
    inp = Input()
    inp.bind_key("a", "q")
    inp.begin_frame()
    inp.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q, mod=0))
    assert inp.pressed("a")
    inp.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z, mod=0))
    assert inp.key_to_action.get(pygame.K_z) is None
    out = tmp_path / "input_map.json"
    inp.save(out)
    assert json.loads(out.read_text())["keyboard"]["a"] == ["q"]


def test_quit_event():
    inp = Input()
    inp.handle_event(pygame.event.Event(pygame.QUIT))
    assert inp.quit_requested
