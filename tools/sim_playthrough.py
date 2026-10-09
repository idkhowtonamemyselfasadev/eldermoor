#!/usr/bin/env python3
"""Walk the critical path headlessly and report how long the game is.

The bot drives the real game: the real input map, the real collision, the
real enemies.  It navigates with a breadth-first search over walkable tiles,
swings at whatever is in front of it, opens chests and takes stairs.  What
comes out is *bot time*, which is then scaled into a human estimate by the
factors in ESTIMATE, each of which is printed so the number can be argued
with.

    python tools/sim_playthrough.py [--quiet] [--max-frames N]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from eldermoor.config import FPS, PLAY_COLS, PLAY_ROWS, TILE  # noqa: E402
from eldermoor.enemies import Enemy  # noqa: E402
from eldermoor.objects import Chest, Door, Reward, Stairs, Torch  # noqa: E402
from eldermoor.tilemap import BLOCKING  # noqa: E402

#: how a bot minute turns into a player minute
ESTIMATE = {
    "explore": 3.2,        # a player wanders, backtracks, re-reads and dies
    "combat": 1.6,         # the bot does not retreat or heal
    "reading": 1.15,       # dialogue at a human text speed
}
BACK = {"north": "south", "south": "north", "east": "west", "west": "east"}


class _Facing:
    """Stand-in attacker used to ask an enemy whether a hit would land."""

    def __init__(self, facing: str) -> None:
        self.facing = facing
EDGE_CELLS = {
    "north": [(c, 0) for c in range(PLAY_COLS)],
    "south": [(c, PLAY_ROWS - 1) for c in range(PLAY_COLS)],
    "west": [(0, r) for r in range(PLAY_ROWS)],
    "east": [(PLAY_COLS - 1, r) for r in range(PLAY_ROWS)],
}


class Bot:
    """Drives a Game towards a list of goals, one room at a time."""

    patience = 25000              # frames allowed per goal before giving up on it

    def __init__(self, game, goals: list[tuple[str, str]]) -> None:
        self.game = game
        self.goals = list(goals)
        self.frames = 0
        self.log: list[tuple[str, int]] = []
        self.stuck = 0
        self.last_pos = (0.0, 0.0)
        self.travel_side: str | None = None
        self.goal_since = 0
        self.travel_next: str | None = None
        self.blocked_links: set[tuple[str, str]] = set()
        self.wiggle = 0
        self.wiggle_dir = "down"

    # ----- graph ---------------------------------------------------------
    def room_graph(self) -> dict[str, set[str]]:
        """Room id -> rooms you can step into from it."""
        from eldermoor.tilemap import Room, list_rooms
        graph: dict[str, set[str]] = {}
        for room_id in list_rooms():
            room = Room.load(room_id)
            links = set(room.exits.values())
            links |= {str(s["to"]) for s in room.objects if s.get("kind") == "stairs"}
            graph[room_id] = links
        return graph

    def route_to(self, graph: dict[str, set[str]], start: str, goal: str) -> list[str]:
        """Shortest room path, empty if there is none."""
        if start == goal:
            return [start]
        seen = {start: [start]}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for nxt in graph.get(node, ()):
                if nxt in seen or (node, nxt) in self.blocked_links:
                    continue
                seen[nxt] = seen[node] + [nxt]
                if nxt == goal:
                    return seen[nxt]
                queue.append(nxt)
        return []

    # ----- tile navigation -----------------------------------------------
    def holding_ground(self) -> bool:
        """True while the goal is to clear this room: do not wander off the edges.

        Rooms reload when you leave, so stepping out mid-fight resurrects
        everything. A player knows that; the bot has to be told.
        """
        goal = self.goal()
        return (goal is not None and goal[1] in ("clear", "boss")
                and goal[0] == self.game.world.room.id)

    def passable(self) -> set[tuple[int, int]]:
        """Cells the hero can stand on right now, tools included."""
        world = self.game.world
        room = world.room
        state = world.state
        blocked = set()
        for ent in world.entities:
            if ent.blocks_movement and ent is not world.hero:
                if isinstance(ent, Door) and ent.open:
                    continue
                blocked.add(ent.col_row())
        hold = self.holding_ground()
        out = set()
        for row in range(PLAY_ROWS):
            for col in range(PLAY_COLS):
                if (col, row) in blocked:
                    continue
                if hold and (row in (0, PLAY_ROWS - 1) or col in (0, PLAY_COLS - 1)):
                    continue
                tile = room.tile_at(col, row)
                if tile is None or tile.collision not in BLOCKING:
                    out.add((col, row))
                elif tile.interact == "cut" and state.sword_level > 0:
                    out.add((col, row))
                elif tile.interact == "burn" and state.has("lantern"):
                    out.add((col, row))
        return out

    def path(self, target: set[tuple[int, int]]) -> list[tuple[int, int]]:
        """Cell path from the hero to the nearest target cell."""
        cells = self.passable()
        start = self.game.world.hero.col_row()
        if start not in cells:
            cells.add(start)
        seen = {start: [start]}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in target:
                return seen[node]
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (node[0] + dc, node[1] + dr)
                if nxt in cells and nxt not in seen:
                    seen[nxt] = seen[node] + [nxt]
                    queue.append(nxt)
        return []

    # ----- goals ---------------------------------------------------------
    def goal(self) -> tuple[str, str] | None:
        """The goal being worked on, if any."""
        return self.goals[0] if self.goals else None

    def goal_entities(self, kind: str) -> list:
        """Entities in this room that satisfy the current goal kind."""
        world = self.game.world
        if kind == "chest":
            return [e for e in world.entities if isinstance(e, Chest) and not e.opened]
        if kind == "reward":
            return [e for e in world.entities if isinstance(e, Reward) and e.alive]
        if kind == "stairs":
            return [e for e in world.entities if isinstance(e, Stairs)]
        if kind == "torches":
            return [e for e in world.entities if isinstance(e, Torch) and not e.lit]
        if kind in ("clear", "boss"):
            return [e for e in world.entities if isinstance(e, Enemy) and e.alive]
        return []

    def current_target(self, graph: dict[str, set[str]]) -> set[tuple[int, int]]:
        """Cells to walk to this frame: the goal in this room, or the way onward."""
        world = self.game.world
        goal = self.goal()
        if goal is None:
            return set()
        goal_room, goal_kind = goal
        self.travel_side = None
        self.travel_next = None
        if world.room.id == goal_room:
            targets = self.goal_entities(goal_kind)
            if not targets:
                if goal_kind in ("chest", "reward") and self.frames - self.goal_since < 120:
                    return set()      # a trigger may still be about to spawn it
                self.goals.pop(0)
                self.stuck = 0
                self.goal_since = self.frames
                return self.current_target(graph)
            cells = self.passable()
            out: set[tuple[int, int]] = set()
            for ent in targets:
                col, row = ent.col_row()
                if goal_kind == "stairs":
                    out |= {(col, row)}
                    continue
                if goal_kind in ("clear", "boss"):
                    behind = self.behind_cell(ent)
                    if behind and behind in cells:
                        out |= {behind}
                        continue
                    # a boss can end up half inside a wall: settle for any
                    # square next to it that the hero can actually stand on
                    around = {(col + dc, row + dr)
                              for dc in (-1, 0, 1) for dr in (-1, 0, 1)}
                    out |= (around & cells) or {(col, row)}
                    continue
                out |= {(col, row + 1), (col, row - 1), (col + 1, row), (col - 1, row)}
            return out & cells
        route = self.route_to(graph, world.room.id, goal_room)
        if len(route) < 2:
            self.goals.pop(0)
            return set()
        nxt = route[1]
        self.travel_next = nxt
        for side, target in world.room.exits.items():
            if target != nxt:
                continue
            door = self.closed_door_on(side)
            if door is not None:
                if door.lock == "shut":
                    alive = [e for e in world.entities if isinstance(e, Enemy) and e.alive]
                    if alive:
                        cells = self.passable()
                        out = set()
                        for ent in alive:
                            behind = self.behind_cell(ent)
                            out |= {behind} if behind else {ent.col_row()}
                        return out & cells
                col, row = door.col_row()
                near = {(col, row + 1), (col, row - 1), (col + 1, row), (col - 1, row)}
                return near & self.passable()
            self.travel_side = side
            return set(EDGE_CELLS[side])
        for spec in world.room.objects:
            if spec.get("kind") == "stairs" and str(spec["to"]) == nxt:
                return {(int(spec["at"][0]), int(spec["at"][1]))}
        return set()

    def threat_near(self, distance: float = 46.0) -> bool:
        """True when something hostile is close enough to be worth blocking."""
        hero = self.game.world.hero
        return any(isinstance(e, Enemy) and e.alive and e.distance_to(hero) < distance
                   for e in self.game.world.entities)

    def can_hurt(self, ent) -> bool:
        """True if swinging from where the hero stands would actually land."""
        if not isinstance(ent, Enemy):
            return True
        here = self.game.world.hero.col_row()
        col, row = ent.col_row()
        if col > here[0]:
            facing = "right"
        elif col < here[0]:
            facing = "left"
        elif row > here[1]:
            facing = "down"
        else:
            facing = "up"
        return ent.vulnerable_from(_Facing(facing))

    @staticmethod
    def behind_cell(ent) -> tuple[int, int] | None:
        """The cell at an armoured enemy's back, or None for anything else."""
        definition = getattr(ent, "definition", None)
        if definition is None or definition.armour != "front":
            return None
        col, row = ent.col_row()
        dc, dr = {"down": (0, -1), "up": (0, 1), "left": (1, 0), "right": (-1, 0)}[ent.facing]
        return (col + dc, row + dr)

    def closed_door_on(self, side: str):
        """A shut door guarding one of this room's exits, if there is one."""
        edge = set(EDGE_CELLS[side])
        inner = {(c + dc, r + dr) for c, r in edge
                 for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0))}
        for ent in self.game.world.entities:
            if isinstance(ent, Door) and not ent.open and ent.col_row() in (edge | inner):
                return ent
        return None

    def adjacent_door(self):
        """A shut door the hero is standing next to."""
        here = self.game.world.hero.col_row()
        for ent in self.game.world.entities:
            if not isinstance(ent, Door) or ent.open or ent.lock == "shut":
                continue              # a barred door needs the room cleared, not a key
            col, row = ent.col_row()
            if abs(col - here[0]) + abs(row - here[1]) <= 1:
                return ent
        return None

    def adjacent_goal_entity(self):
        """The goal's entity if the hero is standing next to it."""
        goal = self.goal()
        if goal is None or self.game.world.room.id != goal[0] or goal[1] == "stairs":
            return None
        here = self.game.world.hero.col_row()
        for ent in self.goal_entities(goal[1]):
            col, row = ent.col_row()
            if abs(col - here[0]) + abs(row - here[1]) <= 1:
                return ent
        return None

    def face(self, cell: tuple[int, int]) -> None:
        """Press the direction that points at a cell."""
        here = self.game.world.hero.col_row()
        inp = self.game.input
        if cell[0] > here[0]:
            inp.press("right")
        elif cell[0] < here[0]:
            inp.press("left")
        elif cell[1] > here[1]:
            inp.press("down")
        elif cell[1] < here[1]:
            inp.press("up")

    def use_lantern(self) -> bool:
        """Press the button the Lantern sits on. False if it is not assigned."""
        slots = self.game.world.state.slots
        if "lantern" not in slots:
            return False
        self.game.input.press(("b", "x", "y")[slots.index("lantern")])
        return True

    # ----- driving -------------------------------------------------------
    def step(self, graph: dict[str, set[str]]) -> None:
        """One logic frame of bot input."""
        game = self.game
        inp = game.input
        inp.begin_frame()
        inp.release_all()
        world = game.world
        if world.dialogue is not None:
            if self.frames % 2 == 0:
                inp.press("a")
            game.update()
            self.frames += 1
            return
        if game.mode != "play":
            inp.press("b")
            game.update()
            self.frames += 1
            return
        if self.stuck > 40 and self.wiggle == 0 and not self.holding_ground():
            self.wiggle = 24
            self.wiggle_dir = ("up", "down", "left", "right")[self.frames % 4]
        if self.frames - self.goal_since > self.patience and self.goals:
            self.goals.pop(0)        # watchdog: never spin forever on one goal
            self.goal_since = self.frames
        self.act(graph)
        moving = any(inp.is_held(d) for d in ("up", "down", "left", "right"))
        game.update()
        self.frames += 1
        pos = (round(world.hero.x), round(world.hero.y))
        # only "stuck" when it asked to move and did not; fighting in place is fine
        self.stuck = self.stuck + 1 if (moving and pos == self.last_pos) else 0
        self.last_pos = pos

    def act(self, graph: dict[str, set[str]]) -> None:
        """Choose this frame's buttons."""
        world = self.game.world
        inp = self.game.input
        hero = world.hero
        goal = self.goal()
        door = self.adjacent_door()
        if door is not None:
            self.face(door.col_row())
            if self.frames % 3 == 0:
                inp.press("a")
            return
        if self.wiggle > 0:
            self.wiggle -= 1
            inp.press(self.wiggle_dir)
            return
        if self.threat_near() and self.frames % 3 != 0:
            inp.press("l")            # raise the shield between swings
        prize = self.adjacent_goal_entity()
        if prize is not None and not self.can_hurt(prize):
            prize = None              # wrong side of an armoured enemy: go around
        if prize is not None and goal is not None:
            self.face(prize.col_row())
            if self.frames % 3 == 0:
                if goal[1] == "torches":
                    self.use_lantern()
                else:
                    inp.press("a")
            return
        front = hero.front_rect()
        for ent in world.entities:
            if ent is hero or not ent.alive or isinstance(ent, Door):
                continue              # doors are handled above, by cell adjacency
            if not ent.body_rect().colliderect(front.inflate(10, 10)):
                continue
            if isinstance(ent, (Chest, Enemy)) and self.frames % 3 == 0:
                inp.press("a")
                return
        if world.room.interactive_cells(front, "burn") and self.use_lantern():
            return
        if world.room.interactive_cells(front, "cut") and world.state.sword_level > 0:
            if self.frames % 4 == 0:
                inp.press("a")
            return
        self.walk(graph)

    def walk(self, graph: dict[str, set[str]]) -> None:
        """Press the direction that moves along the computed path."""
        target = self.current_target(graph)
        if not target:
            if self.stuck > 180 and self.goals:
                self.goals.pop(0)
                self.stuck = 0
            return
        path = self.path(target)
        if not path and self.travel_next is not None:
            # nothing in this room reaches that doorway: route around it
            self.blocked_links.add((self.game.world.room.id, self.travel_next))
            return
        if len(path) < 2:
            if self.travel_side is not None:
                # standing in the doorway: keep pushing until the screen flips
                self.game.input.press({"north": "up", "south": "down",
                                       "east": "right", "west": "left"}[self.travel_side])
                return
            if self.stuck > 180 and self.goals:
                self.goals.pop(0)
                self.stuck = 0
            return
        hero = self.game.world.hero
        nxt = path[1]
        want_x = nxt[0] * TILE + TILE // 2
        want_y = nxt[1] * TILE + TILE // 2
        rect = hero.body_rect()
        if rect.centerx < want_x - 1:
            self.game.input.press("right")
        elif rect.centerx > want_x + 1:
            self.game.input.press("left")
        if rect.centery < want_y - 1:
            self.game.input.press("down")
        elif rect.centery > want_y + 1:
            self.game.input.press("up")


