#!/usr/bin/env python3
"""Build a single-folder release with PyInstaller.

    python tools/build_release.py             build for the machine it runs on
    python tools/build_release.py --onefile   one executable instead of a folder
    python tools/build_release.py --check     say what it would do, build nothing

PyInstaller only builds for the platform it runs on, so a Windows release
has to be built on Windows and a macOS one on macOS; this script is the same
on all three. Everything the game reads at runtime - ``assets/``, ``data/``,
``input_map.json`` - is bundled beside the executable, and the generated
assets are built first so a release never ships a stale sprite sheet.

The result lands in ``dist/LanternOfEldermoor/`` with a ``run`` script beside
it, plus ``eldermoor.desktop`` on Linux.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "LanternOfEldermoor"
#: folders the game reads at runtime, bundled next to the executable
DATA_DIRS = ("assets", "data")
DATA_FILES = ("input_map.json",)


def platform_name() -> str:
    """"linux", "windows" or "macos"."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def icon_argument() -> list[str]:
    """--icon for the platform, if the icon file exists."""
    wanted = {"windows": "icon.ico", "macos": "icon.icns"}.get(platform_name(), "icon_256.png")
    path = ROOT / "assets" / wanted
    return ["--icon", str(path)] if path.exists() else []


def add_data(source: Path, dest: str) -> list[str]:
    """One --add-data argument, with the separator PyInstaller wants here."""
    sep = ";" if platform_name() == "windows" else ":"
    return ["--add-data", f"{source}{sep}{dest}"]


def build_inputs() -> None:
    """Rebuild the generated assets so the release cannot ship a stale one."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    sys.path.insert(0, str(ROOT / "tools"))
    import build_assets
    import build_audio
    import make_icon
    build_assets.main([])
    build_audio.main([])
    make_icon.main([])


def command(onefile: bool) -> list[str]:
    """The whole PyInstaller command line."""
    argv = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--name", NAME, "--windowed",
            "--onefile" if onefile else "--onedir"]
    argv += icon_argument()
    for folder in DATA_DIRS:
        argv += add_data(ROOT / folder, folder)
    for name in DATA_FILES:
        if (ROOT / name).exists():
            argv += add_data(ROOT / name, ".")
    argv.append(str(ROOT / "main.py"))
    return argv


def write_launchers(target: Path) -> None:
    """A run script beside the executable, and the .desktop file on Linux."""
    if platform_name() == "windows":
        return
    runner = target / "run"
    runner.write_text(f'#!/bin/sh\nexec "$(dirname "$0")/{NAME}" "$@"\n')
    runner.chmod(0o755)
    if platform_name() == "linux" and (ROOT / "eldermoor.desktop").exists():
        shutil.copy(ROOT / "eldermoor.desktop", target / "eldermoor.desktop")
        shutil.copy(ROOT / "assets" / "icon_256.png", target / "eldermoor.png")


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="build a release of the game")
    parser.add_argument("--onefile", action="store_true",
                        help="one executable instead of a folder")
    parser.add_argument("--check", action="store_true",
                        help="print the command and the inputs, build nothing")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    line = command(args.onefile)
    if args.check:
        print(f"platform: {platform_name()}")
        print("would run:", " ".join(line))
        missing = [d for d in DATA_DIRS if not (ROOT / d).is_dir()]
        print("missing inputs:", ", ".join(missing) if missing else "none")
        return 0
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. pip install pyinstaller", file=sys.stderr)
        return 1
    print("rebuilding the generated assets ...")
    build_inputs()
    print("running PyInstaller ...")
    result = subprocess.run(line, cwd=ROOT, check=False)
    if result.returncode:
        return result.returncode
    target = ROOT / "dist" / (NAME if not args.onefile else "")
    if target.is_dir():
        write_launchers(target)
    print(f"release in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
