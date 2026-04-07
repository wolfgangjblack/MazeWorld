"""Tests for encounter/quest generation, dialogue exhaustion, checkers,
validators, gameplay audit, and placement utilities."""

import random
from unittest.mock import patch

from src.models.npc import StaticNPC
from src.models.encounter import (
    CombatEvent, PuzzleEvent, EventEncounter,
)
from src.models.story import OverarchingStory, Faction, RoomStoryBeat
from src.models.world_bible import WorldBible, RoomBible

from src.generate.checker import (
    NPCChecker, MonsterChecker, ItemChecker, EventChecker,
)
from src.generate.validator import (
    NPCValidator, MonsterValidator, ItemValidator, EventValidator,
    ValidationReport,
)
from src.generate.world_editor import gameplay_audit
from src.generate.placement import (
    find_open_cells, place_encounters, place_npcs, place_items,
    place_day_night_variants, compute_zones, get_player_start,
)
from src.utils.conversation_utils import check_dialogue_exhaustion


# ─── Helpers ─────────────────────────────────────────────────────────────


def _make_npc(**overrides):
    defaults = dict(x=0, y=0, id=1, name="Arin", job="hunter",
                    personality="cheerful", hobby="tracking",
                    environment="forest")
    defaults.update(overrides)
    npc = StaticNPC(**defaults)
    npc.prepare()
    return npc


def _make_grid(width=10, height=10, wall_id=1):
    """Create a simple grid with border walls and open interior."""
    grid = [[wall_id] * width for _ in range(height)]
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            grid[y][x] = 0
    return grid


# ─── Event time_gate Tests ───────────────────────────────────────────────


class TestEventTimeGate:
    def test_event_has_time_gate_field(self):
        event = CombatEvent(
            id="e1", name="Fight", description="A fight",
            time_gate="night",
        )
        assert event.time_gate == "night"

    def test_event_time_gate_defaults_none(self):
        event = PuzzleEvent(id="e2", name="Lock", description="A lock")
        assert event.time_gate is None

    def test_event_time_gate_day(self):
        event = EventEncounter(
            id="e3", name="Shrine", description="A shrine",
            time_gate="day",
        )
        assert event.time_gate == "day"


# ─── Dialogue Exhaustion Tests ───────────────────────────────────────────


class TestDialogueExhaustion:
    def test_npc_has_exhaustion_fields(self):
        npc = _make_npc()
        assert hasattr(npc, "dialogue_exhausted")
        assert hasattr(npc, "finished_dialogue")
        assert hasattr(npc, "max_dialogue_turns")
        assert npc.dialogue_exhausted is False
        assert npc.max_dialogue_turns == 10

    def test_exhaustion_after_max_turns(self):
        npc = _make_npc()
        # Simulate max_dialogue_turns interactions
        for i in range(npc.max_dialogue_turns):
            npc.add_turn("user", f"msg {i}")
        assert check_dialogue_exhaustion(npc, "hello") is True

    def test_not_exhausted_below_max(self):
        npc = _make_npc()
        npc.add_turn("user", "hello")
        npc.add_turn("npc", "hi")
        assert check_dialogue_exhaustion(npc, "hi") is False

    def test_exhausted_when_quest_completed(self):
        npc = _make_npc()
        npc.add_turn("user", "hello")
        quest_ctx = {"status": "completed"}
        assert check_dialogue_exhaustion(npc, "hi", quest_ctx) is True

    def test_already_exhausted_returns_true(self):
        npc = _make_npc()
        npc.dialogue_exhausted = True
        assert check_dialogue_exhaustion(npc, "hello") is True

    @patch("src.utils.conversation_utils.GAME_MODE", "offline_static")
    def test_static_exhaustion_at_end_node(self):
        npc = _make_npc()
        npc.dialogue_tree = {"_current": "end", "nodes": {"end": {"prompt": "Bye."}}}
        assert check_dialogue_exhaustion(npc, "hi") is True

    @patch("src.utils.conversation_utils.GAME_MODE", "offline_static")
    def test_static_not_exhausted_at_start(self):
        npc = _make_npc()
        npc.dialogue_tree = {
            "nodes": {
                "start": {
                    "prompt": "Hello!",
                    "choices": [{"text": "Hi", "next_node_id": "end"}],
                },
            },
        }
        assert check_dialogue_exhaustion(npc, "hi") is False

    @patch("src.utils.conversation_utils.generate", return_value="I have nothing more to say.")
    def test_exhausted_npc_returns_finished_dialogue(self, _mock):
        from src.utils.conversation_utils import generate_npc_response
        npc = _make_npc()
        npc.has_met_player = True
        npc.dialogue_exhausted = True
        npc.finished_dialogue = "Go away."
        result = generate_npc_response(npc, "hello")
        assert "Go away" in result

    @patch("src.utils.conversation_utils.GAME_MODE", "online")
    def test_non_quest_npc_exhausts_after_6_turns(self):
        npc = _make_npc()
        for i in range(6):
            npc.add_turn("user", f"msg {i}")
        assert check_dialogue_exhaustion(npc, "hello", quest_context=None) is True


