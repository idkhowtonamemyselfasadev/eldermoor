"""Everything read out of data/ once and then shared by the whole game."""
from __future__ import annotations

from pathlib import Path

from eldermoor.config import DATA
from eldermoor.drops import DropTables
from eldermoor.dungeon import Dungeons
from eldermoor.enemies import EnemyRegistry
from eldermoor.items import ItemRegistry
from eldermoor.text import Text


class Content:
    """Item, text, drop, enemy and dungeon tables. Loading is the expensive part, so share one."""

    def __init__(self, root: Path = DATA, language: str = "en") -> None:
        self.root = root
        self.items = ItemRegistry.load(root)
        self.text = Text.load(language, root)
        self.drops = DropTables.load(root)
        self.enemies = EnemyRegistry.load(root)
        self.dungeons = Dungeons.load(root)

    def reload_text(self, language: str) -> None:
        """Swap the string table (settings menu language switch)."""
        self.text = Text.load(language, self.root)
