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
