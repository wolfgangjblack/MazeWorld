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


# ---------------------------------------------------------------------------
# Step 2 async entity generation tests
# ---------------------------------------------------------------------------


class TestStep2AsyncWiring:
    def test_step2_calls_all_generators(self):
        """Verify Step 2 dispatches items, NPCs, monsters, and classes."""
        from unittest.mock import AsyncMock, patch

        bible = WorldBible(
            story=OverarchingStory(title="Test", synopsis="A test."),
        )
        bible.rooms["room_0"] = RoomBible(
            environment="forest", environment_name="Testwood", level=1,
        )

        layout = {
            "room_id": "room_0",
            "room_idx": 0,
            "room_level": 1,
            "id_offset": 0,
            "environment": "forest",
            "environment_name": "Testwood",
            "npc_zones": [(0, 0)],
            "open_spaces": [(5, 5), (6, 6)],
        }

        with patch("src.generate.pipeline._async_generate_classes", new_callable=AsyncMock, return_value=[]) as mock_cls, \
             patch("src.generate.pipeline._async_generate_items", new_callable=AsyncMock, return_value=None) as mock_items, \
             patch("src.generate.pipeline._async_generate_npcs", new_callable=AsyncMock, return_value=[]) as mock_npcs, \
             patch("src.generate.pipeline._async_generate_monsters", new_callable=AsyncMock, return_value=[]) as mock_mons:

            from src.generate.pipeline import _step2_sequential_rooms
            result = asyncio.run(_step2_sequential_rooms(bible, [layout]))

        mock_cls.assert_called_once()
        mock_items.assert_called_once()
        mock_npcs.assert_called_once()
        mock_mons.assert_called_once()
        assert "player_classes" in result
        assert "room_entities" in result

    def test_step2_handles_failures_gracefully(self):
        """Verify Step 2 continues even if some generators raise."""
        from unittest.mock import AsyncMock, patch

        bible = WorldBible(
            story=OverarchingStory(title="Test"),
        )
        bible.rooms["room_0"] = RoomBible(environment="forest", level=1)

        layout = {
            "room_id": "room_0", "room_idx": 0, "room_level": 1,
            "id_offset": 0, "environment": "forest",
            "environment_name": "Wood", "npc_zones": [],
            "open_spaces": [],
        }

        with patch("src.generate.pipeline._async_generate_classes", new_callable=AsyncMock, return_value=[]), \
             patch("src.generate.pipeline._async_generate_items", new_callable=AsyncMock, side_effect=RuntimeError("boom")), \
             patch("src.generate.pipeline._async_generate_npcs", new_callable=AsyncMock, return_value=[{"id": 1, "selected": True}]), \
             patch("src.generate.pipeline._async_generate_monsters", new_callable=AsyncMock, return_value=[]):

            from src.generate.pipeline import _step2_sequential_rooms
            result = asyncio.run(_step2_sequential_rooms(bible, [layout]))

        # Items failed but NPCs and monsters should still be present
        entities = result["room_entities"].get("room_0", {})
        assert entities.get("npc_pool") == [{"id": 1, "selected": True}]

    def test_step2_multi_room_sequential(self):
        """Verify Step 2 handles multiple rooms sequentially."""
        from unittest.mock import AsyncMock, patch

        bible = WorldBible(story=OverarchingStory(title="Test"))
        bible.rooms["room_0"] = RoomBible(environment="forest", level=1)
        bible.rooms["room_1"] = RoomBible(environment="cave", level=2)

        layouts = [
            {"room_id": "room_0", "room_idx": 0, "room_level": 1,
             "id_offset": 0, "environment": "forest",
             "environment_name": "Wood", "npc_zones": [], "open_spaces": []},
            {"room_id": "room_1", "room_idx": 1, "room_level": 2,
             "id_offset": 1000, "environment": "cave",
             "environment_name": "Hollow", "npc_zones": [], "open_spaces": []},
        ]

        with patch("src.generate.pipeline._async_generate_classes", new_callable=AsyncMock, return_value=[]), \
             patch("src.generate.pipeline._async_generate_items", new_callable=AsyncMock, return_value={"100": {"name": "Bread"}}), \
             patch("src.generate.pipeline._async_generate_npcs", new_callable=AsyncMock, return_value=[]), \
             patch("src.generate.pipeline._async_generate_monsters", new_callable=AsyncMock, return_value=[]):

            from src.generate.pipeline import _step2_sequential_rooms
            result = asyncio.run(_step2_sequential_rooms(bible, layouts))

        assert "room_0" in result["room_entities"]
        assert "room_1" in result["room_entities"]


