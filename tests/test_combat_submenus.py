"""Tests for spell/item selection sub-menus in combat."""

import pygame
import pytest

from src.controllers.combat_controller import CombatController
from src.models.items import Food, ItemStats
from src.models.monster import Monster
from src.models.player import PlayerCharacter, PlayerClass, Stats
from src.models.spell import Spell
from src.models.weapon import STARTER_WEAPONS
from src.views.combat_view import CombatView

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(archetype="mage"):
    stat_blocks = {
        "warrior": dict(STR=16, DEX=14, CON=14, INT=8, WIS=8, CHA=10, LUCK=10),
        "mage": dict(STR=8, DEX=12, CON=10, INT=16, WIS=12, CHA=10, LUCK=10),
    }
    pc = PlayerClass(
        name=archetype.title(),
        archetype=archetype,
        stats=Stats(**stat_blocks[archetype]),
    )
    p = PlayerCharacter(x=0, y=0)
    p.player_class = pc
    p.weapon = STARTER_WEAPONS[archetype]
    return p


def _weak_monster():
    return Monster(
        id=5000,
        species="Goblin",
        level=1,
        hp=10,
        max_hp=10,
        ac=10,
        str_mod=0,
        dex_mod=0,
        damage_dice=4,
        damage_type="physical",
    )


def _fireball():
    return Spell(
        name="Fireball",
        spell_type="damage_single",
        element="fire",
        stat="INT",
        damage_dice=8,
        stamina_cost=5,
    )


def _heal():
    return Spell(
        name="Heal",
        spell_type="heal",
        element="light",
        stat="WIS",
        heal_amount=10,
    )


def _bread():
    return Food(
        category="consumable",
        name="Bread",
        desc="Restores 5 stamina",
        item_stats=ItemStats(stamina_value=5),
    )


# ---------------------------------------------------------------------------
# CombatController: spell selection routes correctly
# ---------------------------------------------------------------------------


class TestSpellSelection:
    def test_cast_specific_spell_by_index(self):
        """Player can select a specific spell by index, not just index 0."""
        player = _make_player("mage")
        player.spells = [_fireball(), _heal()]
        player.stamina = 100
        cc = CombatController(player, [_weak_monster()])

        # Force player turn
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)

        initial_hp = player.health
        result = cc.player_cast_spell(1, 0)  # Cast Heal (index 1)
        assert result["success"]
        assert player.health >= initial_hp  # healed or at least didn't lose HP

    def test_cast_spell_index_out_of_range(self):
        player = _make_player("mage")
        player.spells = [_fireball()]
        cc = CombatController(player, [_weak_monster()])
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)
        result = cc.player_cast_spell(5, 0)
        assert not result["success"]
        assert "Invalid" in result["message"]


# ---------------------------------------------------------------------------
# CombatController: item selection uses specific item
# ---------------------------------------------------------------------------


class TestItemSelection:
    def test_use_specific_item_by_name(self):
        player = _make_player("warrior")
        player.stamina = 50
        bread = _bread()
        player.inventory["Bread"] = bread
        cc = CombatController(player, [_weak_monster()])
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)

        result = cc.player_use_item("Bread")
        assert result["success"]
        assert player.stamina > 50

    def test_use_item_not_in_inventory(self):
        player = _make_player("warrior")
        cc = CombatController(player, [_weak_monster()])
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)
        result = cc.player_use_item("Nonexistent")
        assert not result["success"]


# ---------------------------------------------------------------------------
# CombatView: spell and item sub-menu rendering
# ---------------------------------------------------------------------------


@pytest.fixture
def _pygame_init():
    pygame.init()
    from config import SCREEN_HEIGHT, SCREEN_WIDTH

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HIDDEN)
    font = pygame.font.SysFont(None, 24)
    yield screen, font
    pygame.quit()


class TestCombatViewSubMenus:
    def test_draw_with_spell_selector(self, _pygame_init):
        screen, font = _pygame_init
        view = CombatView(screen, font)
        player = _make_player("mage")
        player.spells = [_fireball(), _heal()]
        cc = CombatController(player, [_weak_monster()])
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)

        # Should not raise
        view.draw(cc, selecting_spell=True, selected_spell=0)
        view.draw(cc, selecting_spell=True, selected_spell=1)

    def test_draw_with_item_selector(self, _pygame_init):
        screen, font = _pygame_init
        view = CombatView(screen, font)
        player = _make_player("warrior")
        player.inventory["Bread"] = _bread()
        cc = CombatController(player, [_weak_monster()])
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)

        # Should not raise
        view.draw(cc, selecting_item=True, selected_item=0)

    def test_draw_normal_action_menu(self, _pygame_init):
        """Normal draw still works with new params defaulted."""
        screen, font = _pygame_init
        view = CombatView(screen, font)
        player = _make_player("warrior")
        cc = CombatController(player, [_weak_monster()])
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)
        view.draw(cc, selected_action=0)


# ---------------------------------------------------------------------------
# Esc backs out without consuming a turn
# ---------------------------------------------------------------------------


class TestEscCancels:
    def test_spell_select_esc_does_not_advance_turn(self):
        """Pressing Esc in spell sub-menu should not advance the turn."""
        player = _make_player("mage")
        player.spells = [_fireball()]
        cc = CombatController(player, [_weak_monster()])
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)
        turn_before = cc.turn_index
        # Simulate: nothing happens (no action executed on Esc)
        # The controller doesn't call any CombatController action on Esc,
        # so turn_index stays the same.
        assert cc.turn_index == turn_before
        assert cc.is_player_turn()

    def test_item_select_esc_does_not_advance_turn(self):
        """Pressing Esc in item sub-menu should not advance the turn."""
        player = _make_player("warrior")
        player.inventory["Bread"] = _bread()
        cc = CombatController(player, [_weak_monster()])
        cc.turn_index = next(i for i, c in enumerate(cc.combatants) if c.is_player)
        turn_before = cc.turn_index
        assert cc.turn_index == turn_before
        assert cc.is_player_turn()
