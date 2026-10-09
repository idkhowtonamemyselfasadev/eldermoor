"""Enemies, their data-defined state machines, armour, projectiles and bosses."""
from __future__ import annotations

import random

import pygame
from conftest import run_until, step

from eldermoor.ai import Brain
from eldermoor.bosses import Boss
from eldermoor.config import ENEMY_TELEGRAPH_MIN
from eldermoor.enemies import Enemy, EnemyRegistry, Projectile


def test_registry_has_the_six_kinds_and_two_bosses(content):
    defs = content.enemies.defs
    for kind in ("mote", "thistle", "crag", "wisp", "spitter", "burrow"):
        assert kind in defs
    assert defs["cinderjaw"].raw["boss"] and defs["ashmaw"].raw["boss"]
    assert len(defs) >= 8


def test_every_telegraph_is_readable(content):
    for enemy_id, definition in content.enemies.defs.items():
        for name, state in definition.ai.get("states", {}).items():
            if state.get("telegraph"):
                assert int(state["time"]) >= ENEMY_TELEGRAPH_MIN, f"{enemy_id}.{name}"


def test_duplicate_enemy_ids_are_rejected(tmp_path):
    (tmp_path / "enemies").mkdir()
    (tmp_path / "enemies" / "a.json").write_text('{"x": {}}')
    (tmp_path / "enemies" / "b.json").write_text('{"x": {}}')
    try:
        EnemyRegistry.load(tmp_path)
    except ValueError as exc:
        assert "twice" in str(exc)
    else:
        raise AssertionError("duplicate ids must be rejected")


def test_state_machine_walks_through_its_states(game, content):
    definition = content.enemies["thistle"]
    enemy = Enemy(definition, 80, 80, random.Random(1))
    game.world.spawn(enemy)
    game.world.hero.x, game.world.hero.y = 96.0, 96.0
    seen = set()
    for _ in range(400):
        step(game)
        seen.add(enemy.brain.state)
    assert {"tense", "leap"} <= seen, f"saw {seen}"


def test_armoured_enemy_only_takes_a_hit_from_behind(game, content):
    enemy = Enemy(content.enemies["crag"], 100, 100, random.Random(2))
    enemy.facing = "down"
    hero = game.world.hero
    hero.facing = "up"
    assert not enemy.vulnerable_from(hero), "that is its shield"
    hero.facing = "down"
    assert enemy.vulnerable_from(hero)
    before = enemy.hp
    enemy.take_damage(game.world, 1, hero)
    assert enemy.hp == before - 1


def test_enemy_death_drops_and_tells_the_room(game, content):
    enemy = Enemy(content.enemies["mote"], 100, 100, random.Random(3))
    game.world.spawn(enemy)
    enemy.hp = 1
    enemy.take_damage(game.world, 5, game.world.hero)
    assert not enemy.alive
    assert game.state.flag("seen:mote") == 1


def test_projectile_hurts_then_dies(game):
    hero = game.world.hero
    hero.x, hero.y = 100.0, 100.0
    shot = Projectile(hero.x + 12, hero.y + 4, -1.0, 0.0)
    game.world.spawn(shot)
    health = game.state.health
    assert run_until(game, lambda: game.state.health < health, 40)
    assert not shot.alive


def test_shield_reflects_a_projectile(game):
    game.state.give("shield")
    game.state.shield_level = 1
    hero = game.world.hero
    hero.x, hero.y = 100.0, 100.0
    hero.facing = "right"
    game.input.press("l")
    step(game)
    shot = Projectile(hero.x + 20, hero.y + 4, -1.2, 0.0)
    game.world.spawn(shot)
    assert run_until(game, lambda: shot.vx > 0, 40), "the shot came back"
    assert shot.team == "hero"


def test_boss_is_only_hurt_in_its_weak_state(game, content):
    boss = Boss(content.enemies["cinderjaw"], 120, 80, random.Random(4))
    game.world.spawn(boss)
    game.world.boss = boss
    boss.intro = 0
    boss.brain.state = "roam"
    before = boss.hp
    boss.take_damage(game.world, 2, game.world.hero)
    assert boss.hp == before, "armoured while it is moving"
    game.world.stun_boss("stunned")
    boss.take_damage(game.world, 2, game.world.hero)
    assert boss.hp == before - 2


def test_boss_phases_speed_it_up(game, content):
    boss = Boss(content.enemies["ashmaw"], 120, 80, random.Random(5))
    game.world.spawn(boss)
    boss.intro = 0
    speed = boss.speed
    boss.hp = 11
    boss.brain.state = "stunned"
    boss.take_damage(game.world, 1, game.world.hero)
    step(game)
    assert boss.speed > speed and boss.phase == 1


def test_boss_death_leaves_its_reward(game, content):
    from eldermoor.objects import Reward
    game.world.warp("t1_31")
    boss = game.world.boss
    assert isinstance(boss, Boss)
    boss.intro = 0
    boss.brain.state = "stunned"
    boss.take_damage(game.world, 99, game.world.hero)
    step(game)
    assert game.state.flag("boss:ashmaw") == 1
    assert any(isinstance(e, Reward) for e in game.world.entities)


def test_arena_torches_stun_the_boss(game):
    from eldermoor.objects import Torch
    game.state.give("lantern")
    game.world.warp("t1_31")
    boss = game.world.boss
    boss.intro = 0
    for torch in [e for e in game.world.entities if isinstance(e, Torch)]:
        torch.light(game.world)
    assert boss.brain.state == "stunned"
    assert boss.vulnerable


def test_brain_jumps_when_the_hero_is_close(game, content):
    brain = Brain({"start": "a", "states": {
        "a": {"move": "none", "time": 0, "if_near": {"dist": 40, "go": "b"}},
        "b": {"move": "none", "time": 0},
    }}, random.Random(6))
    enemy = Enemy(content.enemies["mote"], 0, 0, random.Random(6))
    enemy.brain = brain
    game.world.hero.x, game.world.hero.y = 0.0, 0.0
    brain.step(enemy, game.world)
    assert brain.state == "b"


def test_enemy_sprites_all_exist(assets, content):
    for definition in content.enemies.defs.values():
        if definition.directional:
            names = [f"{definition.sprite}_{side}_{i}"
                     for side in ("down", "up", "side") for i in range(definition.frames)]
        else:
            names = [f"{definition.sprite}_{i}" for i in range(definition.frames)]
        for name in names:
            assert assets.sprites.has(name), name


def test_pit_and_lava_bounce_the_hero_back(game):
    game.world.warp("t1_17")           # the lava corridor
    hero = game.world.hero
    safe = (hero.x, hero.y)
    game.world.last_safe = safe
    lava = next((c, r) for r in range(13) for c in range(20)
                if str(game.world.room.collision_at(c, r)) == "lava")
    hero.x, hero.y = float(lava[0] * 16), float(lava[1] * 16)
    health = game.state.health
    step(game)
    assert (hero.x, hero.y) == safe and game.state.health < health


def test_sword_sweep_hits_every_enemy_once(game, content):
    hero = game.world.hero
    hero.x, hero.y = 100.0, 100.0
    enemies = []
    for dx in (18, 20):
        enemy = Enemy(content.enemies["mote"], hero.x + dx, hero.y, random.Random(7))
        enemy.hp = 9
        game.world.spawn(enemy)
        enemies.append(enemy)
    hero.facing = "right"
    hero.start_swing(game.world)
    rect = pygame.Rect(0, 0, 320, 208)
    game.world.sword_hit(hero, rect)
    game.world.sword_hit(hero, rect)
    assert all(e.hp == 8 for e in enemies), "one swing, one hit each"
