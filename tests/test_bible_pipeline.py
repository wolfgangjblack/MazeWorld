"""Tests for Phase 2/10: Bible-driven pipeline, incremental Bible building,
new checkers/validators, generator base class, and manifest validation.
"""

import json

from src.models.story import OverarchingStory, Faction

from src.generate.world_editor import (
    create_world_bible, add_room_to_bible, get_bible_context,
    cross_validate, write_world_bible,
)
from src.generate.checker import (
    ItemChecker, NPCChecker, MonsterChecker,
)
from src.generate.validator import (
    ValidationReport, ItemValidator, NPCValidator, MonsterValidator,
)
from src.generate.generator import (
    BaseGenerator,
)
from src.generate.pipeline import build_manifest, GenerationAborted


# ---------------------------------------------------------------------------
# Incremental Bible building
# ---------------------------------------------------------------------------

class TestCreateWorldBible:
    def test_creates_empty_bible_with_story(self):
        story = OverarchingStory(title="Test", synopsis="A test story")
        bible = create_world_bible(story)
        assert bible.story.title == "Test"
        assert len(bible.rooms) == 0
        assert len(bible.entity_index) == 0


class TestAddRoomToBible:
    def test_adds_single_room(self):
        story = OverarchingStory(title="T")
        bible = create_world_bible(story)
        add_room_to_bible(
            bible,
            room_id="room_0",
            room_level=1,
            maze_environment="forest",
            story_beat="Darkness gathers",
            npc_pool=[
                {"id": 100, "name": "Alice", "selected": True},
                {"id": 101, "name": "Bob", "selected": False},
            ],
            event_list=[
                {"id": "evt_000", "type": "combat", "monsters": [{"name": "Rat"}]},
            ],
            quest_list=[
                {"id": "q_000", "type": "fetch"},
            ],
            item_placements=[
                {"item_id": 200, "x": 1, "y": 1},
            ],
            gate_encounter_id="gate_0",
        )
        assert "room_0" in bible.rooms
        room = bible.rooms["room_0"]
        assert room.environment == "forest"
        assert room.story_beat == "Darkness gathers"
        assert room.gate_encounter_id == "gate_0"
        assert len(room.npcs) == 1  # Only selected NPCs
        assert "npc:100" in bible.entity_index
        assert "npc:101" not in bible.entity_index
        assert len(room.encounters) == 1
        assert len(room.monsters) == 1
        assert len(room.quests) == 1
        assert len(room.items) == 1

    def test_multi_room_incremental(self):
        story = OverarchingStory(title="Multi")
        bible = create_world_bible(story)

        # Room 0
        add_room_to_bible(
            bible, room_id="room_0", room_level=1, maze_environment="forest",
            npc_pool=[{"id": 100, "selected": True}],
            event_list=[{"id": "r0_evt_0", "type": "puzzle"}],
        )
        assert len(bible.rooms) == 1
        assert len(bible.entity_index) == 2  # npc + encounter

        # Room 1 — Bible now has room 0 content
        add_room_to_bible(
            bible, room_id="room_1", room_level=2, maze_environment="cave",
            npc_pool=[{"id": 200, "selected": True}],
            event_list=[{"id": "r1_evt_0", "type": "combat", "monsters": [{"name": "Bat"}]}],
        )
        assert len(bible.rooms) == 2
        assert "npc:100" in bible.entity_index  # Room 0 still present
        assert "npc:200" in bible.entity_index  # Room 1 added
        assert len(bible.entity_index) == 5  # 2 npcs + 2 encounters + 1 monster


class TestGetBibleContext:
    def test_context_includes_story_and_rooms(self):
        story = OverarchingStory(
            title="Test Story", synopsis="Synopsis",
            faction=Faction(name="Evil", description="Bad"),
        )
        bible = create_world_bible(story)
        add_room_to_bible(
            bible, room_id="room_0", room_level=1, maze_environment="forest",
            npc_pool=[{"id": 100, "selected": True}],
        )
        ctx = get_bible_context(bible)
        assert ctx["story_title"] == "Test Story"
        assert ctx["faction_name"] == "Evil"
        assert len(ctx["rooms"]) == 1
        assert ctx["rooms"][0]["environment"] == "forest"
        assert ctx["total_npcs"] == 1


# ---------------------------------------------------------------------------
# Extended cross-validation
# ---------------------------------------------------------------------------

