# CHANGELOG

## 0.1.0 — Milestone 1: engine core

- pygame-ce window, 320×240 canvas with nearest-neighbour integer scaling
  and black bars (`--scale 2..6`, `--fullscreen`, `--stretch`, F11 / Alt+Enter).
- Fixed 60 Hz logic with an accumulator; render rate independent.
- 2-row HUD: hearts (full/half/empty, up to 20), embers, keys, B/X/Y item
  slots with 8×8 icons.
- Input: 12 logical buttons from keyboard and SDL GameController with
  hot-plug, `input_map.json`, last-device tracking, remap API.
- Asset pipeline `tools/build_assets.py`: text pixel-maps → PNG sheets +
  JSON atlases, 32-colour named palette, region palette swaps for tiles.
- 8×8 and 6×8 bitmap fonts (ASCII 32–126, ÄÖÜäöüß, hearts, arrows,
  cursor), tinted and outlined text.
- Meadow tileset (11 tiles) and two rooms (`meadow_00`, `meadow_01`) as
  JSON with legend strings, exits and spawn points.
- Wren: 8-direction walking, 4 facings, 3-frame walk, 2-frame idle,
  3-frame sword swing with separate sword-arc sprites and hitbox,
  axis-separated tile collision.
- 12-frame flip-scroll between rooms.
- F1 debug overlay (fps, frame, room, hero, entities, scroll, input device,
  hearts) with hitboxes.
- `--headless --frames N` mode; pytest suite (37 tests) runs under
  `SDL_VIDEODRIVER=dummy`.
- `run.sh`, `requirements.txt`, `pyproject.toml` (ruff + pytest config),
  DESIGN.md, DECISIONS.md.

## 0.2.0 — Milestone 2: vertical slice

A playable slice with one of everything: Lamplight Village, six meadow
screens and the whole 35-room Ember Temple, from its door to the Flame.

### Systems
- `GameState` holds everything a save contains: items, B/X/Y slots, global
  flags, per-dungeon keys/map/compass/Great Key/Flame, play-time, deaths and
  a completion percentage.
- Three save slots in the OS config dir (`$ELDERMOOR_CONFIG_DIR` overrides),
  written temp-then-rename with a `.bak` of the last good file, a versioned
  schema with migrations, and a crash slot written by a top-level handler
  that also appends to `crash.log`.
- Settings file: volumes, text speed, screen shake, low-health beep, hints,
  stretch — all editable from the pause menu and saved on close.
- Audio: `tools/build_audio.py` synthesises 63 sound effects and 8 music
  tracks from square/triangle/saw/sine/noise oscillators with ADSR, driven by
  a `.song` tracker format with `C4:4` hold shorthand. `eldermoor/audio.py`
  degrades to silence when there is no device.
- `Entity.update(world)`: the world is the one context object. The hero moved
  into `hero.py` and gained the shield (blocks from the facing side), the
  dodge-roll with opening i-frames, the hold-and-release spin attack, mercy
  frames, knockback and item use.
- Data-defined enemy state machines (`data/enemies/*.json` → `ai.py`): ten
  movement modes, distance transitions, and telegraphs that validation keeps
  at 20+ frames. Six enemy kinds, one mini-boss and one boss with phases and
  a weakness that needs the temple item.
- Room objects: chests, signs, NPCs with flag-driven lines, locked/barred/
  great doors, torches, floor switches, crystal switches, pushable blocks,
  stairs and rewards — each remembering itself in a global flag.
- Room scripting: `triggers` turn `enter`, `all_enemies_dead`, `switch`,
  `torches_lit`, `crystal`, `block_moved`, `chest_opened` and `boss_dead`
  into `open`, `spawn`, `reveal`, `say`, `give`, `jingle`, `shake`,
  `stun_boss` and `warp`. Objects a one-shot trigger created come back when
  you re-enter the room.
- Tile interactions: bushes and tall grass cut, pots smash, webs burn — all
  data-driven, all rolling a drop table, all transient so the room restocks.
