"""Engine-wide constants. Everything that is a number in PROMPT.md lives here."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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

# Logical buttons (the 12 the whole game is played with)
BUTTONS = ("up", "down", "left", "right",
           "a", "b", "x", "y", "l", "r", "start", "select")
