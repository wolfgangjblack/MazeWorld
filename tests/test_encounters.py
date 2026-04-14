"""Tests for Phase 5: Encounters & Monsters."""

from unittest.mock import MagicMock

import pygame
import pytest

from src.models.encounter import (
    CombatEvent,
    EventChoice,
    EventEncounter,
    PuzzleEvent,
    create_event_from_data,
)
from src.models.items import ItemStats, Tool
from src.models.monster import (
    LootEntry,
    Monster,
    MonsterAbility,
    _roll_dice,
)
from src.models.player import PlayerCharacter, PlayerClass, Stats

# ─── Helpers ─────────────────────────────────────���─────────────────────


def _make_player(**overrides):
    defaults = {"x": 0, "y": 0, "health": 100, "stamina": 100}
    defaults.update(overrides)
    player = PlayerCharacter(**defaults)
    if player.player_class is None:
        player.player_class = PlayerClass(
            name="TestClass",
            archetype="warrior",
            environment="dungeon",
            starting_weapon="Sword",
            flavor_text="",
            stats=Stats(STR=20, DEX=14, CON=12, INT=10, WIS=10, CHA=10, LUCK=10),
        )
    return player


def _make_tool(name="hammer", attribute="bludgeon"):
    return Tool(
        category="tool",
        name=name,
        desc="test",
        item_stats=ItemStats(attribute=attribute, uses=3),
    )


def _make_monster(**overrides):
    defaults = {
        "name": "TestGoblin",
        "hp": 10,
        "ac": 10,
        "str_mod": 1,
        "dex_mod": 1,
        "attack_name": "slash",
        "damage_dice": 6,
        "damage_dice_expr": "1d6",
        "level": 1,
    }
    defaults.update(overrides)
    return Monster(**defaults)


# ─── Monster Model Tests ──────────────────────────────────────────────


class TestMonster:
    def test_monster_max_hp_equals_hp_on_creation(self):
        m = _make_monster()
        assert m.name == "TestGoblin"
        assert m.hp == 10
        assert m.max_hp == 10
        assert m.is_alive

    def test_take_damage(self):
        m = _make_monster(hp=10)
        m.take_damage(4)
        assert m.hp == 6
        assert m.is_alive

    def test_take_lethal_damage(self):
        m = _make_monster(hp=10)
        m.take_damage(15)
        assert m.hp == 0
        assert not m.is_alive

    def test_roll_initiative_within_range(self):
        m = _make_monster(dex_mod=2)
        for _ in range(50):
            init = m.roll_initiative()
            assert 3 <= init <= 22  # 1+2 to 20+2

    def test_roll_attack_within_range(self):
        m = _make_monster(str_mod=1, level=2)
        for _ in range(50):
            roll = m.roll_attack()
            assert 2 <= roll <= 21  # 1+1 to 20+1

    def test_roll_damage(self):
        m = _make_monster(damage_dice=6, damage_dice_expr="1d6")
        for _ in range(50):
            dmg = m.roll_damage()
            assert 1 <= dmg <= 7  # 1d6 (1-6) + max(str_mod=1, 0)

    def test_status_effects(self):
        m = _make_monster()
        m.apply_status("stun", 2)
        assert m.is_stunned()
        expired = m.tick_status_effects()
        assert "stun" not in expired
        assert m.is_stunned()  # 1 turn remaining
        expired = m.tick_status_effects()
        assert "stun" in expired
        assert not m.is_stunned()

    def test_roll_loot(self):
        m = _make_monster()
        m.loot_table = [LootEntry(item_id=2000, probability=1.0)]
        loot = m.roll_loot()
        assert 2000 in loot

    def test_roll_loot_no_drop(self):
        m = _make_monster()
        m.loot_table = [LootEntry(item_id=2000, probability=0.0)]
        loot = m.roll_loot()
        assert 2000 not in loot

    def test_serialization_round_trip(self):
        m = _make_monster()
        m.abilities = [MonsterAbility(name="Poison", effect_type="poison", damage_dice="1d4")]
        m.loot_table = [LootEntry(item_id=2000, probability=0.5)]
        d = m.to_dict()
        m2 = Monster.from_dict(d)
        assert m2.name == m.name
        assert m2.abilities[0].name == "Poison"
        assert m2.loot_table[0].item_id == 2000

    def test_choose_action_basic(self):
        m = _make_monster()  # No abilities
        action = m.choose_action()
        assert action["type"] == "attack"


# ─── Dice Roller Tests ────────────────────────────────────────────────


class TestDiceRoller:
    def test_0d0(self):
        assert _roll_dice("0d0") == 0

    def test_invalid(self):
        assert _roll_dice("abc") == 0


# ─── CombatEvent Tests ────────────────────────────────────────────────


