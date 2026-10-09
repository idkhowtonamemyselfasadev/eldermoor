# DECISIONS

Decisions made without asking, with the reason. Newest at the bottom.

## Milestone 1

1. **Python 3.11+ syntax, tested on 3.14.** `StrEnum`, `X | None`, dataclasses.
   No dependency beyond pygame-ce and pytest; ruff is a dev tool, not a
   requirement.
2. **Coordinates.** Entities live in play-area pixels (0..320 × 0..208); the
   HUD height (`PLAY_Y = 32`) is added only when drawing. Rooms, collision and
   tests never see the HUD offset.
3. **Side sprites are authored facing right and mirrored at load** for
   left. Halves the hand-drawn sprite count; the asset pipeline stays a plain
   text → PNG compiler with no flip directive. Sword offsets for "left" are
   the negated "right" offsets.
4. **Sword arc is five sprites, not twelve.** `sword_h`, `sword_v_up`,
   `sword_v_down`, `sword_diag_ur`, `sword_diag_dr` are composed per facing
   and frame in `entities.SWORD_FRAMES`. The hero has three genuine swing
   poses per facing. The hitbox is active on frames 1–2 only (frame 0 is the
   wind-up); movement is locked for the whole 12-frame swing.
5. **Room tile layers are legend strings** (`"T..=..T"`), one char per tile,
   mapped through the tileset's `char` field. Readable and diffable; the
   integer ids still exist so later tools can emit them.
6. **Collision enum is complete now** (floor, solid, grass, water, lava, pit,
   ice, ledge_down, bombable, liftable) even though milestone 1 only walks on
   floor and bumps into solid. `BLOCKING` treats water/lava/pit/bombable/
   liftable as walls until swimming, bombs and lifting exist.
7. **Flip-scroll draws the hero only on the incoming room surface.** Drawing
   on both made two Wrens visible side by side mid-scroll. Logic pauses for
   the 12 frames; the hero is placed on the opposite edge at frame 0.
8. **Facing on diagonals keeps the current facing** if it is one of the two
   components, otherwise prefers horizontal. Matches the classic feel where
   walking diagonally does not flicker the sprite.
9. **Fonts are tinted at draw time**: glyph sources are palette white, the
   renderer forces RGB to 255 then multiplies by the requested colour, so
   `draw(..., colour=(255,0,0))` gives exactly red. Outlines are eight
   offset blits in a second colour.
10. **Gamepad via `pygame._sdl2.controller`** (SDL GameController) rather
    than `pygame.joystick`, so button names are device-independent
    (`a`, `b`, `dpup`, `leftshoulder` …) and hot-plug comes from
    `CONTROLLERDEVICEADDED/REMOVED`. The import is guarded; a missing
    controller subsystem never crashes the game.
11. **Alt+Enter is handled in code**, not in `input_map.json`, because the map
    binds single keys and Alt is a modifier.
12. **`--headless` runs N fixed steps without waiting on wall time** and also
    draws every frame, so the draw path is exercised in CI. `--save SLOT` is
    parsed and stored; saves arrive in milestone 2.
13. **vsync is requested and falls back silently** if SDL refuses it for a
    plain resizable window. The accumulator caps at 5 logic steps per
    rendered frame to avoid spiral-of-death after a stall.
14. **Debug overlay in milestone 1 = stats + hitboxes.** Free-cam, god mode,
    give-item, warp and flag editor are listed under section 5 and need the
    systems they manipulate (items, flags, saves); they come with those
    milestones. `World.warp()` already exists for the warp command.
15. **Commit author matches the repository's existing history**
    (`eldermoor <eldermoor@users.noreply.github.com>`), no trailers.
16. **Ruff config in `pyproject.toml`**: line length 110, rules E/F/W/I/B/UP.
    Module limit (600 lines) is enforced by a test.
17. **README is deferred to milestone 9** where PROMPT.md asks for it; `run.sh`
    and `requirements.txt` are enough to run milestone 1.

## Milestone 2

18. **Commit trailers.** Commits now carry the `Co-Authored-By` and
    `Claude-Session` lines the harness asks for. Decision 15 (match the
    existing history, no trailers) is superseded for that reason only; the
    author identity is unchanged.
19. **`Entity.update(world)` instead of `update(inp, room)`.** Entities need
    the state, the audio, the entity list and the spawn helpers, and six more
    milestones of them are coming. One context object beats threading a new
    argument through every class each time.
20. **Cut bushes, smashed pots and burned webs are tile edits, not objects.**
    Rooms are re-read from JSON on entry, so the edits undo themselves and the
    room restocks — exactly the behaviour of the games this follows, and no
    bookkeeping. Chests, doors and switches are objects because they are
    permanent, and they each own a global flag.
21. **Both halves of a two-tile doorway are separate `Door` objects sharing a
    flag.** A door sprite is 16 px; a 32 px doorway is two of them. Each
    watches the shared flag every frame, so unlocking either opens both.
