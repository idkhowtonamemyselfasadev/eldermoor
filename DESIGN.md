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

--------------------------------------------------------------------------
## 4. Milestone 5 — the rest of the kingdom

The main line is finished, so everything in milestone 5 hangs off it: things
to find on screens already painted, people already standing there, and six
caves whose doors were cut into the overworld in milestone 3.

### 4.1 One table per collection
All of it is data. `data/quests/quests.json` holds thirty side quests
(`id`, `name`, `giver`, `needs`, `gives`, `flag`, `hint`);
`data/items/rings.json` the rings; `data/collections/figurines.json` and
`furniture.json` the two display collections; `data/trade.json` the trading
chain. `eldermoor/quests.py` is the only code that reads quest state, and it
reads it out of flags the script engine already sets, so a quest is a
trigger plus a row in a table rather than a new system.

### 4.2 What the save learns to hold
`GameState` gains `rings` (owned), `worn` (two ring slots), `figurines`,
`furniture`, `bestiary` (kill counts by enemy id), `trade` (chain index),
`scores` (best per minigame) and `quests` (finished ids). `SAVE_VERSION`
goes to 3 and `save.migrate` fills the new fields for a version-2 file, so
a milestone-4 save walks straight into milestone 5.

### 4.3 Rings
Two ring slots, worn from the item page. A ring is passive and additive:
damage, defence, walking speed, bomb and arrow caps, shop prices, drop luck.
`eldermoor/rings.py` turns the worn list into one `RingBonus` the rest of
the game asks instead of reading the list itself.

### 4.4 Forty hearts, forty shells
Four pieces make a container, so forty pieces are ten hearts on top of the
three you start with and the eight from the temples — exactly the twenty the
HUD draws. Shells are hidden on screens, under bushes and in the six caves;
the shell hunter pays out at 5, 10, 20, 30 and 40. `tools/validate_data.py`
counts both sets, proves each one is reachable with the items of its region,
and fails if a piece or a shell is placed twice.

### 4.5 Six caves
Bramble Grotto, Tidewrack Cave, Cinder Vent, Tarn Hollow, Glass Burrow and
the Mist Warren: 9 to 16 rooms each on map sheets, one mini-boss, one prize
(a ring, a bottle, a quiver or a heart container) and no Flame, so none of
them is on the critical path. `tools/plan_dungeon.py` lays them out and the
same completability proof covers them.

### 4.6 People
The trading chain is ten steps long and runs through every region. The three
minigames are a shooting gallery, a dig patch and a bomb run; each keeps a
best score in the save and pays a shell the first time it is beaten.
Figurines are won and bought, furniture is bought and placed in Wren's
house, and the bestiary fills itself in as things die.

### 4.7 The collection screens
The pause menu grows a **collections** page with four tabs (shells and
pieces, figurines, furniture, bestiary) and the quest page becomes a real
log: open quests with their hints, finished ones ticked.
`state.completion()` counts the lot — flames, hearts, pieces, shells, items,
rings, figurines, furniture, bestiary entries and quests — because the
endings and the post-game read that one number.


--------------------------------------------------------------------------
## 5. Milestone 6 — after the credits

The post-game is three things, and none of them is new content for its own
sake: the Temple of Mists is the hardest dungeon, the Boss Rush is the whole
game's combat with no walking, and the Master Quest is the whole game again
with the gloves off.

The Temple of Mists is 25 rooms with four wardens in it, gated by the
`cleared` flag so its door does not exist on a file that has not finished.
It has keys and a Great Key but no Flame, because the Flames are over.

The Boss Rush is a single walled room and a counter: `data/bossrush.json`
holds the running order and the prize table, `eldermoor/postgame.py` spawns
the next boss when the last one falls, heals a little every other round, and
pays out whatever round was reached. Its best round is a minigame score, so
it shows up on the same screen as the rest of them.

The Master Quest asks the state three questions - how much does this hit
for, how much life does this have, which drop table does this roll - and
answers them differently on a file with the `master` flag. Nothing else in
the engine knows it exists.


--------------------------------------------------------------------------
## 6. Milestone 7 — the second lamplighter

`Input` keeps three sets of button states - keyboard, gamepad buttons and
gamepad stick - and merged them into one. Co-op only needed a view onto one
of them: `Input.view("keyboard")` and `Input.view("gamepad")` are the two
players, `Input.view("both")` is one-player, and `PlayerInput` does the edge
detection per device so a single frame can hold two directions.

Everything else followed from one question: who is this creature thinking
about? `World.nearest_hero` answers it, and the AI, the projectiles, the
contact damage and the cloak all ask. `World.touching_hero` is the same
question for pickups, switches and rewards. Those two functions are the
whole of co-op's effect on the rest of the engine; `eldermoor/players.py`
holds the joining and leaving.