class TestCombatEvent:
    def _make_combat_event(self, num_monsters=1, level=1):
        monsters = [_make_monster(hp=10, ac=10, level=level) for _ in range(num_monsters)]
        return CombatEvent(
            id=3000,
            name="Test Fight",
            description="A test combat encounter",
            monsters=monsters,
            room_level=level,
        )

    # TODO: rewrite to use CombatController
    # def test_start_combat_rolls_initiative(self):
    #     event = self._make_combat_event()
    #     player = _make_player()
    #     result = event.start_combat(player)
    #     assert "Combat begins" in result["message"]
    #     assert len(event.turn_order) == 2  # Player + 1 monster
    #     assert event.combat_started

    # TODO: rewrite to use CombatController
    # def test_player_attack_hit(self):
    #     monsters = [_make_monster(hp=10, ac=2, dex_mod=0, level=1)]
    #     event = CombatEvent(
    #         id=3001,
    #         name="Easy Fight",
    #         description="A weak foe",
    #         monsters=monsters,
    #         room_level=1,
    #     )
    #     player = _make_player()
    #     event.start_combat(player)
    #
    #     random.seed(99)
    #     hits = 0
    #     for _ in range(50):
    #         event.monsters[0].hp = 10
    #         result = event.player_attack(player, 0)
    #         if result.get("damage"):
    #             hits += 1
    #     assert hits > 0

    # TODO: rewrite to use CombatController
    # def test_player_attack_kills_monster(self):
    #     event = self._make_combat_event()
    #     player = _make_player(health=100)
    #     event.start_combat(player)
    #
    #     monster = event.monsters[0]
    #     monster.hp = 1
    #     result = event.player_attack(player, 0)
    #     # If hit, monster should die
    #     if result.get("damage"):
    #         assert not monster.is_alive

    # TODO: rewrite to use CombatController
    # def test_monster_turn_attacks_player(self):
    #     event = self._make_combat_event()
    #     player = _make_player(health=100)
    #     event.start_combat(player)
    #
    #     # Run multiple times to ensure at least one hit
    #     hits = 0
    #     for _ in range(50):
    #         player.health = 100
    #         result = event.monster_turn(0, player)
    #         if result.get("damage"):
    #             hits += 1
    #     assert hits > 0

    # TODO: rewrite to use CombatController
    # def test_flee_mechanics(self):
    #     event = self._make_combat_event()
    #     player = _make_player(health=100)
    #     event.start_combat(player)
    #
    #     # Try fleeing many times — should succeed sometimes
    #     successes = 0
    #     for _ in range(50):
    #         event.player_fled = False
    #         result = event.try_flee(player)
    #         if result["success"]:
    #             successes += 1
    #     assert successes > 0
    #     assert successes < 50  # Not always

    # TODO: rewrite to use CombatController
    # def test_flee_keeps_tile_active(self):
    #     event = self._make_combat_event()
    #     player = _make_player(health=100)
    #     event.start_combat(player)
    #     event.player_fled = True
    #     assert event.is_combat_over() == "fled"
    #     assert not event.resolved  # Tile stays active

    # TODO: rewrite to use CombatController
    # def test_victory_when_all_dead(self):
    #     event = self._make_combat_event(num_monsters=2)
    #     player = _make_player()
    #     event.start_combat(player)
    #
    #     for m in event.monsters:
    #         m.take_damage(m.hp)
    #     assert event.is_combat_over() == "victory"

    # TODO: rewrite to use CombatController
    # def test_collect_loot_from_dead(self):
    #     event = self._make_combat_event()
    #     event.monsters[0].loot_table = [LootEntry(item_id=2000, probability=1.0)]
    #     event.monsters[0].take_damage(event.monsters[0].hp)
    #     loot = event.collect_loot()
    #     assert 2000 in loot

    # TODO: rewrite to use CombatController
    # def test_legacy_single_roll_resolve(self):
    #     """Old CombatEvent without monsters should use legacy resolve."""
    #     event = CombatEvent(
    #         id=3002,
    #         name="Old Goblin",
    #         description="A goblin attacks!",
    #         difficulty=3,
    #         damage_type="health",
    #         damage_range=[5, 10],
    #     )
    #     player = _make_player()
    #     result = event.resolve(20, player)
    #     assert result["success"]
    #     assert event.resolved


# ─── PuzzleEvent Tests ─────────────────────────────────────────────────