22. **Doorways are snapped on entry.** Neighbouring screens do not always put
    their gap in the same column, and arriving with the old coordinate could
    drop Wren inside a cliff. `World._snap_into_doorway` slides him to the
    nearest opening, and `validate_data.py` additionally fails when two
    neighbours' doorways do not overlap at all.
23. **Armour means "hit it from behind", not "hit it from the opposite
    side".** A Cragguard is open when the attacker is *facing the same way it
    is*, which is what standing at its back means.
24. **`assets/audio/` is generated, not committed.** The sprite sheets stay in
    git, but 8 tracks and 63 effects are 25 MB of pure synthesis; PROMPT.md
    asks for a modest footprint in the same breath as committed assets, and
    the footprint wins. `main.py` renders them on first run, and `run.sh`
    builds them up front.
25. **Bosses are composed, not typed.** A 48x48 pixel-map written one
    character at a time is a typo farm, so `tools/sketch_bosses.py` draws the
    big bosses from discs and spikes. The output is still a plain text
    pixel-map in `assets_src/` and stays the editable source.
26. **`move_circle` walks instead of teleporting.** Placing a 48x48 boss
    straight onto its orbit parked it half inside the wall, where nothing
    could reach it. Orbiting entities now move with collision.
27. **Cragguards were pulled out of the first key room and the gate before the
    mini-boss.** Two shielded knights with three hearts and no shield was a
    difficulty cliff in the wrong place; they now guard optional rooms and the
    later floors.
28. **The playthrough bot is a measuring tape, not a player.** It reports what
    the save actually contains rather than which goals it gave up on, and the
    test suite holds it to leaving the village, reaching the temple and taking
    the map and compass. Automating the boss fights belongs to milestone 8's
    balance pass, which is where PROMPT.md asks for the 90-hour measurement.
29. **The shield answers its button during knockback.** Reading it inside the
    action handler meant a blocked hit froze the shield up permanently,
    because every blocked frame re-armed the knockback timer.
30. **Milestone-2 saves are version 2**, with a migration from the (never
    shipped) version 1 shape so the migration path itself is exercised.

## Milestone 3

31. **The overworld is one canvas, not 256 files.** Every tile is still
    placed by hand, but as one 208 x 320 character map. A road that leaves a
    screen is literally the same row of characters entering the next, the
    whole kingdom can be read at once, and exits are derived rather than
    declared twice. 256 separate JSON rooms would have drifted apart by the
    tenth screen.
32. **Blocks and a layout, then a canvas.** The canvas is stamped from
    hand-drawn 20 x 13 blocks by `tools/build_maps.py`. The committed canvas
    is the source of truth and can be edited by hand afterwards; re-running
    the tool overwrites those edits, which is why it is only run when the
    layout changes.
33. **A screen's wildlife comes from its region**, placed from a hash of the
    room id, not from 256 hand-written enemy lists. A screen that names its
    own objects is left alone, so every landmark stays hand-placed. The hash
    is `zlib.crc32`, because Python's own `hash` is salted per process and
    would move every creature in the kingdom on each launch.
34. **Sixteen room frames are emitted, the motifs are drawn.** The walls-and-
    gaps boxes are boilerplate; what goes inside them is the design. A
    layout entry of `r_nsew+m_pits+m_pots` composes them.
35. **A dungeon starts as a connection map.** `connections.txt` says which
    rooms join which; `tools/plan_dungeon.py` derives the frames and refuses
    a layout with an unreachable room. The locks, chests and creatures are
    hand-placed on top.
36. **Motifs never seal a room.** The water, lava and tile rings have a gap
    in them, because a ring drawn across a room is a locked door nobody can
    open.
37. **The old `village_*` and `meadow_*` rooms were retired** into the
    overworld rather than kept beside it; two geographies of the same place
    is a bug waiting to happen. The Hollow Glade stays a hand-written room,
    and the engine tests use it because it is walled, quiet and unchanging.
38. **The Hookshot stops a tile short of its anchor**, because the anchor is
    a pillar and standing inside one is not an option.
39. **Fins, Fire Boots, the Mirror Cloak and the Titan Gauntlet had their
    gates before they existed.** Water, lava, ice and the heavy blocks were
    painted where they belong in milestone 3, which is what PROMPT.md asks
    for: every region is seen before it can be entered. Milestone 4 only
    had to hand over the relics.
40. **A doorway is an exit unless solid rock stands in it.** Deriving exits
    from walkability alone sealed every flooded or burning hall off from
    its neighbours, because the doorway tile itself was water. Water, lava,
    pits, cracked walls and blocks now join two screens and the relic is
    the gate — which is also what the game already did inside a room.
41. **The final temple is gated by the Flames, not by a key.** The door on
    `ow_0906` has eight sockets; the stairs only exist once `flames8` is
    set. A sign says so either way, because a door that does nothing is a
    bug report waiting to be filed.
42. **The ending is a screen, not a cutscene room.** `world.pending_ending`
    hands the canvas to `eldermoor/ending.py`, which owns its pages and
    the crawl. The run is saved *before* the credits start, so quitting
    halfway through them still leaves a finished file.
