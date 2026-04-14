"""Tests for Phase 2 validation pipeline: checker, validator, world_editor, retry, jester fix."""

import json
import os

import pytest

from src.generate.checker import (
    ClassChecker,
    EventChecker,
    QuestChecker,
)
from src.generate.class_gen import _fallback_class, _fix_stats, _validate_classes
from src.generate.validator import (
    ClassValidator,
    EventValidator,
    QuestValidator,
)
from src.generate.world_editor import build_world_bible, cross_validate, write_world_bible
from src.models.player import (
    STAT_NAMES,
    PlayerClass,
    Spell,
    Stats,
)
from src.models.story import Faction, OverarchingStory, RoomStoryBeat
from src.models.world_bible import EntityRef, RoomBible, WorldBible

# ---------------------------------------------------------------------------
# Checker tests
# ---------------------------------------------------------------------------


class TestClassChecker:
    def _make_valid_classes(self):
        """4 valid class dicts."""
        classes = []
        for arch in ["warrior", "mage", "healer", "jester"]:
            fb = _fallback_class(arch, "forest", "Whisperwood")
            classes.append(fb)
        return classes

    def test_valid_classes_pass(self):
        checker = ClassChecker()
        data = self._make_valid_classes()
        result = checker.check(data)
        assert result.passed, result.issues

    def test_missing_archetype_fails(self):
        checker = ClassChecker()
        data = self._make_valid_classes()
        data.pop()  # remove jester
        result = checker.check(data)
        assert not result.passed
        assert any("Missing archetypes" in i for i in result.issues)
        assert any("jester" in i for i in result.issues)

    def test_wrong_count_fails(self):
        checker = ClassChecker()
        data = self._make_valid_classes()
        data.append(data[0].copy())
        result = checker.check(data)
        assert not result.passed
        assert any("Expected 4" in i for i in result.issues)

    def test_bad_stat_budget_fails(self):
        checker = ClassChecker()
        data = self._make_valid_classes()
        data[0]["stats"]["STR"] = 99
        result = checker.check(data)
        assert not result.passed
        assert any("stat total" in i for i in result.issues)

    def test_not_list_fails(self):
        checker = ClassChecker()
        result = checker.check("not a list")
        assert not result.passed


class TestQuestChecker:
    def test_valid_quest_passes(self):
        checker = QuestChecker()
        quest = {
            "id": 4001,
            "type": "fetch",
            "title": "Get Mushrooms",
            "description": "Find mushrooms.",
            "giver_npc_id": 1000,
            "target_items": [{"item_id": 2000}],
        }
        ctx = {"npc_ids": {1000}, "item_ids": {2000}}
        result = checker.check(quest, ctx)
        assert result.passed, result.issues

    def test_missing_fields_fails(self):
        checker = QuestChecker()
        result = checker.check({"type": "fetch"})
        assert not result.passed
        assert any("Missing fields" in i for i in result.issues)

    def test_bad_giver_npc_fails(self):
        checker = QuestChecker()
        quest = {
            "id": 4001,
            "type": "fetch",
            "title": "Get it",
            "description": "Do it.",
            "giver_npc_id": 1999,
        }
        result = checker.check(quest, {"npc_ids": {1000}})
        assert not result.passed
        assert any("giver NPC" in i for i in result.issues)

    def test_bad_fetch_item_fails(self):
        checker = QuestChecker()
        quest = {
            "id": 4001,
            "type": "fetch",
            "title": "Get it",
            "description": "Do it.",
            "giver_npc_id": 1000,
            "target_items": [{"item_id": 2999}],
        }
        result = checker.check(quest, {"npc_ids": {1000}, "item_ids": {2000}})
        assert not result.passed

    def test_bad_combat_event_fails(self):
        checker = QuestChecker()
        quest = {
            "id": 4001,
            "type": "combat",
            "title": "Kill it",
            "description": "Kill.",
            "giver_npc_id": 1000,
            "target_event_id": 3999,
        }
        result = checker.check(quest, {"npc_ids": {1000}, "event_ids": {3001}})
        assert not result.passed

    def test_escort_bad_npc_fails(self):
        checker = QuestChecker()
        quest = {
            "id": 4001,
            "type": "escort",
            "title": "Escort",
            "description": "Go.",
            "giver_npc_id": 1000,
            "escort_npc_id": 1999,
        }
        result = checker.check(quest, {"npc_ids": {1000}})
        assert not result.passed

    def test_delivery_bad_item_fails(self):
        checker = QuestChecker()
        quest = {
            "id": 4001,
            "type": "delivery",
            "title": "Deliver",
            "description": "Bring.",
            "giver_npc_id": 1000,
            "delivery_item_id": 2999,
            "target_npc_id": 1001,
        }
        result = checker.check(quest, {"npc_ids": {1000, 1001}, "item_ids": {2000}})
        assert not result.passed