- Dialogue box with word wrap, pagination and a typewriter at the chosen
  speed; `data/text/en.json` holds every line. Shop, pause menu (items,
  quest log, dungeon map, options, save) and a three-slot file select.
- Dark rooms, lit by the Lantern or by lighting the room's torch.
- Death follows Zelda rules: back to the temple door or the last overworld
  screen, hearts refilled, everything found still in the bag.

### Content
- 47 rooms: village centre, east row, north gate, pond, two interiors, six
  meadow screens, and the Ember Temple's 35 rooms over two floors.
- The temple's key graph: four small keys, four small-key doors, a Great Key
  behind the last of them, a mini-boss that drops the Lantern, webs and a
  dark room that need it, and the Ashen Maw, which only opens when all four
  arena torches are lit.
- 371 hand-authored pixel-map blocks: item icons, pickups, objects, six
  enemies, six villagers, two bosses, village and temple tilesets.

### Tools
- `tools/validate_data.py`: structure, references, telegraphs, text fitting,
  doorway alignment and a dungeon flood fill that proves completability.
- `tools/sim_playthrough.py`: a breadth-first bot that plays the real game
  and reports what it actually achieved.
- `tools/check_art.py`, `tools/sketch_bosses.py`.

### Tests
113 pytest cases, headless, `ruff` clean.

## 0.3.0 — Milestone 3: the kingdom, and Temples 2 to 4

### The overworld
- All 256 screens, painted as one continuous canvas
  (`data/overworld/eldermoor.map`, 16 x 16 screens of 20 x 13 tiles) and
  sliced into rooms by `eldermoor/mapsheet.py`. Exits are derived from both
  sides of an edge being walkable, so a one-way exit or a doorway that does
  not line up cannot be written by accident.
- `tools/build_maps.py` stamps the hand-drawn blocks of
  `data/overworld/blocks.txt` onto the canvas following `layout.txt`; a
  layout entry may be `frame+motif` and the motifs lay over the frame.
- Nine region palettes: Lamplight meadows and village, Thornwood, Saltmarsh,
  Mount Cinder, the Frozen Tarn, the Sunken Fen, the Hollow Desert and the
  Mistlands, each with its own creatures and its own look.
- An eight-minute day/night clock. Night repaints the world, changes the
  music and brings different things out; it stops indoors and underground.
- Eight warp lanterns, one per region: touch one to light it, then travel
  between the lit ones from the Select-screen map.
- The village, the four temple doors, the signs and the NPCs are placed by
  hand; the wildlife of a screen comes from its region, seeded by the room
  id so the kingdom looks the same every time you walk back into it.

### Temples
- `tools/sketch_rooms.py` emits the sixteen room frames;
  `tools/plan_dungeon.py` turns a hand-drawn connection map into a layout
  and refuses to write one that leaves a room unreachable.
- **Bramble Hollow** (Thornwood, 36 rooms) — the **Power Bracelet**: lift
  rocks and pots, throw them. A thrown rock is what opens the Hollow King.
- **Tidewrack** (Saltmarsh, 36 rooms) — **Bombs** in the first half, the
  **Hookshot** from Brinejaw. Bombs open cracked walls; the chain crosses
  the washed-out floor.
- **The Long Glass** (Hollow Desert, 36 rooms) — the **Bow** from Sandjaw:
  arrows reach crystals, eyes and whatever will not come down.
- Each has a mini-boss, a boss with phases, a map, a compass, four small
  keys, a Great Key, a heart container and a Flame, and each is proved
  completable by `tools/validate_data.py`.

### Engine
- Lift, carry and throw; bombs with a fuse that does not care whose boots
  are nearby; a six-tile hookshot that anchors on pillars and drags Wren
  over pits; arrows that spend from a quiver.
- HUD counters for bombs and arrows; tiles can be hookshot anchors.
- 402 rooms, 14 enemy kinds, 125 tests.
