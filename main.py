#!/usr/bin/env python3
"""Lantern of Eldermoor — entry point.

    python main.py [--scale N] [--fullscreen] [--stretch] [--headless [--frames N]] [--save SLOT]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line flags."""
    p = argparse.ArgumentParser(description="Lantern of Eldermoor")
    p.add_argument("--scale", type=int, default=4, help="window scale 2-6 (default 4)")
    p.add_argument("--fullscreen", action="store_true", help="start fullscreen")
    p.add_argument("--stretch", action="store_true", help="stretch to fill instead of integer scaling")
    p.add_argument("--headless", action="store_true", help="no window; run --frames logic steps and exit")
    p.add_argument("--frames", type=int, default=60, help="frames to run in --headless mode")
    p.add_argument("--save", type=int, default=1, metavar="SLOT", help="save slot 1-3")
    p.add_argument("--no-menu", action="store_true", help="skip the file-select screen")
    p.add_argument("--room", default=None, help="start in this room (debug)")
    return p.parse_args(argv)


def ensure_assets() -> None:
    """Build assets/ from assets_src/ if the generated files are missing.

    Sprite sheets are committed; the WAVs are not (they are tens of megabytes
    of pure synthesis), so the first run renders them.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from eldermoor.assets import assets_built
    from eldermoor.audio import audio_built
    if not assets_built():
        print("assets missing - building from assets_src/ ...")
        import build_assets
        build_assets.main([])
    if not audio_built():
        print("audio missing - synthesising (this takes a minute, once) ...")
        import build_audio
        build_audio.main([])


def main(argv: list[str] | None = None) -> int:
    """Run the game; returns the process exit code."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    ensure_assets()
    from eldermoor.app import App, Options
    opts = Options(scale=args.scale, fullscreen=args.fullscreen, headless=args.headless,
                   frames=args.frames, save_slot=args.save, stretch=args.stretch,
                   no_menu=args.no_menu, start_room=args.room)
    return App(opts).run()


if __name__ == "__main__":
    sys.exit(main())