43. **Which ending you get is read off `state.completion()`**, at 95 % or
    better, rather than from a flag set by a side quest. One number already
    counts everything the post-game cares about; a second bookkeeping path
    would only drift from it.

44. **Side content is tables, not code.** Rings, quests, figurines,
    furniture, the trading chain and the minigames' prizes are each one
    JSON file and one small reader. The engine asks the table a question;
    it never holds a list of what exists. That is what makes
    `tools/validate_data.py` able to fail when something in a table has
    nobody who gives it out, which is the bug that actually happens.
45. **A quest is a condition and a payment, and the world half is a
    token.** Rather than thirty bespoke scripts, a quest reads a counter, a
    flag or an item; the `token` object is the thing you poke to set the
    flag, and a set of tokens shares a count. The five-pot, nine-frog and
    three-sheep quests are the same object placed five, nine and three
    times.
46. **Nothing may stand in the doorway lanes.** The placer learned this the
    hard way: a quest giver on the two middle columns of a screen is a wall
    across the road, and the sim bot walked into one and stopped. Cols 9-10
    and rows 6-7 are the road; everything is placed outside them.
47. **The trading chain is an index, not ten items.** `state.trade` says
    which link you are on, and the item you are carrying is implied by it.
    Ten real items would have inflated the inventory counter, and the chain
    is only ever one thing long anyway.
48. **Trade and quest items that stay in the bag are souvenirs.** The
    twelve quest items are real items and are not taken back when the quest
    is paid: the quest is ticked off in its own list, so there is no reason
    to pick the player's pocket for the sake of tidiness.
49. **Optional means optional.** The six caves carry `optional` in their
    record, and the completability proof stops asking them for a map, a
    compass, keys and a Flame. A cave that demanded the full temple
    furniture would either be a temple or a lie.

50. **The Master Quest is a modifier, not a second kingdom.** A hand-built
    second layout of nine temples would be a year of work and two sets of
    bugs. One flag, scaled damage and life, and a leaner drop table change
    every fight in the game, and the save says which kind of file it is.
51. **The post-game unlocks live in two places on purpose.** Whether *this
    file* has finished the game is a flag on the save, because the Mist Door
    should only open for the file that earned it. Whether the Master Quest
    is on offer at all is in settings.json, because a brand new file cannot
    know what an older one did.
52. **The Standing Ring asks first.** The Boss Rush warps you in and will
    not let you out until it is over, which is the one place in the game
    where a yes/no box is the honest interface.
53. **Mistjaw was missing and the changelog said otherwise.** Writing the
    post-game's boss list is what found it: the Boss Rush table named every
    boss in the game, and one of them had sprites, a name in the notes and
    no data. The lesson stands as the rule the validator already follows -
    a table that names something is a check waiting to be written.

54. **Co-op is a setting, not a secret button.** "Drop-in" is lovely until
    you work out which button a second gamepad can press that player one is
    not already using for an item. The settings page already asks about
    devices, the pause menu is one button away, and turning it off puts the
    second lamplighter away mid-room, which is what drop-out means.
55. **Player one is the camera.** Only player one's position opens the next
    screen, and player two is carried to the same doorway. The alternative -
    either player dragging the screen - means one of them is walked out of a
    fight they were in the middle of.
56. **One heart row.** Two separate health bars means two death rules, two
    respawns and a long argument about what happens to the other player. One
    row, two bodies: the second lamplighter is help, not a second life.
57. **Player two gets copies, not an empty bag.** They start with player
    one's three slots so the first thing a second player does is play, and
    their slots diverge from the moment anyone changes them.

58. **Hit-stop is three frames, not six.** Six reads as a stutter on a
    60 Hz game with no animation blending; three is felt rather than seen.
59. **Thirty-two colours cannot all be distinct to a dichromat.** Requiring
    it would mean a palette of greys. So the check is strict about the
    colours that carry meaning - text, cursors, hearts, the two barrier
    colours - and prints the rest as advice. The strictness is where
    confusion would cost the player something.
60. **Brightness is the channel that survives.** Where two colours collapse
    in hue under a simulation, the check accepts them if their brightness
    still separates them, which is also why the meaningful pairs are checked
    on brightness rather than hue in the first place.
61. **Creatures carry a tier, and the balance check reads it.** "Is this
    fair?" has no answer without "fair to whom?". A tier says what the
    player is expected to be carrying by the time they meet a creature, and
    once that was written down the check found the first temple's bosses
    were a wall rather than a lesson.
62. **The length estimate measures one thing and counts the rest.** The bot
    can honestly measure how long it takes to cross a room and fight what is
    in it; it cannot honestly simulate a player hunting seashells. So it
    measures the room - separately for an overworld screen and a dungeon
    room, over the part of the run that was going somewhere rather than the
    tail where it loops and dies - and everything else is content counted
    out of data/ times a cost printed on its own line.
63. **The companion waits to be wanted.** A hint that fires on entering a
    room is a pop-up with extra steps. Fourteen seconds of standing still is
    a player who has stopped to think, and she says one thing, once.
