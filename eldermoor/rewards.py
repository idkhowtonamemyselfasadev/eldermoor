"""What happens when Wren picks something up: items, keys, hearts and Flames."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eldermoor.world import World


# ----- items and rewards ---------------------------------------------
def grant(world: World, item: str, amount: int = 1) -> None:
    """Give an item, key, currency or dungeon find, with the right fanfare."""
    state = world.state
    if not item:
        return
    if item == "key":
        state.keys += amount
        state.sync_keys()
        world.audio.play("key")
        return
    if item in ("bigkey", "map", "compass"):
        progress = world.dungeon_progress()
        if progress is not None:
            setattr(progress, "big_key" if item == "bigkey" else item, True)
        world.audio.play("bigkey" if item == "bigkey" else "item_get")
        world.say(f"get.{item}")
        return
    if item == "embers":
        state.embers = min(999, state.embers + amount)
        world.audio.play("ember_big")
        return
    if item == "heart":
        state.heal(amount * 2)
        world.audio.play("heart")
        return
    world.give_item(item)

def give_item(world: World, item: str) -> None:
    """Add a real inventory item, auto-assigning the first active one to B."""
    state = world.state
    definition = world.items.get(item)
    state.give(item)
    if item == "sword":
        state.sword_level = max(1, state.sword_level)
    elif item == "shield":
        state.shield_level = max(1, state.shield_level)
    elif item == "bombs":
        state.max_bombs = max(10, state.max_bombs)
        state.bombs = state.max_bombs
    elif item == "bow":
        state.max_arrows = max(30, state.max_arrows)
        state.arrows = state.max_arrows
    if definition is not None and definition.assignable and item not in state.slots:
        for index in range(3):
            if state.slots[index] is None:
                state.assign(index, item)
                break
    world.audio.play("item_get")
    world.say(f"get.{item}")

def take_reward(world: World, what: str, spec: dict[str, Any]) -> None:
    """Pick up a heart piece, heart container, seashell or Flame."""
    state = world.state
    if what == "heart_piece":
        made = state.add_heart_piece()
        world.audio.play("heart_container" if made else "secret")
        world.say("get.heart_piece_full" if made else "get.heart_piece")
    elif what == "heart_container":
        state.add_heart_container()
        world.audio.play("heart_container")
        world.say("get.heart_container")
    elif what == "shell":
        state.seashells += 1
        world.audio.play("shell")
        world.say("get.shell")
    elif what == "flame":
        dungeon_id = str(spec.get("dungeon", world.room.dungeon))
        progress = state.progress(dungeon_id)
        progress.flame = True
        progress.cleared = True
        state.give(str(spec.get("item", "flame_ember")))
        world.audio.play("flame_get")
        world.say(f"get.flame.{dungeon_id}", after=world.leave_dungeon)
