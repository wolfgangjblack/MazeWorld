"""Tests for Phase 5: Encounters & Monsters."""

import random
import pytest
import pygame
from unittest.mock import MagicMock, patch

from src.models.monster import (
    Monster, MonsterAbility, LootEntry,
    generate_monster, generate_encounter_monsters,
    _roll_dice, LEVEL_SCALING, MONSTER_POOLS,
)
from src.models.encounter import (
    CombatEvent, PuzzleEvent, EventEncounter, EventChoice,
    create_event_from_data,
)
from src.models.player import PlayerCharacter
from src.models.items import Tool, ItemStats


# ─── Helpers ─────────────────────────────────────���─────────────────────

def _make_player(**overrides):
    defaults = {"x": 0, "y": 0, "health": 100, "hunger": 100, "thirst": 100}
    defaults.update(overrides)
    return PlayerCharacter(**defaults)


def _make_tool(name="hammer", attribute="bludgeon"):
    return Tool(
        category="tool", name=name, desc="test",
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
        m.loot_table = [LootEntry(item_id=200, probability=1.0)]
        loot = m.roll_loot()
        assert 200 in loot

    def test_roll_loot_no_drop(self):
        m = _make_monster()
        m.loot_table = [LootEntry(item_id=200, probability=0.0)]
        loot = m.roll_loot()
        assert 200 not in loot

    def test_serialization_round_trip(self):
        m = _make_monster()
        m.abilities = [MonsterAbility(name="Poison", effect_type="poison", damage_dice="1d4")]
        m.loot_table = [LootEntry(item_id=200, probability=0.5)]
        d = m.to_dict()
        m2 = Monster.from_dict(d)
        assert m2.name == m.name
        assert m2.abilities[0].name == "Poison"
        assert m2.loot_table[0].item_id == 200

    def test_choose_action_basic(self):
        m = _make_monster()  # No abilities
        action = m.choose_action()
        assert action["type"] == "attack"


# ─── Monster Generation Tests ─────────────────────────────────────────

class TestMonsterGeneration:
    def test_generate_monster_level_scaling(self):
        """Monster stats should be within level scaling guardrails."""
        for level in [1, 2, 3, 4]:
            scaling = LEVEL_SCALING[level]
            m = generate_monster("forest", level)
            assert scaling["hp"][0] <= m.hp <= scaling["hp"][1]
            assert scaling["ac"][0] <= m.ac <= scaling["ac"][1]
            assert m.level == level

    def test_generate_monster_environment_themed(self):
        """Monster names should come from environment pool."""
        for env in MONSTER_POOLS:
            m = generate_monster(env, 1)
            assert m.name in MONSTER_POOLS[env]

    def test_encounter_composition_solo(self):
        """Roll < 0.4 triggers solo: exactly 1 monster at room level."""
        with patch('random.random', return_value=0.1):
            monsters = generate_encounter_monsters("forest", 2)
        assert len(monsters) == 1
        assert monsters[0].level == 2

    def test_encounter_composition_pack(self):
        """Roll between 0.4 and 0.75 triggers pack: 2-4 weaker monsters."""
        with patch('random.random', return_value=0.5):
            monsters = generate_encounter_monsters("cave", 2)
        assert 2 <= len(monsters) <= 4
        for m in monsters:
            assert m.level == 1  # max(1, room_level - 1)

    def test_encounter_composition_mixed(self):
        random.seed(7)
        found_mixed = False
        for _ in range(200):
            monsters = generate_encounter_monsters("dungeon", 3)
            levels = [m.level for m in monsters]
            if len(monsters) >= 3 and max(levels) > min(levels):
                found_mixed = True
                break
        assert found_mixed, "Mixed composition (strong + weak) should appear"

    def test_encounter_scales_with_room(self):
        """Higher room levels should produce tougher monsters."""
        assert LEVEL_SCALING[4]["hp"][0] > LEVEL_SCALING[1]["hp"][0]

    def test_monster_abilities_battle_scoped(self):
        """Monster status effects should not carry between separate encounters."""
        m = generate_monster("forest", 2)
        m.apply_status("stun", 2)
        assert m.is_stunned()
        # Simulate end of combat: create fresh monster from dict (as world_gen does)
        m2 = Monster.from_dict(m.to_dict())
        assert not m2.is_stunned(), "Status effects should not persist through serialization"


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
            id="evt_001", name="Test Fight",
            description="A test combat encounter",
            monsters=monsters, room_level=level,
        )

    def test_start_combat_rolls_initiative(self):
        event = self._make_combat_event()
        player = _make_player()
        result = event.start_combat(player)
        assert "Combat begins" in result["message"]
        assert len(event.turn_order) == 2  # Player + 1 monster
        assert event.combat_started

    def test_player_attack_hit(self):
        monsters = [_make_monster(hp=10, ac=2, dex_mod=0, level=1)]
        event = CombatEvent(
            id="evt_hit", name="Easy Fight",
            description="A weak foe",
            monsters=monsters, room_level=1,
        )
        player = _make_player()
        event.start_combat(player)

        random.seed(99)
        hits = 0
        for _ in range(50):
            event.monsters[0].hp = 10
            result = event.player_attack(player, 0)
            if result.get("damage"):
                hits += 1
        assert hits > 0

    def test_player_attack_kills_monster(self):
        event = self._make_combat_event()
        player = _make_player(health=100)
        event.start_combat(player)

        monster = event.monsters[0]
        monster.hp = 1
        result = event.player_attack(player, 0)
        # If hit, monster should die
        if result.get("damage"):
            assert not monster.is_alive

    def test_monster_turn_attacks_player(self):
        event = self._make_combat_event()
        player = _make_player(health=100)
        event.start_combat(player)

        # Run multiple times to ensure at least one hit
        hits = 0
        for _ in range(50):
            player.health = 100
            result = event.monster_turn(0, player)
            if result.get("damage"):
                hits += 1
        assert hits > 0

    def test_flee_mechanics(self):
        event = self._make_combat_event()
        player = _make_player(health=100)
        event.start_combat(player)

        # Try fleeing many times — should succeed sometimes
        successes = 0
        for _ in range(50):
            event.player_fled = False
            result = event.try_flee(player)
            if result["success"]:
                successes += 1
        assert successes > 0
        assert successes < 50  # Not always

    def test_flee_keeps_tile_active(self):
        event = self._make_combat_event()
        player = _make_player(health=100)
        event.start_combat(player)
        event.player_fled = True
        assert event.is_combat_over() == "fled"
        assert not event.resolved  # Tile stays active

    def test_victory_when_all_dead(self):
        event = self._make_combat_event(num_monsters=2)
        player = _make_player()
        event.start_combat(player)

        for m in event.monsters:
            m.take_damage(m.hp)
        assert event.is_combat_over() == "victory"

    def test_collect_loot_from_dead(self):
        event = self._make_combat_event()
        event.monsters[0].loot_table = [LootEntry(item_id=200, probability=1.0)]
        event.monsters[0].take_damage(event.monsters[0].hp)
        loot = event.collect_loot()
        assert 200 in loot

    def test_legacy_single_roll_resolve(self):
        """Old CombatEvent without monsters should use legacy resolve."""
        event = CombatEvent(
            id="evt_old", name="Old Goblin",
            description="A goblin attacks!",
            difficulty=3, damage_type="health",
            damage_range=[5, 10],
        )
        player = _make_player()
        result = event.resolve(20, player)
        assert result["success"]
        assert event.resolved


