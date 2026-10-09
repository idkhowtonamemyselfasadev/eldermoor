"""Walking into a room: loading it, placing the heroes, building what is in it.

A room is re-read from JSON on every entry, so anything the player broke
grows back; anything permanent lives in a flag. Objects a one-shot trigger
created on an earlier visit are rebuilt here, because a chest that appeared
when a room was cleared has to still be there when the player comes back.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eldermoor import postgame
from eldermoor.bosses import Boss
from eldermoor.config import TILE
from eldermoor.enemies import Enemy
from eldermoor.objects import build
from eldermoor.script import fire
from eldermoor.tilemap import Room

if TYPE_CHECKING:
    from eldermoor.entities import Entity
    from eldermoor.world import World


def enter(world: World, room_id: str, x: float | None = None,
          y: float | None = None) -> None:
    """Load a room, place the lamplighters and build its objects."""
    world.room = Room.load(room_id, tilesets=world.tilesets)
    world._room_surface = None
    world.entities = [world.hero] + ([world.hero2] if world.hero2 is not None else [])
    world.boss = None
    world.dialogue = None
    world.dialogue_after = None
    hero = world.hero
    if x is not None:
        hero.x = x
    elif world.room.spawn:
        hero.x = world.room.spawn[0]
    if y is not None:
        hero.y = y
    elif world.room.spawn:
        hero.y = world.room.spawn[1]
    world.last_safe = (hero.x, hero.y)
    if world.hero2 is not None:                 # player two comes along
        world.hero2.x, world.hero2.y = hero.x, hero.y
        world.hero2.facing = hero.facing
    build_objects(world)
    remember(world)
    world.update_music()
    fire(world, "enter")


def build_objects(world: World) -> None:
    """Spawn everything the room lists, then everything a trigger left behind."""
    for spec in world.room.objects:
        spawn_spec(world, spec)
    respawn_triggered(world)


def respawn_triggered(world: World) -> None:
    """Re-place objects a one-shot trigger created on an earlier visit."""
    for trigger in world.room.triggers:
        flag = trigger.get("flag")
        if not flag or not world.state.flag(str(flag)):
            continue
        for action in trigger.get("do", []):
            if "spawn" in action:
                spawn_spec(world, dict(action["spawn"]))


def applies(world: World, spec: dict[str, Any]) -> bool:
    """Whether a room-object entry is live right now (time of day, flags)."""
    if spec.get("if_night") and not world.is_night:
        return False
    if spec.get("if_day") and world.is_night:
        return False
    flag = spec.get("if_flag")
    if flag and not world.state.flag(str(flag)):
        return False
    unless = spec.get("unless_flag")
    if unless and world.state.flag(str(unless)):
        return False
    return True


def spawn_spec(world: World, spec: dict[str, Any]) -> Entity | None:
    """Create one entity from a room-object entry (``kind`` picks the class)."""
    if not applies(world, spec):
        return None
    if str(spec.get("kind", "")) == "enemy":
        return spawn_enemy(world, spec)
    obj = build(world, spec)
    if obj is None or not obj.alive:
        return None
    world.spawn(obj)
    return obj


def spawn_enemy(world: World, spec: dict[str, Any]) -> Entity | None:
    """One creature, scaled for the kind of file this is."""
    definition = world.enemy_defs.get(str(spec.get("type", "")))
    if definition is None:
        return None
    col, row = spec.get("at", (0, 0))
    cls = Boss if definition.raw.get("boss") else Enemy
    enemy = cls(definition, col * TILE, row * TILE, world.rng)
    enemy.hp = postgame.scale_hp(world.state, enemy.hp)
    enemy.contact_damage = postgame.scale_damage(world.state, enemy.contact_damage)
    if isinstance(enemy, Boss):
        world.boss = enemy
    world.spawn(enemy)
    return enemy


def remember(world: World) -> None:
    """Note the room as visited and work out where dying puts you back."""
    state = world.state
    room = world.room
    if room.id not in state.rooms_visited:
        state.rooms_visited.append(room.id)
    if room.dungeon:
        if state.dungeon != room.dungeon:
            state.enter_dungeon(room.dungeon)
        progress = state.progress(room.dungeon)
        if room.id not in progress.rooms:
            progress.rooms.append(room.id)
        dungeon = world.content.dungeons.get(room.dungeon)
        if dungeon is not None:
            state.respawn_room = dungeon.entrance
            state.respawn_x, state.respawn_y = dungeon.entrance_spawn
    elif state.dungeon:
        state.sync_keys()
        state.enter_dungeon("")
    if not room.dungeon and not room.id.startswith("house"):
        state.respawn_room = room.id
        state.respawn_x, state.respawn_y = room.spawn
    state.room = room.id
