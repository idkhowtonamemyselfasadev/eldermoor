# DESIGN — Milestone 1: engine core

One playable screen pair. Wren walks in 8 directions, swings a sword,
flip-scrolls between two meadow rooms under a 2-row HUD. Everything else
in PROMPT.md builds on the modules laid down here.

## Layout of the engine (`eldermoor/`, each module <= 600 lines)

| module        | job                                                              |
|---------------|------------------------------------------------------------------|
| `config.py`   | constants: canvas 320x240, tile 16, HUD 2 rows, play area 20x13, 60 Hz |
| `app.py`      | window, integer scaling with black bars, fixed-timestep loop, `--headless` |
| `input.py`    | 12 logical buttons; keyboard + SDL GameController; `input_map.json`; last-device tracking |
| `assets.py`   | loads `assets/*.png` + `.json` atlases; `Sheet.get(name)` sub-surfaces; palette |
| `font.py`     | `BitmapFont` for 8x8 and 6x8 sheets; plain and outlined text |
| `tilemap.py`  | tileset definitions (`data/tilesets/*.json`), room JSON, tile collision |
| `entities.py` | `Entity` base, `Hero` (Wren) with walk/idle/swing animation and sword hitbox |
| `world.py`    | current room, hero, exits, 12-frame flip-scroll transition |
| `hud.py`      | hearts (full/half/empty), embers, keys, B/X/Y icon slots |
| `debug.py`    | F1 overlay: fps, room id, entity count, hero pos, input device |
| `game.py`     | `Game`: owns world/hud/debug, `update()`, `draw(canvas)` |

`main.py` parses flags (`--scale N`, `--fullscreen`, `--headless`,
`--save SLOT`, `--frames N`) and runs `App`.

## Frame flow

`App.run()` -> accumulate real time -> for each 1/60 s: `Input.poll()`,
`Game.update()` -> `Game.draw(canvas)` -> scale canvas to window -> flip.
Headless uses `SDL_VIDEODRIVER=dummy`, runs N fixed steps and exits 0.

## Rooms and the asset pipeline

* Rooms are JSON: 20x13 tile ids (ints into a tileset), `tileset`,
  `exits` (`north/east/south/west` -> room id), spawn point.
* Tilesets map tile id -> sprite block name + collision class
  (`solid`, `floor`, `grass`, `water`, ...). Only `solid`/`floor`/`grass`
  are used this milestone; the enum is defined fully.
* `tools/build_assets.py` compiles `assets_src/**/*.txt` pixel-maps to
  `assets/*.png` + atlas JSON. Fonts are blocks named `U+XXXX`.

## Hero

16x16 sprite, 12x10 feet collider, speed 1.25 px/frame (75 px/s),
8-direction movement with normalised diagonals, 4 facing directions for
sprites, 3-frame walk cycle (8 frames per step), 2-frame idle. Sword:
3-frame swing (4 frames each), arc sprite drawn over the hero, hitbox for
later enemies. Movement locked during the swing. Tile collision is
axis-separated AABB vs solid tiles.

## Transition

Walking past a room edge with an exit triggers a flip-scroll: both rooms
are pre-rendered, the old one slides out and the new slides in over 12
frames while logic pauses; the hero is placed on the opposite edge.

## Tests (`tests/`, headless)

Asset build is reproducible; every atlas entry exists; fonts contain
ASCII 32-126 + ÄÖÜäöüß; input map maps all 12 buttons; hero moves/collides
and swing timings; room load; transition completes in 12 frames; HUD draws
hearts correctly for half values; `main.py --headless --frames 10` exits 0.
