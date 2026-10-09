#!/usr/bin/env python3
"""Compose the application icon from the game's own pixel-maps.

The icon is Wren's lantern, drawn once in assets_src/icons/app.txt and then
scaled to the sizes each platform wants:

    assets/icon_256.png   the one the release build and the .desktop use
    assets/icon.ico       Windows, with 16/32/48/64/128/256 inside it
    assets/icon.icns      macOS, when Pillow is available to write it

    python tools/make_icon.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "assets"
SIZES = (16, 32, 48, 64, 128, 256)


def build() -> Path:
    """Write the PNG and, where possible, the .ico and .icns. Returns the PNG."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from build_assets import CHARS, load_palette, parse_blocks
    pygame.init()
    pygame.display.set_mode((64, 64))
    palette = load_palette()
    blocks = {name: (w, h, rows) for name, w, h, rows
              in parse_blocks(ROOT / "assets_src" / "icons" / "app.txt")}
    if "app_icon" not in blocks:
        raise SystemExit("assets_src/icons/app.txt has no @app_icon block")
    w, h, rows = blocks["app_icon"]
    small = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            small.set_at((x, y), (*palette[CHARS.index(ch)], 255))
    png = OUT / "icon_256.png"
    pygame.image.save(pygame.transform.scale(small, (256, 256)), str(png))
    print(f"  wrote {png.relative_to(ROOT)}")
    for size in SIZES:
        pygame.image.save(pygame.transform.scale(small, (size, size)),
                          str(OUT / f"icon_{size}.png"))
    _write_ico(png)
    return png


def _write_ico(png: Path) -> None:
    """Pack the PNGs into a Windows .ico and a macOS .icns, if Pillow is here."""
    try:
        from PIL import Image
    except ImportError:
        print("  (install Pillow for icon.ico and icon.icns)")
        return
    image = Image.open(png)
    image.save(OUT / "icon.ico", sizes=[(s, s) for s in SIZES])
    print("  wrote assets/icon.ico")
    try:
        image.save(OUT / "icon.icns")
        print("  wrote assets/icon.icns")
    except (OSError, ValueError) as exc:
        print(f"  (no icns: {exc})")


def main(argv: list[str]) -> int:
    """Entry point."""
    print("building the application icon ...")
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
