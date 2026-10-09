# PROMPT: Build "LANTERN OF ELDERMOOR" — a 100-hour Zelda-style pixel-art adventure for my laptop

You are a senior game developer and pixel artist. Build a complete, polished,
ORIGINAL top-down action-adventure game in the style of the classic 2D Zelda
games (A Link to the Past, Link's Awakening, Oracle of Ages/Seasons, The
Minish Cap) that runs on my laptop. It must be a
game I will sink 100 hours into: a big hand-made overworld, many themed
dungeons each built around a new item, puzzle rooms, keys, bosses that are
beaten with that dungeon's item, heart pieces, secrets, side quests and a
post-game. "Small" refers to footprint (one repo, modest assets, modest
code), NOT scope.

IP rule: no Nintendo names, characters, logos, music, maps or sprites. The
STRUCTURE and FEEL are the reference; every name, story, sprite and tune is
original. Do not use the words Zelda, Link, Hyrule, Triforce, rupee, Ganon,
Master Sword, Hylian, Ocarina in the game or its data.

Work autonomously. Do not ask me questions; make reasonable decisions, record
them in DECISIONS.md, and keep going until everything in "Definition of done"
is true.

--------------------------------------------------------------------------
## 1. Target platform

- My laptop: Linux (Fedora), normal laptop screen (assume 1920×1080 or
  similar, 16:9), keyboard, trackpad, optional USB/Bluetooth gamepad. It
  must also run unchanged on Windows and macOS.
- No memory, disk, CPU or frame-time requirements. Use whatever the game
  needs.
- Pixel-art look: render the game to a small internal canvas of 320×240
  (20×15 tiles of 16 px — a Zelda-style single screen with a 2-row HUD on
  top and a 20×13 play area) and scale it up with nearest-neighbour, integer
  scaling by default (×4 on 1080p), with black bars on the sides. Options:
  windowed/fullscreen (F11 / Alt+Enter), scale 2–6, "stretch to fill" off by
  default.
- Text must be readable: 8×8 pixel font for dialogue, 6×8 only in dense
  menus, outlined text.
- Controls, keyboard default (fully remappable in the settings menu):
  Arrows / WASD = move, Z or J = A (sword), X or K = B item, C or L = X item,
  V or ; = Y item, Shift = shield (L), Space = dodge-roll (R),
  Enter / Esc = Start (pause/inventory), Tab = Select (map), F11 =
  fullscreen, F1 = debug overlay.
- Gamepad (SDL GameController, any Xbox/PlayStation/Switch-style pad,
  hot-plug): D-pad or left stick = move, A = sword, B/X/Y = item slots,
  LB = shield, RB = roll, Start = pause, Back = map. Show the matching
  button glyphs in the UI for whichever device was used last.
- Audio: stereo is fine.

--------------------------------------------------------------------------
## 2. Technology (decided — do not substitute)

- Python 3.11+ with **pygame-ce** (SDL2). Other Python packages are fine if
  they help. Keep it installable with a single `pip install -r
  requirements.txt`.
- Rendering: one 320×240 `Surface`, scaled to the window by SDL
  (`pygame.SCALED` or a manual integer blit), vsync on.
- Fixed timestep: logic at 60 Hz with an accumulator so game speed is
  independent of the render rate.
- Input: keyboard and SDL GameController via pygame, mapping stored in
  `input_map.json`, remappable in-game.
- Flags: `--scale N`, `--fullscreen`, `--headless` (for tests), `--save SLOT`.
- Data-driven: rooms, overworld, dungeons, enemies, items, dialogue, quests,
  puzzles, bosses are JSON/TOML in `data/`. Code is the engine, data is the
  game.

--------------------------------------------------------------------------
## 3. Assets — you make them, by code

I cannot draw. All art and sound must be generated from scripts in the repo.

- Sprites authored as text pixel-maps in `assets_src/` (one character per
  pixel, keyed to a palette index); `tools/build_assets.py` compiles them to
  PNG sheets. Every sprite is reviewable and editable as text.
