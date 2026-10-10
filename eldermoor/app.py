"""App: window, integer scaling with black bars, fixed 60 Hz timestep, headless mode."""
from __future__ import annotations

import os
from dataclasses import dataclass

import pygame

from eldermoor.config import CANVAS_H, CANVAS_W, DEFAULT_SCALE, DT, MAX_SCALE, MIN_SCALE
from eldermoor.game import Game
from eldermoor.input import Input
from eldermoor.touch import TouchPad

MAX_STEPS_PER_FRAME = 5
TITLE = "Lantern of Eldermoor"


@dataclass
class Options:
    """Command-line options."""

    scale: int = DEFAULT_SCALE
    fullscreen: bool = False
    headless: bool = False
    frames: int = 60
    save_slot: int = 1
    stretch: bool = False
    no_menu: bool = False
    start_room: str | None = None
    #: "auto" shows the on-screen pad on a touchscreen, "on"/"off" decide
    touch: str = "auto"


class App:
    """Creates the window and runs the main loop."""

    def __init__(self, opts: Options) -> None:
        self.opts = opts
        if opts.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        self.scale = max(MIN_SCALE, min(MAX_SCALE, opts.scale))
        self.fullscreen = opts.fullscreen
        self.stretch = opts.stretch
        self.window = self._open_window()
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H))
        self.input = Input()
        self.input.init_controllers()
        self.game = Game(inp=self.input, file_select=not opts.headless and not opts.no_menu)
        self.clock = pygame.time.Clock()
        self.accumulator = 0.0
        self.running = True
        self.picture = pygame.Rect(0, 0, CANVAS_W, CANVAS_H)
        self._laid_out_for = (0, 0)
        self.touch = TouchPad()
        self.touch.visible = self._wants_touch()
        self.touch.font = self.game.assets.font8
        self._relayout()

    # ----- touchscreen ---------------------------------------------------
    def _wants_touch(self) -> bool:
        """Whether to draw the on-screen pad."""
        choice = self.opts.touch
        if choice == "auto":
            choice = self.game.settings.touch_controls
        if choice in ("on", "off"):
            return choice == "on"
        if self.opts.headless:
            return False
        try:
            return bool(pygame.touch.get_num_devices())
        except (AttributeError, pygame.error):
            return False

    def _relayout(self) -> None:
        """Work out where the picture goes, and put the controls beside it."""
        ww, wh = self.window.get_size()
        if self.stretch:
            self.picture = pygame.Rect(0, 0, ww, wh)
        else:
            factor = max(1, min(ww // CANVAS_W, wh // CANVAS_H))
            width, height = CANVAS_W * factor, CANVAS_H * factor
            top = (wh - height) // 2
            if self.touch.visible and wh - height > ww - width:
                top = min(top, round(wh * 0.04))   # portrait: the controls want the room
            self.picture = pygame.Rect((ww - width) // 2, top, width, height)
        self.touch.layout((ww, wh), self.picture)
        self._laid_out_for = (ww, wh)

    # ----- window --------------------------------------------------------
    def _open_window(self) -> pygame.Surface:
        if self.opts.headless:
            return pygame.display.set_mode((CANVAS_W, CANVAS_H))
        pygame.display.set_caption(TITLE)
        if self.fullscreen:
            flags = pygame.FULLSCREEN
            size = (0, 0)
        else:
            flags = pygame.RESIZABLE
            size = (CANVAS_W * self.scale, CANVAS_H * self.scale)
        try:
            return pygame.display.set_mode(size, flags, vsync=1)
        except pygame.error:
            return pygame.display.set_mode(size, flags)

    def toggle_fullscreen(self) -> None:
        """Switch between windowed and fullscreen (F11 / Alt+Enter)."""
        self.fullscreen = not self.fullscreen
        self.window = self._open_window()
        self.touch.release_all(self.input)
        self._relayout()

    def present(self) -> None:
        """Scale the canvas into the picture area, then draw the controls."""
        size = self.window.get_size()
        if size != self._laid_out_for:
            self._relayout()
        self.window.fill((0, 0, 0))
        scaled = pygame.transform.scale(self.canvas, (self.picture.width, self.picture.height))
        self.window.blit(scaled, self.picture.topleft)
        self.touch.draw(self.window)
        pygame.display.flip()

    # ----- loop ----------------------------------------------------------
    def step(self) -> None:
        """Exactly one logic frame: poll events, update the game."""
        self.input.begin_frame()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and self.game.debug.handle_key(self.game, event.key):
                continue
            if event.type == pygame.VIDEORESIZE or event.type == pygame.WINDOWRESIZED:
                self._relayout()
            if self.touch.visible and self.touch.handle(event, self.input,
                                                        self.window.get_size()):
                continue
            self.input.handle_event(event)
        if self.input.quit_requested:
            self.running = False
        self.game.update()
        if self.game.want_fullscreen_toggle:
            self.game.want_fullscreen_toggle = False
            if not self.opts.headless:
                self.toggle_fullscreen()

    async def run_async(self) -> int:
        """The same loop, yielding to the browser between frames.

        A web build runs inside the page's own event loop: if the game never
        gives it a turn, the tab freezes. This is the desktop loop with one
        ``await`` in it, which is all pygbag asks for.
        """
        import asyncio
        try:
            while self.running:
                elapsed = self.clock.tick(60) / 1000.0
                self.accumulator += min(elapsed, 0.25)
                steps = 0
                while self.accumulator >= DT and steps < MAX_STEPS_PER_FRAME:
                    self.step()
                    self.accumulator -= DT
                    steps += 1
                if steps == MAX_STEPS_PER_FRAME:
                    self.accumulator = 0.0
                self.game.debug.fps = self.clock.get_fps()
                self.game.draw(self.canvas)
                self.present()
                await asyncio.sleep(0)
        except Exception:
            self._on_crash()
            raise
        return 0

    def run(self) -> int:
        """Main loop with the crash guard. No crash may lose progress."""
        try:
            return self._run()
        except Exception:
            self._on_crash()
            raise

    def _on_crash(self) -> None:
        """Autosave to the crash slot and append the traceback to crash.log."""
        import traceback

        from eldermoor.settings import crash_log_path, ensure_config_dir
        try:
            self.game.crash_save()
        except Exception:
            pass
        try:
            ensure_config_dir()
            with crash_log_path().open("a", encoding="utf-8") as fh:
                fh.write(traceback.format_exc())
                fh.write("\n")
        except OSError:
            pass

    def _run(self) -> int:
        """Main loop. Headless: run ``frames`` steps as fast as possible and return 0."""
        if self.opts.headless:
            for _ in range(self.opts.frames):
                self.step()
                self.game.draw(self.canvas)
                self.present()
            pygame.quit()
            return 0
        while self.running:
            elapsed = self.clock.tick(240) / 1000.0
            self.accumulator += min(elapsed, 0.25)
            steps = 0
            while self.accumulator >= DT and steps < MAX_STEPS_PER_FRAME:
                self.step()
                self.accumulator -= DT
                steps += 1
            if steps == MAX_STEPS_PER_FRAME:
                self.accumulator = 0.0
            self.game.debug.fps = self.clock.get_fps()
            self.game.draw(self.canvas)
            self.present()
        pygame.quit()
        return 0
