"""Tests for the InventoryManager system."""

from src.models.items import (
    EscortItem,
    Food,
    ItemStats,
    SpellScroll,
    Weapon,
)
from src.models.player import PlayerCharacter, PlayerClass, Stats
from src.systems.inventory import InventoryManager


def _make_player(**kwargs):
    return PlayerCharacter(x=0, y=0, **kwargs)


def _make_food(name="bread", stamina=15, price=10):
    return Food(
        category="food",
        name=name,
        desc="test food",
        item_stats=ItemStats(stamina_value=stamina, price=price),
    )


def _make_weapon(name="sword", attack_dice="1d6", price=30):
    return Weapon(
        category="weapon",
        name=name,
        desc="test weapon",
        weapon_type="simple",
        item_stats=ItemStats(attack_dice=attack_dice, price=price),
    )


def _make_scroll(name="scroll of fire", spell_effect="fire", price=20):
    return SpellScroll(
        category="spell_scroll",
        name=name,
        desc="test scroll",
        spell_effect=spell_effect,
        item_stats=ItemStats(price=price),
    )


class TestInventoryManagerAdd:
    def test_add_different_items(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        mgr.add(_make_food("bread"))
        mgr.add(_make_food("apple", stamina=10, price=5))
        assert len(player.inventory) == 2


class TestInventoryManagerRemove:
    def test_remove_decrements_quantity(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        food = _make_food()
        food.quantity = 3
        mgr.add(food)
        mgr.remove("bread")
        assert player.inventory["bread"].quantity == 2

    def test_remove_deletes_at_zero(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        mgr.add(_make_food())
        mgr.remove("bread")
        assert "bread" not in player.inventory

    def test_remove_nonexistent_is_safe(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        mgr.remove("nonexistent")  # should not raise


class TestInventoryManagerGetList:
    def test_returns_tuples(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        mgr.add(_make_food())
        result = mgr.get_list()
        assert result == [("bread", 1)]


class TestInventoryManagerEquip:
    def test_equip_weapon(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        mgr.add(_make_weapon())
        msg = mgr.equip_weapon("sword")
        assert "equipped" in msg.lower()
        assert player.equipped_weapon == "sword"

    def test_unequip_weapon(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        mgr.add(_make_weapon())
        player.equipped_weapon = "sword"
        msg = mgr.equip_weapon("sword")
        assert "unequipped" in msg.lower()
        assert player.equipped_weapon is None

    def test_equip_non_weapon(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        mgr.add(_make_food())
        msg = mgr.equip_weapon("bread")
        assert "not a weapon" in msg.lower()

    def test_equip_missing(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        msg = mgr.equip_weapon("ghost_sword")
        assert "don't have" in msg.lower()

    def test_get_equipped_weapon(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        w = _make_weapon()
        mgr.add(w)
        player.equipped_weapon = "sword"
        result = mgr.get_equipped_weapon()
        assert result is not None
        assert result.name == "sword"

    def test_get_equipped_weapon_none(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        result = mgr.get_equipped_weapon()
        assert result is None


class TestInventoryManagerUseGive:
    def test_use_food(self):
        player = _make_player(stamina=50)
        mgr = InventoryManager(player.inventory, player)
        mgr.add(_make_food(stamina=20))
        msg = mgr.use_selected(0)
        assert "ate" in msg.lower() or "used" in msg.lower()
        assert player.stamina == 70
        assert "bread" not in player.inventory

    def test_use_escort_item_not_removed(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        escort = EscortItem(
            category="escort",
            name="Bob (escort)",
            desc="test",
            item_stats=ItemStats(),
            npc_id=1000,
            target_zone=(5, 5),
        )
        mgr.add(escort)
        mgr.use_selected(0)
        assert "Bob (escort)" in player.inventory  # Not consumed

    def test_give_item(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        mgr.add(_make_food())
        msg = mgr.give_selected(0)
        assert "gave" in msg.lower()
        assert "bread" not in player.inventory

    def test_use_empty(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        msg = mgr.use_selected(0)
        assert "no item" in msg.lower()

    def test_give_empty(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        msg = mgr.give_selected(0)
        assert "no item" in msg.lower()


class TestInventoryManagerSpellScroll:
    def test_use_scroll(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        scroll = _make_scroll()
        mgr.add(scroll)
        mgr.use_spell_scroll("scroll of fire")
        assert "scroll of fire" not in player.inventory

    def test_jester_learns_spell(self):
        jester_class = PlayerClass(
            name="Jester",
            archetype="jester",
            stats=Stats(LUCK=18, STR=10, DEX=10, CON=10, INT=10, WIS=10, CHA=4),
        )
        player = _make_player()
        player.player_class = jester_class
        mgr = InventoryManager(player.inventory, player)
        scroll = _make_scroll(spell_effect="fireball")
        mgr.add(scroll)
        msg = mgr.use_spell_scroll("scroll of fire")
        assert "learn" in msg.lower()
        assert "fireball" in player.learned_spells

    def test_scroll_not_in_inventory(self):
        player = _make_player()
        mgr = InventoryManager(player.inventory, player)
        msg = mgr.use_spell_scroll("nonexistent")
        assert "don't have" in msg.lower()


class TestPlayerDelegation:
    """Verify PlayerCharacter methods delegate to InventoryManager."""

    def test_add_to_inventory(self):
        player = _make_player()
        player.add_to_inventory(_make_food())
        assert "bread" in player.inventory

    def test_remove_from_inventory(self):
        player = _make_player()
        player.add_to_inventory(_make_food())
        player.remove_from_inventory("bread")
        assert "bread" not in player.inventory

    def test_get_inventory(self):
        player = _make_player()
        player.add_to_inventory(_make_food())
        result = player.get_inventory()
        assert result == [("bread", 1)]

    def test_use_item(self):
        player = _make_player(stamina=50)
        player.add_to_inventory(_make_food(stamina=20))
        player.use_item()
        assert player.stamina == 70

    def test_give_item(self):
        player = _make_player()
        player.add_to_inventory(_make_food())
        player.give_item()
        assert "bread" not in player.inventory

    def test_equip_weapon(self):
        player = _make_player()
        player.add_to_inventory(_make_weapon())
        player.equip_weapon("sword")
        assert player.equipped_weapon == "sword"

    def test_get_equipped_weapon(self):
        player = _make_player()
        w = _make_weapon()
        player.add_to_inventory(w)
        player.equipped_weapon = "sword"
        result = player.get_equipped_weapon()
        assert result.name == "sword"
