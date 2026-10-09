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
