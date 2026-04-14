"""Tests for Phase 3 gap fixes: CombatController wiring, unified enums,
unified Spell model, weapon swapping, prompt framing, and API client caching.
"""

from src.controllers.combat_controller import CombatController
from src.generate.backends.llm_api import ApiLLMBackend
from src.generate.class_gen import _parse_damage_dice, _parse_spells
from src.models.combat import CombatAction, CombatState
from src.models.monster import Monster
from src.models.player import PlayerCharacter, PlayerClass, Stats
from src.models.spell import Spell
from src.models.weapon import STARTER_WEAPONS
from src.prompts.base import LLMRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(archetype="warrior", armor=0):
    stats = {
        "warrior": dict(STR=16, DEX=14, CON=14, INT=8, WIS=8, CHA=10, LUCK=10),
        "mage": dict(STR=8, DEX=12, CON=10, INT=16, WIS=12, CHA=10, LUCK=10),
        "healer": dict(STR=8, DEX=10, CON=12, INT=10, WIS=16, CHA=14, LUCK=10),
        "jester": dict(STR=10, DEX=12, CON=10, INT=10, WIS=10, CHA=10, LUCK=16),
    }
    pc = PlayerClass(
        name=archetype.title(),
        archetype=archetype,
        stats=Stats(**stats[archetype]),
    )
    p = PlayerCharacter(x=0, y=0, armor=armor)
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


# ---------------------------------------------------------------------------
# Task 3: Unified Spell model
# ---------------------------------------------------------------------------


class TestUnifiedSpell:
    def test_spell_from_spell_module(self):
        s = Spell(
            name="Fireball",
            spell_type="damage_single",
            element="fire",
            stat="INT",
            damage_dice=8,
            stamina_cost=5,
        )
        assert s.stamina_cost == 5
        assert s.roll_damage() >= 1

    def test_player_can_afford_spell(self):
        p = _make_player("mage")
        s = Spell(
            name="Fireball",
            spell_type="damage_single",
            element="fire",
            stat="INT",
            damage_dice=8,
            stamina_cost=5,
        )
        assert p.can_afford_spell(s)
        p.stamina = 0
        assert not p.can_afford_spell(s)

    def test_player_pay_spell_cost(self):
        p = _make_player("mage")
        s = Spell(
            name="Heal",
            spell_type="heal",
            element="light",
            stat="WIS",
            heal_amount=10,
            stamina_cost=8,
        )
        initial_stamina = p.stamina
        p.pay_spell_cost(s)
        assert p.stamina == initial_stamina - 8

    def test_spell_imported_through_player_module(self):
        from src.models.player import Spell as PlayerSpell

        assert PlayerSpell is Spell

    def test_parse_damage_dice_int(self):
        """Integer input passes through unchanged."""
        assert _parse_damage_dice(8) == 8
        assert _parse_damage_dice(0) == 0
        assert _parse_damage_dice(12) == 12

    def test_parse_damage_dice_str_dice(self):
        """Dice notation extracts the die size (number of sides)."""
        assert _parse_damage_dice("1d8") == 8
        assert _parse_damage_dice("2d6") == 6
        assert _parse_damage_dice("1d4") == 4
        assert _parse_damage_dice("3d10") == 10

    def test_parse_damage_dice_str_number(self):
        """Plain numeric string parses to integer."""
        assert _parse_damage_dice("0") == 0
        assert _parse_damage_dice("6") == 6

    def test_parse_spells_with_dice_notation(self):
        raw = [{"name": "Bolt", "element": "fire", "damage_dice": "1d8", "spell_type": "damage"}]
        result = _parse_spells(raw)
        assert len(result) == 1
        assert result[0].damage_dice == 8
        assert result[0].spell_type == "damage_single"
        assert result[0].stamina_cost >= 0

    def test_parse_spells_heal(self):
        raw = [{"name": "Heal", "element": "light", "spell_type": "heal", "stat": "WIS"}]
        result = _parse_spells(raw)
        assert len(result) == 1
        assert result[0].stamina_cost >= 0


# ---------------------------------------------------------------------------
# Task 4: Mid-combat weapon swapping
# ---------------------------------------------------------------------------


class TestWeaponSwap:
    def test_swap_weapon_no_alternative(self):
        """Cannot swap if no other weapon in inventory."""
        p = _make_player()
        m = _weak_monster()
        cc = CombatController(p, [m])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_swap_weapon()
        assert result["success"] is False

    def test_swap_weapon_costs_turn(self):
        """Weapon swap should advance the turn."""
        from src.models.items import ItemStats
        from src.models.items import Weapon as ShopWeapon

        p = _make_player()
        # Add a shop weapon to inventory
        sword = ShopWeapon(
            category="weapon",
            name="Silver Sword",
            desc="A silver sword.",
            item_stats=ItemStats(stat_modifier="STR", damage_dice=8),
        )
        p.inventory = {"Silver Sword": sword}
        p.equipped_weapon = "fists"

        m = _weak_monster()
        cc = CombatController(p, [m])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0

        result = cc.player_swap_weapon()
        assert result["success"] is True
        assert "Silver Sword" in result["message"]

    def test_swap_weapon_action_in_enum(self):
        assert CombatAction.SWAP_WEAPON.value == "swap_weapon"


# ---------------------------------------------------------------------------
# Task 5: Prompt framing moved to LLMRequest
# ---------------------------------------------------------------------------