# ---------------------------------------------------------------------------
# Weapon soft-restriction tests
# ---------------------------------------------------------------------------


class TestWeaponSoftRestriction:
    def _make_player(self, archetype: str, weapon_type: str, weapon_stat: str = "STR"):
        from src.models.player import PlayerCharacter, PlayerClass, Stats
        from src.models.weapon import Weapon

        stats = Stats(STR=16, DEX=14, CON=12, INT=10, WIS=10, CHA=10, LUCK=10)
        if archetype == "jester":
            stats = Stats(STR=10, DEX=10, CON=10, INT=10, WIS=10, CHA=10, LUCK=16)

        pc = PlayerClass(
            name="Test", archetype=archetype, flavor_text="test",
            environment="forest", stats=stats,
        )
        weapon = Weapon(
            name="TestWeapon", weapon_type=weapon_type,
            stat=weapon_stat, damage_dice=8,
        )
        player = PlayerCharacter(name="Hero", x=0, y=0)
        player.player_class = pc
        player.weapon = weapon
        return player

    def test_warrior_heavy_weapon_gets_bonus(self):
        """Warrior with a heavy weapon gets full stat bonus."""
        player = self._make_player("warrior", "heavy", "STR")
        bonus = player._weapon_stat_bonus("STR")
        # STR=16 → modifier = 3
        assert bonus == 3

    def test_warrior_simple_weapon_no_bonus(self):
        """Warrior with a simple (mage) weapon gets 0 stat bonus."""
        player = self._make_player("warrior", "simple", "INT")
        bonus = player._weapon_stat_bonus("INT")
        assert bonus == 0

    def test_mage_simple_weapon_gets_bonus(self):
        """Mage with a simple weapon gets full stat bonus."""
        player = self._make_player("mage", "simple", "INT")
        bonus = player._weapon_stat_bonus("INT")
        # INT=10 → modifier = 0
        assert bonus == 0  # 0 is correct for INT=10

    def test_mage_heavy_weapon_no_bonus(self):
        """Mage with a heavy (warrior) weapon gets 0 stat bonus."""
        player = self._make_player("mage", "heavy", "STR")
        bonus = player._weapon_stat_bonus("STR")
        assert bonus == 0

    def test_jester_any_weapon_uses_luck_avg(self):
        """Jester gets avg(LUCK mod, weapon stat mod) for any weapon."""
        player = self._make_player("jester", "heavy", "STR")
        bonus = player._weapon_stat_bonus("STR")
        # LUCK=16 → mod 3, STR=10 → mod 0, avg = 1
        assert bonus == 1

    def test_jester_luck_weapon_bonus(self):
        """Jester with high LUCK and matching stat still uses averaging."""
        from src.models.player import PlayerCharacter, PlayerClass, Stats
        from src.models.weapon import Weapon

        stats = Stats(STR=16, DEX=10, CON=10, INT=10, WIS=10, CHA=10, LUCK=16)
        pc = PlayerClass(
            name="Trickster", archetype="jester", flavor_text="t",
            environment="forest", stats=stats,
        )
        weapon = Weapon(name="Blade", weapon_type="heavy", stat="STR", damage_dice=8)
        player = PlayerCharacter(name="Jester", x=0, y=0)
        player.player_class = pc
        player.weapon = weapon
        # STR=16 → mod 3, LUCK=16 → mod 3, avg = 3
        assert player._weapon_stat_bonus("STR") == 3

    def test_no_weapon_unarmed(self):
        """Without a weapon, soft-restriction still applies."""
        from src.models.player import PlayerCharacter, PlayerClass, Stats

        stats = Stats(STR=16, DEX=14, CON=12, INT=10, WIS=10, CHA=10, LUCK=10)
        pc = PlayerClass(
            name="Fighter", archetype="warrior", flavor_text="t",
            environment="forest", stats=stats,
        )
        player = PlayerCharacter(name="Hero", x=0, y=0)
        player.player_class = pc
        player.weapon = None
        # Unarmed: weapon_type defaults to "simple", warrior doesn't match
        # so bonus is 0 — but that's fine, unarmed is weak by design
        bonus = player._weapon_stat_bonus("STR")
        assert bonus == 0


