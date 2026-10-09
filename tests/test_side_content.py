"""Milestone 5: rings, quests, the trading chain, the minigames and the finds page."""
from __future__ import annotations

import math

import pygame
from conftest import make_game, step

from eldermoor.config import HERO_SPEED, TILE
from eldermoor.state import (
    FIGURINES_TOTAL,
    FURNITURE_TOTAL,
    QUESTS_TOTAL,
    RINGS_TOTAL,
    GameState,
)


# ----- rings --------------------------------------------------------------
def test_two_rings_add_up(content):
    bonus = content.rings.bonus(["ring_power", "ring_guard"])
    assert bonus.damage == 1 and bonus.defence == 1
    assert content.rings.bonus([None, None]).damage == 0


def test_wearing_a_ring_takes_it_off_the_other_hand():
    state = GameState()
    state.find_ring("ring_power")
    state.wear(0, "ring_power")
    state.wear(1, "ring_power")
    assert state.worn == [None, "ring_power"]


def test_ring_of_haste_is_faster(game):
    w = game.world
    w.hero.x, w.hero.y = 6 * TILE, 6 * TILE
    game.state.wear(0, "ring_swift")
    game.input.press("right")
    step(game, 10)
    game.input.release_all()
    bonus = game.content.rings.bonus(game.state.worn)
    assert math.isclose(w.hero.x - 6 * TILE, HERO_SPEED * (1 + bonus.speed) * 10,
                        rel_tol=1e-6)


def test_ring_of_guard_shaves_a_hit(game):
    w = game.world
    game.state.wear(0, "ring_guard")
    before = game.state.health
    w.hero.hurt(w, 2)
    assert game.state.health == before - 1, "two half-hearts become one"


def test_a_hit_always_costs_something(game):
    w = game.world
    game.state.wear(0, "ring_guard")
    before = game.state.health
    w.hero.hurt(w, 1)
    assert game.state.health == before - 1, "defence never reaches zero"


def test_lucky_ring_asks_the_drop_table_again(game, monkeypatch):
    from eldermoor import pickups
    w = game.world
    game.state.wear(0, "ring_luck")
    asked = []

    def roll(table, rng=None):
        asked.append(table)
        return None

    monkeypatch.setattr(w.drops, "roll", roll)
    pickups.spawn_drop(w, 32.0, 32.0, "enemy")
    assert len(asked) == 2, "the ring buys one more roll"


def test_mending_ring_hands_back_a_heart(game):
    game.state.wear(0, "ring_mend")
    game.state.damage(4)
    low = game.state.health
    game.world.regen_timer = game.content.rings.bonus(game.state.worn).regen - 1
    step(game)
    assert game.state.health == low + 1


# ----- ice ---------------------------------------------------------------
def test_ice_carries_wren_and_the_ring_takes_it_back(game):
    w = game.world
    tile = w.room.tileset.legend["I"]
    for row in range(4, 9):
        for col in range(2, 18):
            w.room.tiles[row][col] = tile
    w.hero.x, w.hero.y = 6 * TILE, 6 * TILE
    assert w.on_ice(w.hero)
    game.input.press("right")
    step(game, 6)
    game.input.release_all()
    slid = w.hero.x
    step(game, 6)
    assert w.hero.x > slid, "he keeps going after the stick is let go"
    game.state.wear(0, "ring_grip")
    assert not w.on_ice(w.hero)


# ----- quests -------------------------------------------------------------
def test_the_quest_table_is_thirty_rows(content):
    assert len(content.quests) == QUESTS_TOTAL
    for quest in content.quests.quests.values():
        assert quest.needs and quest.gives, quest.id
        assert content.text.get(quest.name) != quest.name, quest.id
        for line in ("ask", "wait", "thanks", "done"):
            key = quest.line(line)
            assert content.text.get(key) != key, key


def test_a_quest_runs_ask_wait_and_pay(game):
    w = game.world
    quest = game.content.quests.get("q_shells5")
    assert w.talk_quest("q_shells5")
    assert game.state.flag(quest.start_flag), "asking opens the quest"
    assert game.content.quests.status(game.state, "q_shells5") == "open"
    w.dialogue = None
    w.talk_quest("q_shells5")
    assert "q_shells5" not in game.state.quests, "no shells, no ring"
    w.dialogue = None
    game.state.seashells = 5
    w.talk_quest("q_shells5")
    assert "q_shells5" in game.state.quests
    assert "ring_luck" in game.state.rings
    assert game.content.quests.status(game.state, "q_shells5") == "done"


