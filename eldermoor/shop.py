"""The village shop: a list of wares bought with embers, driven by the 12 buttons."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from eldermoor.config import CANVAS_H, CANVAS_W

if TYPE_CHECKING:
    from eldermoor.world import World

ROW_H = 14
TOP = 40


class Shop:
    """One shop visit.

    A stock entry is ``{"item": id, "cost": n, "amount": n}`` for an
    inventory item, or ``{"kind": "ring"|"figurine"|"furniture", "id": ...,
    "cost": n}`` for something that goes in a collection rather than the bag.
    ``once`` marks a one-off: it greys out when the shelf is empty, and
    ``needs_bestiary`` holds a ware back until the bestiary is that full.
    """

    def __init__(self, world: World, stock: list[dict[str, Any]], greeting: str = "shop.hello") -> None:
        self.world = world
        self.stock = [dict(s) for s in stock]
        self.cursor = 0
        self.done = False
        self.note = world.textdb.get(greeting)

    # ----- frame ---------------------------------------------------------
    def update(self, inp: Any) -> str | None:
        """One frame. Returns "close" when the shop should go away."""
        if inp.pressed("b") or inp.pressed("start"):
            self.world.audio.play("menu_back")
            return "close"
        if inp.pressed("down"):
            self.cursor = (self.cursor + 1) % max(1, len(self.stock))
            self.world.audio.play("select_cursor")
        if inp.pressed("up"):
            self.cursor = (self.cursor - 1) % max(1, len(self.stock))
            self.world.audio.play("select_cursor")
        if inp.pressed("a") and self.stock:
            self._buy(self.stock[self.cursor])
        return None

    def price(self, entry: dict[str, Any]) -> int:
        """What this costs today: the listed price, less whatever a ring shaves off."""
        cost = int(entry.get("cost", 0))
        off = self.world.ring_bonus.price
        return cost if not cost or not off else max(1, round(cost * (100 + off) / 100))

    def _buy(self, entry: dict[str, Any]) -> None:
        state = self.world.state
        cost = self.price(entry)
        if self.sold_out(entry):
            self.note = self.world.textdb.get("shop.sold")
            self.world.audio.play("error")
            return
        want = int(entry.get("needs_bestiary", 0))
        if want and len(state.bestiary) < want:
            self.note = self.world.textdb.get("shop.locked", n=want)
            self.world.audio.play("error")
            return
        if state.embers < cost:
            self.note = self.world.textdb.get("shop.poor")
            self.world.audio.play("error")
            return
        state.embers -= cost
        kind = str(entry.get("kind", ""))
        if kind:
            self._take_home(kind, str(entry.get("id", "")))
        else:
            self.world.grant(str(entry.get("item", "")), int(entry.get("amount", 1)))
        self.world.dialogue = None          # the shop prints its own note instead
        self.note = self.world.textdb.get("shop.thanks")

    def _take_home(self, kind: str, entry_id: str) -> None:
        """Buy something that lives in a collection, not in the bag."""
        state = self.world.state
        if kind == "ring":
            state.find_ring(entry_id)
            self.world.audio.play("item_get")
        else:
            state.collect("figurines" if kind == "figurine" else "furniture", entry_id)
            self.world.audio.play("figurine")

    def sold_out(self, entry: dict[str, Any]) -> bool:
        """True for a one-off the player already has."""
        state = self.world.state
        kind = str(entry.get("kind", ""))
        if kind:
            box = {"ring": state.rings, "figurine": state.figurines,
                   "furniture": state.furniture}[kind]
            return str(entry.get("id", "")) in box
        return bool(entry.get("once")) and state.has(str(entry.get("item", "")))

    def label(self, entry: dict[str, Any]) -> tuple[str, str]:
        """(icon, display name) for one stock entry."""
        kind = str(entry.get("kind", ""))
        if kind:
            entry_id = str(entry.get("id", ""))
            table = {"ring": self.world.content.rings.get(entry_id),
                     "figurine": self.world.content.figurines.get(entry_id),
                     "furniture": self.world.content.furniture.get(entry_id)}[kind]
            if table is not None:
                return table.icon, self.world.textdb.get(table.name)
            return "icon_empty", entry_id
        item = self.world.items.get(str(entry.get("item", "")))
        if item is None:
            return "icon_empty", str(entry.get("item", ""))
        return item.icon, self.world.textdb.get(item.name)

    # ----- drawing -------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        """The counter, the wares and the ember purse."""
        assets = self.world.assets
        target.fill(assets.colour("ink"))
        font = assets.font8
        font.draw(target, self.world.textdb.get("shop.title"), 12, 12, assets.colour("gold"))
        font.draw(target, f"{self.world.state.embers:03d}", CANVAS_W - 40, 12,
                  assets.colour("white"))
        target.blit(assets.icons.get("ember"), (CANVAS_W - 52, 12))
        for i, entry in enumerate(self.stock):
            y = TOP + i * ROW_H
            selected = i == self.cursor
            colour = assets.colour("gold") if selected else assets.colour("white")
            if self.sold_out(entry):
                colour = assets.colour("stone")
            icon, label = self.label(entry)
            if assets.icons.has(icon):
                target.blit(assets.icons.get(icon), (20, y))
            font.draw(target, label, 36, y, colour)
            font.draw(target, f"{self.price(entry):3d}", CANVAS_W - 56, y, colour)
        pygame.draw.rect(target, assets.colour("slate"),
                         pygame.Rect(8, TOP - 6, CANVAS_W - 16, len(self.stock) * ROW_H + 8), 1)
        font.draw(target, self.note[:38], 12, CANVAS_H - 20, assets.colour("mist"))