# ---------------------------------------------------------------------------
# Sequential Bible propagation tests
# ---------------------------------------------------------------------------


class TestSequentialBiblePropagation:
    """Tests verifying that room N's Bible context includes room N-1's entities."""

    def _make_multi_room_bible(self):
        """Create a Bible with 3 rooms, room 0 populated with entities."""
        bible = WorldBible(
            story=OverarchingStory(
                title="The Dark Tide",
                synopsis="Evil rises.",
                faction=Faction(name="Abyssal Order", description="deep-sea cult",
                                history="Ancient evil"),
                beats=[
                    RoomStoryBeat(room_id="room_0", summary="Strange tides.", escalation=1),
                    RoomStoryBeat(room_id="room_1", summary="The deep calls.", escalation=3),
                    RoomStoryBeat(room_id="room_2", summary="The abyss opens.", escalation=5),
                ],
                story_npcs=[StoryNPC(name="Marina", backstory="lighthouse keeper", room_id="room_0")],
            ),
        )
        for i in range(3):
            rid = f"room_{i}"
            bible.rooms[rid] = RoomBible(
                environment=["forest", "cave", "dungeon"][i],
                environment_name=["Whisperwood", "Gloomhollow", "Dreadkeep"][i],
                level=i + 1,
                story_beat=bible.story.beats[i].summary,
            )
        # Populate room 0 with generated entities
        bible.add_npc("room_0", EntityLore(
            entity_type="npc", name="Greta", room_id="room_0",
            lore="A blacksmith who forges weapons against the cult.",
        ))
        bible.add_item("room_0", EntityLore(
            entity_type="item", name="Tide-Forged Blade", room_id="room_0",
            lore="A sword tempered in tidal waters.",
        ))
        bible.add_monster("room_0", EntityLore(
            entity_type="monster", name="Corrupted Crab", room_id="room_0",
            lore="A massive crab twisted by abyssal magic.",
        ))
        return bible

    def test_room1_context_includes_room0_entities(self):
        """Room 1's cumulative context includes room 0's generated NPCs, items, monsters."""
        bible = self._make_multi_room_bible()
        ctx = bible.get_cumulative_context("room_1")

        # Should include story context
        assert "The Dark Tide" in ctx
        assert "Abyssal Order" in ctx
        assert "The deep calls" in ctx  # room 1's own beat

        # Should include room 0's generated entities
        assert "Greta" in ctx
        assert "Tide-Forged Blade" in ctx
        assert "Corrupted Crab" in ctx
        assert "Previously generated content" in ctx

    def test_room0_context_has_no_previous_rooms(self):
        """Room 0's cumulative context should NOT include 'Previously generated' section."""
        bible = self._make_multi_room_bible()
        ctx = bible.get_cumulative_context("room_0")

        assert "The Dark Tide" in ctx
        assert "Previously generated content" not in ctx

    def test_room2_context_includes_room0_and_room1(self):
        """Room 2's cumulative context includes entities from both room 0 and room 1."""
        bible = self._make_multi_room_bible()
        # Add room 1 entities
        bible.add_npc("room_1", EntityLore(
            entity_type="npc", name="Cavern Elder", room_id="room_1",
            lore="An ancient guide through the caves.",
        ))
        bible.add_item("room_1", EntityLore(
            entity_type="item", name="Glowing Mushroom", room_id="room_1",
            lore="Bioluminescent fungus.",
        ))

        ctx = bible.get_cumulative_context("room_2")

        # Room 0 entities
        assert "Greta" in ctx
        assert "Tide-Forged Blade" in ctx
        assert "Corrupted Crab" in ctx

        # Room 1 entities
        assert "Cavern Elder" in ctx
        assert "Glowing Mushroom" in ctx

    def test_quest_generator_receives_bible_context(self):
        """Verify that quest generators can receive Bible context."""
        bible = self._make_multi_room_bible()
        ctx = bible.get_cumulative_context("room_1")

        # The context should be non-empty and contain story info
        assert len(ctx) > 50
        assert "Abyssal Order" in ctx

    def test_multi_step_quests_can_reference_cross_room_entities(self):
        """Verify cross-room quest linking works."""
        from src.generate.pipeline import _link_cross_room_quests

        story = OverarchingStory(
            title="Test",
            faction=Faction(name="TestFaction", description="test"),
        )
        bible = self._make_multi_room_bible()

        room_results = [
            {
                "room_id": "room_0", "room_idx": 0, "room_level": 1,
                "environment": "forest", "environment_name": "Wood",
                "npc_pool": [], "active_npcs": [],
                "event_list": [], "item_placements": [],
                "quest_list": [
                    {"id": "r0_q_000", "type": "fetch", "is_story_quest": True,
                     "giver_npc_id": 100, "prerequisite_quest_id": None,
                     "title": "Gather Intel"},
                ],
                "gate_encounter_id": None, "player_start": (1, 1),
                "maze": None, "generated_items": None, "room_dir": "/tmp",
            },
            {
                "room_id": "room_1", "room_idx": 1, "room_level": 2,
                "environment": "cave", "environment_name": "Hollow",
                "npc_pool": [], "active_npcs": [],
                "event_list": [], "item_placements": [],
                "quest_list": [
                    {"id": "r1_q_000", "type": "combat", "is_story_quest": True,
                     "giver_npc_id": 1100, "prerequisite_quest_id": None,
                     "title": "Purge the Depths"},
                ],
                "gate_encounter_id": None, "player_start": (1, 1),
                "maze": None, "generated_items": None, "room_dir": "/tmp",
            },
        ]

        _link_cross_room_quests(room_results, bible, story)

        # Room 1's first story quest should now have room 0's last story quest as prerequisite
        assert room_results[1]["quest_list"][0]["prerequisite_quest_id"] == "r0_q_000"

        # A global multi-step quest should have been created in the last room
        multi_quests = [q for q in room_results[-1]["quest_list"] if q["type"] == "multi_step"]
        assert len(multi_quests) == 1
        assert "r0_q_000" in multi_quests[0]["sub_quest_ids"]
        assert "r1_q_000" in multi_quests[0]["sub_quest_ids"]


