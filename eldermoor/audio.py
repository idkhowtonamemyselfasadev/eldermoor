"""Sound: the mixer, a cache of SFX and the music track, degrading to silence."""
from __future__ import annotations

from pathlib import Path

import pygame

from eldermoor.config import ASSETS

SFX_DIR = ASSETS / "audio" / "sfx"
MUSIC_DIR = ASSETS / "audio" / "music"
CHANNELS = 16
#: a sound asked for this many frames ago is not restarted (stops machine-gunning)
REPEAT_GUARD = 3


class Audio:
    """Plays the generated WAVs. Every call is safe when there is no audio device."""

    def __init__(self, music_volume: float = 0.7, sfx_volume: float = 0.9,
                 root: Path = ASSETS) -> None:
        self.sfx_dir = root / "audio" / "sfx"
        self.music_dir = root / "audio" / "music"
        self.music_volume = music_volume
        self.sfx_volume = sfx_volume
        self.enabled = self._init_mixer()
        self._cache: dict[str, pygame.mixer.Sound | None] = {}
        self._recent: dict[str, int] = {}
        self.frame = 0
        self.current_music: str | None = None
        self.log: list[str] = []          # what was asked for, for tests and the debug overlay

    @staticmethod
    def _init_mixer() -> bool:
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(CHANNELS)
        except pygame.error:
            return False
        return True

    # ----- sound effects -------------------------------------------------
    def _sound(self, name: str) -> pygame.mixer.Sound | None:
        if name in self._cache:
            return self._cache[name]
        path = self.sfx_dir / f"{name}.wav"
        sound: pygame.mixer.Sound | None = None
        if self.enabled and path.exists():
            try:
                sound = pygame.mixer.Sound(str(path))
            except pygame.error:
                sound = None
        self._cache[name] = sound
        return sound

    def play(self, name: str, volume: float = 1.0) -> None:
        """Play a sound effect by name. Unknown or missing names are ignored."""
        self.log.append(name)
        if len(self.log) > 64:
            del self.log[:-64]
        if self._recent.get(name, -99) > self.frame - REPEAT_GUARD:
            return
        self._recent[name] = self.frame
        sound = self._sound(name)
        if sound is None:
            return
        sound.set_volume(max(0.0, min(1.0, volume * self.sfx_volume)))
        sound.play()

    # ----- music ---------------------------------------------------------
    def play_music(self, name: str, fade_ms: int = 500) -> None:
        """Start a looping track; re-asking for the current track does nothing."""
        if name == self.current_music:
            return
        self.current_music = name
        if not self.enabled:
            return
        path = self.music_dir / f"{name}.wav"
        if not path.exists():
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1, fade_ms=fade_ms)
        except pygame.error:
            self.current_music = None

    def stop_music(self, fade_ms: int = 400) -> None:
        """Fade the current track out."""
        self.current_music = None
        if self.enabled:
            try:
                pygame.mixer.music.fadeout(fade_ms)
            except pygame.error:
                pass

    def set_volumes(self, music: float, sfx: float) -> None:
        """Apply new volumes from the settings menu."""
        self.music_volume = max(0.0, min(1.0, music))
        self.sfx_volume = max(0.0, min(1.0, sfx))
        if self.enabled:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except pygame.error:
                pass

    def tick(self) -> None:
        """Called once per logic frame so the repeat guard can age."""
        self.frame += 1


def audio_built(root: Path = ASSETS) -> bool:
    """True if tools/build_audio.py has been run."""
    return (root / "audio" / "sfx" / "sword.wav").exists()
