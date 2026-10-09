"""Loading of the generated sprite sheets, atlases, palette and fonts."""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from eldermoor.config import ASSETS
from eldermoor.font import BitmapFont


class Sheet:
    """A PNG sheet plus its atlas: name -> [x, y, w, h]. Sub-surfaces are cached."""

    def __init__(self, image: pygame.Surface, atlas: dict[str, list[int]]) -> None:
        self.image = image
        self.atlas = atlas
        self._cache: dict[tuple[str, bool], pygame.Surface] = {}

    @classmethod
    def load(cls, png: Path, atlas_json: Path) -> Sheet:
        """Load a sheet from disk, converting to the display format when there is a display."""
        image = pygame.image.load(str(png))
        if pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        return cls(image, json.loads(atlas_json.read_text()))

    def has(self, name: str) -> bool:
        """True if the atlas contains this block name."""
        return name in self.atlas

    @property
    def names(self) -> list[str]:
        """All block names in the sheet."""
        return list(self.atlas)

    def get(self, name: str, flip_x: bool = False) -> pygame.Surface:
        """Return the sub-surface for a block (optionally mirrored horizontally)."""
        key = (name, flip_x)
        surf = self._cache.get(key)
        if surf is None:
            if name not in self.atlas:
                raise KeyError(f"no sprite {name!r} in sheet")
            x, y, w, h = self.atlas[name]
            surf = self.image.subsurface(pygame.Rect(x, y, w, h))
            if flip_x:
                surf = pygame.transform.flip(surf, True, False)
            self._cache[key] = surf
        return surf


class Assets:
    """Everything loaded from assets/: sheets, tiles per region, fonts, palette."""

    def __init__(self, root: Path = ASSETS) -> None:
        self.root = root
        self.sprites = Sheet.load(root / "sprites.png", root / "sprites.json")
        self.icons = Sheet.load(root / "icons.png", root / "icons.json")
        tile_atlas = root / "tiles.json"
        self.tiles: dict[str, Sheet] = {}
        for png in sorted(root.glob("tiles_*.png")):
            region = png.stem[len("tiles_"):]
            self.tiles[region] = Sheet.load(png, tile_atlas)
        self.font8 = BitmapFont(Sheet.load(root / "font8.png", root / "font8.json"), 8, 8)
        self.font6 = BitmapFont(Sheet.load(root / "font6.png", root / "font6.json"), 6, 8)
        pal = json.loads((root / "palette.json").read_text())
        self.palette: list[tuple[int, int, int]] = [tuple(c) for c in pal["rgb"]]
        self.palette_names: list[str] = pal["names"]

    def colour(self, name: str) -> tuple[int, int, int]:
        """Palette colour by name, e.g. ``assets.colour("ember")``."""
        return self.palette[self.palette_names.index(name)]

    def region_tiles(self, region: str) -> Sheet:
        """Tile sheet for a region palette; falls back to the meadow sheet."""
        return self.tiles.get(region) or self.tiles["meadow"]


def assets_built(root: Path = ASSETS) -> bool:
    """True if the generated assets exist."""
    needed = ("sprites.png", "sprites.json", "icons.png", "icons.json",
              "tiles.json", "tiles_meadow.png", "font8.png", "font8.json",
              "font6.png", "font6.json", "palette.json")
    return all((root / n).exists() for n in needed)