# ─── NPC Checker Tests ──────────────────────────────────────────────────


class TestNPCChecker:
    def test_valid_npc_passes(self):
        checker = NPCChecker()
        npc = {"id": 100, "name": "Alice", "type": "StaticNPC",
               "selected": True, "opening_greeting": "Hello!"}
        result = checker.check(npc)
        assert result.passed

    def test_missing_name_fails(self):
        checker = NPCChecker()
        npc = {"id": 100, "name": "", "type": "StaticNPC", "selected": True}
        result = checker.check(npc)
        assert not result.passed
        assert any("empty name" in i for i in result.issues)

    def test_active_npc_missing_greeting_fails(self):
        checker = NPCChecker()
        npc = {"id": 100, "name": "Alice", "type": "StaticNPC", "selected": True}
        result = checker.check(npc)
        assert not result.passed
        assert any("opening_greeting" in i for i in result.issues)

    def test_unknown_type_fails(self):
        checker = NPCChecker()
        npc = {"id": 100, "name": "Alice", "type": "FlyingNPC"}
        result = checker.check(npc)
        assert not result.passed

    def test_merchant_missing_shop_fails(self):
        checker = NPCChecker()
        npc = {"id": 100, "name": "Shop", "type": "MerchantNPC",
               "selected": True, "opening_greeting": "Welcome!"}
        result = checker.check(npc)
        assert not result.passed
        assert any("shop_inventory" in i for i in result.issues)


# ─── Monster Checker Tests ──────────────────────────────────────────────


class TestMonsterChecker:
    def test_valid_monster_passes(self):
        checker = MonsterChecker()
        monster = {"name": "Wolf", "hp": 10, "ac": 10, "level": 1}
        result = checker.check(monster)
        assert result.passed

    def test_missing_name_fails(self):
        checker = MonsterChecker()
        monster = {"hp": 10, "ac": 10, "level": 1}
        result = checker.check(monster)
        assert not result.passed

    def test_zero_hp_fails(self):
        checker = MonsterChecker()
        monster = {"name": "Ghost", "hp": 0, "ac": 10, "level": 1}
        result = checker.check(monster)
        assert not result.passed

    def test_hp_out_of_range_fails(self):
        checker = MonsterChecker()
        # Level 1 expects 8-12 HP, *3 for bosses = 36 max
        monster = {"name": "Dragon", "hp": 100, "ac": 10, "level": 1}
        result = checker.check(monster)
        assert not result.passed
        assert any("HP" in i for i in result.issues)


# ─── Item Checker Tests ─────────────────────────────────────────────────