class TestSequentialStep2:
    """Tests for the sequential room-by-room entity generation."""

    def test_sequential_rooms_processes_in_order(self):
        """Verify _step2_sequential_rooms processes rooms sequentially."""
        from unittest.mock import AsyncMock, patch

        bible = WorldBible(story=OverarchingStory(title="Test"))
        bible.rooms["room_0"] = RoomBible(environment="forest", level=1)
        bible.rooms["room_1"] = RoomBible(environment="cave", level=2)

        layouts = [
            {"room_id": "room_0", "room_idx": 0, "room_level": 1,
             "id_offset": 0, "environment": "forest",
             "environment_name": "Wood", "npc_zones": [], "open_spaces": []},
            {"room_id": "room_1", "room_idx": 1, "room_level": 2,
             "id_offset": 1000, "environment": "cave",
             "environment_name": "Hollow", "npc_zones": [], "open_spaces": []},
        ]

        call_order = []

        async def mock_room_entities(bible, layout):
            call_order.append(layout["room_id"])
            return {"items": None, "npc_pool": [], "monsters": []}

        with patch("src.generate.pipeline._async_generate_classes",
                   new_callable=AsyncMock, return_value=[]), \
             patch("src.generate.pipeline._step2_generate_room_entities",
                   side_effect=mock_room_entities):

            from src.generate.pipeline import _step2_sequential_rooms
            result = asyncio.run(_step2_sequential_rooms(bible, layouts))

        # Rooms should have been processed in order
        assert call_order == ["room_0", "room_1"]
        assert "room_0" in result["room_entities"]
        assert "room_1" in result["room_entities"]

    def test_sequential_room_entities_parallel_within_room(self):
        """Verify that within a single room, items/NPCs/monsters run in parallel."""
        from unittest.mock import AsyncMock, patch

        bible = WorldBible(story=OverarchingStory(title="Test"))
        bible.rooms["room_0"] = RoomBible(environment="forest", level=1)

        layout = {
            "room_id": "room_0", "room_idx": 0, "room_level": 1,
            "id_offset": 0, "environment": "forest",
            "environment_name": "Wood", "npc_zones": [], "open_spaces": [],
        }

        with patch("src.generate.pipeline._async_generate_items",
                   new_callable=AsyncMock, return_value={"100": {"name": "Bread"}}) as mock_items, \
             patch("src.generate.pipeline._async_generate_npcs",
                   new_callable=AsyncMock, return_value=[{"id": 1}]) as mock_npcs, \
             patch("src.generate.pipeline._async_generate_monsters",
                   new_callable=AsyncMock, return_value=[]) as mock_mons:

            from src.generate.pipeline import _step2_generate_room_entities
            result = asyncio.run(_step2_generate_room_entities(bible, layout))

        mock_items.assert_called_once()
        mock_npcs.assert_called_once()
        mock_mons.assert_called_once()
        assert result["items"] == {"100": {"name": "Bread"}}
        assert result["npc_pool"] == [{"id": 1}]


