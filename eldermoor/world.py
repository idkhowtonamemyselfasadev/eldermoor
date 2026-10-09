"""The world: the current room, its entities, transitions, dialogue and the services
every entity calls into."""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

import pygame

from eldermoor import actions, rewards
from eldermoor.bosses import Boss
from eldermoor.config import PLAY_H, PLAY_W, PLAY_Y, TEXT_SPEED_DEFAULT, TILE
from eldermoor.content import Content
from eldermoor.enemies import Enemy, Projectile
from eldermoor.entities import Entity
from eldermoor.hero import Hero
from eldermoor.objects import Door, Torch, build
from eldermoor.pickups import Pickup, spawn_drop
from eldermoor.script import fire
from eldermoor.state import GameState
from eldermoor.textbox import TextBox
from eldermoor.tilemap import HOPPABLE, Collision, Room, Tileset
from eldermoor.transition import FlipScroll

if TYPE_CHECKING:
    from eldermoor.assets import Assets
    from eldermoor.audio import Audio
    from eldermoor.input import Input

EDGE_MARGIN = 6
LANTERN_FRAMES = 26
#: eight real minutes from dawn to dawn
DAY_LENGTH = 8 * 60.0
NIGHT_FROM = 0.55
NIGHT_TO = 0.95


class World:
    """Owns the room, the entities and the services they call."""

    def __init__(self, assets: Assets, state: GameState | None = None,
                 inp: Input | None = None, audio: Audio | None = None,
                 content: Content | None = None, start_room: str | None = None) -> None:
        from eldermoor.audio import Audio as RealAudio
        from eldermoor.input import Input as RealInput
        self.assets = assets
        self.state = state or GameState()
        self.input = inp or RealInput()
        self.audio = audio or RealAudio()
        self.content = content or Content()
        self.rng = random.Random(20260420)
        self.tilesets: dict[str, Tileset] = {}
        self.entities: list[Entity] = []
        self.hero = Hero(0, 0)
        self.transition: FlipScroll | None = None
        self.dialogue: TextBox | None = None
        self.dialogue_after: Any = None
        self.pending_shop: dict[str, Any] | None = None
        self.shake_timer = 0
        self.boss: Boss | None = None
        self._room_surface: pygame.Surface | None = None
        self.play_rect = pygame.Rect(0, 0, PLAY_W, PLAY_H)
        self.text_speed = TEXT_SPEED_DEFAULT
        self.god_mode = False
        self._surface_night = False
        self.last_safe = (0.0, 0.0)
        self.room = Room.load(start_room or self.state.room, tilesets=self.tilesets)
        self.enter_room(self.room.id, *self.state_position(start_room))

    # ----- short-hands entities use --------------------------------------
    @property
    def items(self) -> Any:
        """The item registry."""
        return self.content.items

    @property
    def textdb(self) -> Any:
        """The string table."""
        return self.content.text

    @property
    def drops(self) -> Any:
        """The drop tables."""
        return self.content.drops

    @property
    def enemy_defs(self) -> Any:
        """The enemy registry."""
        return self.content.enemies

    @property
    def rooms_visited(self) -> list[str]:
        """Rooms seen so far (kept in the save)."""
        return self.state.rooms_visited

    def state_position(self, start_room: str | None) -> tuple[float | None, float | None]:
        """Where to place the hero on construction: a saved spot, else the room's own."""
        if start_room is not None and start_room != self.state.room:
            return None, None
        if not self.state.rooms_visited:
            return None, None          # a fresh game uses the room's spawn point
        return self.state.x, self.state.y

    # ----- rooms ---------------------------------------------------------
    def enter_room(self, room_id: str, x: float | None = None, y: float | None = None) -> None:
        """Load a room, place the hero and build its objects."""
        self.room = Room.load(room_id, tilesets=self.tilesets)
        self._room_surface = None
        self.entities = [self.hero]
        self.boss = None
        self.dialogue = None
        self.dialogue_after = None
        if x is not None:
            self.hero.x = x
        elif self.room.spawn:
            self.hero.x = self.room.spawn[0]
        if y is not None:
            self.hero.y = y
        elif self.room.spawn:
            self.hero.y = self.room.spawn[1]
        self.last_safe = (self.hero.x, self.hero.y)
        self._build_objects()
        self._remember_room()
        self.update_music()
        fire(self, "enter")

    def _build_objects(self) -> None:
        for spec in self.room.objects:
            self.spawn_from_spec(spec)
        self._respawn_triggered_objects()

    def _respawn_triggered_objects(self) -> None:
        """Re-place objects a one-shot trigger created on an earlier visit.

        A chest that appears when a room is cleared must still be there when
        the player comes back for it; the trigger itself has already fired, so
        the object is rebuilt here and reads its own flag to know whether it
        was opened.
        """
        for trigger in self.room.triggers:
            flag = trigger.get("flag")
            if not flag or not self.state.flag(str(flag)):
                continue
            for action in trigger.get("do", []):
                if "spawn" in action:
                    self.spawn_from_spec(dict(action["spawn"]))

    def spec_applies(self, spec: dict[str, Any]) -> bool:
        """Whether a room-object entry is live right now (time of day, flags)."""
        if spec.get("if_night") and not self.is_night:
            return False
        if spec.get("if_day") and self.is_night:
            return False
        flag = spec.get("if_flag")
        if flag and not self.state.flag(str(flag)):
            return False
        unless = spec.get("unless_flag")
        if unless and self.state.flag(str(unless)):
            return False
        return True

    def spawn_from_spec(self, spec: dict[str, Any]) -> Entity | None:
        """Create one entity from a room-object entry (``kind`` picks the class)."""
        if not self.spec_applies(spec):
            return None
        kind = str(spec.get("kind", ""))
        if kind == "enemy":
            return self._spawn_enemy(spec)
        obj = build(self, spec)
        if obj is None or not obj.alive:
            return None
        self.spawn(obj)
        return obj

    def _spawn_enemy(self, spec: dict[str, Any]) -> Entity | None:
        definition = self.enemy_defs.get(str(spec.get("type", "")))
        if definition is None:
            return None
        col, row = spec.get("at", (0, 0))
        cls = Boss if definition.raw.get("boss") else Enemy
        enemy = cls(definition, col * TILE, row * TILE, self.rng)
        if isinstance(enemy, Boss):
            self.boss = enemy
        self.spawn(enemy)
        return enemy

    def _remember_room(self) -> None:
        if self.room.id not in self.state.rooms_visited:
            self.state.rooms_visited.append(self.room.id)
        if self.room.dungeon:
            if self.state.dungeon != self.room.dungeon:
                self.state.enter_dungeon(self.room.dungeon)
            progress = self.state.progress(self.room.dungeon)
            if self.room.id not in progress.rooms:
                progress.rooms.append(self.room.id)
            dungeon = self.content.dungeons.get(self.room.dungeon)
            if dungeon is not None:
                self.state.respawn_room = dungeon.entrance
                self.state.respawn_x, self.state.respawn_y = dungeon.entrance_spawn
        elif self.state.dungeon:
            self.state.sync_keys()
            self.state.enter_dungeon("")
        if not self.room.dungeon and not self.room.id.startswith("house"):
            self.state.respawn_room = self.room.id
            self.state.respawn_x, self.state.respawn_y = self.room.spawn
        self.state.room = self.room.id

    def update_music(self) -> None:
        """Pick the track for the current room."""
        track = self.room.music
        if not track and self.room.dungeon:
            dungeon = self.content.dungeons.get(self.room.dungeon)
            track = dungeon.music if dungeon else ""
        if not track and self.room.outdoors:
            track = "overworld_night" if self.is_night else "overworld_day"
        self.audio.play_music(track or "overworld_day")

    @property
    def is_night(self) -> bool:
        """True while the mist is up. The clock only runs outdoors."""
        phase = (self.state.minutes_of_day % DAY_LENGTH) / DAY_LENGTH
        return NIGHT_FROM <= phase < NIGHT_TO

    @property
    def draw_region(self) -> str:
        """Palette the current room draws with, night included."""
        if self.room.outdoors and self.is_night:
            return "night"
        return self.room.palette_region

    def tick_clock(self, seconds: float) -> None:
        """Advance the day/night clock; indoors and underground time stands still."""
        if self.room.outdoors:
            was = self.is_night
            self.state.minutes_of_day = (self.state.minutes_of_day + seconds) % DAY_LENGTH
            if self.is_night != was:
                self._room_surface = None
                self.update_music()

    def room_surface(self) -> pygame.Surface:
        """The current room's tile layer, rendered once and cached per palette."""
        if self._room_surface is None or self._surface_night != self.is_night:
            self._room_surface = self.room.render(self.assets, self.draw_region)
            self._surface_night = self.is_night
        return self._room_surface

    def set_tile(self, col: int, row: int, char: str) -> None:
        """Change a tile and repaint it on the cached room surface."""
        self.room.set_tile(col, row, char)
        self.room.draw_tile(self.room_surface(), self.assets, col, row, self.draw_region)

    def warp(self, room_id: str, x: float | None = None, y: float | None = None) -> None:
        """Jump straight to a room (stairs, debug, loading a save)."""
        self.transition = None
        self.enter_room(room_id, x, y)
        self.save_position()

    def save_position(self) -> None:
        """Record where the hero is, for autosave and respawn."""
        self.state.room = self.room.id
        self.state.x, self.state.y = self.hero.x, self.hero.y
        self.state.facing = self.hero.facing

    # ----- entity services -----------------------------------------------
    def spawn(self, entity: Entity) -> Entity:
        """Add an entity to the room."""
        self.entities.append(entity)
        return entity

    def enemies(self) -> list[Enemy]:
        """Living enemies in the room."""
        return [e for e in self.entities if isinstance(e, Enemy) and e.alive]

    def blocked(self, rect: pygame.Rect, ignore: Entity | None = None) -> bool:
        """True if a rect hits a blocking tile or a solid entity."""
        passable = HOPPABLE if (ignore is self.hero and self.hero.airborne) else frozenset()
        if self.room.blocked(rect, passable):
            return True
        for ent in self.entities:
            if ent is ignore or not ent.alive or not ent.blocks_movement:
                continue
            if isinstance(ent, Door) and not ent.blocks:
                continue
            if ent.body_rect().colliderect(rect):
                return True
        return False

    def drop_from(self, x: float, y: float, table: str) -> Pickup | None:
        """Roll a drop table at a position."""
        return spawn_drop(self, x, y, table)

    def spawn_projectile(self, source: Entity, dx: float, dy: float,
                         params: dict[str, Any]) -> Projectile:
        """Fire a shot from an enemy."""
        speed = float(params.get("shot_speed", 1.4))
        cx, cy = source.center
        shot = Projectile(cx - 4, cy - 4, dx * speed, dy * speed,
                          str(params.get("shot", "shot_ember")),
                          int(params.get("shot_damage", 1)))
        self.audio.play("shoot")
        return self.spawn(shot)

    def shake(self, frames: int = 12) -> None:
        """Shake the screen for a few frames."""
        self.shake_timer = max(self.shake_timer, frames)

    def trigger(self, event: str, value: Any = None) -> int:
        """Fire the room's triggers for an event."""
        return fire(self, event, value)

    def dungeon_progress(self) -> Any:
        """Progress record for the dungeon the hero is in, or None."""
        return self.state.progress(self.room.dungeon) if self.room.dungeon else None

    # ----- dialogue ------------------------------------------------------
    def say(self, key: str, choice: tuple[str, str] | None = None, after: Any = None) -> TextBox:
        """Open the dialogue box on a text key (or a literal string)."""
        pages = self.textdb.pages(key) if self.textdb.has(key) else [key]
        self.dialogue = TextBox(pages, self.text_speed, choice)
        self.dialogue_after = after
        return self.dialogue

    def request_shop(self, spec: dict[str, Any]) -> None:
        """Ask the game to open a shop screen after this conversation."""
        self.pending_shop = spec

    def npc_line(self, spec: dict[str, Any]) -> str:
        """Pick an NPC's line for the current story state: later flags win."""
        lines = spec.get("lines")
        if isinstance(lines, list):
            for entry in reversed(lines):
                flag = entry.get("if_flag")
                if flag is None or self.state.flag(str(flag)):
                    return str(entry.get("text", ""))
        return str(spec.get("text", "npc.hello"))

    def _update_dialogue(self) -> None:
        box = self.dialogue
        if box is None:
            return
        result = box.update(self.input)
        if result == "typed":
            self.audio.play("text")
        if box.done:
            self.dialogue = None
            after, self.dialogue_after = self.dialogue_after, None
            self.audio.play("text_end")
            if after is not None:
                after(box.result)

    # ----- items and rewards ---------------------------------------------
    def grant(self, item: str, amount: int = 1) -> None:
        """Give an item, key, currency or dungeon find, with the right fanfare."""
        rewards.grant(self, item, amount)

    def give_item(self, item: str) -> None:
        """Add a real inventory item and announce it."""
        rewards.give_item(self, item)

    def take_reward(self, what: str, spec: dict[str, Any]) -> None:
        """Pick up a heart piece, heart container, seashell or Flame."""
        rewards.take_reward(self, what, spec)

    def leave_dungeon(self, _result: int | None = None) -> None:
        """After taking a Flame, step back outside to the dungeon's return room."""
        dungeon = self.content.dungeons.get(self.room.dungeon)
        if dungeon is not None and dungeon.return_room:
            self.warp(dungeon.return_room)

    def boss_defeated(self, boss: Boss) -> None:
        """A boss died: shake, leave its reward and tell the room."""
        self.shake(30)
        self.state.set_flag(f"boss:{boss.definition.id}", 1)
        if boss.reward:
            col, row = boss.col_row()
            self.spawn_from_spec({"kind": "reward", "what": boss.reward, "at": [col, row],
                                  "flag": f"reward:{boss.definition.id}"})
        self.boss = None
        self.trigger("boss_dead", boss.definition.id)

    # ----- hero actions ---------------------------------------------------
    def try_interact(self, hero: Hero) -> bool:
        """A press in front of the hero: talk, read, open, unlock or push."""
        return actions.try_interact(self, hero)

    def use_item(self, hero: Hero, item: str | None) -> None:
        """Use whatever is in a B/X/Y slot."""
        actions.use_item(self, hero, item)

    def sword_hit(self, hero: Hero, rect: pygame.Rect) -> None:
        """Apply a sword rect to enemies, crystals and cuttable tiles."""
        actions.sword_hit(self, hero, rect)

    def hit_tiles(self, rect: pygame.Rect, kind: str) -> int:
        """Clear every tile under ``rect`` that this tool removes."""
        return actions.hit_tiles(self, rect, kind)

    def throw_carried(self, hero: Hero) -> None:
        """Throw the rock or pot the hero is holding."""
        actions.throw_carried(self, hero)

    def stun_boss(self, state: str = "stunned") -> None:
        """Put the room's boss into a vulnerable state."""
        if self.boss is not None:
            self.boss.stun(self, state)

    def on_hero_death(self) -> None:
        """Zelda rules: back to the dungeon entrance or the village, items kept."""
        state = self.state
        state.deaths += 1
        state.health = state.max_hearts * 2
        self.audio.stop_music(200)
        self.warp(state.respawn_room, state.respawn_x, state.respawn_y)

    # ----- frame ----------------------------------------------------------
    def update(self) -> None:
        """One logic frame."""
        self.audio.tick()
        if self.shake_timer > 0:
            self.shake_timer -= 1
        if self.dialogue is not None:
            self._update_dialogue()
            return
        if self.transition is not None:
            self.transition.update()
            if self.transition.done:
                self.transition = None
            return
        for ent in list(self.entities):
            if ent.alive:
                ent.update(self)
        self.entities = [e for e in self.entities if e.alive]
        self._check_hazards()
        if not self.enemies():
            self.trigger("all_enemies_dead")
        self._check_exit()

    def _check_hazards(self) -> None:
        hero = self.hero
        if hero.airborne or hero.invulnerable:
            return
        hazard = self.room.hazard_at(hero.body_rect())
        if hazard is None:
            if not self.room.blocked(hero.body_rect()):
                self.last_safe = (hero.x, hero.y)
            return
        self.audio.play("fall" if hazard is Collision.PIT else "lava")
        hero.x, hero.y = self.last_safe
        hero.hurt(self, 1)

    def _check_exit(self) -> None:
        direction = self.exit_direction()
        if direction is None:
            return
        if direction in self.room.exits:
            self.start_transition(direction)
        else:
            self.hero.clamp_to_room()

    def exit_direction(self) -> str | None:
        """Which edge the hero has walked past, if any."""
        cx = self.hero.x + self.hero.width / 2
        cy = self.hero.y + self.hero.height / 2
        if cx < -EDGE_MARGIN + 8:
            return "west"
        if cx > PLAY_W + EDGE_MARGIN - 8:
            return "east"
        if cy < -EDGE_MARGIN + 8:
            return "north"
        if cy > PLAY_H + EDGE_MARGIN - 8:
            return "south"
        return None

    def start_transition(self, direction: str) -> None:
        """Begin a flip-scroll to the room through the given exit."""
        target = self.room.exits[direction]
        old = self.room_surface().copy()
        self.enter_room(target, *self._entry_position(direction))
        self._snap_into_doorway(direction)
        new = self.room_surface().copy()
        for ent in sorted(self.entities, key=lambda e: (e.depth, e.layer)):
            ent.draw(new, self.assets, 0)
        self.transition = FlipScroll(direction, old, new)
        self.save_position()

    def _snap_into_doorway(self, direction: str) -> None:
        """Line the hero up with the doorway he just stepped through.

        Neighbouring screens do not always put their gap in the same column,
        so arriving with the old x can drop Wren inside a cliff. Slide him to
        the nearest opening on the edge he came in through.
        """
        from eldermoor.config import PLAY_COLS, PLAY_ROWS
        from eldermoor.tilemap import BLOCKING
        hero = self.hero
        if direction in ("north", "south"):
            row = 0 if direction == "south" else PLAY_ROWS - 1
            cols = [c for c in range(PLAY_COLS)
                    if self.room.collision_at(c, row) not in BLOCKING]
            if not cols:
                return
            centre = (hero.x + hero.width / 2) / TILE - 0.5
            col = min(cols, key=lambda c: abs(c - centre))
            hero.x = float(col * TILE + (TILE - hero.width) // 2)
        else:
            col = 0 if direction == "east" else PLAY_COLS - 1
            rows = [r for r in range(PLAY_ROWS)
                    if self.room.collision_at(col, r) not in BLOCKING]
            if not rows:
                return
            centre = (hero.y + hero.height / 2) / TILE - 0.5
            row = min(rows, key=lambda r: abs(r - centre))
            hero.y = float(row * TILE + (TILE - hero.height) // 2)
        self.last_safe = (hero.x, hero.y)

    def _entry_position(self, direction: str) -> tuple[float, float]:
        h = self.hero
        if direction == "east":
            return 0.0, h.y
        if direction == "west":
            return float(PLAY_W - h.width), h.y
        if direction == "south":
            return h.x, 0.0
        return h.x, float(PLAY_H - h.height)

    # ----- drawing --------------------------------------------------------
    @property
    def shake_offset(self) -> tuple[int, int]:
        """Screen-shake offset for this frame."""
        if self.shake_timer <= 0:
            return 0, 0
        return (self.shake_timer % 3) - 1, (self.shake_timer % 2)

    def draw(self, target: pygame.Surface, oy: int = PLAY_Y) -> None:
        """Draw the play area at vertical offset ``oy``."""
        if self.transition is not None:
            self.transition.draw(target, oy)
            return
        sx, sy = self.shake_offset
        target.blit(self.room_surface(), (sx, oy + sy))
        for ent in sorted(self.entities, key=lambda e: (e.depth, e.layer)):
            ent.draw(target, self.assets, oy + sy)
        if self.room.dark:
            self._draw_darkness(target, oy + sy)
        if self.boss is not None and self.boss.alive:
            self.boss.draw_bar(target, self.assets, self.textdb.get(self.boss.name_key))
        if self.dialogue is not None:
            self.dialogue.draw(target, self.assets)

    def _draw_darkness(self, target: pygame.Surface, oy: int) -> None:
        """A dark room: black except a circle around Wren, wider with the Lantern lit.

        Lighting the room's torch clears it for good, which is what the
        Lantern is for.
        """
        if any(isinstance(e, Torch) and e.lit for e in self.entities):
            return
        radius = 30
        if self.state.has("lantern"):
            radius = 76 if self.hero.lantern_timer > 0 else 62
        shade = pygame.Surface((PLAY_W, PLAY_H), pygame.SRCALPHA)
        shade.fill((2, 2, 8, 248))
        cx, cy = self.hero.center
        for i in range(6):
            r = radius - i * radius // 7
            alpha = 248 - round(248 * (1.0 - i / 6.0) ** 0.6)
            pygame.draw.circle(shade, (2, 2, 8, alpha), (round(cx), round(cy)), r)
        target.blit(shade, (0, oy))