class TestCrossValidateExtended:
    def _make_bible_2rooms(self):
        story = OverarchingStory(title="T")
        bible = create_world_bible(story)
        add_room_to_bible(
            bible, room_id="room_0", room_level=1, maze_environment="forest",
            npc_pool=[{"id": 100, "selected": True}],
            gate_encounter_id="gate_0",
        )
        add_room_to_bible(
            bible, room_id="room_1", room_level=2, maze_environment="cave",
            npc_pool=[{"id": 200, "selected": True}],
        )
        return bible

    def test_missing_gate_encounter(self):
        story = OverarchingStory(title="T")
        bible = create_world_bible(story)
        add_room_to_bible(
            bible, room_id="room_0", room_level=1, maze_environment="forest",
            gate_encounter_id="",  # Missing gate for non-final room
        )
        add_room_to_bible(
            bible, room_id="room_1", room_level=2, maze_environment="cave",
        )
        issues = cross_validate(bible, [], [], [], [])
        assert any("gate encounter" in i for i in issues)

    def test_gate_on_final_room_not_required(self):
        story = OverarchingStory(title="T")
        bible = create_world_bible(story)
        add_room_to_bible(
            bible, room_id="room_0", room_level=1, maze_environment="forest",
            gate_encounter_id="gate_0",
        )
        add_room_to_bible(
            bible, room_id="room_1", room_level=2, maze_environment="cave",
            gate_encounter_id="",  # Final room, no gate needed
        )
        issues = cross_validate(bible, [], [], [], [])
        gate_issues = [i for i in issues if "gate encounter" in i]
        assert len(gate_issues) == 0

    def test_missing_story_quest(self):
        bible = self._make_bible_2rooms()
        quest_list = [
            {"id": "q_0", "type": "fetch", "giver_npc_id": 100,
             "room_id": "room_0", "is_story_quest": False},
        ]
        npc_pool = [{"id": 100, "selected": True}]
        issues = cross_validate(bible, npc_pool, [], quest_list, [])
        # Both rooms should flag missing story quest
        story_issues = [i for i in issues if "story quest" in i]
        assert len(story_issues) >= 1

    def test_empty_room_npcs(self):
        story = OverarchingStory(title="T")
        bible = create_world_bible(story)
        add_room_to_bible(
            bible, room_id="room_0", room_level=1, maze_environment="forest",
            npc_pool=[],  # No NPCs at all
        )
        issues = cross_validate(bible, [], [], [], [])
        assert any("no active NPCs" in i for i in issues)


# ---------------------------------------------------------------------------
# New Checkers
# ---------------------------------------------------------------------------

class TestItemChecker:
    def test_valid_food_passes(self):
        checker = ItemChecker()
        item = {"name": "Bread", "category": "food",
                "item_stats": {"nutrition_value": 15, "price": 5}}
        result = checker.check(item)
        assert result.passed

    def test_missing_name_fails(self):
        checker = ItemChecker()
        item = {"category": "food", "item_stats": {"nutrition_value": 15}}
        result = checker.check(item)
        assert not result.passed
        assert any("missing name" in i for i in result.issues)

    def test_invalid_category_fails(self):
        checker = ItemChecker()
        item = {"name": "Thing", "category": "invalid", "item_stats": {}}
        result = checker.check(item)
        assert not result.passed

    def test_weapon_missing_dice_fails(self):
        checker = ItemChecker()
        item = {"name": "Sword", "category": "weapon",
                "item_stats": {"stat_modifier": "STR"}}
        result = checker.check(item)
        assert not result.passed
        assert any("attack_dice" in i for i in result.issues)

    def test_tool_missing_attribute_fails(self):
        checker = ItemChecker()
        item = {"name": "Hammer", "category": "tool", "item_stats": {}}
        result = checker.check(item)
        assert not result.passed

    def test_food_no_nutrition_fails(self):
        checker = ItemChecker()
        item = {"name": "Empty", "category": "food",
                "item_stats": {"nutrition_value": 0, "hydration_value": 0}}
        result = checker.check(item)
        assert not result.passed


class TestNPCChecker:
    def test_valid_npc_passes(self):
        checker = NPCChecker()
        npc = {"name": "Alice", "type": "StaticNPC",
               "environment": "forest", "personality": "kind"}
        result = checker.check(npc)
        assert result.passed

    def test_missing_fields_fails(self):
        checker = NPCChecker()
        npc = {"name": "Alice"}
        result = checker.check(npc)
        assert not result.passed

    def test_invalid_type_fails(self):
        checker = NPCChecker()
        npc = {"name": "Alice", "type": "InvalidNPC",
               "environment": "forest", "personality": "kind"}
        result = checker.check(npc)
        assert not result.passed

    def test_empty_name_fails(self):
        checker = NPCChecker()
        npc = {"name": "", "type": "StaticNPC",
               "environment": "forest", "personality": "kind"}
        result = checker.check(npc)
        assert not result.passed