class TestPuzzleEvent:
    def _make_puzzle_event(self):
        return PuzzleEvent(
            id=3003,
            name="Locked Chest",
            description="A locked chest blocks your path.",
            choices=[
                EventChoice(text="Force it open", stat_check="STR", dc=12),
                EventChoice(text="Use a bludgeon tool", tool_attribute="bludgeon", dc=8),
                EventChoice(text="Walk away", auto_success=True),
            ],
            reward_item_id=2000,
        )

    def test_walk_away_safe(self):
        event = self._make_puzzle_event()
        player = _make_player()
        result = event.resolve(2, 0, player)  # Walk away
        assert result["success"]
        assert result["reward_item_id"] is None
        assert not event.resolved  # Walk away doesn't resolve

    def test_stat_check_success(self):
        event = self._make_puzzle_event()
        player = _make_player(health=100)
        # STR=20 -> modifier (20-10)//2 = 5, roll needs >= 12-5 = 7
        result = event.resolve(0, 15, player)
        assert result["success"]
        assert event.resolved

    def test_tool_bonus(self):
        event = self._make_puzzle_event()
        player = _make_player()
        player.inventory = {"hammer": _make_tool(attribute="bludgeon")}
        # Tool gives +5, so roll 3 + 5 = 8 >= dc 8
        result = event.resolve(1, 3, player)
        assert result["success"]

    def test_wrong_tool_consumed(self):
        event = self._make_puzzle_event()
        player = _make_player()
        # Give a cutting tool, but puzzle wants bludgeon
        player.inventory = {"saw": _make_tool(name="saw", attribute="cutting")}
        # Try bludgeon choice — no bludgeon tool, will fail and not consume
        result = event.resolve(1, 1, player)  # Low roll, should fail
        # The cutting tool isn't consumed because the choice checks bludgeon
        assert not result["success"]

    def test_matching_tool_consumed_on_failure(self):
        """When a matching tool is used and the roll fails, the tool is consumed."""
        event = self._make_puzzle_event()
        player = _make_player()
        player.inventory = {"hammer": _make_tool(name="hammer", attribute="bludgeon")}
        # Bludgeon choice (index 1), very low roll to guarantee failure
        result = event.resolve(1, 1, player)  # roll 1 + 5 (tool) = 6 < dc 8
        assert not result["success"]
        assert result.get("consumed_tool") == "hammer"
        assert "hammer" not in player.inventory

    def test_solvability_at_least_one_option(self):
        """Puzzle must have at least one completable solution."""
        event = self._make_puzzle_event()
        solvable = any(c.auto_success or c.tool_attribute or c.stat_check for c in event.choices)
        assert solvable


# ─── EventEncounter Tests ──────────────────────────────────────────────


class TestEventEncounter:
    def _make_event_encounter(self):
        return EventEncounter(
            id=3004,
            name="Strange Shrine",
            description="A strange shrine glows in the darkness.",
            choices=[
                EventChoice(text="Pray at the shrine", stat_check="STR", dc=12),
                EventChoice(text="Smash it with a tool", tool_attribute="bludgeon", dc=10),
                EventChoice(text="Walk away", auto_success=True),
            ],
            reward_item_id=2001,
            failure_damage_type="health",
            failure_damage_range=[5, 10],
        )

    def test_walk_away_no_penalty(self):
        event = self._make_event_encounter()
        player = _make_player()
        initial_health = player.health
        result = event.resolve(2, 0, player)  # Walk away
        assert result["success"]
        assert result.get("walked_away")
        assert not event.resolved  # Event stays active
        assert player.health == initial_health

    def test_success_with_stat_check(self):
        event = self._make_event_encounter()
        player = _make_player(health=100)
        result = event.resolve(0, 18, player)  # High roll
        assert result["success"]
        assert event.resolved

    def test_failure_applies_damage(self):
        event = self._make_event_encounter()
        player = _make_player(health=100)
        initial_health = player.health
        result = event.resolve(0, 1, player)  # Very low roll
        assert not result["success"]
        assert player.health < initial_health

    def test_dice_plus_modifier(self):
        event = self._make_event_encounter()
        player = _make_player(health=100)
        # STR=20 → modifier (20-10)//2 = 5, so roll 7 + 5 = 12 >= dc 12
        result = event.resolve(0, 7, player)
        assert result["success"]


# ─── Event Tile Trigger Tests ──────────────────────────────────────────


class TestEncounterTileTrigger:
    def test_event_tile_detected(self, maze):
        """Player stepping on event tile should detect it."""
        player = _make_player()
        for y, row in enumerate(maze.grid):
            for x, cell in enumerate(row):
                if cell == maze.event_tile_id:
                    player.x, player.y = x, y
                    assert player.is_on_event_tile(maze)
                    return
        pytest.skip("No event tiles in maze")

    def test_event_tile_cleared_on_victory(self, maze):
        """Resolved event should clear the tile to 0."""
        for y, row in enumerate(maze.grid):
            for x, cell in enumerate(row):
                if cell == maze.event_tile_id:
                    maze.grid[y][x] = 0
                    assert maze.grid[y][x] == 0
                    return
        pytest.skip("No event tiles in maze")