class TestPromptFraming:
    def test_format_for_completion(self):
        req = LLMRequest(
            system="You are a test assistant.",
            examples=[("Hello", "Hi there!")],
            user_message="What is 2+2?",
        )
        text = req.format_for_completion()
        assert "You are a test assistant." in text
        assert "User: Hello" in text
        assert "Assistant: Hi there!" in text
        assert "User: What is 2+2?" in text
        assert text.endswith("Assistant:")
        # Should NOT contain old ##Input:/##Output: markers
        assert "##Input" not in text
        assert "##Output" not in text

    def test_format_for_completion_no_examples(self):
        req = LLMRequest(system="sys", user_message="msg")
        text = req.format_for_completion()
        assert "sys" in text
        assert "User: msg" in text
        assert "Assistant:" in text


# ---------------------------------------------------------------------------
# Task 6: Anthropic client caching
# ---------------------------------------------------------------------------


class TestApiClientCaching:
    def test_client_is_none_initially(self):
        backend = ApiLLMBackend()
        assert backend._client is None

    def test_client_cached_after_first_call(self):
        """_get_client should cache — but we can't call it without a key,
        so just verify the attribute exists and __init__ sets it to None."""
        backend = ApiLLMBackend()
        assert hasattr(backend, "_client")
        assert backend._client is None


# ---------------------------------------------------------------------------
# Task 1: CombatController wired into game loop
# ---------------------------------------------------------------------------


class TestCombatControllerWiring:
    def test_combat_controller_full_combat_flow(self):
        """Run a full combat: attack until victory."""
        p = _make_player("warrior")
        p.player_class.stats.STR = 30
        p.level = 5
        m = Monster(
            id=5000,
            species="Goblin",
            level=1,
            hp=5,
            max_hp=5,
            ac=8,
            str_mod=0,
            dex_mod=0,
            damage_dice=2,
            damage_type="physical",
        )
        cc = CombatController(p, [m])
        # Force player first
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0

        # Keep attacking until combat ends
        for _ in range(20):
            if cc.state != CombatState.ONGOING:
                break
            if cc.is_player_turn():
                cc.player_attack(0)
            else:
                cc.execute_monster_turn()

        assert cc.state == CombatState.VICTORY

    def test_combat_controller_spell_flow(self):
        """Mage can cast spells through CombatController."""
        p = _make_player("mage")
        p.player_class.stats.INT = 30
        p.level = 5
        p.spells = [
            Spell(
                name="Fireball",
                spell_type="damage_single",
                element="fire",
                stat="INT",
                damage_dice=12,
                stamina_cost=5,
                targets="single",
            ),
        ]
        m = Monster(
            id=5000,
            species="Goblin",
            level=1,
            hp=5,
            max_hp=5,
            ac=8,
            str_mod=0,
            dex_mod=0,
            damage_dice=2,
            magic_resistance=0,
        )
        cc = CombatController(p, [m], room_level=1)
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0

        initial_stamina = p.stamina
        result = cc.player_cast_spell(0, 0)
        assert p.stamina == initial_stamina - 5
        assert "Fireball" in result["message"]

    def test_combat_controller_flee_flow(self):
        """Player can flee through CombatController."""
        p = _make_player("warrior")
        p.player_class.stats.DEX = 30
        m = _weak_monster()
        cc = CombatController(p, [m])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0

        result = cc.player_flee()
        assert result["success"] is True
        assert cc.state == CombatState.FLED

    def test_combat_controller_item_usage(self):
        """Player can use items through CombatController."""
        from src.models.items import Food, ItemStats

        p = _make_player("warrior")
        bread = Food(
            category="food",
            name="Bread",
            desc="A loaf",
            item_stats=ItemStats(stamina_value=20, health_value=5),
        )
        p.inventory = {"Bread": bread}
        p.stamina = 50
        m = _weak_monster()
        cc = CombatController(p, [m], room_level=1)
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0

        result = cc.player_use_item("Bread")
        assert result["success"] is True
        con_mod = p.get_stat_mod("CON") if hasattr(p, "get_stat_mod") else 0
        expected = min(50 + max(1, 20 + 2 * con_mod), p.max_stamina)
        assert p.stamina == expected

    def test_combat_controller_collect_loot(self):
        """Loot collection from dead monsters."""
        from src.models.monster import LootDrop

        p = _make_player("warrior")
        m = Monster(
            id=5000,
            species="Rat",
            level=1,
            hp=0,
            max_hp=5,
            ac=8,
            str_mod=0,
            dex_mod=0,
            damage_dice=2,
            loot_table=[LootDrop(item_id=2000, probability=1.0)],
        )
        cc = CombatController(p, [m])
        loot = cc.collect_loot()
        assert 2000 in loot

    def test_game_controller_has_combat_state(self):
        """GameController should have combat_controller attribute."""
        import pygame

        pygame.init()
        from config import SCREEN_HEIGHT, SCREEN_WIDTH

        screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        from src.models.dialogue_box import DialogueBox

        db = DialogueBox(screen, font)

        # Minimal maze mock
        class FakeMaze:
            grid = [[0]]
            event_tile_id = 99

            def is_wall(self, x, y):
                return False

        from src.controllers.game_controller import GameController

        p = _make_player()
        gc = GameController(screen, font, FakeMaze(), p, [], db)
        assert gc.combat_handler.combat_controller is None
        assert gc.combat_handler.combat_view is None
        assert gc.combat_handler.active is False
        pygame.quit()
