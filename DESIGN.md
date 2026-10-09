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

---

## Milestone 3 — The kingdom (plan)

Goal: all 256 overworld screens, every region, day and night, the warp
lanterns, every kind of item gate placed where it belongs, and Temples 2, 3
and 4 with the Power Bracelet, the Bombs and Hookshot, and the Bow.

### 3.1 Map sheets: how 256 hand-made screens get authored

One JSON file per screen does not scale to 361 rooms, and it makes the
screens drift apart: neighbouring doorways stop lining up and roads stop at
the seam. So the overworld is painted as **one continuous canvas**:

    data/overworld/eldermoor.map     208 lines x 320 characters
                                     = 16 x 16 screens of 20 x 13 tiles

Every tile is still placed by hand, one legend character at a time — but a
road that leaves a screen is literally the same row of characters on the
other side, so continuity is free and the whole kingdom can be read at once.
`eldermoor/mapsheet.py` slices the canvas into rooms on demand:

* a screen's id is `ow_<row><col>`, zero-padded (`ow_0713`);
* exits are **derived**: a screen has an exit where its own edge and the
  neighbour's facing edge are both walkable for at least two tiles, which
  removes one-way exits and misaligned doorways by construction;
* `data/overworld/sheet.json` carries the per-screen extras — region,
  name, music, objects, triggers — and only for screens that need them.

Dungeons use the same machinery: one canvas per floor
(`data/dungeons/temple2/f1.map`), so a temple's rooms line up by
construction too. The Ember Temple's existing 35 JSON rooms stay as they
are; `Room.load` tries `data/rooms/<id>.json` first and falls back to the
sheets.

### 3.2 Regions
Eight, each a palette swap of the shared tile sheet plus its own tileset
entries, music, enemies and secrets:

| region | where | gate that opens it |
| --- | --- | --- |
| Lamplight & meadows | south centre | none (start) |
| Thornwood | west, rows 3-8 | sword (cut the thorns) |
| Saltmarsh & coast | the whole south edge | Fins, later |
| Mount Cinder | north-east | Fire Boots, later |
| Frozen Tarn | north centre | Fire Boots melt the ice |
| Sunken Fen | centre | Hookshot |
| Hollow Desert | east, rows 4-11 | Power Bracelet |
| Mistlands | north-west | the Lantern, very late |

Every region is *visible* before it is enterable: the screen next door shows
the thorns, the ice or the chasm first.

### 3.3 Day and night
An eight-minute clock in `GameState.minutes_of_day`. Night swaps the tile
sheet for the `night` palette variant that already exists, changes which
enemies spawn, and gates a handful of secrets. The clock stops indoors and
in dungeons.

### 3.4 Warp lanterns
One per region, an object that lights on first touch, sets a flag and adds
the region to the Select-screen warp list. Warping is chosen from the map
screen with A.

### 3.5 Temples 2-4
Temple 2 "Bramble Hollow" (Thornwood) — Power Bracelet: lift rocks and pots,
throw them. Temple 3 "Tidewrack" (Saltmarsh) — Bombs in the first half,
Hookshot from the mini-boss. Temple 4 "The Long Glass" (Hollow Desert) —
Bow: switches, eyes, flying enemies. Each is 35+ rooms on a map sheet, each
with its own mini-boss, boss, map, compass, Great Key, heart container and
Flame, and each validated by `tools/validate_data.py` exactly like Temple 1.


### 3.6 Temples 5-8 and the Great Lantern
Temple 5 "Drowned Hollow" (Tidewrack) — Fins: deep water is a road. Temple 6
"The Kiln" (Cinderwaste) — Cinderstep Boots: lava is a floor, ice is not a
wall. Temple 7 "The Long Mirror" (Hollow Tarn) — Mirror Cloak: the watchers
lose you, and their shots come home. Temple 8 "The Giant's Gate" (Mistlands)
— Titan Gauntlet and the Whistle of Winds. Each is 36 rooms on a map sheet
with a mini-boss, a boss, a map, a compass, four keys, a Great Key, a heart
container and a Flame.

Temple 9 "The Great Lantern" is smaller on purpose: 16 rooms, no keys and no
Flame, because its door is the lock. It opens on the eighth Flame and ends
at The Quiet. Beating it writes `cleared` and rolls one of two endings,
chosen by `state.completion()` against `FULL_ENDING_AT`.

The map sheets for these five are what forced `tilemap.SEALED`: a hall that
is flooded or on fire has water or lava in its doorway, and the old rule —
an exit exists where both sides are walkable — quietly cut those rooms out
of the dungeon. Exits now exist unless solid rock is in the way, and the
relic is the gate. `tools/validate_data.py` carries the same rule, so the
proof of completability is still a proof.