CRITICAL_PATH: list[tuple[str, str]] = [
    ("house_wren", "chest"),      # the Lamplighter's Blade
    ("t1_01", "arrive"),          # the long walk to the temple door
    ("t1_18", "clear"),           # two Cragguards guard the first small key
    ("t1_18", "chest"),
    ("t1_06", "chest"),           # map (through the first locked door)
    ("t1_08", "chest"),           # compass
    ("t1_09", "clear"),           # Cinderjaw
    ("t1_09", "chest"),           # the Lantern
    ("t1_04", "torches"),         # four wicks
    ("t1_04", "chest"),           # small key
    ("t1_10", "chest"),           # dark room, small key
    ("t1_17", "chest"),           # lava corridor, small key
    ("t1_25", "chest"),           # the Great Key
    ("t1_31", "torches"),         # light the arena to open the Maw
    ("t1_31", "clear"),           # the Ashen Maw
    ("t1_31", "reward"),          # the Flame
]


def run(max_frames: int, quiet: bool) -> dict[str, float]:
    """Run the bot and return a report."""
    pygame.init()
    pygame.display.set_mode((320, 240))
    from eldermoor.game import Game
    from eldermoor.input import Input
    game = Game(inp=Input(), start_room="village_00")
    game.state.respawn_room = "village_00"
    # The route walks past the village shop, so the sim assumes the Oak Shield
    # has been bought; the bot does not play the minigame of earning embers.
    game.state.give("shield")
    game.state.shield_level = 1
    bot = Bot(game, CRITICAL_PATH)
    graph = bot.room_graph()
    marks: dict[str, int] = {}
    pending = {room for room, _ in CRITICAL_PATH}
    while bot.goals and bot.frames < max_frames:
        bot.step(graph)
        room = game.world.room.id
        if room in pending:
            marks[room] = bot.frames
            pending.discard(room)
        if bot.stuck > 1500:
            if not quiet:
                print(f"  bot stuck in {room} after {bot.frames} frames")
            break
    seconds = bot.frames / FPS
    factor = ESTIMATE["explore"] * ESTIMATE["reading"]
    state = game.state
    progress = state.progress("temple1")
    done = {
        "sword": state.has("sword"),
        "reached_temple": "t1_01" in state.rooms_visited,
        "map": progress.map,
        "compass": progress.compass,
        "lantern": state.has("lantern"),
        "big_key": progress.big_key,
        "flame": progress.flame,
    }
    report = {
        "frames": bot.frames,
        "bot_minutes": round(seconds / 60, 2),
        "milestones_done": sum(1 for v in done.values() if v),
        "milestones": len(done),
        "rooms_seen": len(state.rooms_visited),
        "player_hours_slice": round(seconds * factor / 3600, 2),
        "completion": state.completion(),
        "deaths": state.deaths,
        "done": done,
    }
    if not quiet:
        print(f"  bot ran {report['frames']} frames ({report['bot_minutes']} bot-min), "
              f"{report['deaths']} deaths")
        print(f"  {report['rooms_seen']} rooms seen, completion {report['completion']}%")
        for name, got in done.items():
            print(f"    [{'x' if got else ' '}] {name}")
        print(f"  measured slice: {report['player_hours_slice']} player-hours "
              f"(bot time x{round(factor, 2)})")
        for room, frame in sorted(marks.items(), key=lambda kv: kv[1]):
            print(f"    {room:12s} first seen at {frame / FPS / 60:6.2f} bot-min")
    pygame.quit()
    return report


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="measure Eldermoor's length")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--max-frames", type=int, default=400000)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if not args.quiet:
        print("simulating the critical path ...")
    report = run(args.max_frames, args.quiet)
    # The bot is a measuring tape, not a speedrunner: it has to get Wren out of
    # the village, into the temple and through its first rooms. Clearing the
    # whole temple unattended is milestone 8's balance-pass work.
    needed = ("sword", "reached_temple", "map", "compass")
    missing = [k for k in needed if not report["done"][k]]
    if missing:
        print("bot did not manage:", ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
