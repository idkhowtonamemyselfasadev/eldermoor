"""Conversations: quest givers, minigame hosts and which line an NPC says.

The world owns the dialogue box; this module owns what goes in it when the
person in front of Wren is a quest giver, a game host, or a villager with
several things to say depending on how far along the story is.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eldermoor import quests

if TYPE_CHECKING:
    from eldermoor.world import World


def quest(world: World, quest_id: str) -> bool:
    """One conversation with a quest giver: ask, wait, pay or reminisce."""
    definition = world.content.quests.get(quest_id)
    if definition is None:
        world.say("npc.hello")
        return True
    state = world.state
    if quest_id in state.quests:
        world.say(definition.line("done"))
        return True
    if not state.flag(definition.start_flag):
        state.set_flag(definition.start_flag, 1)
        world.say(definition.line("ask"))
        return True
    if quests.satisfied(world, definition):
        quests.pay(world, definition)
        world.say(definition.line("thanks"))
    else:
        world.say(definition.line("wait"))
    return True


def minigame(world: World, game_id: str, spec: dict[str, Any]) -> bool:
    """Take the fee and hand the screen over, once the host stops talking."""
    definition = world.content.minigames.get(game_id)
    if definition is None:
        world.say("npc.hello")
        return True
    if world.state.embers < definition.cost:
        world.say("game.poor")
        return True

    def pay(_result: int | None) -> None:
        world.state.embers -= definition.cost
        world.pending_minigame = game_id

    world.say(str(spec.get("text", definition.greeting)), after=pay)
    return True


def npc_line(world: World, spec: dict[str, Any]) -> str:
    """Pick an NPC's line for the current story state: later flags win."""
    lines = spec.get("lines")
    if isinstance(lines, list):
        for entry in reversed(lines):
            flag = entry.get("if_flag")
            if flag is None or world.state.flag(str(flag)):
                return str(entry.get("text", ""))
    return str(spec.get("text", "npc.hello"))