class TestEditorCoherenceCheck:
    """Tests for the editor agent coherence check."""

    def test_detects_duplicate_npc_names(self):
        from src.generate.world_editor import editor_coherence_check

        bible = WorldBible(story=OverarchingStory(title="Test"))
        bible.rooms["room_0"] = RoomBible(environment="forest", level=1)
        bible.rooms["room_1"] = RoomBible(environment="cave", level=2)
        bible.add_npc("room_0", EntityLore(entity_type="npc", name="Greta", room_id="room_0"))
        bible.add_npc("room_1", EntityLore(entity_type="npc", name="Greta", room_id="room_1"))

        issues = editor_coherence_check(bible, [
            {"room_id": "room_0", "event_list": [{"id": "e1"}], "quest_list": [{"id": "q1", "is_story_quest": True}]},
            {"room_id": "room_1", "event_list": [{"id": "e2"}], "quest_list": [{"id": "q2", "is_story_quest": True}]},
        ])
        assert any("Duplicate NPC name" in i for i in issues)

    def test_flags_empty_rooms(self):
        from src.generate.world_editor import editor_coherence_check

        bible = WorldBible(story=OverarchingStory(title="Test"))
        bible.rooms["room_0"] = RoomBible(environment="forest", level=1)

        issues = editor_coherence_check(bible, [
            {"room_id": "room_0", "event_list": [], "quest_list": []},
        ])
        assert any("no events" in i for i in issues)
        assert any("no quests" in i for i in issues)
