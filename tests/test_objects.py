"""Room objects: chests, doors and keys, torches and the Lantern, switches, rewards, triggers."""
from __future__ import annotations

from conftest import run_until, step, tap

from eldermoor.objects import Chest, Door, FloorSwitch, PushBlock, Reward, Torch
from eldermoor.tilemap import Room


def face_and_act(game, entity, button: str = "a", frames: int = 4) -> None:
    """Stand next to an entity, look at it and press a button."""
    col, row = entity.col_row()
    hero = game.world.hero
    hero.x = float(col * 16)
    hero.y = float((row + 1) * 16)
    hero.facing = "up"
    step(game)
    for _ in range(frames):
        tap(game, button)
        step(game)


def test_chest_opens_once_and_sets_a_flag(village):
    village.world.warp("house_wren")
    chest = next(e for e in village.world.entities if isinstance(e, Chest))
    assert not chest.opened
    face_and_act(village, chest)
    assert chest.opened and village.state.has("sword")
    assert village.state.flag("chest:wren_sword") == 1
    village.world.warp("ow_1105")
    village.world.warp("house_wren")
    again = next(e for e in village.world.entities if isinstance(e, Chest))
    assert again.opened, "a chest stays open after you leave the room"


def test_locked_door_eats_one_key_and_opens_both_halves(game):
    game.state.enter_dungeon("temple1")
    game.world.warp("t1_02")
    doors = [e for e in game.world.entities if isinstance(e, Door)]
    assert len(doors) == 2 and all(not d.open for d in doors)
    game.state.keys = 0
    face_and_act(game, doors[0])
    assert not doors[0].open, "no key, no entry"
    assert game.world.dialogue is not None
    game.world.dialogue = None
    game.state.keys = 2
    face_and_act(game, doors[0])
    step(game, 2)
    assert doors[0].open and doors[1].open, "both halves of the doorway open"
    assert game.state.keys == 1
    assert game.state.progress("temple1").used_keys == 1


def test_big_door_needs_the_great_key(game):
    game.state.enter_dungeon("temple1")
    game.world.warp("t1_30")
    door = next(e for e in game.world.entities if isinstance(e, Door))
    face_and_act(game, door)
    assert not door.open
    game.world.dialogue = None
    game.state.progress("temple1").big_key = True
    face_and_act(game, door)
    assert door.open


def test_lantern_lights_a_torch_and_burns_a_web(game):
    game.state.give("lantern")
    game.state.assign(0, "lantern")
    game.world.warp("t1_10")
    torch = next(e for e in game.world.entities if isinstance(e, Torch))
    face_and_act(game, torch, button="b", frames=6)
    assert torch.lit
    game.world.warp("t1_11")
    room = game.world.room
    webs = [(c, r) for r in range(13) for c in range(20)
            if (t := room.tile_at(c, r)) and t.interact == "burn"]
    assert webs, "the web gallery has webs"
    col, row = webs[0]
    hero = game.world.hero
    hero.x, hero.y = float(col * 16), float((row + 1) * 16)
    hero.facing = "up"
    step(game, 30)            # the Lantern has a short cooldown between uses
    for _ in range(6):
        tap(game, "b")
        step(game, 6)
    assert room.tile_at(col, row).interact != "burn", "the web burned away"


def test_dark_room_needs_the_lantern(game):
    assert Room.load("t1_10").dark
    game.world.warp("t1_10")
    import pygame
    canvas = pygame.Surface((320, 240))
    game.draw(canvas)
    far_corner = canvas.get_at((300, 60))[:3]
    assert sum(far_corner) < 40, "a dark room is dark"


def test_floor_switch_fires_a_trigger(game):
    game.world.warp("t1_22")
    plate = next(e for e in game.world.entities if isinstance(e, FloorSwitch))
    hero = game.world.hero
    col, row = plate.col_row()
    hero.x, hero.y = float(col * 16), float(row * 16 - 6)
    assert run_until(game, lambda: plate.pressed, 60)
    assert run_until(game, lambda: all(d.open for d in game.world.entities
                                       if isinstance(d, Door)), 60)


def test_push_block_moves_one_tile(game):
    game.world.warp("t1_22")
    block = next(e for e in game.world.entities if isinstance(e, PushBlock))
    before = block.col_row()
    hero = game.world.hero
    hero.x = float(block.x)
    hero.y = float(block.y + 16)
    hero.facing = "up"
    step(game)
    tap(game, "a")
    step(game, 24)
    assert block.col_row() != before


def test_reward_is_taken_on_touch_and_stays_taken(village):
    village.world.warp("ow_1104")
    reward = next(e for e in village.world.entities if isinstance(e, Reward))
    village.world.hero.x = float(reward.x)
    village.world.hero.y = float(reward.y)
    step(village, 2)
    assert village.state.heart_pieces == 1
    village.world.warp("ow_1105")
    village.world.warp("ow_1104")
    assert not [e for e in village.world.entities if isinstance(e, Reward)]


def test_cutting_grass_can_drop_something(game):
    game.world.warp("ow_1010")
    room = game.world.room
    cuttable = [(c, r) for r in range(13) for c in range(20)
                if (t := room.tile_at(c, r)) and t.interact == "cut"]
    assert cuttable
    col, row = cuttable[0]
    cleared = game.world.hit_tiles(
        __import__("pygame").Rect(col * 16, row * 16, 16, 16), "cut")
    assert cleared == 1
    assert room.tile_at(col, row).interact != "cut"


def test_stairs_move_the_hero_between_rooms(village):
    world = village.world
    world.warp("ow_1105", 48, 80)      # on the path below Wren's own door
    for _ in range(60):
        village.input.begin_frame()
        village.input.press("up")
        village.update()
        if world.room.id == "house_wren":
            break
    assert world.room.id == "house_wren"
