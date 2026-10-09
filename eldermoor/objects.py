"""Room objects: chests, doors, NPCs, signs, torches, switches, stairs and rewards.

Objects come from a room's ``objects`` list; each entry is ``{"kind": ...,
"at": [col, row], ...}``.  Anything permanent remembers itself in a global
flag so a solved room stays solved.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pygame

from eldermoor.config import TILE
from eldermoor.entities import Entity

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.world import World

LOCK_SPRITES = {"": "door_closed", "small": "door_locked", "big": "door_big",
                "boss": "door_big", "shut": "door_closed"}


class RoomObject(Entity):
    """Base for anything placed by a room's object list."""

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        col, row = spec.get("at", (0, 0))
        super().__init__(col * TILE, row * TILE)
        self.col = int(col)
        self.row = int(row)
        self.spec = spec
        self.id = str(spec.get("id", f"{self.col},{self.row}"))
        self.flag_name = str(spec.get("flag", f"{world.room.id}:{spec['kind']}:{self.id}"))

    def done(self, world: World) -> bool:
        """True if this object's flag has already been set."""
        return bool(world.state.flag(self.flag_name))

    def mark(self, world: World) -> None:
        """Set this object's flag."""
        world.state.set_flag(self.flag_name, 1)


class Chest(RoomObject):
    """A treasure chest. Opened with A; its contents are given once."""

    blocks_movement = True
    body = pygame.Rect(1, 2, 14, 13)

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.item = str(spec.get("item", ""))
        self.amount = int(spec.get("amount", 1))
        self.opened = self.done(world)

    def sprite_name(self) -> str:
        """Open or closed lid."""
        return "chest_open" if self.opened else "chest_closed"

    def interact(self, world: World) -> bool:
        """Open the chest and hand over what is inside."""
        if self.opened:
            return False
        self.opened = True
        self.mark(world)
        world.audio.play("chest_open")
        world.grant(self.item, self.amount)
        world.trigger("chest_opened", self.id)
        return True


class Sign(RoomObject):
    """A readable sign."""

    blocks_movement = True

    def sprite_name(self) -> str | None:
        """Signs are painted into the tile layer."""
        return None

    def interact(self, world: World) -> bool:
        """Show the sign's text."""
        world.say(self.spec.get("text", "sign.blank"))
        return True


