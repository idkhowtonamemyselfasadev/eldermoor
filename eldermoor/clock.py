"""The day/night clock, and which track a room plays under it.

A day is eight minutes long and only runs outdoors: indoors and underground
the mist never comes in, so the clock stands still and the music does not
change under your feet.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eldermoor.state import GameState
    from eldermoor.world import World

#: seconds in one full day
DAY_LENGTH = 8 * 60.0
#: the slice of the day the mist owns
NIGHT_FROM = 0.55
NIGHT_TO = 0.95


def is_night(state: GameState) -> bool:
    """True while the mist is up."""
    phase = (state.minutes_of_day % DAY_LENGTH) / DAY_LENGTH
    return NIGHT_FROM <= phase < NIGHT_TO


def advance(state: GameState, seconds: float) -> None:
    """Move the clock on, wrapping at the end of the day."""
    state.minutes_of_day = (state.minutes_of_day + seconds) % DAY_LENGTH


def track_for(world: World) -> str:
    """The music the current room should be playing."""
    track = world.room.music
    if not track and world.room.dungeon:
        dungeon = world.content.dungeons.get(world.room.dungeon)
        track = dungeon.music if dungeon else ""
    if not track and world.room.outdoors:
        track = "overworld_night" if is_night(world.state) else "overworld_day"
    return track or "overworld_day"