class TestEventChecker:
    def test_valid_combat_event(self):
        checker = EventChecker()
        event = {"name": "Goblin", "type": "combat", "monsters": [{"name": "Goblin"}]}
        result = checker.check(event)
        assert result.passed

    def test_combat_no_monsters_fails(self):
        checker = EventChecker()
        event = {"name": "Empty Fight", "type": "combat", "monsters": []}
        result = checker.check(event)
        assert not result.passed

    def test_puzzle_no_walkaway_fails(self):
        checker = EventChecker()
        event = {
            "name": "Locked Door",
            "type": "puzzle",
            "choices": [{"text": "Force it", "dc": 12}],
        }
        result = checker.check(event)
        assert not result.passed

    def test_puzzle_with_walkaway_passes(self):
        checker = EventChecker()
        event = {
            "name": "Locked Door",
            "type": "puzzle",
            "choices": [
                {"text": "Force it", "dc": 12},
                {"text": "Walk away", "auto_success": True},
            ],
        }
        result = checker.check(event)
        assert result.passed

    def test_missing_name_fails(self):
        checker = EventChecker()
        result = checker.check({"type": "event"})
        assert not result.passed


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestClassValidator:
    def test_valid_warrior(self):
        v = ClassValidator()
        # Use _validate_classes to get post-padding PlayerClass with abilities
        fb = _fallback_class("warrior", "forest", "Whisperwood")
        validated = _validate_classes([fb], "forest", "Whisperwood")
        result = v.validate(validated[0])
        assert result.passed, result.reasons

    def test_valid_jester(self):
        v = ClassValidator()
        fb = _fallback_class("jester", "forest", "Whisperwood")
        validated = _validate_classes([fb], "forest", "Whisperwood")
        result = v.validate(validated[0])
        assert result.passed, result.reasons

    def test_bad_budget_fails(self):
        v = ClassValidator()
        data = {"archetype": "warrior", "stats": {s: 20 for s in STAT_NAMES}}
        result = v.validate(data)
        assert not result.passed
        assert any("Stat total" in r for r in result.reasons)

    def test_validates_playerclass_object(self):
        v = ClassValidator()
        stats = _fix_stats({}, "mage")
        pc = PlayerClass(
            name="Druid",
            archetype="mage",
            stats=stats,
            spells=[
                Spell(name=f"S{i}", description="x", spell_type="damage_single", element="fire", stat="INT")
                for i in range(4)
            ],
        )
        result = v.validate(pc)
        assert result.passed, result.reasons

    def test_mage_insufficient_spells(self):
        v = ClassValidator()
        stats = _fix_stats({}, "mage")
        pc = PlayerClass(name="Bad Mage", archetype="mage", stats=stats, spells=[])
        result = v.validate(pc)
        assert not result.passed
        assert any("spells" in r for r in result.reasons)


class TestQuestValidator:
    def test_valid_fetch_quest(self):
        v = QuestValidator()
        quest = {
            "type": "fetch",
            "giver_npc_id": 1000,
            "target_items": [{"item_id": 2000}],
        }
        ctx = {"npc_ids": {1000}, "item_ids": {2000}}
        result = v.validate(quest, ctx)
        assert result.passed

    def test_missing_giver(self):
        v = QuestValidator()
        quest = {"type": "fetch", "giver_npc_id": 1999}
        result = v.validate(quest, {"npc_ids": {1000}})
        assert not result.passed

    def test_combat_missing_event(self):
        v = QuestValidator()
        quest = {"type": "combat", "giver_npc_id": 1000, "target_event_id": 3999}
        result = v.validate(quest, {"npc_ids": {1000}, "event_ids": {3001}})
        assert not result.passed


class TestEventValidator:
    def test_valid_combat(self):
        v = EventValidator()
        event = {"name": "Fight", "description": "A fight.", "type": "combat", "monsters": [{"name": "Rat"}]}
        result = v.validate(event)
        assert result.passed

    def test_puzzle_unsolvable(self):
        v = EventValidator()
        event = {
            "name": "Lock",
            "description": "A lock.",
            "type": "puzzle",
            "choices": [{"text": "Use wrench", "tool_attribute": "wrench"}],
        }
        result = v.validate(event, {"tool_attributes": {"hammer"}})
        assert not result.passed

    def test_missing_name(self):
        v = EventValidator()
        result = v.validate({"description": "x", "type": "event"})
        assert not result.passed


# ---------------------------------------------------------------------------
# WorldBible / world_editor tests
# ---------------------------------------------------------------------------


