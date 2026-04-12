import random

from src.models.items import (
    Weapon, SpellScroll, Food, Tool, ItemStats,
)
from src.models.player import PlayerCharacter, PlayerClass


# --- Weapon tests ---

def _make_weapon(name="iron sword", attack_dice="1d6", modifier="STR",
                 weapon_type="heavy", price=20):
    return Weapon(
        category="weapon", name=name, desc="test weapon",
        weapon_type=weapon_type,
        item_stats=ItemStats(attack_dice=attack_dice, stat_modifier=modifier, price=price),
    )


def _make_scroll(name="scroll of fire", health=25, spell_effect="damage", price=30):
    return SpellScroll(
        category="spell_scroll", name=name, desc="test scroll",
        spell_effect=spell_effect,
        item_stats=ItemStats(health_value=health, price=price),
    )


def test_weapon_equip():
    player = PlayerCharacter(x=0, y=0)
    weapon = _make_weapon()
    player.inventory = {weapon.name: weapon}
    msg = weapon.use(player)
    assert "equipped" in msg.lower()
    assert player.equipped_weapon == weapon.name


def test_weapon_unequip():
    player = PlayerCharacter(x=0, y=0)
    weapon = _make_weapon()
    player.inventory = {weapon.name: weapon}
    player.equipped_weapon = weapon.name
    msg = weapon.use(player)
    assert "unequipped" in msg.lower()
    assert player.equipped_weapon is None


def test_weapon_roll_damage():
    """Fixed seed: 1d6 weapon produces a known damage value."""
    weapon = _make_weapon(attack_dice="1d6")
    random.seed(42)
    assert weapon.roll_damage() == 6  # known result for seed 42


def test_weapon_roll_damage_multi_dice():
    weapon = _make_weapon(attack_dice="2d4")
    for _ in range(50):
        dmg = weapon.roll_damage()
        assert 2 <= dmg <= 8



# --- SpellScroll tests ---

def test_spell_scroll_use_heals():
    player = PlayerCharacter(x=0, y=0)
    player.health = 50
    scroll = _make_scroll(health=30)
    msg = scroll.use(player)
    assert player.health == 80
    assert "cast" in msg.lower()


def test_spell_scroll_health_cap():
    player = PlayerCharacter(x=0, y=0)
    player.health = 90
    scroll = _make_scroll(health=30)
    scroll.use(player)
    assert player.health == player.max_health



# --- Player equip methods ---

def test_player_equip_weapon():
    player = PlayerCharacter(x=0, y=0)
    weapon = _make_weapon(name="test blade")
    player.inventory = {weapon.name: weapon}
    msg = player.equip_weapon("test blade")
    assert player.equipped_weapon == "test blade"
    assert "equipped" in msg.lower()


def test_player_equip_non_weapon():
    player = PlayerCharacter(x=0, y=0)
    food = Food(
        category="food", name="bread", desc="test",
        item_stats=ItemStats(stamina_value=20),
    )
    player.inventory = {"bread": food}
    msg = player.equip_weapon("bread")
    assert player.equipped_weapon is None
    assert "not a weapon" in msg.lower()


def test_player_equip_missing_item():
    player = PlayerCharacter(x=0, y=0)
    msg = player.equip_weapon("phantom blade")
    assert "don't have" in msg.lower()


def test_player_toggle_equip():
    player = PlayerCharacter(x=0, y=0)
    weapon = _make_weapon(name="toggle sword")
    player.inventory = {weapon.name: weapon}
    player.equip_weapon("toggle sword")
    assert player.equipped_weapon == "toggle sword"
    player.equip_weapon("toggle sword")
    assert player.equipped_weapon is None


def test_get_equipped_weapon_returns_weapon():
    player = PlayerCharacter(x=0, y=0)
    weapon = _make_weapon(name="get test")
    player.inventory = {weapon.name: weapon}
    player.equipped_weapon = weapon.name
    assert player.get_equipped_weapon() is weapon


def test_get_equipped_weapon_clears_stale():
    player = PlayerCharacter(x=0, y=0)
    player.equipped_weapon = "deleted weapon"
    assert player.get_equipped_weapon() is None
    assert player.equipped_weapon is None


# --- Money tests ---

def test_player_add_money():
    player = PlayerCharacter(x=0, y=0)
    player.add_money(100)
    assert player.money == 100


def test_player_spend_money_success():
    player = PlayerCharacter(x=0, y=0, money=50)
    assert player.spend_money(30) is True
    assert player.money == 20


