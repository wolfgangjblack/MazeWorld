"""Tests for the Bible-driven pipeline architecture.

Covers: WorldBible model, story models, generator base class,
pipeline Step 1 / Step 2, and entity model enrichments.
"""

import asyncio
import json
import os
import tempfile

from src.models.story import (
    OverarchingStory, Faction, RoomStoryBeat,
    StoryNPC, StoryItem, StoryMonster,
)
from src.models.world_bible import WorldBible, RoomBible, EntityLore
from src.models.monster import Monster
from src.models.npc import NPC, StaticNPC


# ---------------------------------------------------------------------------
# Story model tests
# ---------------------------------------------------------------------------


class TestStoryModels:
    def test_story_npc_has_backstory(self):
        npc = StoryNPC(name="Aria", role="ally", backstory="A brave healer from the south.")
        assert npc.backstory
        assert npc.role == "ally"

    def test_story_item_has_lore(self):
        item = StoryItem(name="Orb of Dawn", lore="Forged in the first sunrise.")
        assert "sunrise" in item.lore

    def test_story_monster_boss_flag(self):
        boss = StoryMonster(name="Gorath", is_boss=True, lore="Ancient demon king.")
        assert boss.is_boss is True

    def test_overarching_story_has_story_entities(self):
        story = OverarchingStory(
            title="Test",
            story_npcs=[StoryNPC(name="A", backstory="b")],
            story_items=[StoryItem(name="C", lore="d")],
            story_monsters=[StoryMonster(name="E", lore="f", is_boss=True)],
        )
        assert len(story.story_npcs) == 1
        assert len(story.story_items) == 1
        assert len(story.story_monsters) == 1

    def test_faction_has_history(self):
        f = Faction(name="Cult", description="bad guys", history="Founded in shadows")
        assert f.history == "Founded in shadows"

    def test_room_beat_has_boss_fields(self):
        beat = RoomStoryBeat(
            room_id="room_0", summary="test",
            boss_name="Guardian", boss_lore="Guards the gate",
        )
        assert beat.boss_name == "Guardian"
        assert beat.boss_lore == "Guards the gate"

    def test_story_final_boss_lore(self):
        story = OverarchingStory(
            final_boss_name="Dark Lord",
            final_boss_lore="Once a king, now a lich.",
        )
        assert story.final_boss_lore == "Once a king, now a lich."


# ---------------------------------------------------------------------------
# WorldBible model tests
# ---------------------------------------------------------------------------


class TestWorldBible:
    def _make_bible(self):
        bible = WorldBible(
            story=OverarchingStory(
                title="Test Story",
                synopsis="A test synopsis.",
                faction=Faction(name="TestFaction", description="desc", history="hist"),
                beats=[RoomStoryBeat(
                    room_id="room_0", summary="Room 0 beat",
                    boss_name="Boss0", boss_lore="Boss lore",
                )],
                story_npcs=[StoryNPC(name="Ally", backstory="brave soul", room_id="room_0")],
            ),
        )
        bible.rooms["room_0"] = RoomBible(
            environment="forest", environment_name="Whisperwood", level=1,
            story_beat="Room 0 beat", boss_name="Boss0",
        )
        return bible

    def test_add_and_retrieve_npc(self):
        bible = self._make_bible()
        bible.add_npc("room_0", EntityLore(
            entity_type="npc", name="Greta", room_id="room_0", lore="A blacksmith.",
        ))
        assert len(bible.rooms["room_0"].npcs) == 1
        assert bible.rooms["room_0"].npcs[0].name == "Greta"

    def test_add_item(self):
        bible = self._make_bible()
        bible.add_item("room_0", EntityLore(
            entity_type="item", name="Sword", room_id="room_0", lore="Sharp.",
        ))
        assert len(bible.rooms["room_0"].items) == 1

    def test_add_monster(self):
        bible = self._make_bible()
        bible.add_monster("room_0", EntityLore(
            entity_type="monster", name="Wolf", room_id="room_0", lore="Howls.",
        ))
        assert len(bible.rooms["room_0"].monsters) == 1

    def test_add_player_class(self):
        bible = self._make_bible()
        bible.add_player_class(EntityLore(
            entity_type="player_class", name="Ranger", lore="A forest warrior.",
        ))
        assert len(bible.player_classes) == 1

    def test_get_story_context(self):
        bible = self._make_bible()
        ctx = bible.get_story_context("room_0")
        assert "Test Story" in ctx
        assert "TestFaction" in ctx
        assert "Room 0 beat" in ctx
        assert "Boss0" in ctx
        assert "Ally" in ctx  # story NPC

    def test_get_all_npc_names(self):
        bible = self._make_bible()
        bible.add_npc("room_0", EntityLore(
            entity_type="npc", name="Greta", room_id="room_0",
        ))
        names = bible.get_all_npc_names()
        assert "Greta" in names

    def test_persist_and_load(self):
        bible = self._make_bible()
        bible.add_npc("room_0", EntityLore(
            entity_type="npc", name="Greta", room_id="room_0", lore="A blacksmith.",
        ))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bible.persist(path)
            loaded = WorldBible.load(path)
            assert loaded.story.title == "Test Story"
            assert len(loaded.rooms["room_0"].npcs) == 1
            assert loaded.rooms["room_0"].npcs[0].name == "Greta"
        finally:
            os.unlink(path)

    def test_get_room_nonexistent(self):
        bible = WorldBible()
        assert bible.get_room("nonexistent") is None

    def test_add_to_nonexistent_room_is_safe(self):
        bible = WorldBible()
        # Should not raise — just silently skip
        bible.add_npc("nonexistent", EntityLore(entity_type="npc", name="X"))
        bible.add_item("nonexistent", EntityLore(entity_type="item", name="X"))
        bible.add_monster("nonexistent", EntityLore(entity_type="monster", name="X"))