- One fixed 32-colour palette (define it, name every colour, give hex).
  Region palettes are swaps of the same sprites at build time.
- Tiles 16×16. Hero 16×16 (16×24 with hat/weapon overlay). Enemies 16×16 or
  32×32. Bosses 32×32 to 64×64 assembled from 16×16 parts. Item icons 8×8,
  world pickups 16×16.
- Animation: 3-frame walk ×4 directions, 3-frame sword swing with a separate
  sword-arc sprite, 2-frame idle, hit-flash by palette swap, 4-frame death
  puff shared by all small enemies.
- Fonts: 8×8 and 6×8 bitmap, ASCII 32–126 plus ÄÖÜäöüß, hearts, arrows.
- Audio: `tools/build_audio.py` synthesises everything to 44 100 Hz stereo
  from square/triangle/noise/saw oscillators with ADSR, plus a tiny tracker
  format (`.song` JSON). Minimum: 16 music tracks (title, overworld day,
  overworld night, village, each of 8 dungeon themes, mini-boss, boss, final
  boss, credits), 50 SFX including the classic set: sword swing, hit, enemy
  die, heart pickup, key pickup, door unlock, secret-found jingle, item-get
  fanfare, puzzle-solved chime, low-health beep.

--------------------------------------------------------------------------
## 4. The game: LANTERN OF ELDERMOOR (design brief)

Genre: top-down 2D action-adventure, single-screen rooms with screen-to-screen
scrolling (flip-scroll on the overworld like Link's Awakening, smooth
scroll in large dungeon rooms). 8-directional walking, 4-directional sword,
item-gated exploration, hearts, dungeons with maps/compasses/keys/boss keys.

Pitch: The island kingdom of Eldermoor is lit by the Great Lantern. Its
eight flames have been stolen and hidden in eight temples; without them the
mists are swallowing the land. You are Wren, a lamplighter's apprentice,
sent to reclaim the flames. Original setting, original names.

### 4.1 Play-time targets (design to these, then measure)
- Main story (8 temples + final): ~30 h.
- Side quests, trading sequence, optional dungeons, all heart pieces,
  all secrets, full map: +40 h.
- Post-game (Temple of Mists, the 3 shrines, boss rush, master quest): +30 h.
- Total to 100 %: ~100 h. Track play-time and completion % in the save.

### 4.2 Overworld
- One contiguous hand-made overworld of 16×16 screens (256 screens) in 8
  regions: Lamplight Village & meadows (start), Thornwood, Saltmarsh &
  the coast, Mount Cinder, the Frozen Tarn, the Sunken Fen, the Hollow
  Desert, and the Mistlands (late). Each has its own palette, tileset,
  music, enemies and secrets.
- Overworld progression is item-gated the Zelda way: cut bushes (sword),
  lift rocks (Power Bracelet), bomb cracked walls, hookshot across gaps,
  swim (Fins), cross lava (Fire Boots), light dark rooms (Lantern), move
  heavy blocks (Titan Gauntlet), etc. Every region is first seen before it
  is enterable so the player wants the item.
- Secrets: ≥ 150 hidden things on the overworld: 40 heart pieces (4 = 1
  heart container), caves behind bombable walls, hidden grottos under rocks,
  secret seashells (collect 40 for a sword upgrade), treasure chests with
  rupee-equivalent currency ("embers"), great fairies/fountains that upgrade
  bomb/arrow capacity, a trading sequence of 14 steps.
- Day/night (8 real minutes) changes some enemies and NPCs; a few secrets
  only exist at night.
- Warp system: 8 warp lanterns, one per region, lit when first found;
  later an Ocarina-like item (Whistle of Winds) to warp from anywhere.
- Lamplight Village: ~25 NPCs, shop, bomb shop, item-trading, house with
  furniture collection, a minigame hall (fishing, target shooting, dig-for-
  treasure, crane game), mail from NPCs as you progress.