class Npc(RoomObject):
    """A villager. Talks when the hero presses A facing them."""

    blocks_movement = True
    sprite_offset = (0, -8)
    body = pygame.Rect(2, 4, 12, 12)

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.sprite = str(spec.get("sprite", "npc_elder"))
        self.facing = str(spec.get("face", "down"))
        self.bob = 0

    def update(self, world: World) -> None:
        """A one-pixel breath so a crowd does not look frozen."""
        self.frame += 1
        self.bob = -1 if (self.frame // 40) % 2 else 0

    def sprite_name(self) -> str:
        """The villager's single pose."""
        return self.sprite

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Blit with the bob applied."""
        ox, oys = self.sprite_offset
        target.blit(assets.sprites.get(self.sprite_name()),
                    (round(self.x) + ox, round(self.y) + oy + oys + self.bob))

    def interact(self, world: World) -> bool:
        """Say the line for the current story state, then quest, shop or nothing."""
        quest_id = str(self.spec.get("quest", ""))
        if quest_id:
            return world.talk_quest(quest_id)
        if "trade" in self.spec:
            return world.talk_trade(int(self.spec["trade"]))
        game = str(self.spec.get("minigame", ""))
        if game:
            return world.offer_minigame(game, self.spec)
        stock = self.spec.get("shop")
        after = (lambda _r: world.request_shop(self.spec)) if stock else None
        world.say(world.npc_line(self.spec), after=after)
        return True


class Token(RoomObject):
    """A thing in the world that answers a press by setting a flag.

    One token sets its own flag. A set of them share a ``count`` and an
    ``of``: poke all five pots, or walk all three sheep home, and the shared
    flag goes up once the last one is done. ``needs`` holds a token back
    until an item is in the bag.
    """

    blocks_movement = True

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.sprite = str(spec.get("sprite", "npc_elder"))
        self.count = str(spec.get("count", ""))
        self.of = int(spec.get("of", 1))
        self.needs = str(spec.get("needs", ""))
        self.sets = str(spec.get("sets", ""))
        self.gone = bool(spec.get("vanish", False)) and self.done(world)

    def sprite_name(self) -> str | None:
        """Its sprite, unless it has been used up."""
        return None if self.gone else self.sprite

    @property
    def counter(self) -> str:
        """Flag that holds how many of a set have been done."""
        return f"count:{self.count}"

    def interact(self, world: World) -> bool:
        """Poke it: refuse, repeat, or count it and say the line."""
        if self.needs and not world.state.has(self.needs):
            world.say(str(self.spec.get("refuse", "token.refuse")))
            return True
        if self.done(world):
            world.say(str(self.spec.get("again", self.spec.get("text", "token.again"))))
            return True
        self.mark(world)
        world.audio.play(str(self.spec.get("sound", "secret")))
        if self.count:
            now = world.state.flag(self.counter) + 1
            world.state.set_flag(self.counter, now)
            if now >= self.of and self.sets:
                world.state.set_flag(self.sets, 1)
                world.audio.play("puzzle")
        elif self.sets:
            world.state.set_flag(self.sets, 1)
        if bool(self.spec.get("vanish", False)):
            self.gone = True
            self.blocks = False
        world.say(str(self.spec.get("text", "token.found")))
        world.trigger("token", self.id)
        return True


class Display(RoomObject):
    """One spot in Wren's house that shows a piece of furniture he owns.

    Which piece stands here is whatever is nth in the collection, so the room
    fills up as he collects; ``placed`` in the save remembers the pairing so a
    piece does not jump around the room when a new one arrives.
    """

    blocks_movement = True
    body = pygame.Rect(2, 4, 12, 12)

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.slot = int(spec.get("slot", 0))
        self.piece = self._piece(world)
        if self.piece is None:
            self.alive = False

    def _piece(self, world: World) -> str | None:
        """The furniture id standing in this slot, if any."""
        state = world.state
        spot = f"spot{self.slot}"
        placed = state.placed.get(spot)
        if placed and placed in state.furniture:
            return placed
        free = [f for f in state.furniture if f not in state.placed.values()]
        if not free:
            return None
        state.placed[spot] = free[0]
        return free[0]

    def sprite_name(self) -> str | None:
        """Furniture is drawn from its 8x8 icon, not a sprite."""
        return None

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Blit the piece's icon in the middle of its tile."""
        entry = self.piece
        if entry is None:
            return
        icon = "icon_chair"
        target.blit(assets.icons.get(icon), (round(self.x) + 4, round(self.y) + oy + 4))

    def interact(self, world: World) -> bool:
        """Say what it is."""
        entry = world.content.furniture.get(self.piece or "")
        world.say(entry.name if entry is not None else "token.again")
        return True


class Door(RoomObject):
    """A door in a wall. Small/big keys open it; triggers can shut or open it."""

    blocks_movement = True

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.lock = str(spec.get("lock", ""))
        self.open = self.done(world) or self.lock == "open"

    @property
    def blocks(self) -> bool:
        """True while the door is shut."""
        return not self.open

    def sprite_name(self) -> str:
        """Open frame or the lock's own frame."""
        return "door_open" if self.open else LOCK_SPRITES.get(self.lock, "door_closed")

    def update(self, world: World) -> None:
        """A doorway is two tiles wide, so both halves watch the same flag."""
        if not self.open and self.done(world):
            self.open = True

    def unlock(self, world: World) -> bool:
        """Spend a key (if the door needs one) and open. False if it cannot be opened."""
        state = world.state
        if self.lock == "small":
            if state.keys <= 0:
                world.say("door.locked")
                world.audio.play("error")
                return False
            state.keys -= 1
            progress = world.dungeon_progress()
            if progress is not None:
                progress.used_keys += 1
            state.sync_keys()
        elif self.lock in ("big", "boss"):
            progress = world.dungeon_progress()
            if progress is None or not progress.big_key:
                world.say("door.bigkey")
                world.audio.play("error")
                return False
        elif self.lock == "shut":
            return False
        self.open = True
        self.mark(world)
        world.audio.play("door_unlock")
        world.trigger("door_opened", self.id)
        return True

    def interact(self, world: World) -> bool:
        """Pressing A at a locked door tries to open it."""
        if self.open:
            return False
        return self.unlock(world) or True

    def force_open(self, world: World) -> None:
        """Opened by a trigger rather than a key."""
        if not self.open:
            self.open = True
            self.mark(world)
            world.audio.play("door_open")


class Torch(RoomObject):
    """A torch. The Lantern lights it; rooms count lit torches."""

    blocks_movement = True

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        #: a torch with burn_time goes out again and is never remembered, so a
        #: puzzle built on it (the boss arena) can be solved more than once
        self.burn_time = int(spec.get("burn_time", 0))
        self.lit = bool(spec.get("lit", False)) or (self.done(world) and not self.burn_time)
        self.timer = 0

    def sprite_name(self) -> str:
        """Unlit, or one of the two flame frames."""
        if not self.lit:
            return "torch_unlit"
        return f"torch_lit_{(self.frame // 8) % 2}"

    def update(self, world: World) -> None:
        """Animate and, for a timed torch, burn down."""
        self.frame += 1
        if self.lit and self.burn_time:
            self.timer += 1
            if self.timer >= self.burn_time:
                self.lit = False
                self.timer = 0

    def light(self, world: World) -> bool:
        """Light the torch. False if it was already burning."""
        if self.lit:
            return False
        self.lit = True
        self.timer = 0
        if not self.burn_time:
            self.mark(world)
        world.audio.play("torch_light")
        world.trigger("torch_lit", self.id)
        world.trigger("torches_lit", self.id)
        return True


class FloorSwitch(RoomObject):
    """A floor plate held down by the hero or a pushed block."""

    body = pygame.Rect(2, 2, 12, 12)

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.hold = bool(spec.get("hold", False))   # True: springs back up
        self.pressed = self.done(world) and not self.hold

    def sprite_name(self) -> str:
        """Raised or pressed plate."""
        return "switch_down" if self.pressed else "switch_up"

    def update(self, world: World) -> None:
        """Check what is standing on the plate."""
        on = self.body_rect().colliderect(world.hero.body_rect())
        if not on:
            on = any(isinstance(e, PushBlock) and e.body_rect().colliderect(self.body_rect())
                     for e in world.entities)
        if on and not self.pressed:
            self.pressed = True
            world.audio.play("switch")
            if not self.hold:
                self.mark(world)
            world.trigger("switch", self.id)
        elif not on and self.pressed and self.hold:
            self.pressed = False
            world.trigger("switch_released", self.id)


class Crystal(RoomObject):
    """A crystal switch: hit it with the sword to toggle the room's barriers."""

    blocks_movement = True
    team = "enemy"

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.red = bool(world.state.flag(self.flag_name))
        self.hp = 9999

    def sprite_name(self) -> str:
        """Blue or red crystal."""
        return "crystal_red" if self.red else "crystal_blue"

    def take_damage(self, world: World, amount: int, source: Entity | None = None) -> bool:
        """A sword hit flips the crystal instead of hurting it."""
        self.red = not self.red
        world.state.set_flag(self.flag_name, 1 if self.red else 0)
        world.audio.play("switch")
        world.trigger("crystal", self.id)
        return False


class PushBlock(RoomObject):
    """A heavy block the hero can shove one tile at a time."""

    blocks_movement = True

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.target: tuple[float, float] | None = None
        #: a heavy block waits for the Titan Gauntlet
        self.heavy = bool(spec.get("heavy", False))

    def sprite_name(self) -> str:
        """The block sprite."""
        return "block"

    def update(self, world: World) -> None:
        """Slide towards the pushed-to tile."""
        if self.target is None:
            return
        tx, ty = self.target
        step = 1.0
        self.x += max(-step, min(step, tx - self.x))
        self.y += max(-step, min(step, ty - self.y))
        if abs(self.x - tx) < 0.5 and abs(self.y - ty) < 0.5:
            self.x, self.y = tx, ty
            self.target = None
            world.trigger("block_moved", self.id)

    def push(self, world: World, dx: int, dy: int) -> bool:
        """Try to shove the block one tile. False if something is in the way."""
        if self.target is not None:
            return False
        nx, ny = self.x + dx * TILE, self.y + dy * TILE
        if world.blocked(self.body_rect(nx, ny), ignore=self):
            return False
        self.target = (nx, ny)
        world.audio.play("push")
        return True


class Stairs(RoomObject):
    """Stairs or a doorway: stepping on them takes the hero to another room."""

    body = pygame.Rect(4, 4, 8, 8)

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.to = str(spec["to"])
        self.spawn = spec.get("spawn")
        self.sound = str(spec.get("sound", "stairs"))
        self.armed = False

    def sprite_name(self) -> str | None:
        """Stairs are part of the tile layer."""
        return None

    def update(self, world: World) -> None:
        """Warp once the hero is standing on the stairs."""
        touching = self.body_rect().colliderect(world.hero.body_rect())
        if touching and self.armed:
            world.audio.play(self.sound)
            spawn = tuple(self.spawn) if self.spawn else None
            world.warp(self.to, spawn[0] if spawn else None, spawn[1] if spawn else None)
        elif not touching:
            self.armed = True


class Reward(RoomObject):
    """Something waiting to be taken: a piece, a shell, a ring, a Flame."""

    body = pygame.Rect(2, 2, 12, 12)

    SPRITES = {"heart_piece": "icon_piece", "heart_container": "heart_container",
               "shell": "pickup_shell", "flame": "flame_pickup",
               "ring": "icon_ring_gold", "figurine": "icon_figurine",
               "furniture": "icon_chair"}

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.what = str(spec.get("what", "heart_piece"))
        if self.done(world):
            self.alive = False

    def sprite_name(self) -> str:
        """Sprite for the reward kind."""
        return self.SPRITES.get(self.what, "pickup_shell")

    def draw(self, target: pygame.Surface, assets: Assets, oy: int = 0) -> None:
        """Heart pieces use an 8x8 icon, everything else a 16x16 sprite."""
        name = self.sprite_name()
        sheet = assets.icons if assets.icons.has(name) else assets.sprites
        bob = -1 if (self.frame // 24) % 2 else 0
        off = 4 if sheet is assets.icons else 0
        target.blit(sheet.get(name), (round(self.x) + off, round(self.y) + oy + bob + off))

    def update(self, world: World) -> None:
        """Taken on touch."""
        self.frame += 1
        if self.body_rect().colliderect(world.hero.body_rect()):
            self.alive = False
            self.mark(world)
            world.take_reward(self.what, self.spec)


class WarpLantern(RoomObject):
    """A region's warp lantern. Touch it once and you can come back to it."""

    body = pygame.Rect(2, 4, 12, 12)
    blocks_movement = True

    def __init__(self, world: World, spec: dict[str, Any]) -> None:
        super().__init__(world, spec)
        self.region = str(spec.get("region", "meadow"))
        self.lit = bool(world.state.flag(self.flag_name))

    def sprite_name(self) -> str:
        """Dark post, or one of the two flame frames."""
        if not self.lit:
            return "warp_unlit"
        return f"warp_lit_{(self.frame // 10) % 2}"

    def update(self, world: World) -> None:
        """Light on first touch and remember the region."""
        self.frame += 1
        if self.lit:
            return
        if self.body_rect().inflate(6, 6).colliderect(world.hero.body_rect()):
            self.lit = True
            self.mark(world)
            world.state.warps[self.region] = world.room.id
            world.audio.play("secret")
            world.say("warp.lit", after=None)
            world.trigger("warp_lit", self.region)


#: room object kind -> class
KINDS: dict[str, Callable[[World, dict[str, Any]], RoomObject]] = {
    "chest": Chest, "sign": Sign, "npc": Npc, "door": Door, "torch": Torch,
    "token": Token, "display": Display,
    "switch": FloorSwitch, "crystal": Crystal, "block": PushBlock,
    "stairs": Stairs, "reward": Reward, "warp": WarpLantern,
}


def build(world: World, spec: dict[str, Any]) -> RoomObject | None:
    """Create one room object from its JSON entry, or None for an unknown kind."""
    factory = KINDS.get(str(spec.get("kind", "")))
    return factory(world, spec) if factory else None
