"""Input: 12 logical buttons fed by keyboard and SDL GameController, mapped by input_map.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pygame

from eldermoor.config import BUTTONS, INPUT_MAP_FILE

SYSTEM_ACTIONS = ("fullscreen", "debug")
ALL_ACTIONS = BUTTONS + SYSTEM_ACTIONS

GAMEPAD_BUTTON_NAMES: dict[str, int] = {
    "a": pygame.CONTROLLER_BUTTON_A,
    "b": pygame.CONTROLLER_BUTTON_B,
    "x": pygame.CONTROLLER_BUTTON_X,
    "y": pygame.CONTROLLER_BUTTON_Y,
    "back": pygame.CONTROLLER_BUTTON_BACK,
    "guide": pygame.CONTROLLER_BUTTON_GUIDE,
    "start": pygame.CONTROLLER_BUTTON_START,
    "leftstick": pygame.CONTROLLER_BUTTON_LEFTSTICK,
    "rightstick": pygame.CONTROLLER_BUTTON_RIGHTSTICK,
    "leftshoulder": pygame.CONTROLLER_BUTTON_LEFTSHOULDER,
    "rightshoulder": pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
    "dpup": pygame.CONTROLLER_BUTTON_DPAD_UP,
    "dpdown": pygame.CONTROLLER_BUTTON_DPAD_DOWN,
    "dpleft": pygame.CONTROLLER_BUTTON_DPAD_LEFT,
    "dpright": pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
}

AXIS_MAX = 32767.0


def load_input_map(path: Path = INPUT_MAP_FILE) -> dict[str, Any]:
    """Read input_map.json. Missing file falls back to the built-in default."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return DEFAULT_MAP


DEFAULT_MAP: dict[str, Any] = {
    "keyboard": {
        "up": ["up", "w"], "down": ["down", "s"], "left": ["left", "a"], "right": ["right", "d"],
        "a": ["z", "j"], "b": ["x", "k"], "x": ["c", "l"], "y": ["v", ";"],
        "l": ["left shift", "right shift"], "r": ["space"],
        "start": ["return", "escape"], "select": ["tab"],
        "fullscreen": ["f11"], "debug": ["f1"],
    },
    "gamepad": {
        "up": ["dpup"], "down": ["dpdown"], "left": ["dpleft"], "right": ["dpright"],
        "a": ["a"], "b": ["b"], "x": ["x"], "y": ["y"],
        "l": ["leftshoulder"], "r": ["rightshoulder"], "start": ["start"], "select": ["back"],
    },
    "gamepad_stick_deadzone": 0.4,
}