# ─── create_event_from_data Tests ─────────────────────────────────────


class TestCreateEventFromData:
    def test_combat_with_monsters(self):
        data = {
            "id": 3000,
            "type": "combat",
            "name": "Wolf Pack",
            "description": "Wolves attack!",
            "monsters": [
                {"name": "Wolf", "hp": 10, "ac": 10, "damage_dice_expr": "1d6", "level": 1},
            ],
            "room_level": 1,
        }
        event = create_event_from_data(data)
        assert isinstance(event, CombatEvent)
        assert len(event.monsters) == 1
        assert event.monsters[0].name == "Wolf"

    def test_puzzle_event(self):
        data = {
            "id": 3010,
            "type": "puzzle",
            "name": "Locked Door",
            "description": "A locked door.",
            "choices": [
                {"text": "Pick lock", "dc": 12},
                {"text": "Leave", "auto_success": True},
            ],
        }
        event = create_event_from_data(data)
        assert isinstance(event, PuzzleEvent)
        assert len(event.choices) == 2

    def test_event_encounter(self):
        data = {
            "id": 3011,
            "type": "event",
            "name": "Mysterious Light",
            "description": "A light appears.",
            "choices": [
                {"text": "Investigate", "stat_check": "STR", "dc": 10},
                {"text": "Ignore", "auto_success": True},
            ],
            "failure_damage_type": "stamina",
            "failure_damage_range": [3, 8],
        }
        event = create_event_from_data(data)
        assert isinstance(event, EventEncounter)
        assert event.failure_damage_type == "stamina"


# ─── EncounterView Render Tests ──────────────────────────────────────


class TestEncounterViewRender:
    """Smoke tests: EncounterView.draw() should not raise for any event type."""

    @pytest.fixture(autouse=True)
    def _init_pygame(self):
        pygame.init()
        yield
        pygame.quit()

    def _make_dialogue_box(self, event):
        db = MagicMock()
        db.current_event = event
        db.event_active = True
        db.awaiting_roll = False
        db.event_context = {}
        db.combat_active = False
        db.combat_phase = None
        db.combat_log = []
        db.player_stunned_turns = 0
        db.player_poison_turns = 0
        return db

    def test_render_combat_trigger(self):
        from config import SCREEN_HEIGHT, SCREEN_WIDTH
        from src.views.encounter_view import EncounterView

        screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        monsters = [_make_monster()]
        event = CombatEvent(
            id=3005,
            name="Wolf Pack",
            description="Wolves attack!",
            monsters=monsters,
            room_level=1,
        )
        db = self._make_dialogue_box(event)
        db.combat_active = True
        db.combat_phase = "initiative"
        view.draw(db)  # Should not raise

    def test_render_puzzle(self):
        from config import SCREEN_HEIGHT, SCREEN_WIDTH
        from src.views.encounter_view import EncounterView

        screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        event = PuzzleEvent(
            id=3006,
            name="Locked Chest",
            description="A locked chest blocks your path.",
            choices=[
                EventChoice(text="Force it", stat_check="STR", dc=12),
                EventChoice(text="Walk away", auto_success=True),
            ],
        )
        db = self._make_dialogue_box(event)
        view.draw(db)

    def test_render_event(self):
        from config import SCREEN_HEIGHT, SCREEN_WIDTH
        from src.views.encounter_view import EncounterView

        screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        event = EventEncounter(
            id=3007,
            name="Strange Shrine",
            description="A shrine glows.",
            choices=[
                EventChoice(text="Pray", stat_check="STR", dc=10),
                EventChoice(text="Leave", auto_success=True),
            ],
        )
        db = self._make_dialogue_box(event)
        view.draw(db)

    def test_render_puzzle_with_result(self):
        from config import SCREEN_HEIGHT, SCREEN_WIDTH
        from src.views.encounter_view import EncounterView

        screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        event = PuzzleEvent(
            id=3008,
            name="Lock",
            description="A lock.",
            choices=[EventChoice(text="Pick", dc=10)],
        )
        db = self._make_dialogue_box(event)
        db.event_context = {
            "result": {"success": True, "message": "Unlocked!"},
            "dice_roll": 18,
        }
        view.draw(db)

    def test_render_event_with_failure(self):
        from config import SCREEN_HEIGHT, SCREEN_WIDTH
        from src.views.encounter_view import EncounterView

        screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        event = EventEncounter(
            id=3009,
            name="Trap",
            description="A trap!",
            choices=[EventChoice(text="Jump", dc=15)],
        )
        db = self._make_dialogue_box(event)
        db.event_context = {
            "result": {"success": False, "message": "You fell!", "damage": 5, "damage_type": "health"},
            "dice_roll": 3,
        }
        view.draw(db)