### 4.3 Dungeons (minimum 8 main + 6 optional + 1 post-game)
Each MAIN temple follows the classic template, and each is ~2.5–4 h:
- 35–60 rooms on 1–3 floors with a distinct theme, tileset, music, gimmick.
- Collectibles: Map, Compass (shows chests + boss), small keys (count
  shown on HUD), Big Key, the Temple Item (new), a heart container after
  the boss, and the Flame.
- The Temple Item is introduced halfway, with the second half of the dungeon
  built around it, and the boss is weak to it. Items, one per temple:
  1. Lantern (light torches, burn webs, reveal dark rooms)
  2. Power Bracelet (lift rocks/pots, throw)
  3. Bombs (walls, floors, enemies) + Hookshot in the same temple's second half
  4. Bow (switches, eyes, flying enemies)
  5. Fins (swim, dive) 
  6. Fire Boots (lava, melt ice, dash)
  7. Mirror Cloak (reflect beams, become invisible to some enemies)
  8. Titan Gauntlet + Whistle of Winds
  Plus non-dungeon items: Shield → Mirror Shield, Sword ×3 tiers, Boomerang
  (from a side quest), Magic Rod (from the trading sequence), Bottles ×4,
  Feather (jump) early from the village.
- Puzzle types (≥ 25 distinct kinds, data-defined): block push (Sokoban-
  lite), torch lighting order, floor switches with blocks, timed doors,
  crystal switches that toggle blue/red barriers, eye statues that follow
  you, mirrors redirecting beams, conveyor belts, ice sliding, dark rooms,
  crumbling floors, falling to the floor below as a mechanic, minecart
  rails, water level changes, 2-floor puzzles.
- Each temple: 1 mini-boss (drops a key item or Hookshot etc.), 1 boss, 3
  secret rooms, 1 "Fairy fountain".
- OPTIONAL dungeons (6): shorter, harder, item-rewards (Bottles, capacity
  upgrades, Mirror Shield, sword tier, the Magic Rod's upgrade).
- POST-GAME: the Temple of Mists, a 40-floor gauntlet assembled from
  hand-made room prefabs (new order every run) ending in a true final boss;
  plus Boss Rush (all bosses back-to-back, timed) and Master Quest (all
  temples remixed: rooms rearranged, puzzles harder, enemies ×1.5).

### 4.4 Combat & health
- Hearts: start with 3, max 20 (8 from temples, 10 from 40 heart pieces,
  2 from post-game). Damage in half-hearts. Low-health beep (toggleable).
- Sword: 4-directional swing, spin attack on hold-and-release, sword beam at
  full health with the final sword. Shield blocks projectiles when held/
  facing. Dodge-roll on R with 8 i-frames and no stamina.
- No XP, no levels: ALL power comes from items, hearts, sword/shield tiers,
  tunics (defense), and capacity upgrades — exactly like Zelda.
- Enemy roster: ≥ 60 distinct enemy types with Zelda-style behaviours
  (bush-jumpers, spear throwers, bouncing slimes, shielded knights that must
  be hit from behind, bomb-droppers, wall-crawling eyes, laser statues,
  burrowers, ghosts only visible by Lantern, mimics, item-stealers that
  must be chased down). Every enemy has a readable telegraph ≥ 20 frames.
- Drops: hearts, embers, bombs, arrows, magic — tuned so the player is rarely
  completely out.

### 4.5 Bosses (minimum 24)
- 8 temple bosses, 8 mini-bosses, 6 optional-dungeon bosses, 1 three-phase
  final boss, 1 post-game true final boss, plus 4 extra bosses in the
  Mistlands that guard heart pieces/upgrades.
- Every boss: unique sprite (≥ 32×32), 2–3 phases with new attacks per phase,
  a vulnerability that uses the temple's item (hookshot the mask off, light
  the torches to stun it, bomb its open mouth, reflect its beam with the
  Mirror Cloak), an intro, a health bar with name, a victory fanfare, a
  heart container.
- Fair on a 3.2" screen: large telegraphs, no 1-frame reads, nothing comes
  from off-screen without an audio cue.
- Rematch any boss from the village minigame hall for a timed/no-hit medal.