class TestItemChecker:
    def test_valid_food_passes(self):
        checker = ItemChecker()
        item = {"name": "Bread", "category": "food",
                "item_stats": {"nutrition_value": 15}}
        result = checker.check(item)
        assert result.passed

    def test_valid_weapon_passes(self):
        checker = ItemChecker()
        item = {"name": "Sword", "category": "weapon",
                "item_stats": {"attack_dice": "1d8", "stat_modifier": "STR"}}
        result = checker.check(item)
        assert result.passed

    def test_invalid_category_fails(self):
        checker = ItemChecker()
        item = {"name": "Magic Orb", "category": "artifact",
                "item_stats": {}}
        result = checker.check(item)
        assert not result.passed

    def test_weapon_missing_dice_fails(self):
        checker = ItemChecker()
        item = {"name": "Stick", "category": "weapon", "item_stats": {}}
        result = checker.check(item)
        assert not result.passed

    def test_tool_missing_attribute_fails(self):
        checker = ItemChecker()
        item = {"name": "Wrench", "category": "tool",
                "item_stats": {"uses": 3}}
        result = checker.check(item)
        assert not result.passed

    def test_tool_zero_uses_fails(self):
        checker = ItemChecker()
        item = {"name": "Wrench", "category": "tool",
                "item_stats": {"attribute": "bludgeon", "uses": 0}}
        result = checker.check(item)
        assert not result.passed


# ─── Event Checker time_gate Tests ───────────────────────────────────────


class TestEventCheckerTimeGate:
    def test_valid_time_gate_passes(self):
        checker = EventChecker()
        event = {"name": "Night Ambush", "type": "combat",
                 "monsters": [{"name": "Rat"}], "time_gate": "night"}
        result = checker.check(event)
        assert result.passed

    def test_invalid_time_gate_fails(self):
        checker = EventChecker()
        event = {"name": "Bad Event", "type": "combat",
                 "monsters": [{"name": "Rat"}], "time_gate": "midnight"}
        result = checker.check(event)
        assert not result.passed
        assert any("time_gate" in i for i in result.issues)


# ─── NPC Validator Tests ────────────────────────────────────────────────


class TestNPCValidator:
    def test_valid_npc_passes(self):
        v = NPCValidator()
        npc = {"id": 100, "name": "Alice", "type": "StaticNPC",
               "selected": True, "identity": "A hunter", "opening_greeting": "Hi!"}
        result = v.validate(npc)
        assert result.passed

    def test_active_npc_missing_identity_fails(self):
        v = NPCValidator()
        npc = {"id": 100, "name": "Alice", "selected": True,
               "opening_greeting": "Hi!"}
        result = v.validate(npc)
        assert not result.passed

    def test_merchant_empty_shop_fails(self):
        v = NPCValidator()
        npc = {"id": 100, "name": "Shop", "type": "MerchantNPC",
               "selected": True, "identity": "x", "opening_greeting": "x",
               "shop_inventory": []}
        result = v.validate(npc)
        assert not result.passed

    def test_merchant_invalid_price_fails(self):
        v = NPCValidator()
        npc = {"id": 100, "name": "Shop", "type": "MerchantNPC",
               "selected": True, "identity": "x", "opening_greeting": "x",
               "shop_inventory": [{"item_id": 200, "price": 0, "stock": 1}]}
        result = v.validate(npc)
        assert not result.passed


# ─── Monster Validator Tests ────────────────────────────────────────────


class TestMonsterValidator:
    def test_valid_monster_passes(self):
        v = MonsterValidator()
        monster = {"name": "Wolf", "hp": 10, "ac": 10, "level": 1}
        result = v.validate(monster)
        assert result.passed

    def test_zero_hp_fails(self):
        v = MonsterValidator()
        monster = {"name": "Ghost", "hp": 0, "ac": 10, "level": 1}
        result = v.validate(monster)
        assert not result.passed

    def test_low_ac_fails(self):
        v = MonsterValidator()
        monster = {"name": "Slime", "hp": 10, "ac": 2, "level": 1}
        result = v.validate(monster)
        assert not result.passed

    def test_invalid_ability_effect_fails(self):
        v = MonsterValidator()
        monster = {"name": "Mage", "hp": 10, "ac": 10, "level": 1,
                   "abilities": [{"name": "Zap", "effect_type": "teleport"}]}
        result = v.validate(monster)
        assert not result.passed


# ─── Item Validator Tests ───────────────────────────────────────────────