class TestMonsterChecker:
    def test_valid_monster_passes(self):
        checker = MonsterChecker()
        monster = {"name": "Goblin", "hp": 20, "attack_dice": "1d6", "ac": 12}
        result = checker.check(monster)
        assert result.passed

    def test_missing_name_fails(self):
        checker = MonsterChecker()
        monster = {"hp": 20, "attack_dice": "1d6", "ac": 12}
        result = checker.check(monster)
        assert not result.passed

    def test_zero_hp_fails(self):
        checker = MonsterChecker()
        monster = {"name": "Ghost", "hp": 0, "attack_dice": "1d4", "ac": 10}
        result = checker.check(monster)
        assert not result.passed

    def test_missing_attack_dice_fails(self):
        checker = MonsterChecker()
        monster = {"name": "Slime", "hp": 10, "ac": 8}
        result = checker.check(monster)
        assert not result.passed


# ---------------------------------------------------------------------------
# New Validators
# ---------------------------------------------------------------------------

class TestItemValidator:
    def test_valid_weapon(self):
        v = ItemValidator()
        item = {"name": "Sword", "category": "weapon",
                "item_stats": {"attack_dice": "1d6", "stat_modifier": "STR", "price": 20}}
        result = v.validate(item)
        assert result.passed

    def test_food_no_nutrition(self):
        v = ItemValidator()
        item = {"name": "Empty", "category": "food",
                "item_stats": {"nutrition_value": 0, "price": 5}}
        result = v.validate(item)
        assert not result.passed

    def test_negative_price(self):
        v = ItemValidator()
        item = {"name": "Bread", "category": "food",
                "item_stats": {"nutrition_value": 15, "price": -5}}
        result = v.validate(item)
        assert not result.passed

    def test_missing_stats(self):
        v = ItemValidator()
        item = {"name": "Thing", "category": "food"}
        result = v.validate(item)
        assert not result.passed


class TestNPCValidator:
    def test_valid_npc(self):
        v = NPCValidator()
        npc = {"name": "Alice", "type": "StaticNPC", "environment": "forest",
               "personality": "kind", "opening_greeting": "Hello!"}
        result = v.validate(npc)
        assert result.passed

    def test_missing_greeting(self):
        v = NPCValidator()
        npc = {"name": "Bob", "type": "RandomNPC", "environment": "cave",
               "personality": "grumpy"}
        result = v.validate(npc)
        assert not result.passed

    def test_merchant_no_shop(self):
        v = NPCValidator()
        npc = {"name": "Trader", "type": "MerchantNPC", "environment": "city",
               "personality": "shrewd", "opening_greeting": "Buy something!"}
        result = v.validate(npc)
        assert not result.passed
        assert any("shop_inventory" in r for r in result.reasons)


class TestMonsterValidator:
    def test_valid_monster(self):
        v = MonsterValidator()
        monster = {"name": "Rat", "hp": 10, "max_hp": 10,
                   "attack_dice": "1d4", "ac": 8, "level": 1}
        result = v.validate(monster)
        assert result.passed

    def test_zero_max_hp(self):
        v = MonsterValidator()
        monster = {"name": "Ghost", "hp": 10, "max_hp": 0,
                   "attack_dice": "1d4", "ac": 10, "level": 1}
        result = v.validate(monster)
        assert not result.passed

    def test_missing_level(self):
        v = MonsterValidator()
        monster = {"name": "Slime", "hp": 5, "max_hp": 5,
                   "attack_dice": "1d4", "ac": 6}
        result = v.validate(monster)
        assert not result.passed


# ---------------------------------------------------------------------------
# ValidationReport wiring
# ---------------------------------------------------------------------------

class TestValidationReportInManifest:
    def test_build_manifest_includes_validation(self):
        report = ValidationReport()
        report.rooms_validated = 2
        report.add_warning("test warning", phase="test")

        manifest = build_manifest(
            seed=42, story_seed="test", game_mode="offline_static",
            num_rooms=2, environments=["forest", "cave"],
            generated_at="2026-01-01T00:00:00Z",
            validation=report.to_dict(),
            active_npc_count=4, item_count=10, quest_count=3,
            event_list=[], npc_pool=[],
            player_portrait_path=None, env_portrait_path=None,
            environment="forest", env_name="Whisperwood",
            maze_width=40, maze_height=25,
            class_count=4, portraits_generated=False,
            story_title="Test", faction_name="Evil",
        )
        assert "validation" in manifest
        assert manifest["validation"]["status"] == "passed_with_warnings"
        assert manifest["validation"]["rooms_validated"] == 2
        assert manifest["validation"]["minor_warnings"] == 1

    def test_validation_report_status_lifecycle(self):
        report = ValidationReport()
        assert report.status == "passed"

        report.add_warning("minor issue")
        assert report.status == "passed_with_warnings"

        report.add_critical("critical issue")
        assert report.status == "failed"


