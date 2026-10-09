"""Game: ties world, HUD, debug overlay and input into update/draw."""
from __future__ import annotations

import pygame

from eldermoor.assets import Assets
from eldermoor.config import CANVAS_H, CANVAS_W
from eldermoor.debug import DebugOverlay
from eldermoor.hud import Hud, PlayerState
from eldermoor.input import Input
from eldermoor.world import World


class Game:
    """One logic step is ``update()``; one picture is ``draw(canvas)``."""

    def __init__(self, assets: Assets | None = None, inp: Input | None = None,
                 start_room: str = "meadow_00") -> None:
        self.assets = assets or Assets()
        self.input = inp or Input()
        self.world = World(self.assets, start_room)
        self.state = PlayerState(items=["icon_sword", "icon_shield", "icon_lantern"])
        self.hud = Hud(self.assets)
        self.debug = DebugOverlay(self.assets)
        self.frame = 0
        self.want_fullscreen_toggle = False
        self.running = True

    def update(self) -> None:
        """Advance exactly one 60 Hz logic frame using the current input state."""
        inp = self.input
        if inp.pressed("debug"):
            self.debug.toggle()
        if inp.pressed("fullscreen"):
            self.want_fullscreen_toggle = True
        self.world.update(inp)
        self.frame += 1

    def draw(self, canvas: pygame.Surface) -> None:
        """Paint the full 320x240 frame."""
        canvas.fill(self.assets.colour("ink"), pygame.Rect(0, 0, CANVAS_W, CANVAS_H))
        self.world.draw(canvas)
        self.hud.draw(canvas, self.state)
        self.debug.draw(canvas, self)