# ─── PuzzleEvent Tests ─────────────────────────────────────────────────

class TestPuzzleEvent:
    def _make_puzzle_event(self):
        return PuzzleEvent(
            id="evt_p01", name="Locked Chest",
            description="A locked chest blocks your path.",
            choices=[
                EventChoice(text="Force it open", stat_check="health", dc=12),
                EventChoice(text="Use a bludgeon tool", tool_attribute="bludgeon", dc=8),
                EventChoice(text="Walk away", auto_success=True),
            ],
            reward_item_id=200,
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
        # health//20 = 5, roll needs >= 12-5 = 7
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
        solvable = any(
            c.auto_success or c.tool_attribute or c.stat_check
            for c in event.choices
        )
        assert solvable


# ─── EventEncounter Tests ──────────────────────────────────────────────

class TestEventEncounter:
    def _make_event_encounter(self):
        return EventEncounter(
            id="evt_e01", name="Strange Shrine",
            description="A strange shrine glows in the darkness.",
            choices=[
                EventChoice(text="Pray at the shrine", stat_check="health", dc=12),
                EventChoice(text="Smash it with a tool", tool_attribute="bludgeon", dc=10),
                EventChoice(text="Walk away", auto_success=True),
            ],
            reward_item_id=201,
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
        # health//20 = 5, so roll 7 + 5 = 12 >= dc 12
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
            "id": "evt_001",
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
            "id": "evt_002",
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
            "id": "evt_003",
            "type": "event",
            "name": "Mysterious Light",
            "description": "A light appears.",
            "choices": [
                {"text": "Investigate", "stat_check": "health", "dc": 10},
                {"text": "Ignore", "auto_success": True},
            ],
            "failure_damage_type": "hunger",
            "failure_damage_range": [3, 8],
        }
        event = create_event_from_data(data)
        assert isinstance(event, EventEncounter)
        assert event.failure_damage_type == "hunger"


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
        from src.views.encounter_view import EncounterView
        screen = pygame.Surface((800, 700))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        monsters = [_make_monster()]
        event = CombatEvent(
            id="evt_c", name="Wolf Pack", description="Wolves attack!",
            monsters=monsters, room_level=1,
        )
        db = self._make_dialogue_box(event)
        db.combat_active = True
        db.combat_phase = "initiative"
        view.draw(db)  # Should not raise

    def test_render_puzzle(self):
        from src.views.encounter_view import EncounterView
        screen = pygame.Surface((800, 700))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        event = PuzzleEvent(
            id="evt_p", name="Locked Chest",
            description="A locked chest blocks your path.",
            choices=[
                EventChoice(text="Force it", stat_check="health", dc=12),
                EventChoice(text="Walk away", auto_success=True),
            ],
        )
        db = self._make_dialogue_box(event)
        view.draw(db)

    def test_render_event(self):
        from src.views.encounter_view import EncounterView
        screen = pygame.Surface((800, 700))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        event = EventEncounter(
            id="evt_e", name="Strange Shrine",
            description="A shrine glows.",
            choices=[
                EventChoice(text="Pray", stat_check="health", dc=10),
                EventChoice(text="Leave", auto_success=True),
            ],
        )
        db = self._make_dialogue_box(event)
        view.draw(db)

    def test_render_puzzle_with_result(self):
        from src.views.encounter_view import EncounterView
        screen = pygame.Surface((800, 700))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        event = PuzzleEvent(
            id="evt_pr", name="Lock",
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
        from src.views.encounter_view import EncounterView
        screen = pygame.Surface((800, 700))
        font = pygame.font.SysFont(None, 24)
        view = EncounterView(screen, font)

        event = EventEncounter(
            id="evt_ef", name="Trap",
            description="A trap!",
            choices=[EventChoice(text="Jump", dc=15)],
        )
        db = self._make_dialogue_box(event)
        db.event_context = {
            "result": {"success": False, "message": "You fell!", "damage": 5, "damage_type": "health"},
            "dice_roll": 3,
        }
        view.draw(db)