Shared: hearts, keys, embers, items, flags, the save. Separate: the three
item slots, which is what PROMPT.md asks for and what makes a second player
useful rather than decorative.


--------------------------------------------------------------------------
## 7. Milestone 8 — the pass over everything

Three kinds of work, and two of them produced findings rather than features.

**Juice** is `eldermoor/juice.py`: sparks, dust, three frames of hit-stop and
the item-get fanfare. All of it hangs off existing call sites - take_damage,
the shield block, the roll, give_item - so there is no new system to keep in
step with the old ones.

**The palette check** (`tools/check_palette.py`) simulates the three
dichromacies. It is strict about the colours the interface is drawn in and
advisory about the rest, because a 32-colour palette cannot be fully
distinct to a dichromat and pretending otherwise would mean shipping greys.
It found four real problems; red, sea, mist and gold moved to fix them.

**The balance pass** is `--balance` on the sim. Every creature carries a
tier; the check asks how many swings it takes to kill and how many touches
it takes to die, against the hearts and sword a player of that tier has.
It found the first temple's mini-boss and boss killing a three-heart
lamplighter in three touches - the thing the bot's death count had been
saying for two milestones - and halving their damage took the bot's deaths
in temple one from 22 to 4.

**The length estimate** is now a projection with its workings shown: the bot
measures an overworld screen and a dungeon room over the productive part of
its run, and the rest is content counted out of `data/` at stated costs.
51 hours for the main line, 102 to 100 %.


--------------------------------------------------------------------------
## 8. The definition of done, line by line

PROMPT.md ends with a list. Here is each line with what backs it, measured
rather than asserted, and what is not backed.

| Asked for | Built | Checked by |
| --- | --- | --- |
| runs from `python main.py` | yes | `pytest`, and played headless |
| runs from the PyInstaller build | yes, on Linux | the build was run and the binary played |
| Linux, Windows, macOS | code and scripts for all three; **run and verified on Linux only** | — |
| windowed or fullscreen | yes | `tests/test_hud_app.py` |
| keyboard or gamepad | yes | `tests/test_input.py`, `tests/test_coop.py` |
| 256-screen overworld | 256 | `tools/validate_data.py` |
| 8 temples + 6 optional + post-game | 9 temples (the eighth Flame opens a ninth), 6 caves, the Temple of Mists | `tools/validate_data.py` |
| ≥ 24 bosses | 28 | `tests/test_enemies.py` |
| ≥ 60 enemies | 61 kinds | `tests/test_enemies.py`, which also proves each is placed |
| ≥ 120 items/collectibles | 168 (40 items, 40 heart pieces, 40 shells, 12 rings, 24 figurines, 12 furniture) | `tools/validate_data.py` |
| 25+ puzzle types | 26, listed below | the rooms that use them load and validate |
| 40 heart pieces | 40 | `tools/validate_data.py` |
| trading sequence | 10 steps | `tests/test_side_content.py` |
| minigames | 3 | `tests/test_side_content.py` |
| 2 endings | 2, chosen at 95 % | `tests/test_relics.py` |
| Master Quest | yes | `tests/test_postgame.py` |
| Boss Rush | 22 rounds | `tests/test_postgame.py` |
| co-op | yes | `tests/test_coop.py` |
| only the 12 buttons | yes | `tests/test_input.py` |
| ≥ 90 h to 100 % | 106 h projected (53 h main line) | `tools/sim_playthrough.py`, workings printed |
| all tests green | 230 | `pytest` |
| data validation green | 0 problems | `tools/validate_data.py` |
| README steps verified | yes | run from a clean virtual environment |

The one honest gap: the game has only ever been run on Linux. Nothing in it
is platform-specific - pygame-ce, pathlib, and a config directory chosen per
platform - and `run.bat` and the macOS path in the README are written from
the same shape as the Linux one, but written is not run.

### The 26 puzzle types
Cut grass; lift and throw rocks and pots; smash pots; bomb cracked walls;
burn torches with the Lantern; light several torches at once; floor
switches, held and latched; crystals shot or struck; push blocks; heavy
blocks that wait for the Gauntlet; pits crossed with the Feather; pits
crossed by hookshot; water crossed with the Fins; lava walked with the
Cinderstep Boots; ice walls melted; ice floors that carry you; hookshot
posts; eyes shot with the Bow; small-key doors; the Great Key door; doors
that open when a room is cleared; doors that open on a puzzle; one-way
ledges; dark rooms lit by the Lantern; sentinels blinded by the Mirror
Cloak; and counted sets of things to find - five pots, nine frogs, three
sheep - that open a quest rather than a door.
