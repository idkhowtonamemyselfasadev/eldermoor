"""Room scripting: a room's ``triggers`` list turns events into actions.

    {"on": "all_enemies_dead", "do": [{"open": "north"}], "once": true}
    {"on": "torches_lit", "count": 4, "do": [{"open": "a"}, {"jingle": "puzzle"}]}
    {"on": "switch", "id": "s1", "do": [{"reveal": [9, 5, "<"]}]}

``once`` (the default for anything with a ``flag``) means the trigger fires a
single time ever; the flag is global and saved, so a solved room stays solved.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eldermoor.objects import Door, Torch

if TYPE_CHECKING:
    from eldermoor.world import World

EVENTS = ("enter", "all_enemies_dead", "switch", "switch_released", "torch_lit", "torches_lit",
          "crystal", "block_moved", "chest_opened", "door_opened", "enemy_died", "boss_dead",
          "timer", "flag", "item_used")


def _matches(world: World, trigger: dict[str, Any], event: str, value: Any) -> bool:
    """True if this trigger fires for the event."""
    if trigger.get("on") != event:
        return False
    if "id" in trigger and str(trigger["id"]) != str(value):
        return False
    if event == "torches_lit":
        want = int(trigger.get("count", 0))
        lit = sum(1 for e in world.entities if isinstance(e, Torch) and e.lit)
        return lit >= want
    if event == "flag":
        return bool(world.state.flag(str(trigger.get("flag_name", ""))))
    return True


def fire(world: World, event: str, value: Any = None) -> int:
    """Run every trigger in the current room that matches. Returns how many fired."""
    fired = 0
    for trigger in world.room.triggers:
        if not _matches(world, trigger, event, value):
            continue
        flag = trigger.get("flag")
        once = bool(trigger.get("once", flag is not None))
        key = flag or f"{world.room.id}:trig:{world.room.triggers.index(trigger)}"
        if once and world.state.flag(key):
            continue
        if once:
            world.state.set_flag(key, 1)
        run(world, list(trigger.get("do", [])))
        fired += 1
    return fired


def run(world: World, actions: list[dict[str, Any]]) -> None:
    """Perform a trigger's action list in order."""
    for action in actions:
        for name, argument in action.items():
            handler = ACTIONS.get(name)
            if handler is not None:
                handler(world, argument)


# ----- actions -----------------------------------------------------------
def _open(world: World, which: Any) -> None:
    """Open every door whose id matches (or all of them for '*')."""
    for ent in world.entities:
        if isinstance(ent, Door) and (which == "*" or str(ent.id) == str(which)):
            ent.force_open(world)


def _reveal(world: World, spec: Any) -> None:
    """Replace a tile: [col, row, legend_char]."""
    col, row, char = int(spec[0]), int(spec[1]), str(spec[2])
    world.set_tile(col, row, char)
    world.audio.play("secret")


def _spawn(world: World, spec: Any) -> None:
    """Spawn an object or an enemy described like a room object entry."""
    world.spawn_from_spec(dict(spec))


def _jingle(world: World, name: Any) -> None:
    """Play a sound."""
    world.audio.play(str(name))


def _set_flag(world: World, name: Any) -> None:
    """Set a global flag."""
    world.state.set_flag(str(name), 1)


def _clear_flag(world: World, name: Any) -> None:
    """Clear a global flag."""
    world.state.set_flag(str(name), 0)


def _say(world: World, key: Any) -> None:
    """Show a dialogue box."""
    world.say(str(key))


def _give(world: World, item: Any) -> None:
    """Hand the player an item, with the usual fanfare."""
    world.grant(str(item))


def _shake(world: World, frames: Any) -> None:
    """Shake the screen."""
    world.shake(int(frames))


def _stun_boss(world: World, state: Any) -> None:
    """Put the room's boss into a vulnerable state."""
    world.stun_boss(str(state) if state else "stunned")


def _warp(world: World, spec: Any) -> None:
    """Move the hero to another room: [room_id] or [room_id, x, y]."""
    if isinstance(spec, str):
        world.warp(spec)
    else:
        world.warp(str(spec[0]), float(spec[1]), float(spec[2]))


ACTIONS = {
    "open": _open, "reveal": _reveal, "spawn": _spawn, "jingle": _jingle,
    "set_flag": _set_flag, "clear_flag": _clear_flag, "say": _say, "give": _give,
    "shake": _shake, "stun_boss": _stun_boss, "warp": _warp,
}