class Input:
    """Edge-detected button state. Call ``begin_frame`` once per logic step, then feed events."""

    def __init__(self, mapping: dict[str, Any] | None = None) -> None:
        self.mapping = mapping or load_input_map()
        self.key_to_action: dict[int, str] = {}
        self.pad_to_action: dict[int, str] = {}
        self.deadzone: float = float(self.mapping.get("gamepad_stick_deadzone", 0.4))
        self.rebuild()
        self.held: dict[str, bool] = {a: False for a in ALL_ACTIONS}
        self._prev: dict[str, bool] = dict(self.held)
        self._key_held: dict[str, bool] = {a: False for a in ALL_ACTIONS}
        self._pad_held: dict[str, bool] = {a: False for a in ALL_ACTIONS}
        self._stick: dict[str, bool] = {a: False for a in ("up", "down", "left", "right")}
        self._prev_key: dict[str, bool] = dict(self._key_held)
        self._prev_pad: dict[str, bool] = dict(self._pad_held)
        self._prev_stick: dict[str, bool] = dict(self._stick)
        self.last_device = "keyboard"
        self.controllers: dict[int, Any] = {}
        self.quit_requested = False

    # ----- mapping -------------------------------------------------------
    def rebuild(self) -> None:
        """Rebuild the key/button lookup tables from ``self.mapping``."""
        self.key_to_action.clear()
        for action, names in self.mapping.get("keyboard", {}).items():
            for name in names:
                try:
                    self.key_to_action[pygame.key.key_code(name)] = action
                except ValueError:
                    continue
        self.pad_to_action.clear()
        for action, names in self.mapping.get("gamepad", {}).items():
            for name in names:
                code = GAMEPAD_BUTTON_NAMES.get(name)
                if code is not None:
                    self.pad_to_action[code] = action

    def bind_key(self, action: str, key_name: str) -> None:
        """Remap one action to one keyboard key (replaces the list)."""
        self.mapping.setdefault("keyboard", {})[action] = [key_name]
        self.rebuild()

    def bind_pad(self, action: str, button_name: str) -> None:
        """Remap one action to one gamepad button (replaces the list)."""
        self.mapping.setdefault("gamepad", {})[action] = [button_name]
        self.rebuild()

    def save(self, path: Path = INPUT_MAP_FILE) -> None:
        """Write the current mapping to disk."""
        path.write_text(json.dumps(self.mapping, indent=2), encoding="utf-8")

    def unmapped_buttons(self) -> list[str]:
        """Logical buttons that have no keyboard binding (used by tests / settings)."""
        kb = self.mapping.get("keyboard", {})
        return [b for b in BUTTONS if not kb.get(b)]

    # ----- per-frame -----------------------------------------------------
    def begin_frame(self) -> None:
        """Snapshot the previous state so ``pressed`` can detect edges."""
        self._prev = dict(self.held)
        self._prev_key = dict(self._key_held)
        self._prev_pad = dict(self._pad_held)
        self._prev_stick = dict(self._stick)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Feed one pygame event."""
        t = event.type
        if t == pygame.KEYDOWN or t == pygame.KEYUP:
            self._on_key(event)
        elif t == pygame.CONTROLLERBUTTONDOWN or t == pygame.CONTROLLERBUTTONUP:
            action = self.pad_to_action.get(event.button)
            if action:
                self.last_device = "gamepad"
                self._pad_held[action] = t == pygame.CONTROLLERBUTTONDOWN
                self._recompute(action)
        elif t == pygame.CONTROLLERAXISMOTION:
            self._on_axis(event)
        elif t == pygame.CONTROLLERDEVICEADDED:
            self._open_controller(event.device_index)
        elif t == pygame.CONTROLLERDEVICEREMOVED:
            self.controllers.pop(getattr(event, "instance_id", -1), None)
        elif t == pygame.QUIT:
            self.quit_requested = True

    def _on_key(self, event: pygame.event.Event) -> None:
        down = event.type == pygame.KEYDOWN
        if down and event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT:
            self._key_held["fullscreen"] = True
            self._recompute("fullscreen")
            return
        if not down and event.key == pygame.K_RETURN:
            self._key_held["fullscreen"] = False
            self._recompute("fullscreen")
        action = self.key_to_action.get(event.key)
        if action is None:
            return
        self.last_device = "keyboard"
        self._key_held[action] = down
        self._recompute(action)

    def _on_axis(self, event: pygame.event.Event) -> None:
        value = event.value / AXIS_MAX
        if event.axis == pygame.CONTROLLER_AXIS_LEFTX:
            self._stick["left"] = value < -self.deadzone
            self._stick["right"] = value > self.deadzone
            self._recompute("left")
            self._recompute("right")
        elif event.axis == pygame.CONTROLLER_AXIS_LEFTY:
            self._stick["up"] = value < -self.deadzone
            self._stick["down"] = value > self.deadzone
            self._recompute("up")
            self._recompute("down")
        else:
            return
        if abs(value) > self.deadzone:
            self.last_device = "gamepad"

    def _recompute(self, action: str) -> None:
        self.held[action] = (self._key_held.get(action, False)
                             or self._pad_held.get(action, False)
                             or self._stick.get(action, False))

    def _open_controller(self, index: int) -> None:
        try:
            from pygame._sdl2 import controller
            if not controller.get_init():
                controller.init()
            if controller.is_controller(index):
                pad = controller.Controller(index)
                self.controllers[pad.id] = pad
                self.last_device = "gamepad"
        except Exception:
            return

    def init_controllers(self) -> None:
        """Open every controller already connected (hot-plug adds later ones)."""
        try:
            from pygame._sdl2 import controller
            controller.init()
            for i in range(controller.get_count()):
                self._open_controller(i)
        except Exception:
            return

    # ----- queries -------------------------------------------------------
    def is_held(self, action: str) -> bool:
        """True while the button is down."""
        return self.held.get(action, False)

    def pressed(self, action: str) -> bool:
        """True only on the frame the button went down."""
        return self.held.get(action, False) and not self._prev.get(action, False)

    def released(self, action: str) -> bool:
        """True only on the frame the button went up."""
        return not self.held.get(action, False) and self._prev.get(action, False)

    def axis(self) -> tuple[int, int]:
        """Movement direction as (-1/0/1, -1/0/1)."""
        dx = int(self.held["right"]) - int(self.held["left"])
        dy = int(self.held["down"]) - int(self.held["up"])
        return dx, dy

    # ----- one player's share of the buttons ------------------------------
    def view(self, source: str = "both") -> PlayerInput:
        """A read-only view of one device's buttons ("keyboard", "gamepad", "both")."""
        return PlayerInput(self, source)

    def held_on(self, source: str, action: str) -> bool:
        """Is this button down on one device?"""
        if source == "keyboard":
            return self._key_held.get(action, False)
        if source == "gamepad":
            return self._pad_held.get(action, False) or self._stick.get(action, False)
        return self.held.get(action, False)

    def was_held_on(self, source: str, action: str) -> bool:
        """Was it down on the previous frame, on that device?"""
        if source == "keyboard":
            return self._prev_key.get(action, False)
        if source == "gamepad":
            return self._prev_pad.get(action, False) or self._prev_stick.get(action, False)
        return self._prev.get(action, False)

    # ----- test / script helpers -----------------------------------------
    def press_pad(self, action: str) -> None:
        """Simulate holding a gamepad button (tests, bots)."""
        self._pad_held[action] = True
        self._recompute(action)

    def release_pad(self, action: str) -> None:
        """Simulate releasing a gamepad button."""
        self._pad_held[action] = False
        self._recompute(action)

    def press(self, action: str) -> None:
        """Simulate holding a logical button (tests, bots)."""
        self._key_held[action] = True
        self._recompute(action)

    def release(self, action: str) -> None:
        """Simulate releasing a logical button."""
        self._key_held[action] = False
        self._pad_held[action] = False
        self._stick[action] = False if action in self._stick else self._stick.get(action, False)
        self._recompute(action)

    def release_all(self) -> None:
        """Release every button."""
        for a in ALL_ACTIONS:
            self.release(a)


class PlayerInput:
    """One lamplighter's share of the buttons.

    In one-player games both heroes-worth of buttons come from "both", which
    is every device at once. In two-player games player one reads the
    keyboard and player two the gamepad, so the same frame can hold two
    different directions.
    """

    def __init__(self, source_input: Input, source: str = "both") -> None:
        self.input = source_input
        self.source = source

    def is_held(self, action: str) -> bool:
        """True while this player holds the button."""
        if isinstance(action, tuple):
            return any(self.is_held(a) for a in action)
        return self.input.held_on(self.source, action)

    def pressed(self, action: str) -> bool:
        """True on the frame this player pushed it down."""
        return self.is_held(action) and not self.input.was_held_on(self.source, action)

    def released(self, action: str) -> bool:
        """True on the frame this player let it go."""
        return not self.is_held(action) and self.input.was_held_on(self.source, action)

    def axis(self) -> tuple[int, int]:
        """This player's movement direction."""
        dx = int(self.is_held("right")) - int(self.is_held("left"))
        dy = int(self.is_held("down")) - int(self.is_held("up"))
        return dx, dy
