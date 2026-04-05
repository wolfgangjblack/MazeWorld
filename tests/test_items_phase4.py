import pytest
from src.models.items import (
    Weapon, SpellScroll, Food, Drink, Tool, ItemStats,
)
from src.models.player_character import PlayerCharacter


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
    weapon = _make_weapon(attack_dice="1d6")
    for _ in range(50):
        dmg = weapon.roll_damage()
        assert 1 <= dmg <= 6


def test_weapon_roll_damage_multi_dice():
    weapon = _make_weapon(attack_dice="2d4")
    for _ in range(50):
        dmg = weapon.roll_damage()
        assert 2 <= dmg <= 8


def test_weapon_clone():
    weapon = _make_weapon()
    cloned = weapon.clone()
    assert cloned.name == weapon.name
    assert cloned.weapon_type == weapon.weapon_type
    assert cloned is not weapon


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


def test_spell_scroll_clone():
    scroll = _make_scroll()
    cloned = scroll.clone()
    assert cloned.spell_effect == scroll.spell_effect
    assert cloned is not scroll


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
        item_stats=ItemStats(nutrition_value=20),
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
