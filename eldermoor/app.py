"""App: window, integer scaling with black bars, fixed 60 Hz timestep, headless mode."""
from __future__ import annotations

import os
from dataclasses import dataclass

import pygame

from eldermoor.config import CANVAS_H, CANVAS_W, DEFAULT_SCALE, DT, MAX_SCALE, MIN_SCALE
from eldermoor.game import Game
from eldermoor.input import Input

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

    def present(self) -> None:
        """Scale the canvas to the window with nearest-neighbour and black bars."""
        ww, wh = self.window.get_size()
        if self.stretch:
            scaled = pygame.transform.scale(self.canvas, (ww, wh))
            self.window.blit(scaled, (0, 0))
        else:
            factor = max(1, min(ww // CANVAS_W, wh // CANVAS_H))
            self.window.fill((0, 0, 0))
            scaled = pygame.transform.scale_by(self.canvas, factor)
            self.window.blit(scaled, ((ww - scaled.get_width()) // 2, (wh - scaled.get_height()) // 2))
        pygame.display.flip()

    # ----- loop ----------------------------------------------------------
    def step(self) -> None:
        """Exactly one logic frame: poll events, update the game."""
        self.input.begin_frame()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and self.game.debug.handle_key(self.game, event.key):
                continue
            self.input.handle_event(event)
        if self.input.quit_requested:
            self.running = False
        self.game.update()
        if self.game.want_fullscreen_toggle:
            self.game.want_fullscreen_toggle = False
            if not self.opts.headless:
                self.toggle_fullscreen()

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
