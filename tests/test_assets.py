"""Asset pipeline, atlases, palette and fonts."""
from __future__ import annotations

import json

import pygame

from eldermoor.config import ASSETS, ROOT

REQUIRED_SPRITES = [f"wren_{d}_{f}" for d in ("down", "up", "side") for f in ("0", "1", "2", "idle")]
REQUIRED_SPRITES += [f"wren_swing_{d}_{f}" for d in ("down", "up", "side") for f in range(3)]
REQUIRED_SPRITES += ["sword_h", "sword_v_down", "sword_v_up", "sword_diag_dr", "sword_diag_ur"]
REQUIRED_ICONS = ["heart_full", "heart_half", "heart_empty", "ember", "key",
                  "icon_sword", "icon_shield", "icon_lantern"]
FONT_EXTRA = "ÄÖÜäöüß♥♡←↑→↓"


def test_palette_has_32_named_colours(assets):
    assert len(assets.palette) == 32
    assert len(set(assets.palette_names)) == 32
    assert assets.colour("ember") == (0xF0, 0x80, 0x30)


def test_build_is_reproducible():
    import build_assets
    before = {p.name: p.read_bytes() for p in ASSETS.iterdir() if p.suffix in (".png", ".json")}
    build_assets.main([])
    after = {p.name: p.read_bytes() for p in ASSETS.iterdir() if p.suffix in (".png", ".json")}
    assert before == after


def test_sprites_and_icons_present(assets):
    for name in REQUIRED_SPRITES:
        assert assets.sprites.has(name), name
        assert assets.sprites.get(name).get_size() == (16, 16)
    for name in REQUIRED_ICONS:
        assert assets.icons.has(name), name
        assert assets.icons.get(name).get_size() == (8, 8)


def test_atlas_entries_fit_their_sheets():
    for name in ("sprites", "icons", "font8", "font6"):
        atlas = json.loads((ASSETS / f"{name}.json").read_text())
        img = pygame.image.load(str(ASSETS / f"{name}.png"))
        for x, y, w, h in atlas.values():
            assert x + w <= img.get_width() and y + h <= img.get_height()


def test_region_tile_sheets_exist(assets):
    swaps = json.loads((ROOT / "assets_src" / "region_palettes.json").read_text())
    for region in swaps:
        if not region.startswith("_"):
            assert region in assets.tiles, region
    # a swap really recolours: thornwood maps leaf(17) -> moss(16)
    meadow = assets.tiles["meadow"].get("grass").get_at((0, 0))[:3]
    thorn = assets.tiles["thornwood"].get("grass").get_at((0, 0))[:3]
    assert meadow == assets.colour("leaf") and thorn == assets.colour("moss")


def test_fonts_cover_ascii_and_umlauts(assets):
    for font in (assets.font8, assets.font6):
        for code in range(32, 127):
            assert font.has(chr(code)), f"missing {chr(code)!r} in {font.width}x{font.height}"
        for ch in FONT_EXTRA:
            assert font.has(ch), f"missing {ch!r}"
        assert font.glyph("A").get_size() == (font.width, font.height)


def test_font_draw_tints_and_outlines(assets):
    surf = pygame.Surface((80, 16), pygame.SRCALPHA)
    end = assets.font8.draw(surf, "Hi", 1, 1, (255, 0, 0), outline=(0, 0, 255))
    assert end == 17
    pixels = {surf.get_at((x, y))[:3] for x in range(20) for y in range(10)}
    assert (255, 0, 0) in pixels and (0, 0, 255) in pixels
    assert assets.font6.measure("abc") == 18


def test_flipped_sprite_is_mirror(assets):
    a = assets.sprites.get("wren_side_1")
    b = assets.sprites.get("wren_side_1", flip_x=True)
    assert a.get_at((3, 8)) == b.get_at((12, 8))
