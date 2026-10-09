"""Game: the mode stack (file select, play, pause, shop) over world, HUD and overlay."""
from __future__ import annotations

from typing import Any

import pygame

from eldermoor import save as savefile
from eldermoor.assets import Assets
from eldermoor.audio import Audio
from eldermoor.companion import Companion
from eldermoor.config import CANVAS_H, CANVAS_W, DT
from eldermoor.content import Content
from eldermoor.debug import DebugOverlay
from eldermoor.ending import Ending
from eldermoor.hud import Hud
from eldermoor.input import Input
from eldermoor.menu import PAGES, FileSelect, PauseMenu
from eldermoor.minigames import MiniGame
from eldermoor.minigames import start as start_minigame
from eldermoor.settings import Settings
from eldermoor.shop import Shop
from eldermoor.state import GameState
from eldermoor.world import World

NEW_GAME_ROOM = "ow_1105"


class Game:
    """One logic step is ``update()``; one picture is ``draw(canvas)``."""

    def __init__(self, assets: Assets | None = None, inp: Input | None = None,
                 start_room: str | None = None, state: GameState | None = None,
                 content: Content | None = None, audio: Audio | None = None,
                 settings: Settings | None = None, file_select: bool = False) -> None:
        self.assets = assets or Assets()
        self.input = inp or Input()
        self.settings = (settings or Settings.load()).clamped()
        self.audio = audio or Audio(self.settings.music_volume, self.settings.sfx_volume)
        self.content = content or Content(language=self.settings.language)
        self.state = state or GameState(room=start_room or NEW_GAME_ROOM)
        self.world = World(self.assets, self.state, self.input, self.audio, self.content,
                           start_room or self.state.room)
        self.world.text_speed = self.settings.text_speed
        self.world.screen_shake = self.settings.screen_shake
        self.hud = Hud(self.assets, self.content.items)
        self.debug = DebugOverlay(self.assets)
        self.pause: PauseMenu | None = None
        self.shop: Shop | None = None
        self.ending: Ending | None = None
        self.minigame: MiniGame | None = None
        self.companion = Companion(self.content.hints)
        self.companion.enabled = self.settings.hints
        self.file_select: FileSelect | None = None
        if file_select:
            self.file_select = FileSelect(self.assets, self.content,
                                          savefile.all_summaries(), self.audio,
                                          self.settings.master_unlocked)
            self.audio.play_music("title")
        self.frame = 0
        self.want_fullscreen_toggle = False
        self.running = True
        self._last_room = self.world.room.id

    # ----- modes ---------------------------------------------------------
    @property
    def mode(self) -> str:
        """Which screen is on top."""
        if self.file_select is not None:
            return "file"
        if self.ending is not None:
            return "ending"
        if self.minigame is not None:
            return "minigame"
        if self.shop is not None:
            return "shop"
        if self.pause is not None:
            return "pause"
        return "play"

    def update(self) -> None:
        """Advance exactly one 60 Hz logic frame."""
        inp = self.input
        if inp.pressed("debug"):
            self.debug.toggle()
        if inp.pressed("fullscreen"):
            self.want_fullscreen_toggle = True
        self.world.god_mode = self.debug.god
        getattr(self, f"_update_{self.mode}")()
        self.frame += 1

    def _update_file(self) -> None:
        menu = self.file_select
        chosen = menu.update(self.input) if menu else None
        if chosen is None or menu is None:
            return
        master = menu.wants_master
        self.file_select = None
        loaded = savefile.load(chosen)
        self.state = loaded or GameState(slot=chosen, room=NEW_GAME_ROOM)
        if loaded is None and master:
            self.state.set_flag("master", 1)
        self.state.slot = chosen
        self.world = World(self.assets, self.state, self.input, self.audio, self.content,
                           self.state.room)
        self.world.text_speed = self.settings.text_speed
        self.world.screen_shake = self.settings.screen_shake
        self._last_room = self.world.room.id

    def _sync_players(self) -> None:
        """Drop the second lamplighter in or out to match the setting."""
        if self.settings.two_player and self.world.hero2 is None:
            self.world.join_player_two()
        elif not self.settings.two_player and self.world.hero2 is not None:
            self.world.drop_player_two()

    def _update_play(self) -> None:
        self._sync_players()
        self.companion.update(self.world)
        self.state.playtime += DT
        self.world.tick_clock(DT)
        self.hud.tick(self.state, self.audio, self.settings.low_health_beep)
        if self.world.dialogue is None:
            if self.input.pressed("start"):
                self._open_pause(0)
                return
            if self.input.pressed("select"):
                self._open_pause(PAGES.index("map"))
                return
        self.world.update()
        if self.world.pending_shop is not None:
            spec = self.world.pending_shop
            self.world.pending_shop = None
            self.shop = Shop(self.world, list(spec.get("shop", [])),
                             str(spec.get("greeting", "shop.hello")))
            self.audio.play("menu_select")
        if self.world.pending_warp_menu:
            self.world.pending_warp_menu = False
            self._open_pause(PAGES.index("map"))
            return
        if self.world.pending_minigame:
            game_id, self.world.pending_minigame = self.world.pending_minigame, ""
            self.minigame = start_minigame(self.world, game_id)
            self.world.dialogue = None
            self.audio.play("menu_select")
            return
        if self.world.pending_ending:
            self._start_ending(self.world.pending_ending)
            return
        if self.world.room.id != self._last_room:
            self._last_room = self.world.room.id
            self.companion.reset()
            self.autosave()

    def _open_pause(self, page: int) -> None:
        self.pause = PauseMenu(self.assets, self.content, self.state, self.audio,
                               self.settings, page)
        self.audio.play("pause")

    def _update_pause(self) -> None:
        menu = self.pause
        if menu is None:
            return
        if menu.update(self.input) == "close":
            self.pause = None
            self._apply_settings()
            return
        if menu.want_save:
            menu.want_save = False
            self.save()
        if menu.want_warp:
            target, menu.want_warp = menu.want_warp, ""
            self.pause = None
            self.world.warp(target)

    # ----- ending --------------------------------------------------------
    def _start_ending(self, which: str) -> None:
        """Hand the screen over to the credits and bank the finished run."""
        self.world.pending_ending = ""
        self.state.set_flag("cleared", 1)
        self.state.set_flag("ending", 2 if which == "full" else 1)
        self.settings.master_unlocked = True
        self.settings.save()
        self.save()
        self.ending = Ending(self.assets, self.content, self.state, self.audio, which)

    def _update_ending(self) -> None:
        if self.ending is None or not self.ending.update(self.input):
            return
        self.ending = None
        self.audio.play_music("title")
        self.file_select = FileSelect(self.assets, self.content, savefile.all_summaries(),
                                      self.audio, self.settings.master_unlocked)

    def _update_minigame(self) -> None:
        if self.minigame is not None and self.minigame.update(self.input) == "close":
            self.minigame = None
            self.save()

    def _update_shop(self) -> None:
        if self.shop is not None and self.shop.update(self.input) == "close":
            self.shop = None

    # ----- saving --------------------------------------------------------
    def _apply_settings(self) -> None:
        self.settings.clamped()
        self._sync_players()
        self.audio.set_volumes(self.settings.music_volume, self.settings.sfx_volume)
        self.world.text_speed = self.settings.text_speed
        self.world.screen_shake = self.settings.screen_shake
        self.companion.enabled = self.settings.hints
        self.settings.save()

    def save(self) -> None:
        """Write the current slot."""
        self.world.save_position()
        savefile.save(self.state, self.state.slot)

    def autosave(self) -> None:
        """Called on every screen change and after a boss."""
        self.save()

    def crash_save(self) -> Any:
        """Dump to the crash slot; used by the top-level exception handler."""
        self.world.save_position()
        return savefile.crash_save(self.state)

    # ----- drawing -------------------------------------------------------
    def draw(self, canvas: pygame.Surface) -> None:
        """Paint the full 320x240 frame."""
        canvas.fill(self.assets.colour("ink"), pygame.Rect(0, 0, CANVAS_W, CANVAS_H))
        if self.file_select is not None:
            self.file_select.draw(canvas)
            return
        if self.ending is not None:
            self.ending.draw(canvas)
            return
        if self.minigame is not None:
            self.minigame.draw(canvas)
            return
        if self.shop is not None:
            self.shop.draw(canvas)
            return
        if self.pause is not None:
            self.pause.draw(canvas)
            return
        self.world.draw(canvas)
        self.hud.draw(canvas, self.state, self.world.hero2 is not None)
        self.debug.draw(canvas, self)