# ---------------------------------------------------------------------------
# Entity model enrichment tests
# ---------------------------------------------------------------------------


class TestEntityEnrichments:
    def test_monster_has_backstory_and_time_availability(self):
        m = Monster(
            species="Shadow Wolf",
            backstory="Cursed by the faction to guard the gate.",
            time_availability="night_only",
        )
        assert m.backstory == "Cursed by the faction to guard the gate."
        assert m.time_availability == "night_only"

    def test_monster_default_time_availability(self):
        m = Monster(species="Goblin")
        assert m.time_availability == "always"

    def test_npc_has_backstory(self):
        npc = NPC(x=0, y=0, id=1, backstory="A veteran of the old wars.")
        assert npc.backstory == "A veteran of the old wars."

    def test_static_npc_backstory(self):
        npc = StaticNPC(x=5, y=5, id=2, backstory="Keeps the library secrets.")
        assert npc.backstory is not None


# ---------------------------------------------------------------------------
# Generator base class tests
# ---------------------------------------------------------------------------


class TestGeneratorBase:
    def test_generator_reads_story_context(self):
        from src.generate.generator import Generator

        bible = WorldBible(
            story=OverarchingStory(title="TestGen", synopsis="A test."),
        )
        bible.rooms["room_0"] = RoomBible(
            environment="forest", environment_name="Testwood", level=1,
        )

        # Generator is abstract, so we make a concrete subclass
        class DummyGenerator(Generator):
            async def generate(self):
                return []

        gen = DummyGenerator(bible, "room_0", room_level=1)
        assert gen.environment == "forest"
        assert gen.environment_name == "Testwood"
        assert "TestGen" in gen._story_context

    def test_generator_writes_to_bible(self):
        from src.generate.generator import Generator

        bible = WorldBible()
        bible.rooms["room_0"] = RoomBible(environment="cave", level=1)

        class DummyGenerator(Generator):
            async def generate(self):
                self._write_to_bible("npc", "TestNPC", "A test NPC.", tags=["test"])
                self._write_to_bible("item", "TestItem", "A test item.")
                self._write_to_bible("monster", "TestMonster", "A test monster.")
                return []

        gen = DummyGenerator(bible, "room_0")
        asyncio.run(gen.generate())

        assert len(bible.rooms["room_0"].npcs) == 1
        assert bible.rooms["room_0"].npcs[0].name == "TestNPC"
        assert len(bible.rooms["room_0"].items) == 1
        assert len(bible.rooms["room_0"].monsters) == 1


# ---------------------------------------------------------------------------
# Pipeline helper tests
# ---------------------------------------------------------------------------


