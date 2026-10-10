#!/usr/bin/env python3
"""Build the game for a phone: a web page that plays in a mobile browser.

    python tools/build_web.py            stage the files and build with pygbag
    python tools/build_web.py --stage    stage only, so the files can be looked at
    python tools/build_web.py --serve    build, then serve it on :8000

pygbag compiles CPython and pygame-ce to WebAssembly and packs a folder into
a page. It packs *everything* in that folder, so this stages a clean copy
first: the engine, the data, the compressed audio and the sheets, and
nothing else - no WAVs, no tests, no sources, no virtual environment. The
staged copy gets its own ``main.py``, because a page cannot run a blocking
loop; it awaits between frames instead.

The result is ``build/web/`` - static files, so any web host will do, and a
phone browser can add it to the home screen.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "build" / "web_src"
OUT = ROOT / "build" / "web"

#: what the game actually reads at runtime
COPY_DIRS = ("eldermoor", "data")
COPY_FILES = ("input_map.json",)
#: from assets/, everything but the uncompressed audio
SKIP_SUFFIXES = (".wav",)

WEB_MAIN = '''"""Lantern of Eldermoor, in a browser. Written by tools/build_web.py."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# the browser's persistent storage, so saves survive a reload
os.environ.setdefault("ELDERMOOR_CONFIG_DIR", "/data/data/eldermoor/files")


async def main() -> None:
    """Start the game and hand the page a turn between frames."""
    from eldermoor.app import App, Options
    app = App(Options(scale=4, touch="auto"))
    await app.run_async()


asyncio.run(main())
'''


def _short(path: Path) -> str:
    """A path to print: relative to the repository when it is inside it."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def stage() -> Path:
    """Copy the runtime files into a clean folder. Returns it."""
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    for folder in COPY_DIRS:
        shutil.copytree(ROOT / folder, STAGE / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in COPY_FILES:
        if (ROOT / name).exists():
            shutil.copy(ROOT / name, STAGE / name)
    copied = 0
    for path in sorted((ROOT / "assets").rglob("*")):
        if path.is_dir() or path.suffix in SKIP_SUFFIXES:
            continue
        target = STAGE / "assets" / path.relative_to(ROOT / "assets")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, target)
        copied += 1
    (STAGE / "main.py").write_text(WEB_MAIN, encoding="utf-8")
    size = sum(p.stat().st_size for p in STAGE.rglob("*") if p.is_file())
    print(f"staged {copied} asset files, {size / 1e6:.1f} MB in {_short(STAGE)}")
    return STAGE


def check_audio() -> None:
    """Warn loudly if the small audio was never built."""
    oggs = list((ROOT / "assets" / "audio").rglob("*.ogg"))
    if not oggs:
        print("  no OGG audio found - run tools/build_audio.py --ogg first, or the\n"
              "  page will be silent (the WAVs are far too big to ship)", file=sys.stderr)


#: pygbag fetches its WebAssembly runtime from here at build time
RUNTIME_HOST = "https://pygame-web.github.io"


def runtime_reachable(timeout: float = 10.0) -> bool:
    """Can we reach the host pygbag downloads its runtime from?"""
    import urllib.error
    import urllib.request
    try:
        urllib.request.urlopen(f"{RUNTIME_HOST}/", timeout=timeout).close()
    except (urllib.error.URLError, OSError):
        return False
    return True


def self_contained(frames: int = 120) -> bool:
    """Run the staged copy on its own, to prove nothing was left behind.

    The staged folder is what the page will hold, so if it plays from a
    different working directory with nothing else on the path, the page has
    everything it needs. This is the half of a web build that is actually
    ours to get right.
    """
    script = (
        "import os, sys\n"
        "os.environ['SDL_VIDEODRIVER'] = 'dummy'\n"
        "os.environ['SDL_AUDIODRIVER'] = 'dummy'\n"
        f"sys.path.insert(0, {str(STAGE)!r})\n"
        "from eldermoor.app import App, Options\n"
        "app = App(Options(headless=True, no_menu=True, touch='on', "
        f"frames={frames}))\n"
        "print('ok', app.run())\n"
    )
    result = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT.parent),
                            capture_output=True, text=True, check=False)
    if result.returncode:
        print(result.stdout[-2000:], file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
    return result.returncode == 0


def build(serve: bool) -> int:
    """Run pygbag over the staged folder."""
    try:
        import pygbag  # noqa: F401
    except ImportError:
        print("pygbag is not installed. pip install pygbag", file=sys.stderr)
        return 1
    if not runtime_reachable():
        print(f"cannot reach {RUNTIME_HOST}, where pygbag fetches its runtime.\n"
              "  pygbag will retry that forever rather than fail, so stopping here.\n"
              "  Run this on a machine that can reach it, or allow that host.",
              file=sys.stderr)
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, "-m", "pygbag", "--build",
            "--app_name", "eldermoor", "--title", "Lantern of Eldermoor",
            "--ume_block", "0", str(STAGE / "main.py")]
    if serve:
        argv.remove("--build")
    env = dict(os.environ, PYGBAG_NO_ANALYTICS="1")
    result = subprocess.run(argv, cwd=ROOT, env=env, check=False)
    if result.returncode:
        return result.returncode
    built = STAGE / "build" / "web"
    if built.is_dir():
        if OUT.exists():
            shutil.rmtree(OUT)
        shutil.copytree(built, OUT)
        size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
        print(f"built {_short(OUT)}: {size / 1e6:.1f} MB")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="build the game for the web")
    parser.add_argument("--stage", action="store_true", help="stage the files only")
    parser.add_argument("--serve", action="store_true", help="serve it after building")
    parser.add_argument("--check", action="store_true",
                        help="stage, then play the staged copy headlessly to prove it runs")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    check_audio()
    stage()
    if args.check:
        ok = self_contained()
        print("the staged copy plays on its own" if ok
              else "the staged copy is missing something", file=sys.stderr if not ok else None)
        return 0 if ok else 1
    if args.stage:
        return 0
    return build(args.serve)


if __name__ == "__main__":
    sys.exit(main())