class TestItemValidator:
    def test_valid_weapon_passes(self):
        v = ItemValidator()
        item = {"name": "Sword", "category": "weapon",
                "item_stats": {"attack_dice": "1d8", "stat_modifier": "STR"}}
        result = v.validate(item)
        assert result.passed

    def test_weapon_bad_dice_format_fails(self):
        v = ItemValidator()
        item = {"name": "Sword", "category": "weapon",
                "item_stats": {"attack_dice": "8"}}
        result = v.validate(item)
        assert not result.passed

    def test_food_restores_nothing_fails(self):
        v = ItemValidator()
        item = {"name": "Stale Bread", "category": "food",
                "item_stats": {"nutrition_value": 0, "hydration_value": 0, "health_value": 0}}
        result = v.validate(item)
        assert not result.passed

    def test_missing_stats_fails(self):
        v = ItemValidator()
        item = {"name": "Mystery", "category": "food"}
        result = v.validate(item)
        assert not result.passed


# ─── Event Validator time_gate Tests ────────────────────────────────────


class TestEventValidatorTimeGate:
    def test_valid_time_gate_passes(self):
        v = EventValidator()
        event = {"name": "Night Fight", "description": "A fight at night.",
                 "type": "combat", "monsters": [{"name": "Bat"}],
                 "time_gate": "night"}
        result = v.validate(event)
        assert result.passed

    def test_invalid_time_gate_fails(self):
        v = EventValidator()
        event = {"name": "Bad", "description": "x", "type": "combat",
                 "monsters": [{"name": "Bat"}], "time_gate": "dawn"}
        result = v.validate(event)
        assert not result.passed


# ─── Gameplay Audit Tests ───────────────────────────────────────────────


class TestGameplayAudit:
    def _make_world(self, **overrides):
        story = OverarchingStory(
            title="Test Story", synopsis="Synopsis",
            faction=Faction(name="Evil Cult", description="Bad"),
            beats=[RoomStoryBeat(room_id="room_0", summary="Darkness")],
        )
        bible = WorldBible(story=story)
        bible.rooms["room_0"] = RoomBible(environment="forest")

        defaults = {
            "bible": bible,
            "npc_pool": [
                {"id": 100, "name": "Alice", "selected": True, "quest_id": None},
                {"id": 101, "name": "Bob", "selected": True, "quest_id": None},
            ],
            "event_list": [
                {"id": "evt_000", "type": "combat", "name": "Rat",
                 "monsters": [{"name": "Rat"}]},
            ],
            "quest_list": [
                {"id": "q_000", "type": "fetch", "giver_npc_id": 100,
                 "target_items": [{"item_id": 200}], "is_story_quest": True},
            ],
            "item_placements": [{"item_id": 200}],
        }
        defaults.update(overrides)
        return defaults

    def test_clean_world_no_errors(self):
        world = self._make_world()
        issues = gameplay_audit(**world)
        errors = [i for i in issues if i["severity"] == "error"]
        assert errors == []

    def test_missing_giver_npc(self):
        world = self._make_world()
        world["quest_list"][0]["giver_npc_id"] = 999
        issues = gameplay_audit(**world)
        assert any("giver NPC" in i["message"] for i in issues)

    def test_missing_fetch_item(self):
        world = self._make_world()
        world["quest_list"][0]["target_items"] = [{"item_id": 999}]
        issues = gameplay_audit(**world)
        assert any("Fetch item" in i["message"] for i in issues)

    def test_combat_event_no_monsters(self):
        world = self._make_world()
        world["event_list"][0]["monsters"] = []
        issues = gameplay_audit(**world)
        assert any("no monsters" in i["message"] for i in issues)

    def test_no_story_quests_warning(self):
        world = self._make_world()
        world["quest_list"][0]["is_story_quest"] = False
        issues = gameplay_audit(**world)
        assert any("No story quests" in i["message"] for i in issues)

    def test_multi_step_missing_sub_quest(self):
        world = self._make_world()
        world["quest_list"].append({
            "id": "q_ms", "type": "multi_step", "giver_npc_id": 100,
            "sub_quest_ids": ["q_000", "q_nonexist"],
        })
        issues = gameplay_audit(**world)
        assert any("sub-quest" in i["message"] for i in issues)

    def test_npc_assigned_to_nonexistent_quest(self):
        world = self._make_world()
        world["npc_pool"][0]["quest_id"] = "q_ghost"
        issues = gameplay_audit(**world)
        assert any("non-existent quest" in i["message"] for i in issues)

    def test_no_faction_warning(self):
        story = OverarchingStory(title="Test", synopsis="S")
        bible = WorldBible(story=story)
        bible.rooms["room_0"] = RoomBible(environment="forest")
        world = self._make_world(bible=bible)
        issues = gameplay_audit(**world)
        assert any("No faction" in i["message"] for i in issues)