class TestPipelineHelpers:
    def test_build_manifest(self):
        from src.generate.pipeline import build_manifest
        m = build_manifest(
            seed=1234,
            story_seed="test",
            game_mode="online",
            num_rooms=1,
            environments=["forest"],
            generated_at="2024-01-01",
            validation={},
            active_npc_count=5,
            item_count=10,
            quest_count=3,
            event_list=[{"event_type": "combat", "monsters": [{}, {}]}],
            npc_pool=[],
            player_portrait_path=None,
            env_portrait_path=None,
            environment="forest",
            env_name="Whisperwood",
            maze_width=40,
            maze_height=30,
            class_count=4,
            portraits_generated=False,
            story_title="Test",
            faction_name="Cult",
        )
        assert m["seed"] == 1234
        assert m["content_index"]["monsters"] == 2

    def test_step1_builds_bible_with_fallback(self):
        """Test that _step1_generate_story produces a valid Bible even when LLM fails."""
        from src.generate.pipeline import _step1_generate_story
        from unittest.mock import patch

        with patch("src.generate.pipeline._llm_generate_full_story", return_value=None), \
             patch("src.generate.pipeline._llm_generate_story", return_value=None):
            story, bible = _step1_generate_story(
                "test seed", 2, ["forest", "cave"]
            )

        assert story.title == "The Shadow's Grasp"
        assert "room_0" in bible.rooms
        assert "room_1" in bible.rooms
        assert bible.rooms["room_0"].environment == "forest"
        assert bible.rooms["room_1"].environment == "cave"

    def test_step1_with_story_data(self):
        """Test Step 1 with mocked LLM returning full story data."""
        from src.generate.pipeline import _step1_generate_story
        from unittest.mock import patch

        mock_story = {
            "title": "The Dark Tide",
            "synopsis": "Evil rises from the deep.",
            "faction": {"name": "Abyssal Order", "description": "Deep-sea cult", "history": "Ancient", "leader": "Kraken King"},
            "escalation_arc": ["Ripples", "Waves"],
            "climax": "Face the Kraken King in the abyss.",
            "final_boss_name": "Kraken King",
            "final_boss_lore": "Once a sailor, now a horror.",
            "beats": [
                {"room_id": "room_0", "summary": "Strange tides.", "escalation": 1, "boss_name": "Sea Hag", "boss_lore": "Corrupted siren."},
                {"room_id": "room_1", "summary": "The deep calls.", "escalation": 3, "boss_name": "Kraken King", "boss_lore": "Final horror."},
            ],
            "key_npc_names": ["Marina"],
            "story_npcs": [{"name": "Marina", "role": "ally", "backstory": "A lighthouse keeper.", "room_id": "room_0", "personality": "brave", "job": "keeper"}],
            "story_items": [{"name": "Trident", "description": "Ancient weapon", "lore": "Forged in a rift.", "room_id": "room_1"}],
            "story_monsters": [{"name": "Sea Hag", "description": "Corrupted siren", "lore": "She sings death.", "room_id": "room_0", "is_boss": True, "species": "siren"}],
        }

        with patch("src.generate.pipeline._llm_generate_full_story", return_value=mock_story):
            story, bible = _step1_generate_story(
                "test", 2, ["forest", "cave"]
            )

        assert story.title == "The Dark Tide"
        assert len(story.story_npcs) == 1
        assert story.story_npcs[0].name == "Marina"
        assert len(story.story_monsters) == 1
        # Check Bible was populated
        assert len(bible.rooms["room_0"].npcs) == 1
        assert len(bible.rooms["room_0"].monsters) == 1
        assert len(bible.rooms["room_1"].items) == 1
        # Check story context includes story entities
        ctx = bible.get_story_context("room_0")
        assert "Marina" in ctx
        assert "Sea Hag" in ctx


# ---------------------------------------------------------------------------
# LLM primitives tests
# ---------------------------------------------------------------------------


class TestLLMPrimitives:
    def test_generate_full_story_primitive_parses_json(self):
        """Test that the primitive correctly delegates to prompt + LLM."""
        from unittest.mock import patch
        from src.generate.generators.llm_primitives import generate_full_story_primitive

        mock_response = json.dumps({
            "title": "Test", "synopsis": "test",
            "faction": {"name": "X"}, "beats": [],
            "story_npcs": [], "story_items": [], "story_monsters": [],
        })

        with patch("src.generate.generators.llm_primitives.generate", return_value=mock_response):
            result = generate_full_story_primitive("seed", 1, ["forest"])

        assert result["title"] == "Test"

    def test_generate_monster_primitive_returns_list(self):
        from unittest.mock import patch
        from src.generate.generators.llm_primitives import generate_monster_primitive

        mock_response = json.dumps([
            {"name": "Wolf", "species": "Wolf", "level": 1, "hp": 10},
        ])

        with patch("src.generate.generators.llm_primitives.generate", return_value=mock_response):
            result = generate_monster_primitive(
                {"environment": {"type": "forest", "name": "Wood"}}, 1, "context"
            )

        assert isinstance(result, list)
        assert result[0]["name"] == "Wolf"

    def test_generate_npc_backstory_returns_string(self):
        from unittest.mock import patch
        from src.generate.generators.llm_primitives import generate_npc_backstory

        with patch("src.generate.generators.llm_primitives.generate", return_value="A brave warrior from the north."):
            result = generate_npc_backstory({"name": "Greta"}, "context")

        assert "brave" in result
