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


## 0.4.0 — Milestone 4: Temples 5 to 8, the Great Lantern, the endings

### Relics
- **Fins** (Drowned Hollow) — deep water becomes swimmable. Wren swims at
  72 % of his walking speed and cannot swing a sword while he does it.
- **Cinderstep Boots** (The Kiln) — lava is walkable and no longer bites,
  and they melt an ice wall out of a doorway.
- **Mirror Cloak** (The Long Mirror) — hold its button and anything that
  hunts by sight loses Wren entirely; reflectable shots come straight back
  at whoever fired them. The cloak costs 20 % of his speed.
- **Titan Gauntlet** (The Giant's Gate) — the heavy blocks, painted into
  the world since milestone 3, finally move.
- **Whistle of Winds** (also The Giant's Gate) — opens the warp list
  wherever you stand, as long as one lantern is lit somewhere.

### Temples
- **Drowned Hollow** (Tidewrack, 36 rooms) — the Fins; Weedjaw and the
  Drowned King. The flooded halls are crossed by swimming, not by draining.
- **The Kiln** (Cinderwaste, 36 rooms) — the Cinderstep Boots; Slagjaw and
  the Kiln Maw. Lava rivers cut the floor in two until the boots arrive.
- **The Long Mirror** (Hollow Tarn, 36 rooms) — the Mirror Cloak; Frostjaw
  and the Glass King. Sentinels watch the only road; ice walls bar the rest.
- **The Giant's Gate** (Mistlands, 36 rooms) — the Titan Gauntlet and the
  Whistle of Winds; Stonejaw and the Titan Maw.
- **The Great Lantern** (16 rooms) — the final temple. Its door has eight
  sockets and no handle: it opens only once all eight Flames burn. Mistjaw
  guards the stair and **The Quiet** waits at the top.
- Five new boss pairs (36 new boss frames from `tools/sketch_bosses.py`),
  and all nine dungeons proved completable by `tools/validate_data.py`.

### Endings
- Two endings: the short goodbye, and the long one for a run at 95 %
  completion or better, both followed by a credits crawl
  (`eldermoor/ending.py`, the `ending` script action, a new `credits`
  track and `great_lantern` for the final temple).
- Finishing the game banks the run: the `cleared` and `ending` flags are
  saved before the credits roll, and the file select comes back after.

### Engine and tools
- Screens are joined wherever solid rock is not in the doorway: water,
  lava and pits in a doorway are gates for the right relic, not walls
  (`tilemap.SEALED`), which is what lets a flooded or burning hall be laid
  out as one continuous map sheet.
- Triggers take `if_flag` / `unless_flag`; the `ending` action hands the
  screen to the credits; an `t_ice` tile sprite replaces the stand-in.
- 562 rooms, 24 enemy kinds, 143 tests.


## 0.5.0 — Milestone 5: everything else in the kingdom

### Rings
- Twelve rings, two worn at a time, summed into one bonus the engine asks
  for: sword damage, defence (never down to nothing), walking speed, bomb
  and quiver room, shop prices, drop luck, ember handfuls, roll cooldown,
  reflected shots, grip on ice and slow mending.
- Ice carries Wren now — a new puzzle floor — and the Ring of Grip is what
  takes it back.

### Thirty side quests
- `data/quests/quests.json`: thirty givers, each with a condition, a
  payment and four lines (ask, wait, thanks, and what they say years
  later). `eldermoor/quests.py` is the only code that knows what a quest is.
- The world half is the new `token` object: poke the cat on the roof, or
  all five cracked pots, or all nine lantern frogs, and the flag a quest
  waits on goes up. Thirty-three of them are placed.
- Twelve quest items sit in chests across the kingdom; the quest log on the
  pause screen lists what is open, with a hint, and what is finished.

### Six optional caves
- Bramble Grotto, Tidewrack Cave, Cinder Vent, Tarn Hollow, Glass Burrow
  and the Mist Warren: 9 to 16 rooms, a mini-boss each, a ring, a heart
  piece and a shell. None of them is on the critical path, and the
  completability proof knows an optional cave has no keys, map or Flame.

### Things to find
- Forty heart pieces and forty seashells, counted and proved reachable by
  `tools/validate_data.py`, which also refuses two prizes that share a flag.
- Twelve rings, twenty-four figurines, twelve pieces of furniture — and the
  validator fails if anything in those tables has nobody who gives it out.
- The furniture you own stands in Wren's house, one piece per spot.

### People and games
- A ten-step trading chain across every region, ending in the Ring of Haste.
- Three minigames: the shooting gallery, the dig patch and the bells. Each
  keeps a best score and pays figurines, embers, a heart piece or a shell
  the first time a score is reached.
- Two new shops: the Little Gallery (figurines, three of them for
  collectors with a full enough bestiary) and Second-Hand Everything
  (furniture, and one ring).

### Screens
- The pause menu grows RINGS and FINDS pages; FINDS has four tabs —
  counters, figurines, furniture and the bestiary, which fills itself in as
  things die. `completion()` counts flames, hearts, pieces, shells, items,
  rings, figurines, furniture, bestiary entries and quests.

### Engine
- Twelve more creatures drawn by `tools/sketch_critters.py`, each with its
  own state machine, and six cave mini-bosses.
- Save version 3: rings, worn rings, figurines, furniture, where furniture
  stands, the bestiary, finished quests, the trading step and best scores.
  A milestone-4 file migrates straight into it.
- 641 rooms, 42 enemy kinds, 173 tests.


## 0.6.0 — Milestone 6: the post-game

### The Temple of Mists
- Twenty-five rooms in the Mistlands, behind a door that is not there until
  the kingdom has been saved once. Four keys, a Great Key, and no Flame:
  there is nothing left to light.
- Four wardens: **Veilmaw**, which wears the mist and takes it off to hit
  you; **Duskmaw**; **the Mere Warden**; and behind the Quiet Door, **the
  Pale Warden**, which is only visible by lantern light. Each has three
  phases, and the last one leaves a whole heart.
- **Mistjaw** finally exists: the mini-boss on the Great Lantern's stair,
  which the milestone-4 notes promised and the data did not have.

### The Boss Rush
- The Standing Ring: every boss in the game, one after another, a breather
  every other round, and prizes for getting six, twelve, eighteen and all
  twenty-two rounds in. The best round reached is kept in the save.
- Its host turns up in the village once the game has been finished, and
  asks before it starts, because it does not let you out again.

### The Master Quest
- A new file can be started as a Master Quest once an ending has rolled.
  Everything in the kingdom hits twice as hard, has half again as much
  life, and gives up far fewer hearts.
- It is one flag on the save and three small questions the engine asks
  (`eldermoor/postgame.py`), so every room, enemy and drop table in the
  game is harder without a second copy of any of them.
- 667 rooms, 47 enemy kinds, 190 tests.


## 0.7.0 — Milestone 7: two lamplighters

- **Local co-op.** Turn on *Two players* in the settings page and a second
  lamplighter drops in beside the first; turn it off and they step back out.
  Player one reads the keyboard, player two the gamepad, so the same frame
  can hold two different directions (`Input.view`, `PlayerInput`).
- **Own item slots.** Player two starts with a copy of player one's three
  items and keeps their own set after that; the items page switches between
  the two with Select, and the HUD halves its slot boxes and stacks them,
  player one over player two.
- **One heart row, two bodies.** Both lamplighters draw on the same hearts,
  keys and embers, because it is one save and one kingdom. Either of them
  can be hit, fall in a pit, pick something up, stand on a floor switch or
  take a reward.
- **Creatures think about the nearer one.** Chasing, orbiting, shooting,
  telegraphing and the Mirror Cloak all ask which lamplighter a creature is
  closest to, so a second player splits a boss's attention rather than
  standing in a blind spot.
- **Both carry a light.** A dark room now has one circle of lantern light
  per lamplighter.
- **Screens stay shared.** Player one walks the party from screen to screen;
  player two is carried along to the same doorway, and cannot drag the
  screen along by standing on an edge.
- Save version 3 gained `slots2`; a milestone-6 file migrates into it with
  empty second slots.
- 207 tests.


## 0.8.0 — Milestone 8: polish, balance and getting out of the way

### Juice
- Sparks fly out of every landed blow, a different colour when armour turns
  one aside, and the whole room holds still for three frames on a hit, which
  is what makes a sword connect rather than pass through (`eldermoor/juice.py`).
- Dust under a roll, sparks off a shield block, a gold burst when something
  dies.
- **Item-get fanfare**: a found item rises over Wren's head in a ring of
  light with its name underneath while the room waits, and then the usual
  line appears.
- *Screen shake* in the settings is now actually honoured.

### The companion in the lantern
- Stand still for fourteen seconds and the companion offers the one hint
  that fits where the story has got to - the sword, then the village, then
  each temple in turn, then the Mist Door - once per room, in the ordinary
  dialogue box. No pop-ups, no tutorial screens; `data/hints.json` is the
  whole tutorial and *Hint companion* in the settings turns her off.

### Accessibility
- `tools/check_palette.py` simulates protanopia, deuteranopia and
  tritanopia. The colours the interface is drawn in must stay apart under
  all three - by brightness where hue collapses - and the palette must span
  a decent brightness range. It found three meaning-carrying pairs too close
  together (a full heart against moss, the red and blue barriers, a chosen
  menu row against an unchosen one) and lime against gold under protanopia;
  red, sea, mist and gold moved, and the sweep over the remaining colours
  now prints advice rather than failing, because thirty-two colours cannot
  all be distinct to a dichromat and two shades of green looking alike is a
  picture, not a puzzle.

### The balance pass
- `tools/sim_playthrough.py --balance` checks every creature against the
  player it is written for: each has a **tier** in its data saying roughly
  when it is met, and the check asks how many swings it takes to kill and
  how many touches it takes to die. It found the first temple's mini-boss
  and boss both killing a three-heart lamplighter in three touches, which
  is what the bot's death count had been saying all along; both now hit for
  half a heart, and the bot's deaths in temple one went from 22 to 4.
- The sim measures the cost of a room over the part of its run that was
  going somewhere, and separately for an overworld screen and a dungeon
  room, then projects the whole game from the content counted out of
  `data/`. Every line of the projection is printed:

      overworld 2.1 h, dungeons 34.5 h, bosses 2.8 h, heart pieces 2.0 h,
      seashells 2.0 h, side quests 4.0 h, minigames 0.6 h, trading 0.3 h,
      boss rush 0.5 h, master quest 51.2 h

  which comes to **51 hours for the main line and 102 hours to 100 %**,
  against PROMPT.md's 90-hour target.
- 221 tests.


## 0.9.0 — Milestone 9: packaging

- **README.md** with exact steps for Fedora, Ubuntu, Windows 11 and macOS,
  the button table, where saves live, how to build a release and what each
  tool proves. The by-hand install was run from a clean virtual environment
  to check it: pip install, build the assets, synthesise the audio, 227
  tests green, the game runs headless.
- **run.bat** for Windows, matching `run.sh`: make the venv, install,
  build the sprite sheets and the sounds, start the game. `run.sh` now
  builds the audio too, so a first run on a fresh clone is silent-free.
- **tools/build_release.py**: a single-folder (or one-file) PyInstaller
  build with `assets/`, `data/` and `input_map.json` bundled, the generated
  assets rebuilt first so a release cannot ship a stale sheet, a `run`
  script beside the executable and the `.desktop` file and icon on Linux.
  `--check` prints what it would do without building. The build was run:
  `dist/LanternOfEldermoor/` plays headless.
- **tools/make_icon.py** composes the application icon - Wren's lantern -
  from a pixel-map in `assets_src/icons/app.txt`, scaled to every size the
  three platforms want, plus `.ico` and `.icns` where Pillow is available.
- **eldermoor.desktop** so it turns up in a Linux app menu.
- A frozen build finds its data: `eldermoor.config` reads `sys._MEIPASS`
  when PyInstaller set it and the repository root otherwise.
- 227 tests.


## 0.9.1 — The last of the bestiary

Checking the definition of done line by line found one count short: sixty
creatures were asked for and forty-seven existed.

- Fourteen more, drawn by `tools/sketch_critters.py` from three new shapes
  (a spiked crown, a tilting kite, a compressing coil): Bog Wisp, Saltling,
  Flintback, Gloamfly, Chalk Crab, Barbthorn, Ash Grub, Tidecoil, Duneskip,
  Slagling, Frostnip, Hollow Pup, Lantern Moth and Stillshade. **61 kinds**
  now, 28 of them bosses.
- Every region's day and night wildlife was rewritten around them, and the
  caves, the later temples and the Temple of Mists got their own lists, so
  the new creatures are met rather than merely defined.
- Three new tests hold the line: there are at least sixty kinds and at
  least twenty-four bosses; every one has a sprite, a name and a bestiary
  line; and **every one is actually placed somewhere** - which is what
  caught the Flintback, defined and drawn and living nowhere.
- 230 tests. The length estimate, re-measured: 53 hours for the main line,
  **106 to 100 %**.