class TestBuildWorldBible:
    @pytest.fixture
    def world_data(self):
        story = OverarchingStory(
            title="Test Story",
            synopsis="Synopsis",
            faction=Faction(name="Evil Cult", description="Bad guys"),
            beats=[RoomStoryBeat(room_id="room_0", summary="Darkness gathers")],
        )
        npc_pool = [
            {"id": 1000, "name": "Alice", "selected": True},
            {"id": 1001, "name": "Bob", "selected": True},
            {"id": 1002, "name": "Unselected", "selected": False},
        ]
        event_list = [
            {"id": 3000, "type": "combat", "name": "Rat", "monsters": [{"name": "Rat"}, {"name": "Rat"}]},
            {"id": 3001, "type": "puzzle", "name": "Lock"},
        ]
        quest_list = [
            {"id": 4000, "type": "fetch", "giver_npc_id": 1000, "target_items": [{"item_id": 2000}]},
            {"id": 4001, "type": "combat", "giver_npc_id": 1001, "target_event_id": 3000},
        ]
        item_placements = [
            {"x": 1, "y": 1, "item_id": 2000},
            {"x": 2, "y": 2, "item_id": 2001},
        ]
        event_position_map = [
            {"x": 3, "y": 3, "event_id": 3000},
            {"x": 5, "y": 5, "event_id": 3001},
        ]
        return {
            "story": story,
            "npc_pool": npc_pool,
            "event_list": event_list,
            "quest_list": quest_list,
            "item_placements": item_placements,
            "event_position_map": event_position_map,
            "maze_environment": "forest",
        }

    def test_build_indexes_entities(self, world_data):
        bible = build_world_bible(**world_data)
        assert "room_0" in bible.rooms
        room = bible.rooms["room_0"]
        # 2 active NPCs
        assert len(room.npcs) == 2
        # 2 unique items
        assert len(room.items) == 2
        # 2 encounters
        assert len(room.encounters) == 2
        # 2 monsters from combat event
        assert len(room.monsters) == 2
        # 2 quests
        assert len(room.quests) == 2
        # Entity index includes all refs
        assert "npc:1000" in bible.entity_index
        assert "item:2000" in bible.entity_index
        assert "quest:4000" in bible.entity_index
        assert "encounter:3000" in bible.entity_index

    def test_unselected_npcs_excluded(self, world_data):
        bible = build_world_bible(**world_data)
        assert "npc:1002" not in bible.entity_index

    def test_story_beat_propagated(self, world_data):
        bible = build_world_bible(**world_data)
        assert bible.rooms["room_0"].story_beat == "Darkness gathers"

    def test_story_attached(self, world_data):
        bible = build_world_bible(**world_data)
        assert bible.story.title == "Test Story"


class TestCrossValidate:
    def test_valid_world_no_issues(self):
        npc_pool = [
            {"id": 1000, "selected": True},
            {"id": 1001, "selected": True},
        ]
        event_list = [{"id": 3000, "type": "combat"}]
        quest_list = [
            {"id": 4000, "type": "fetch", "giver_npc_id": 1000, "target_items": [{"item_id": 2000}]},
        ]
        item_placements = [{"item_id": 2000}]
        bible = WorldBible()
        issues = cross_validate(bible, npc_pool, event_list, quest_list, item_placements)
        assert issues == []

    def test_missing_giver_npc(self):
        npc_pool = [{"id": 1000, "selected": True}]
        quest_list = [{"id": 4000, "type": "fetch", "giver_npc_id": 1999}]
        issues = cross_validate(WorldBible(), npc_pool, [], quest_list, [])
        assert any("giver NPC" in i for i in issues)

    def test_missing_fetch_item(self):
        npc_pool = [{"id": 1000, "selected": True}]
        quest_list = [
            {"id": 4000, "type": "fetch", "giver_npc_id": 1000, "target_items": [{"item_id": 2999}]},
        ]
        issues = cross_validate(WorldBible(), npc_pool, [], quest_list, [{"item_id": 2000}])
        assert any("fetch item" in i for i in issues)

    def test_missing_combat_event(self):
        npc_pool = [{"id": 1000, "selected": True}]
        quest_list = [
            {"id": 4000, "type": "combat", "giver_npc_id": 1000, "target_event_id": 3999},
        ]
        issues = cross_validate(WorldBible(), npc_pool, [{"id": 3000}], quest_list, [])
        assert any("target event" in i for i in issues)


class TestWriteWorldBible:
    def test_writes_json(self, tmp_path):
        story = OverarchingStory(title="T", synopsis="S")
        bible = WorldBible(story=story)
        bible.rooms["room_0"] = RoomBible(environment="forest")
        bible.entity_index["npc:1000"] = EntityRef(
            entity_type="npc",
            room_id="room_0",
            entity_id="1000",
        )
        out_path = str(tmp_path / "world_bible.json")
        result = write_world_bible(bible, out_path)
        assert result == out_path
        assert os.path.exists(out_path)
        with open(out_path) as f:
            data = json.load(f)
        assert data["story"]["title"] == "T"
        assert "npc:1000" in data["entity_index"]
        assert data["rooms"]["room_0"]["environment"] == "forest"