### 4.6 Items & collectibles (≥ 120 distinct)
- Equipment items (above), Bottles with 8 bottle contents (fairy, potions,
  bugs, the trading sequence items), 3 tunics, 3 shields, 3 swords, 2 rings
  with 20 collectible rings (Oracle-style passive effects: +defense, less
  knockback, swim faster, magnet embers, etc.; wear 2), 4 trading chains,
  40 seashells, 40 heart pieces, 20 collectible figurines (crane game),
  12 furniture pieces, 8 maps/compasses/big keys per temple, quest items.
- Inventory: Zelda-style grid, assign any item to B/X/Y, equip rings,
  L/R to flip pages, Select-screen map with marker pins. Any common action
  in ≤ 3 button presses.
- Collection screens: item list with %, seashell/heart piece counters with
  region hints once an item is bought, figurine gallery, enemy bestiary.

### 4.7 Narrative
- ~40 story beats, 40+ named NPCs with dialogue that updates after each
  temple, a companion spirit in the lantern that gives hints (toggleable),
  2 endings (one for 100 %). Dialogue in a bottom box, 3 lines of 8×8, A to
  advance, B to fast-skip. All text in `data/text/en.json`.
- Side quests (≥ 30): lost pets, letters, ghost that wants its grave,
  fisherman's bet, the trading sequence, photo/figurine collection, the
  lighthouse rebuild, the night market, a cuckoo-chase, a haunted house.

### 4.8 Two-player (after single-player is done)
- Local co-op: player 2 on a gamepad (or player 1 keyboard + player 2
  gamepad): a second lamplighter with own item slots sharing the screen;
  camera clamps to keep both visible, P2 teleports to P1 on screen change.
  Drop-in/out.

--------------------------------------------------------------------------
## 5. Systems the engine must have

- Save: 3 slots, autosave on screen change and after bosses, manual save in
  pause menu, atomic writes (temp + rename), versioned schema with
  migrations, keep last good backup. Death = restart from the dungeon
  entrance / last village with items kept (Zelda rules, no item loss).
- Settings: music/SFX volume, screen-shake, window scale / fullscreen /
  stretch, keyboard and gamepad remap, text speed, low-health beep, hint
  companion on/off. Saved in the OS user-config dir
  (`~/.config/eldermoor/` on Linux, `%APPDATA%` on Windows, Application
  Support on macOS).
- Pause (Start): items grid, rings, quest log, collectibles, settings,
  save, quit. Select: overworld map + dungeon map (current floor, visited
  rooms, chests, boss once compass found). All D-pad + A/B + L/R only.
- Camera: screen-locked rooms; flip-scroll transitions (12 frames) on the
  overworld; smooth scroll in rooms larger than one screen.
- Collision: tile grid (solid, water, lava, pit, ice, ledge-jump-down,
  tall grass, bombable, liftable) + AABB for entities. Ledges can be
  jumped down, never up.
- Room scripting: rooms are JSON with triggers (enter, all-enemies-dead,
  switch-pressed, torch-lit-all, block-on-plate, timer) → actions (open
  door, spawn chest, play jingle, reveal stairs, set flag). Flags are global
  and saved so a solved room stays solved.
- Entity system with components (sprite, body, health, ai, interact, lift,
  burn, freeze) and data-defined AI state machines.
- Debug overlay (F1): entity count, room id, free-cam,
  god mode, give-item, warp-to-room, flag editor.

--------------------------------------------------------------------------
## 6. Running and packaging on the laptop

- `python main.py` after `pip install -r requirements.txt` in a venv is the
  primary way to run it. Provide `run.sh` (Linux/macOS) and `run.bat`
  (Windows) that create the venv, install, and launch.
- Also provide `tools/build_release.py` using PyInstaller to produce a
  single-folder release for Linux, Windows and macOS, with a generated icon.
- `.desktop` file for Linux so it appears in the app menu.
- README.md with exact steps for Fedora, Ubuntu, Windows 11 and macOS.

--------------------------------------------------------------------------
## 7. Repository layout