def test_player_spend_money_insufficient():
    player = PlayerCharacter(x=0, y=0, money=10)
    assert player.spend_money(50) is False
    assert player.money == 10


# --- ItemStats price field ---

def test_item_stats_price_default():
    stats = ItemStats()
    assert stats.price == 0


def test_item_stats_attack_dice():
    stats = ItemStats(attack_dice="2d6", stat_modifier="DEX")
    assert stats.attack_dice == "2d6"
    assert stats.stat_modifier == "DEX"


# --- Jester spell scroll learning ---

def _make_class(archetype="warrior"):
    return PlayerClass(name=f"Test {archetype.title()}", archetype=archetype)


def test_jester_learns_spell_permanently():
    player = PlayerCharacter(x=0, y=0, player_class=_make_class("jester"))
    scroll = _make_scroll(name="scroll of fire", spell_effect="damage")
    player.inventory = {scroll.name: scroll}
    msg = player.use_spell_scroll("scroll of fire")
    assert "learn" in msg.lower()
    assert "damage" in player.learned_spells
    assert "scroll of fire" not in player.inventory


def test_jester_no_duplicate_learned_spell():
    player = PlayerCharacter(x=0, y=0, player_class=_make_class("jester"))
    player.learned_spells = ["damage"]
    scroll = _make_scroll(name="scroll of fire", spell_effect="damage")
    player.inventory = {scroll.name: scroll}
    player.use_spell_scroll("scroll of fire")
    assert player.learned_spells.count("damage") == 1


def test_non_jester_consumes_scroll():
    player = PlayerCharacter(x=0, y=0, player_class=_make_class("warrior"), health=50)
    scroll = _make_scroll(name="scroll of heal", health=25, spell_effect="heal")
    player.inventory = {scroll.name: scroll}
    msg = player.use_spell_scroll("scroll of heal")
    assert "crumbles" in msg.lower()
    assert player.health == 75
    assert len(player.learned_spells) == 0
    assert "scroll of heal" not in player.inventory


def test_use_spell_scroll_missing():
    player = PlayerCharacter(x=0, y=0)
    msg = player.use_spell_scroll("phantom scroll")
    assert "don't have" in msg.lower()


def test_use_spell_scroll_not_scroll():
    player = PlayerCharacter(x=0, y=0)
    food = Food(category="food", name="bread", desc="test",
                item_stats=ItemStats(stamina_value=20))
    player.inventory = {"bread": food}
    msg = player.use_spell_scroll("bread")
    assert "not a spell scroll" in msg.lower()


# --- Item generation helpers ---

def _sample_llm_result():
    return {
        "food": [
            {"name": "forest bread", "desc": "Hearty bread.", "stamina_value": 20, "health_value": 0},
            {"name": "berries", "desc": "Wild berries.", "stamina_value": 10, "health_value": 5},
        ],
        "drink": [
            {"name": "spring water", "desc": "Cool water.", "stamina_value": 15, "health_value": 0},
        ],
        "tools": [
            {"name": "hatchet", "desc": "A small hatchet.", "attribute": "cutting"},
        ],
        "weapons": [
            {"name": "oak club", "desc": "Heavy club.", "weapon_type": "heavy",
             "stat_modifier": "STR", "attack_dice": "1d6"},
        ],
        "spell_scrolls": [
            {"name": "scroll of heal", "desc": "Heals wounds.", "spell_effect": "heal"},
        ],
    }


def test_build_items_json_structure():
    """Test _build_items_json converts LLM output to proper items.json format."""
    from src.generate.pipeline_utils import _build_items_json
    items = _build_items_json(_sample_llm_result(), room_level=1)
    # Check food IDs start at 200
    assert "200" in items
    assert items["200"]["category"] == "food"
    assert items["200"]["name"] == "forest bread"
    # Check drink IDs start at 300
    assert "300" in items
    assert items["300"]["category"] == "drink"
    # Check tool IDs start at 400
    assert "400" in items
    assert items["400"]["item_stats"]["attribute"] == "cutting"
    # Check weapon IDs start at 500
    assert "500" in items
    assert items["500"]["weapon_type"] == "heavy"
    assert items["500"]["item_stats"]["attack_dice"] == "1d6"
    # Check scroll IDs start at 600
    assert "600" in items
    assert items["600"]["spell_effect"] == "heal"


def test_weapon_dice_scaling():
    """Test that WEAPON_DICE_BY_LEVEL maps room levels to appropriate dice."""
    from src.generate.generators.llm_primitives import WEAPON_DICE_BY_LEVEL
    assert set(WEAPON_DICE_BY_LEVEL[1]) == {"1d4", "1d6"}
    assert set(WEAPON_DICE_BY_LEVEL[4]) == {"1d10", "1d12"}


