"""Everything read out of data/ once and then shared by the whole game."""
from __future__ import annotations

from pathlib import Path

from eldermoor.collections_data import Collection
from eldermoor.config import DATA
from eldermoor.drops import DropTables
from eldermoor.dungeon import Dungeons
from eldermoor.enemies import EnemyRegistry
from eldermoor.items import ItemRegistry
from eldermoor.minigames import MiniGames
from eldermoor.postgame import Rush
from eldermoor.quests import Quests
from eldermoor.rings import Rings
from eldermoor.text import Text
from eldermoor.trade import Trade


class Content:
    """Item, text, drop, enemy, dungeon, ring, quest and collection tables.

    Loading is the expensive part, so the whole game shares one.
    """

    def __init__(self, root: Path = DATA, language: str = "en") -> None:
        self.root = root
        self.items = ItemRegistry.load(root)
        self.text = Text.load(language, root)
        self.drops = DropTables.load(root)
        self.enemies = EnemyRegistry.load(root)
        self.dungeons = Dungeons.load(root)
        self.rings = Rings.load(root)
        self.quests = Quests.load(root)
        self.figurines = Collection.load("figurines", root)
        self.furniture = Collection.load("furniture", root)
        self.trade = Trade.load(root)
        self.minigames = MiniGames.load(root)
        self.rush = Rush.load(root)

    def reload_text(self, language: str) -> None:
        """Swap the string table (settings menu language switch)."""
        self.text = Text.load(language, self.root)