# ---------------------------------------------------------------------------
# Retry-with-feedback tests
# ---------------------------------------------------------------------------


class TestRetryWithFeedback:
    def test_passes_first_try(self):
        from src.generate.pipeline_utils import _retry_with_feedback

        def gen(feedback=None):
            return {"value": 42}

        def val(content):
            return True, []

        result = _retry_with_feedback(gen, val, "fallback", label="test")
        assert result == {"value": 42}

    def test_retries_then_passes(self):
        from src.generate.pipeline_utils import _retry_with_feedback

        call_count = [0]

        def gen(feedback=None):
            call_count[0] += 1
            if call_count[0] < 3:
                return {"bad": True}
            return {"good": True}

        def val(content):
            if content.get("bad"):
                return False, ["content is bad"]
            return True, []

        result = _retry_with_feedback(gen, val, "fallback", label="test")
        assert result == {"good": True}
        assert call_count[0] == 3

    def test_exhausts_retries_returns_fallback(self):
        from src.generate.pipeline_utils import _retry_with_feedback

        def gen(feedback=None):
            return {"always_bad": True}

        def val(content):
            return False, ["always fails"]

        result = _retry_with_feedback(gen, val, "fallback_val", label="test")
        assert result == "fallback_val"

    def test_passes_feedback_to_generator(self):
        from src.generate.pipeline_utils import _retry_with_feedback

        received_feedback = []

        def gen(feedback=None):
            if feedback:
                received_feedback.extend(feedback)
                return {"fixed": True}
            return {"broken": True}

        def val(content):
            if content.get("broken"):
                return False, ["it broke"]
            return True, []

        result = _retry_with_feedback(gen, val, None, label="test")
        assert result == {"fixed": True}
        assert "it broke" in received_feedback

    def test_handles_generator_exception(self):
        from src.generate.pipeline_utils import _retry_with_feedback

        call_count = [0]

        def gen(feedback=None):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("LLM down")
            return {"ok": True}

        def val(content):
            return True, []

        result = _retry_with_feedback(gen, val, "fallback", label="test")
        assert result == {"ok": True}
        assert call_count[0] == 2


# ---------------------------------------------------------------------------
# Jester stat range fix tests
# ---------------------------------------------------------------------------


class TestJesterStatRangeFix:
    def test_validate_guardrails_jester_uses_9_13(self):
        """validate_guardrails should accept 9-13 secondary range for jester."""
        stats = _fix_stats({}, "jester")
        errors = stats.validate_guardrails("jester")
        assert errors == [], f"Jester fallback stats failed guardrails: {errors}"

    def test_jester_secondary_11_passes(self):
        """A jester stat at 11 should pass secondary validation (range 11-15)."""
        stats = Stats(LUCK=16, STR=11, DEX=13, CON=13, INT=13, WIS=13, CHA=11)
        errors = stats.validate_guardrails("jester")
        secondary_errors = [e for e in errors if "secondary" in e]
        assert not any("STR=11" in e for e in secondary_errors)

    def test_jester_secondary_16_fails(self):
        """A jester stat at 16 should fail secondary validation (max is 15)."""
        stats = Stats(LUCK=16, STR=16, DEX=11, CON=11, INT=11, WIS=11, CHA=11)
        errors = stats.validate_guardrails("jester")
        assert any("STR=16" in e and "secondary" in e for e in errors)

    @pytest.mark.parametrize("archetype", ["warrior", "mage", "healer", "jester"])
    def test_fallback_class_passes_guardrails(self, archetype):
        """Every fallback class should pass validate_guardrails."""
        fb = _fallback_class(archetype, "forest", "Whisperwood")
        stats = Stats(**fb["stats"])
        errors = stats.validate_guardrails(archetype)
        assert errors == [], f"{archetype} fallback failed: {errors}"


# ---------------------------------------------------------------------------
# Import bug fix test
# ---------------------------------------------------------------------------


class TestImportBugFix:
    def test_generate_and_save_image_importable(self):
        """generate_and_save_image should be importable from image_client."""
        from src.generate.image_client import generate_and_save_image

        assert callable(generate_and_save_image)

    def test_pipeline_imports_correct_name(self):
        """pipeline.py should no longer reference _generate_and_save."""
        import inspect

        import src.generate.pipeline as pipeline_mod

        source = inspect.getsource(pipeline_mod)
        assert "_generate_and_save" not in source
        assert "generate_and_save_image" in source