def test_quest_rewards_land_in_the_right_box(game):
    for quest_id, check in (("q_cat", lambda s: "fig_cat" in s.figurines),
                            ("q_broom", lambda s: "fur_broom" in s.furniture),
                            ("q_lamp", lambda s: s.heart_pieces == 1),
                            ("q_sheep", lambda s: s.embers >= 40)):
        quest = game.content.quests.get(quest_id)
        for need, value in quest.needs.items():
            if need == "flag":
                game.state.set_flag(str(value), 1)
        game.state.set_flag(quest.start_flag, 1)
        game.world.dialogue = None
        game.world.talk_quest(quest_id)
        assert check(game.state), quest_id


def test_a_token_counts_its_set(game):
    w = game.world
    specs = [{"kind": "token", "id": f"p{i}", "at": [3 + i, 3], "count": "pots", "of": 3,
              "sets": "pots_broken", "flag": f"t{i}", "text": "token.pot"} for i in range(3)]
    tokens = [w.spawn_from_spec(spec) for spec in specs]
    for token in tokens[:2]:
        token.interact(w)
        w.dialogue = None
    assert not game.state.flag("pots_broken")
    tokens[2].interact(w)
    assert game.state.flag("pots_broken") == 1
    assert game.state.flag("count:pots") == 3


def test_a_token_can_wait_for_an_item(game):
    w = game.world
    token = w.spawn_from_spec({"kind": "token", "id": "boat", "at": [4, 4],
                               "sets": "boat_free", "needs": "gauntlet",
                               "text": "token.boat"})
    token.interact(w)
    assert not game.state.flag("boat_free")
    w.dialogue = None
    game.state.give("gauntlet")
    token.interact(w)
    assert game.state.flag("boat_free") == 1


# ----- the trading chain --------------------------------------------------
def test_the_chain_runs_end_to_end(game):
    w = game.world
    chain = game.content.trade
    assert len(chain) == 10
    for step_index in range(len(chain)):
        w.dialogue = None
        assert w.talk_trade(step_index)
        assert game.state.trade == step_index + 1
    assert "ring_swift" in game.state.rings, "the last trade pays a ring"


def test_the_chain_will_not_skip(game):
    w = game.world
    w.talk_trade(4)
    assert game.state.trade == 0, "nobody trades with you out of order"


# ----- the minigames ------------------------------------------------------
def test_three_games_with_prizes(content):
    assert len(content.minigames) == 3
    for definition in content.minigames.games.values():
        assert definition.prizes
        assert content.text.get(definition.name) != definition.name


def test_the_gallery_scores_and_pays(assets, content, silent_audio):
    from eldermoor import minigames
    game = make_game(assets, content, silent_audio)
    mini = minigames.start(game.world, "gallery")
    assert mini is not None
    mini.score = 10
    mini.finish()
    assert game.state.scores["gallery"] == 10
    assert "fig_thistle" in game.state.figurines
    assert "fig_crag" in game.state.figurines


def test_a_prize_is_only_paid_once(assets, content, silent_audio):
    from eldermoor import minigames
    game = make_game(assets, content, silent_audio)
    definition = content.minigames.get("dig")
    minigames.pay_prizes(game.world, definition, 10)
    embers = game.state.embers
    pieces = game.state.heart_pieces
    minigames.pay_prizes(game.world, definition, 10)
    assert game.state.embers == embers and game.state.heart_pieces == pieces


def test_the_dig_patch_runs_out_of_digs(assets, content, silent_audio):
    from eldermoor import minigames
    game = make_game(assets, content, silent_audio)
    mini = minigames.start(game.world, "dig")
    canvas = pygame.Surface((320, 240))
    for _ in range(400):
        game.input.begin_frame()
        game.input.press("a")
        mini.update(game.input)
        game.input.release("a")
        game.input.begin_frame()
        game.input.press("right")
        mini.update(game.input)
        game.input.release("right")
        mini.draw(canvas)
        if mini.over:
            break
    assert mini.over, "ten digs and it is finished"
    assert 0 <= mini.score <= 10


def test_a_host_takes_the_fee_and_opens_the_game(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio)
    game.state.embers = 50
    spec = {"kind": "npc", "at": [4, 4], "minigame": "bells"}
    npc = game.world.spawn_from_spec(spec)
    npc.interact(game.world)
    box = game.world.dialogue
    assert box is not None
    box.done = True
    game.world._update_dialogue()
    game.update()
    assert game.mode == "minigame"
    assert game.state.embers == 50 - content.minigames.get("bells").cost