# ─── Placement Tests ────────────────────────────────────────────────────


class TestPlacement:
    def test_find_open_cells(self):
        grid = _make_grid(5, 5)
        cells = find_open_cells(grid)
        # Interior: 3x3 = 9 open cells
        assert len(cells) == 9

    def test_find_open_cells_with_occupied(self):
        grid = _make_grid(5, 5)
        cells = find_open_cells(grid, occupied={(1, 1), (2, 2)})
        assert len(cells) == 7

    def test_place_encounters(self):
        grid = _make_grid(10, 10)
        events = [
            {"id": f"evt_{i}", "type": "combat", "name": f"Fight {i}"}
            for i in range(5)
        ]
        random.seed(42)
        positions = place_encounters(grid, events, density=0.1)
        assert len(positions) > 0
        for pos in positions:
            assert "x" in pos and "y" in pos and "event_id" in pos

    def test_place_encounters_assigns_time_gates(self):
        grid = _make_grid(20, 20)
        events = [
            {"id": f"evt_{i}", "type": "combat", "name": f"Fight {i}"}
            for i in range(50)
        ]
        random.seed(42)
        place_encounters(grid, events, density=0.5, time_gate_ratio=0.5)
        gated = [e for e in events if e.get("time_gate")]
        assert len(gated) > 0

    def test_place_npcs(self):
        grid = _make_grid(20, 20)
        npc_pool = [
            {"id": 100, "name": "Alice", "selected": True, "zone": [1, 1]},
            {"id": 101, "name": "Bob", "selected": True, "zone": [5, 5]},
        ]
        zones = [(1, 1), (5, 5)]
        result = place_npcs(grid, npc_pool, zones)
        active = [n for n in result if n.get("selected")]
        assert len(active) == 2
        for npc in active:
            assert "x" in npc and "y" in npc

    def test_place_items(self):
        grid = _make_grid(10, 10)
        item_ids = [200, 201, 202]
        placements = place_items(grid, item_ids)
        assert len(placements) == 3
        for p in placements:
            assert p["item_id"] in item_ids

    def test_place_day_night_variants(self):
        events = [{"id": f"evt_{i}"} for i in range(100)]
        random.seed(42)
        result = place_day_night_variants(events, time_gate_ratio=0.2)
        gated = [e for e in result if e.get("time_gate")]
        # Should be roughly 20% (+/- variance)
        assert 5 <= len(gated) <= 40

    def test_compute_zones(self):
        zones = compute_zones(40, 25, 10)
        assert len(zones) == 12  # 4 columns * 3 rows (25 rounds to 3 zone rows)

    def test_get_player_start(self):
        grid = _make_grid(10, 10)
        pos = get_player_start(grid)
        assert pos is not None
        x, y = pos
        assert grid[y][x] == 0

    def test_get_player_start_no_space(self):
        grid = [[1] * 5 for _ in range(5)]  # All walls
        pos = get_player_start(grid)
        assert pos is None


# ─── ValidationReport Tests ────────────────────────────────────────────


class TestValidationReport:
    def test_empty_report_passes(self):
        report = ValidationReport()
        assert report.status == "passed"

    def test_warning_produces_passed_with_warnings(self):
        report = ValidationReport()
        report.add_warning("minor issue")
        assert report.status == "passed_with_warnings"
        assert report.minor_warnings == 1

    def test_critical_produces_failed(self):
        report = ValidationReport()
        report.add_critical("critical issue")
        assert report.status == "failed"
        assert report.critical_failures == 1

    def test_to_dict(self):
        report = ValidationReport(rooms_validated=1)
        report.add_warning("test warning", entity_id="npc_1", phase="npcs")
        d = report.to_dict()
        assert d["status"] == "passed_with_warnings"
        assert d["rooms_validated"] == 1
        assert len(d["details"]) == 1
        assert d["details"][0]["severity"] == "minor"
