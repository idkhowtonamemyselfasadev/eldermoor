# Lantern of Eldermoor

A top-down adventure for one or two players: a 256-screen kingdom, nine
temples, six caves, a post-game, and forty of most things to find. Every
sprite in it is a text file, every sound is an oscillator, and every room
was placed by hand.

- 320×240, 16×16 tiles, a fixed 60 Hz step, scaled up with whole numbers.
- Python 3.11+ and [pygame-ce](https://pyga.me). Nothing else.
- Keyboard or gamepad, twelve buttons, no mouse.

```
python main.py                 # play it
python main.py --scale 5       # a bigger window (2–6)
python main.py --fullscreen
python main.py --headless --frames 600    # no window; used by the tests
```

--------------------------------------------------------------------------
## Installing

The short version, on any of the four platforms below: get Python 3.11 or
newer, then run `./run.sh` (Linux and macOS) or `run.bat` (Windows). Those
scripts make a virtual environment, install pygame-ce into it, build the
sprite sheets and the sounds, and start the game. Everything stays inside
the project folder.

### Fedora 39+

```sh
sudo dnf install -y python3 python3-pip SDL2 SDL2_image SDL2_mixer
git clone <this repository> eldermoor && cd eldermoor
./run.sh
```

### Ubuntu 22.04+ / Debian 12+

```sh
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libsdl2-2.0-0 \
    libsdl2-image-2.0-0 libsdl2-mixer-2.0-0
git clone <this repository> eldermoor && cd eldermoor
./run.sh
```

### Windows 11

1. Install Python from the Microsoft Store, or from
   [python.org](https://www.python.org/downloads/windows/) with **Add
   python.exe to PATH** ticked.
2. Download or clone this repository.
3. Double-click `run.bat`, or in a terminal:

```bat
cd path\to\eldermoor
run.bat
```

### macOS 12+

```sh
brew install python@3.12          # or python.org's installer
git clone <this repository> eldermoor && cd eldermoor
./run.sh
```

On the first run it synthesises the music and sound effects, which takes
about a minute and happens once. The sprite sheets are already in the
repository; `tools/build_assets.py` rebuilds them from `assets_src/`.

### Doing it by hand

```sh
python3 -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python tools/build_assets.py
python tools/build_audio.py
python main.py
```

--------------------------------------------------------------------------
## Playing

| Button | Keyboard | Gamepad | Does |
| --- | --- | --- | --- |
| move | arrows / WASD | d-pad, left stick | walk |
| A | Z or J | A | talk, read, open, lift, swing |
| B / X / Y | X·K / C·L / V·; | B / X / Y | the three item slots |
| L | shift | left shoulder | raise the shield |
| R | space | right shoulder | roll |
| Start | Enter or Esc | Start | pause: items, rings, log, finds, settings, save |
| Select | Tab | Back | the map, and the warp list |
| F11 / Alt+Enter | | | fullscreen |
| F1 | | | debug overlay |

Hold A with a levelled sword to charge a spin. Everything is remappable in
`input_map.json`.

**Two players.** Turn on *Two players* on the settings page: player one
keeps the keyboard, player two takes the gamepad, and a second lamplighter
drops in beside the first with their own three item slots. They share the
hearts, the keys and the kingdom. Turning it off again puts them away.

**Hints.** The companion in the lantern offers a hint if you stand still
for a while, once per room. *Hint companion* on the settings page turns her
off.

Saves and settings live in `~/.config/eldermoor/` on Linux, `%APPDATA%\
eldermoor\` on Windows and `~/Library/Application Support/eldermoor/` on
macOS. Set `ELDERMOOR_CONFIG_DIR` to put them somewhere else. A crash
autosaves to a crash slot and appends to `crash.log`; no crash loses
progress.

--------------------------------------------------------------------------
## Playing it on a phone

The game is built for a phone browser: one build, and it works on both
iPhone and Android from a link. Add it to the home screen and it behaves
like an app.

```sh
pip install pygbag
python tools/build_audio.py --ogg     # 39 MB of WAV becomes 2.5 MB
python tools/build_web.py             # build/web/ - static files
python tools/build_web.py --serve     # build, then serve it on :8000
python tools/build_web.py --check     # prove the bundle runs, build nothing
```

`build/web/` is static, so any host will do. The download is about 4 MB of
game on top of pygbag's runtime.

**It needs the network.** pygbag fetches its WebAssembly runtime from
`pygame-web.github.io` while building, and it retries that forever rather
than failing, so `build_web.py` checks the host first and stops with a
message if it cannot be reached.

**The controls.** On a touchscreen the game draws its own pad: a thumb
stick that reads eight directions and the eight buttons, laid out in the
black bars either side of the picture (or underneath it, in portrait) so
they never cover the game. *On-screen pad* on the settings page forces it
on or off; `--touch on` does the same from the command line, which is how
to see it on a desktop.

An Android APK is a second, separate path (Buildozer and
python-for-android) and would reuse all of the above; it has not been
built.

--------------------------------------------------------------------------
## Building a release

```sh
pip install pyinstaller pillow
python tools/build_release.py            # dist/LanternOfEldermoor/
python tools/build_release.py --onefile  # one executable
python tools/build_release.py --check    # print the command, build nothing
```

PyInstaller only builds for the platform it runs on, so a Windows release
has to be built on Windows and a macOS one on macOS. On Linux the release
folder also gets `eldermoor.desktop` and an icon; copy both into
`~/.local/share/applications/` and `~/.local/share/icons/` to have it in
the app menu.

--------------------------------------------------------------------------
## Working on it

```sh
pytest                                   # headless, no window, no sound
ruff check .
python tools/validate_data.py            # every room, door, key and prize
python tools/check_art.py                # every pixel-map parses
python tools/check_palette.py            # colour-blind safety
python tools/sim_playthrough.py          # length estimate
python tools/sim_playthrough.py --balance
```

`tools/validate_data.py` is the one that matters: it proves every temple can
be finished with the items available at that point, that no key can be
wasted, that all forty heart pieces and forty seashells exist and are
reachable, and that everything in a collection has somebody who gives it
out. It fails the build rather than the player.

| Where | What |
| --- | --- |
| `eldermoor/` | the engine and the game, no module over 600 lines |
| `data/` | rooms, dungeons, enemies, items, quests, text — all of it |
| `assets_src/` | text pixel-maps, the palette, the fonts, the songs |
| `assets/` | generated sheets and sounds |
| `tools/` | the builders, the validators, the bot |
| `tests/` | pytest, headless |

`DESIGN.md` is how it is put together, `DECISIONS.md` is why, and
`CHANGELOG.md` is what happened in which order.

--------------------------------------------------------------------------
## What is in it

667 rooms, of which 256 are the overworld; nine temples, six optional caves
and a post-game temple; 61 kinds of creature, 28 of them bosses; 40 items,
40 heart pieces, 40 seashells, 12 rings, 24 figurines and 12 pieces of
furniture; 30 side quests, a ten-step trading chain, three minigames, two
endings, a Boss Rush, a Master Quest and local co-op. 684 lines of
dialogue. `tools/sim_playthrough.py` projects about 53 hours for the main
line and 106 to 100 %, and prints its workings.

It has been built and played on Linux. The Windows and macOS instructions
above are written from the same shape and have not been run on those
machines; nothing in the game is platform-specific, but that is a claim
about the code rather than a test result. The same goes for the phone
build: the controls, the staged bundle and the compressed audio are all
tested here, but the final page is assembled by pygbag against a host this
machine cannot reach, so it has not been opened on a real phone.

--------------------------------------------------------------------------
## About the kingdom

Eldermoor is original. Its places, people, creatures, items and story are
not borrowed from anyone, and neither are its pixels or its noises: the art
is text files in `assets_src/`, compiled to PNG sheets at build time, and
the audio is oscillators and envelopes rendered to WAV by
`tools/build_audio.py`.