def test_validate_puzzle_tools():
    """Test that _validate_puzzle_tools fixes invalid tool_attribute references."""
    from unittest.mock import MagicMock
    from src.generate.pipeline_utils import _validate_puzzle_tools
    from src.models.items import ItemStats

    mock_reg = MagicMock()
    tool = Tool(category="tool", name="hatchet", desc="A hatchet",
                item_stats=ItemStats(attribute="cutting", uses=3))
    mock_reg.item_registry = {400: tool}

    events = [
        {
            "type": "puzzle",
            "choices": [
                {"text": "Dig through", "tool_attribute": "digging", "dc": 10},
                {"text": "Walk away", "tool_attribute": None, "dc": 0},
            ],
        },
    ]
    _validate_puzzle_tools(events, mock_reg)
    # "digging" doesn't exist in registry, should be replaced with "cutting"
    assert events[0]["choices"][0]["tool_attribute"] == "cutting"
    # None stays None
    assert events[0]["choices"][1]["tool_attribute"] is None


# --- Consumable scaling tests ---

def test_consumable_scaling_level_1_no_change():
    """At room_level 1 the multiplier is 1.0 so stats stay at base values."""
    from src.generate.pipeline_utils import _build_items_json
    items = _build_items_json(_sample_llm_result(), room_level=1)
    assert items["200"]["item_stats"]["stamina_value"] == 20
    assert items["300"]["item_stats"]["stamina_value"] == 15


def test_consumable_scaling_level_3():
    """At room_level 3 the multiplier is 1.6 — stats and prices should increase."""
    from src.generate.pipeline_utils import _build_items_json
    import random
    random.seed(42)
    items = _build_items_json(_sample_llm_result(), room_level=3)
    assert items["200"]["item_stats"]["stamina_value"] == 32
    assert items["300"]["item_stats"]["stamina_value"] == 24
    # prices should be > base (base range 5-15, scaled by 1.6)
    assert items["200"]["item_stats"]["price"] >= 8


def test_consumable_scaling_level_4():
    """At room_level 4 the multiplier is 2.0 — stats double."""
    from src.generate.pipeline_utils import _build_items_json
    items = _build_items_json(_sample_llm_result(), room_level=4)
    assert items["200"]["item_stats"]["stamina_value"] == 40
    assert items["300"]["item_stats"]["stamina_value"] == 30


def test_consumable_scaling_high_level_caps_at_4():
    """Room levels above 4 use the level-4 multiplier (2.0)."""
    from src.generate.pipeline_utils import _build_items_json
    items = _build_items_json(_sample_llm_result(), room_level=7)
    assert items["200"]["item_stats"]["stamina_value"] == 40


def test_tool_uses_not_scaled():
    """Tool uses should remain constant regardless of room level."""
    from src.generate.pipeline_utils import _build_items_json
    items_l1 = _build_items_json(_sample_llm_result(), room_level=1)
    items_l4 = _build_items_json(_sample_llm_result(), room_level=4)
    assert items_l1["400"]["item_stats"]["uses"] == 3
    assert items_l4["400"]["item_stats"]["uses"] == 3


def test_tool_price_scales():
    """Tool prices should increase with room level."""
    from src.generate.pipeline_utils import _build_items_json
    import random
    random.seed(42)
    items_l1 = _build_items_json(_sample_llm_result(), room_level=1)
    random.seed(42)
    items_l4 = _build_items_json(_sample_llm_result(), room_level=4)
    assert items_l4["400"]["item_stats"]["price"] >= items_l1["400"]["item_stats"]["price"]


def test_spell_scroll_scales_at_half_rate():
    """Spell scroll effects scale at half the consumable rate."""
    from src.generate.pipeline_utils import _build_items_json
    items = _build_items_json(_sample_llm_result(), room_level=4)
    # mult=2.0, scroll_mult = 1.0 + (2.0-1.0)*0.5 = 1.5
    # heal scroll: 25 * 1.5 = 37
    assert items["600"]["item_stats"]["health_value"] == 37


def test_consumable_scaling_dict_values():
    """Verify the CONSUMABLE_SCALING dict has expected values."""
    from src.generate.pipeline_utils import CONSUMABLE_SCALING
    assert CONSUMABLE_SCALING[1] == 1.0
    assert CONSUMABLE_SCALING[2] == 1.3
    assert CONSUMABLE_SCALING[3] == 1.6
    assert CONSUMABLE_SCALING[4] == 2.0