# ----- the collections ----------------------------------------------------
def test_collections_are_the_size_the_counters_expect(content):
    assert len(content.figurines) == FIGURINES_TOTAL
    assert len(content.furniture) == FURNITURE_TOTAL
    assert len(content.rings) == RINGS_TOTAL


def test_a_collection_takes_each_thing_once():
    state = GameState()
    assert state.collect("figurines", "fig_cat")
    assert not state.collect("figurines", "fig_cat")
    assert state.figurines == ["fig_cat"]


def test_the_bestiary_counts_kills(game):
    w = game.world
    enemy = w.spawn_from_spec({"kind": "enemy", "type": "mote", "at": [5, 5]})
    enemy.die(w)
    assert game.state.bestiary["mote"] == 1
    enemy2 = w.spawn_from_spec({"kind": "enemy", "type": "mote", "at": [6, 5]})
    enemy2.die(w)
    assert game.state.bestiary["mote"] == 2


def test_completion_counts_everything(content):
    state = GameState()
    assert state.completion() == 0.0
    state.seashells = 40
    first = state.completion()
    assert first > 0
    state.quests = [f"q{i}" for i in range(QUESTS_TOTAL)]
    assert state.completion() > first


def test_every_menu_page_draws(assets, content, silent_audio):
    from eldermoor.menu import PAGES, PauseMenu
    from eldermoor.settings import Settings
    game = make_game(assets, content, silent_audio)
    game.state.find_ring("ring_power")
    game.state.wear(0, "ring_power")
    game.state.collect("figurines", "fig_cat")
    game.state.collect("furniture", "fur_broom")
    game.state.record_kill("mote")
    game.state.set_flag("q_cat:asked", 1)
    game.state.finish_quest("q_broom")
    canvas = pygame.Surface((320, 240))
    for page in range(len(PAGES)):
        menu = PauseMenu(assets, content, game.state, silent_audio, Settings(), page)
        for tab in range(4):
            menu.tab = tab
            menu.draw(canvas)


def test_furniture_shows_up_in_the_house(assets, content, silent_audio):
    game = make_game(assets, content, silent_audio, room="house_wren")
    assert not [e for e in game.world.entities if type(e).__name__ == "Display"]
    game.state.collect("furniture", "fur_broom")
    game.world.warp("house_wren")
    shown = [e for e in game.world.entities if type(e).__name__ == "Display"]
    assert len(shown) == 1
    assert game.state.placed["spot0"] == "fur_broom"


def test_a_shop_can_sell_a_ring(assets, content, silent_audio):
    from eldermoor.shop import Shop
    game = make_game(assets, content, silent_audio)
    game.state.embers = 300
    shop = Shop(game.world, [{"kind": "ring", "id": "ring_haggle", "cost": 240}])
    game.input.begin_frame()
    game.input.press("a")
    shop.update(game.input)
    game.input.release("a")
    assert "ring_haggle" in game.state.rings
    assert game.state.embers == 60
    assert shop.sold_out(shop.stock[0])


def test_the_haggle_ring_lowers_a_price(assets, content, silent_audio):
    from eldermoor.shop import Shop
    game = make_game(assets, content, silent_audio)
    game.state.find_ring("ring_haggle")
    game.state.wear(0, "ring_haggle")
    shop = Shop(game.world, [{"item": "heart", "cost": 100}])
    assert shop.price(shop.stock[0]) == 75


def test_a_gated_figurine_waits_for_the_bestiary(assets, content, silent_audio):
    from eldermoor.shop import Shop
    game = make_game(assets, content, silent_audio)
    game.state.embers = 999
    entry = {"kind": "figurine", "id": "fig_quiet", "cost": 320, "needs_bestiary": 42}
    shop = Shop(game.world, [entry])
    shop._buy(entry)
    assert "fig_quiet" not in game.state.figurines
    game.state.bestiary = {f"beast{i}": 1 for i in range(42)}
    shop._buy(entry)
    assert "fig_quiet" in game.state.figurines


# ----- the save -----------------------------------------------------------
def test_a_version_two_save_walks_into_version_three():
    from eldermoor import save
    raw = {"version": 2, "slot": 1, "max_hearts": 5, "health": 10, "owned": ["sword"],
           "flags": {"a": 1}, "dungeons": {}, "room": "ow_1105"}
    state = GameState.from_json(save.migrate(dict(raw)))
    assert state.rings == [] and state.worn == [None, None]
    assert state.figurines == [] and state.furniture == []
    assert state.bestiary == {} and state.scores == {}
    assert state.quests == [] and state.trade == 0
    assert state.max_hearts == 5