# ---------------------------------------------------------------------------
# Generator base class
# ---------------------------------------------------------------------------

class TestBaseGenerator:
    def test_simple_generator_passes(self):
        class SimpleGen(BaseGenerator):
            def _generate(self, context, feedback=None):
                return {"value": 42}
            def _fallback(self, context):
                return {"value": 0}

        gen = SimpleGen()
        result = gen.generate({}, label="test")
        assert result.passed
        assert result.content == {"value": 42}
        assert not result.used_fallback
        assert result.attempts == 1

    def test_generator_uses_fallback_on_exception(self):
        class FailGen(BaseGenerator):
            max_retries = 2
            def _generate(self, context, feedback=None):
                raise RuntimeError("LLM down")
            def _fallback(self, context):
                return {"fallback": True}

        gen = FailGen()
        report = ValidationReport()
        result = gen.generate({}, report=report, label="test")
        assert result.passed
        assert result.used_fallback
        assert result.content == {"fallback": True}
        assert report.major_retries >= 1

    def test_generator_retries_on_check_failure(self):
        from src.generate.checker import BaseChecker, CheckResult

        class StrictChecker(BaseChecker):
            def check(self, data, context=None):
                if data.get("attempt", 0) < 2:
                    return CheckResult(passed=False, issues=["not ready"])
                return CheckResult(passed=True, data=data)

        call_count = [0]
        class RetryGen(BaseGenerator):
            max_retries = 3
            def __init__(self):
                self.checker = StrictChecker()
            def _generate(self, context, feedback=None):
                call_count[0] += 1
                return {"attempt": call_count[0]}
            def _fallback(self, context):
                return {"fallback": True}

        gen = RetryGen()
        result = gen.generate({}, label="test")
        assert result.passed
        assert not result.used_fallback
        assert result.content["attempt"] == 2


# ---------------------------------------------------------------------------
# Prompt directory imports
# ---------------------------------------------------------------------------

class TestPromptImports:
    def test_checker_prompts_importable(self):
        from src.prompts.checker_prompts import (
            event_check_prompt, quest_check_prompt,
            npc_check_prompt, item_check_prompt,
        )
        assert callable(event_check_prompt)
        assert callable(quest_check_prompt)
        assert callable(npc_check_prompt)
        assert callable(item_check_prompt)

    def test_validator_prompts_importable(self):
        from src.prompts.validator_prompts import (
            event_validate_prompt,
        )
        assert callable(event_validate_prompt)

    def test_world_editor_prompts_importable(self):
        from src.prompts.world_editor_prompts import (
            cross_validate_prompt, bible_lore_prompt,
        )
        assert callable(cross_validate_prompt)
        assert callable(bible_lore_prompt)

    def test_checker_prompt_returns_llm_request(self):
        from src.prompts.checker_prompts import event_check_prompt
        from src.prompts.base import LLMRequest
        result = event_check_prompt(
            {"name": "Fight", "type": "combat"},
            "forest", "Whisperwood",
        )
        assert isinstance(result, LLMRequest)
        assert result.max_tokens > 0


# ---------------------------------------------------------------------------
# GenerationAborted exception
# ---------------------------------------------------------------------------

class TestGenerationAborted:
    def test_exception_exists(self):
        assert issubclass(GenerationAborted, Exception)

    def test_exception_message(self):
        exc = GenerationAborted("test failure")
        assert "test failure" in str(exc)


# ---------------------------------------------------------------------------
# World Bible persistence
# ---------------------------------------------------------------------------

class TestBiblePersistence:
    def test_incremental_write_and_read(self, tmp_path):
        story = OverarchingStory(title="Persist Test", synopsis="S")
        bible = create_world_bible(story)

        add_room_to_bible(
            bible, room_id="room_0", room_level=1, maze_environment="forest",
            npc_pool=[{"id": 100, "selected": True}],
            event_list=[{"id": "evt_0", "type": "combat", "monsters": []}],
        )

        path = str(tmp_path / "bible.json")
        write_world_bible(bible, path)

        with open(path) as f:
            data = json.load(f)
        assert data["story"]["title"] == "Persist Test"
        assert "room_0" in data["rooms"]
        assert "npc:100" in data["entity_index"]

        # Add room 1 and re-write
        add_room_to_bible(
            bible, room_id="room_1", room_level=2, maze_environment="cave",
            npc_pool=[{"id": 200, "selected": True}],
        )
        write_world_bible(bible, path)

        with open(path) as f:
            data = json.load(f)
        assert "room_0" in data["rooms"]
        assert "room_1" in data["rooms"]
        assert "npc:200" in data["entity_index"]
