"""Rooms, tilesets, exits and the flip-scroll transition."""
from __future__ import annotations

import pygame
import pytest
from conftest import step

from eldermoor.config import FLIP_SCROLL_FRAMES, PLAY_H, PLAY_W
from eldermoor.tilemap import Collision, Room, Tileset, list_rooms


def test_every_room_loads_and_references_existing_sprites(assets):
    rooms = list_rooms()
    assert len(rooms) >= 2
    for rid in rooms:
        room = Room.load(rid)
        assert len(room.tiles) == 13 and all(len(r) == 20 for r in room.tiles)
        sheet = assets.region_tiles(room.tileset.region)
        for td in room.tileset.tiles.values():
            assert sheet.has(td.sprite), f"{rid}: tile sprite {td.sprite} missing"
        for direction, target in room.exits.items():
            back = Room.load(target)
            assert back.exits.get(back_dir(direction)) == rid, f"{rid} {direction} exit is one-way"
        surf = room.render(assets)
        assert surf.get_size() == (PLAY_W, PLAY_H)


def back_dir(d: str) -> str:
    return {"north": "south", "south": "north", "east": "west", "west": "east"}[d]


def test_tileset_collision_classes():
    ts = Tileset.load("meadow")
    assert ts.tiles[ts.legend["T"]].collision is Collision.SOLID
    assert ts.tiles[ts.legend["."]].collision is Collision.FLOOR
    assert ts.tiles[ts.legend["~"]].collision is Collision.WATER
    assert len(Collision) == 10


def test_bad_room_rejected(tmp_path):
    (tmp_path / "rooms").mkdir()
    (tmp_path / "tilesets").mkdir()
    (tmp_path / "tilesets" / "t.json").write_text('{"tiles": {"0": {"char": ".", "sprite": "grass"}}}')
    (tmp_path / "rooms" / "bad.json").write_text('{"tileset": "t", "tiles": ["...."]}')
    with pytest.raises(ValueError):
        Room.load("bad", root=tmp_path)


def test_flip_scroll_east_then_back(game):
    w = game.world
    h = w.hero
    h.y = 98  # the row the east doorway sits on
    game.input.press("right")
    frames = 0
    while w.transition is None:
        step(game)
        frames += 1
        assert frames < 500, "never reached the exit"
    assert w.room.id == "meadow_01"
    assert w.transition.direction == "east" and w.transition.frame == 0
    assert h.x == 0
    assert h.y == 96, "the hero is lined up with the doorway he came through"
    x_during = h.x
    step(game, FLIP_SCROLL_FRAMES - 1)
    assert w.transition is not None and h.x == x_during, "logic pauses during the scroll"
    step(game)
    assert w.transition is None, "exactly 12 frames"
    assert w.rooms_visited == ["meadow_00", "meadow_01"]
    game.input.release_all()
    game.input.press("left")
    for _ in range(60):
        step(game)
        if w.transition is not None:
            break
    assert w.room.id == "meadow_00" and h.x == PLAY_W - 16
    step(game, FLIP_SCROLL_FRAMES)
    assert w.transition is None and w.rooms_visited == ["meadow_00", "meadow_01"]


def test_edge_without_exit_clamps(game):
    w = game.world
    w.warp("meadow_00", x=150, y=0)
    w.room.exits.pop("north", None)
    # remove the tree row so the hero can reach the edge
    w.room.tiles[0] = [w.room.tileset.legend["."]] * 20
    game.input.press("up")
    step(game, 30)
    assert w.hero.y == 0 and w.transition is None and w.room.id == "meadow_00"


def test_transition_draw_covers_play_area(game):
    w = game.world
    w.hero.y = 98
    w.start_transition("east")
    canvas = pygame.Surface((320, 240))
    for _ in range(FLIP_SCROLL_FRAMES + 1):
        canvas.fill((255, 0, 255))
        game.draw(canvas)
        assert canvas.get_at((0, 40))[:3] != (255, 0, 255)
        assert canvas.get_at((319, 239))[:3] != (255, 0, 255)
        w.transition.update()
