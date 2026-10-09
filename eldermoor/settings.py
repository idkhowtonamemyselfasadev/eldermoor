"""Where the user's files live, and the options menu's backing store."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from eldermoor.config import APP_NAME, DEFAULT_SCALE, TEXT_SPEED_DEFAULT

ENV_OVERRIDE = "ELDERMOOR_CONFIG_DIR"


def config_dir() -> Path:
    """The per-user config directory: ~/.config/eldermoor, %APPDATA% or Application Support."""
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        return Path(override)
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME


def ensure_config_dir() -> Path:
    """Create the config directory (and its saves/ subfolder) and return it."""
    d = config_dir()
    (d / "saves").mkdir(parents=True, exist_ok=True)
    return d


def crash_log_path() -> Path:
    """Where the top-level exception handler writes."""
    return config_dir() / "crash.log"


@dataclass
class Settings:
    """Everything the settings menu can change. Saved as settings.json."""

    music_volume: float = 0.7
    sfx_volume: float = 0.9
    screen_shake: bool = True
    scale: int = DEFAULT_SCALE
    fullscreen: bool = False
    stretch: bool = False
    text_speed: int = TEXT_SPEED_DEFAULT
    low_health_beep: bool = True
    hints: bool = True
    language: str = "en"
    show_button_glyphs: bool = True
    #: set the first time an ending rolls: the Master Quest is on offer after that
    master_unlocked: bool = False
    #: two lamplighters: player one on the keyboard, player two on the gamepad
    two_player: bool = False

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        """Read settings.json, falling back to defaults for anything missing or broken."""
        p = path or (config_dir() / "settings.json")
        if not p.exists():
            return cls()
        try:
            raw: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, path: Path | None = None) -> None:
        """Write settings.json atomically."""
        p = path or (config_dir() / "settings.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        tmp.replace(p)

    def clamped(self) -> Settings:
        """Return a copy with every value inside its legal range."""
        self.music_volume = min(1.0, max(0.0, float(self.music_volume)))
        self.sfx_volume = min(1.0, max(0.0, float(self.sfx_volume)))
        self.text_speed = min(4, max(1, int(self.text_speed)))
        self.scale = min(6, max(2, int(self.scale)))
        return self
