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

---

## Milestone 2 — Vertical slice (plan)

Goal: a slice that contains one of everything the rest of the game is made
of. Wren leaves his house in Lamplight Village, is given the sword, buys a
shield, crosses six meadow screens fighting six kinds of enemy, finds the
Ember Temple, collects its map, compass, small keys and big key, wins the
Lantern from the mini-boss, burns his way to the boss, beats it with the
Lantern, and takes the first Flame home. Everything is saved.

### 2.1 New systems and the module that owns them

| module | job |
| --- | --- |
| `state.py` | `GameState` — every number a save holds; items, flags, per-dungeon progress, play-time, completion % |
| `save.py` | 3 slots in the OS config dir, atomic temp+rename, `.bak` of the last good file, versioned schema with migrations, crash slot |
| `settings.py` | config dir per OS (`$ELDERMOOR_CONFIG_DIR` overrides), volumes, text speed, shake, beep, hints |
| `items.py` | `data/items/items.json` registry; which items may sit in B/X/Y |
| `audio.py` + `tools/build_audio.py` | square/triangle/noise/saw + ADSR synth, `.song` tracker JSON → WAV; mixer wrapper with music fade and SFX channels |
| `drops.py` | drop tables: hearts, embers, bombs, arrows, magic, fairies |
| `objects.py` | chests, pots, signs, NPCs, doors, keyholes, torches, switches, stairs, warps, heart pieces, the Flame |
| `enemies.py` + `ai.py` | `data/enemies/*.json` → state machines (`wait`, `chase`, `wander`, `charge`, `shoot`, `hop`, `patrol`, `flee`), telegraphs ≥ 20 frames |
| `combat.py` | damage both ways, half-hearts, knockback, i-frames, hit flash, shield block, death puff |
| `textbox.py` + `dialogue.py` | 3-line 8×8 bottom box, typewriter at the chosen speed, A advances, B skips; `data/text/en.json` keys |
| `shop.py` | buy screen built on the text box |
| `menu.py` | pause (items grid, assign to B/X/Y, save, settings) and the Select map screen |
| `script.py` | room triggers → actions, global flags |
| `dungeon.py` | `data/dungeons/*.json`: floors, room grid for the map, key graph, boss |
| `scene.py` | scene stack so dialogue/pause/shop suspend the world |

### 2.2 Refactors
* `Entity.update(inp, room)` becomes `Entity.update(world)`. The world is the
  context object: input, room, state, audio, entity list, spawn helpers.
  Everything an entity needs is reachable without threading more arguments
  through every milestone.
* The hero moves out of `entities.py` into `hero.py`; `entities.py` keeps the
  base class, bodies and the shared helpers.
* `hud.PlayerState` becomes an alias of `state.GameState`.
* Cuttable bush / smashable pot / liftable rock stay **tiles**. A room keeps a
  transient overlay of tiles changed this visit, so they come back when you
  leave and return, exactly like the games this copies. Chests, NPCs, doors
  and switches are **objects** in the room JSON because they are permanent and
  flag-backed.

### 2.3 Room JSON v2
`objects` (kind + grid position + kind-specific fields) and `triggers`
(`on` one of `enter`, `all_enemies_dead`, `switch`, `torches_lit`,
`block_on_plate`, `timer`, `flag` → `do` list of actions: `open`, `spawn`,
`reveal`, `jingle`, `set_flag`, `shake`) plus `dungeon`, `floor`,
`map_pos`. Milestone-1 rooms stay valid: every new key is optional.

### 2.4 Definition of done for milestone 2
`pytest` green, `ruff` clean, and `tools/validate_data.py` proves the Ember
Temple is completable: a flood fill that respects webs, pits, locked doors
and the key count reaches the boss room and the Flame, and the temple holds
as many small keys as it has small-key doors, so no key can be wasted.

`tools/sim_playthrough.py` drives the real game with a tile-level
breadth-first bot. It leaves the village, crosses the meadow, enters the
Ember Temple and takes the map and the compass; that is what the test suite
holds it to. Fighting the mini-boss and the Ashen Maw unattended is a
different problem — one for milestone 8, where PROMPT.md asks for the
balance pass and the 90-hour measurement. The tool already reports what it
achieved from the save state rather than from goals it gave up on, so the
number never flatters itself.