```
eldermoor/
  main.py                 # --scale N, --headless, --save SLOT
  eldermoor/              # engine + game, modules ≤ 600 lines
  data/                   # overworld/, dungeons/, rooms/, enemies/, items/,
                          # bosses/, quests/, puzzles/, text/, songs/
  assets_src/             # text pixel-maps, palettes, font sources
  assets/                 # generated PNG/WAV — committed, rebuilt by tools/
  tools/build_assets.py  tools/build_audio.py  tools/validate_data.py
  tools/sim_playthrough.py  tools/room_editor.py (optional, pygame-based)
  tests/                  # pytest, headless
  run.sh  run.bat  requirements.txt  tools/build_release.py
  README.md  DESIGN.md  DECISIONS.md  CHANGELOG.md
```

--------------------------------------------------------------------------
## 8. Process — milestones, each one playable

Deliver in order; each milestone ends with tests green and a CHANGELOG note:

1. Engine core: window, 320×240 surface with 2-row HUD (hearts, embers,
   keys, B/X/Y item icons), fixed timestep, input map, asset pipeline,
   fonts, one room, Wren walks + swings sword, screen flip-scroll between
   two rooms, debug overlay, headless mode, tests.
2. Vertical slice: the village, 6 overworld screens, 6 enemies, sword/
   shield/roll, hearts & drops, chests, bushes/rocks/pots, dialogue, shop,
   save/load, and Temple 1 complete (keys, map, compass, big key, Lantern,
   mini-boss, boss, heart container, flame).
3. Full overworld (256 screens) with all region tilesets, warp lanterns,
   day/night, all gate types placed; Temples 2–4 and their items.
4. Temples 5–8, final temple, final boss, endings.
5. All side content: 6 optional dungeons, 40 heart pieces, 40 seashells,
   rings, trading sequence, minigames, figurines, furniture, 30 side quests,
   bestiary, collection screens, completion %.
6. Post-game: Temple of Mists, Boss Rush, Master Quest, 4 Mistlands bosses.
7. Co-op.
8. Polish: juice, item-get fanfares, tutorialisation via NPCs not pop-ups,
   balance pass with `sim_playthrough.py`, accessibility (text speed,
   shake off, colour-blind-safe palette check, hint companion).
9. Packaging: run scripts, PyInstaller release builds, README, final full
   test run.

--------------------------------------------------------------------------
## 9. Quality bar

- `pytest`, headless: save round-trip + migration, collision, damage/
  half-heart maths, every room loads, every referenced
  asset exists, every door/key/big-key graph is solvable with the items
  available at that point (`tools/validate_data.py` must prove each temple
  is completable and that no required key can be wasted — fail CI
  otherwise), every heart piece/seashell/item reachable, every quest
  completable, every boss reachable, text fits its boxes, all 12 buttons
  mapped.
- `tools/sim_playthrough.py`: a bot walks the critical path headlessly and
  reports estimated hours per temple/region; the 100 h target is measured.
- No crash may lose progress: top-level exception handler autosaves to a
  crash slot and logs to `~/.config/eldermoor/crash.log`.
- Type hints, docstrings on public functions, no module > 600 lines, no
  function > 80 lines, `ruff` clean.

--------------------------------------------------------------------------
## 10. Definition of done

- Runs from `python main.py` (and the PyInstaller build) on Linux, Windows
  and macOS, windowed or fullscreen, keyboard or gamepad.
- 256-screen overworld, 8 temples + 6 optional + post-game temple, ≥ 24
  bosses, ≥ 60 enemies, ≥ 120 items/collectibles, 25+ puzzle types, 40
  heart pieces, trading sequence, minigames, 2 endings, Master Quest, Boss
  Rush, co-op, all playable with only the 12 buttons.
- `tools/sim_playthrough.py` estimates ≥ 90 h to 100 %.
- All tests green, data validation green, README install steps verified.

Start with milestone 1. For every milestone, first write a one-page plan
into DESIGN.md, then implement, then test, then write the CHANGELOG entry.
