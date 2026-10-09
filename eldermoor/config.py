"""Engine-wide constants. Everything that is a number in PROMPT.md lives here."""
from __future__ import annotations

import sys
from pathlib import Path


def _root() -> Path:
    """Where assets/ and data/ live, whether run from source or frozen.

    PyInstaller unpacks the bundled folders beside the executable and points
    ``sys._MEIPASS`` at them; from a source checkout it is the repository.
    """
    bundle = getattr(sys, "_MEIPASS", "")
    return Path(bundle) if bundle else Path(__file__).resolve().parent.parent


ROOT = _root()
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
INPUT_MAP_FILE = ROOT / "input_map.json"

CANVAS_W = 320
CANVAS_H = 240
TILE = 16
HUD_ROWS = 2
HUD_H = HUD_ROWS * TILE          # 32 px
PLAY_COLS = 20
PLAY_ROWS = 13
PLAY_W = PLAY_COLS * TILE        # 320
PLAY_H = PLAY_ROWS * TILE        # 208
PLAY_Y = HUD_H                   # play area starts under the HUD

FPS = 60
DT = 1.0 / FPS

DEFAULT_SCALE = 4
MIN_SCALE = 2
MAX_SCALE = 6

FLIP_SCROLL_FRAMES = 12

# Hero
HERO_SPEED = 1.25                # px per frame (75 px/s)
HERO_WALK_FRAME_TIME = 8         # frames per walk-cycle frame
HERO_IDLE_FRAME_TIME = 30
SWING_FRAME_TIME = 4             # frames per swing frame
SWING_FRAMES = 3
SWING_TOTAL = SWING_FRAME_TIME * SWING_FRAMES

SAVE_VERSION = 3
APP_NAME = "eldermoor"
SAVE_SLOTS = 3

# Combat and reactions
HERO_INVULN_FRAMES = 54          # ~0.9 s of mercy after a hit
HERO_KNOCKBACK_SPEED = 2.5
KNOCKBACK_FRAMES = 8
HIT_FLASH_FRAMES = 10
ROLL_FRAMES = 20
ROLL_IFRAMES = 8
ROLL_SPEED = 2.75
ROLL_COOLDOWN = 12
#: how slowly ice gives up Wren's old heading (0 = not at all)
ICE_SLIP = 0.09
SHIELD_SPEED_FACTOR = 0.55
SWIM_SPEED_FACTOR = 0.72
CLOAK_SPEED_FACTOR = 0.8
DEATH_PUFF_FRAMES = 16           # 4 frames x 4 ticks
SPIN_CHARGE_FRAMES = 36          # hold A this long for a spin attack
SPIN_FRAMES = 24
ENEMY_TELEGRAPH_MIN = 20         # every attack must be readable this long

# Text
TEXT_SPEED_DEFAULT = 2           # glyphs per frame
DIALOGUE_LINES = 3
DIALOGUE_COLS = 36

# Logical buttons (the 12 the whole game is played with)
BUTTONS = ("up", "down", "left", "right",
           "a", "b", "x", "y", "l", "r", "start", "select")
