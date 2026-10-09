"""Damage both ways: shield, dodge-roll, mercy frames, knockback, death and respawn."""
from __future__ import annotations

import random

from conftest import step, tap

from eldermoor.config import HERO_INVULN_FRAMES, ROLL_FRAMES, ROLL_IFRAMES, SPIN_CHARGE_FRAMES
from eldermoor.enemies import Enemy

STILL = {"start": "idle", "states": {"idle": {"move": "none", "time": 0}}}


def touching_enemy(game, content, kind: str = "mote", still: bool = True) -> Enemy:
    """Spawn an enemy right on top of Wren, standing still so tests stay honest."""
    from eldermoor.ai import Brain
    hero = game.world.hero
    enemy = Enemy(content.enemies[kind], hero.x, hero.y, random.Random(9))
    if still:
        enemy.brain = Brain(STILL, random.Random(9))
    game.world.spawn(enemy)
    return enemy


def press_against(game, enemy, frames: int, dx: float = 0.0, dy: float = 0.0) -> None:
    """Step, keeping the enemy glued to Wren so knockback cannot end the test early."""
    hero = game.world.hero
    for _ in range(frames):
        enemy.x, enemy.y = hero.x + dx, hero.y + dy
        step(game)


def test_contact_damage_and_mercy_frames(game, content):
    hero = game.world.hero
    enemy = touching_enemy(game, content)
    health = game.state.health
    step(game)
    assert game.state.health == health - 1
    assert hero.invuln == HERO_INVULN_FRAMES
    press_against(game, enemy, 10)
    assert game.state.health == health - 1, "mercy frames hold"
    press_against(game, enemy, HERO_INVULN_FRAMES + 4)
    assert game.state.health < health - 1, "and then they run out"


def test_knockback_pushes_the_hero_away(game, content):
    hero = game.world.hero
    hero.x, hero.y = 150.0, 100.0
    enemy = touching_enemy(game, content)
    enemy.x, enemy.y = 150.0, 100.0
    before = (hero.x, hero.y)
    step(game, 4)
    assert (hero.x, hero.y) != before and hero.knock_timer >= 0


def test_shield_blocks_a_hit_from_the_front(game, content):
    game.state.give("shield")
    game.state.shield_level = 1
    hero = game.world.hero
    hero.x, hero.y = 150.0, 100.0
    hero.facing = "right"
    game.input.press("l")
    step(game)
    enemy = touching_enemy(game, content)
    health = game.state.health
    press_against(game, enemy, 6, dx=10)
    assert game.state.health == health, "the shield held"
    game.input.release_all()
    press_against(game, enemy, 24, dx=10)   # knockback has to finish first
    assert game.state.health < health, "and lowering it does not"


def test_roll_has_invincible_frames_and_a_cooldown(game):
    hero = game.world.hero
    game.input.press("right")
    step(game)
    tap(game, "r")
    assert hero.roll_timer == ROLL_FRAMES
    assert hero.invulnerable, "the first frames of a roll are free"
    step(game, ROLL_IFRAMES + 1)
    assert not hero.invulnerable
    step(game, ROLL_FRAMES)
    assert hero.roll_timer == 0 and hero.roll_cooldown > 0
    tap(game, "r")
    assert hero.roll_timer == 0, "cannot roll again straight away"


def test_spin_attack_after_a_long_hold(game):
    game.state.sword_level = 2
    hero = game.world.hero
    game.input.press("a")
    step(game, SPIN_CHARGE_FRAMES + 20)        # one swing, then the charge builds
    assert hero.charge >= SPIN_CHARGE_FRAMES
    game.input.begin_frame()
    game.input.release("a")
    game.update()
    assert hero.spinning and hero.sword_hitbox() is not None
    assert hero.sprite_name().startswith("wren_swing_")


def test_death_sends_the_hero_to_the_respawn_point(game):
    game.world.warp("t1_02")
    assert game.state.respawn_room == "t1_01", "a temple sends you back to its door"
    game.state.health = 1
    game.world.hero.hurt(game.world, 2)
    assert game.world.room.id == "t1_01"
    assert game.state.deaths == 1
    assert game.state.health == game.state.max_hearts * 2
    assert game.state.has("sword"), "Zelda rules: you keep what you found"


def test_overworld_respawn_is_the_last_screen(village):
    village.world.warp("ow_1010")
    assert village.state.respawn_room == "ow_1010"


def test_low_health_beep_only_when_low(game, silent_audio):
    game.state.health = 6
    for _ in range(120):
        game.hud.tick(game.state, silent_audio, True)
    assert "low_health" not in silent_audio.log
    game.state.health = 1
    for _ in range(120):
        game.hud.tick(game.state, silent_audio, True)
    assert "low_health" in silent_audio.log
    silent_audio.log.clear()
    game.hud.tick(game.state, silent_audio, False)
    assert not silent_audio.log


def test_feather_hops_over_a_pit(game):
    game.state.give("feather")
    game.state.assign(0, "feather")
    game.world.warp("t1_23")               # the room full of pits
    hero = game.world.hero
    tap(game, "b")
    assert hero.airborne and hero.hop_height >= 0
    step(game, 13)
    assert hero.hop_height > 0
    step(game, 30)
    assert not hero.airborne


def test_god_mode_stops_damage(game, content):
    game.debug.god = True
    touching_enemy(game, content)
    health = game.state.health
    step(game, 10)
    assert game.state.health == health
