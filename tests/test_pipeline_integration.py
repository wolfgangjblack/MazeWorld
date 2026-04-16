"""End-to-end integration test for the world generation pipeline.

Mocks all AI backends (LLM, image, music, SFX) and runs generate_world()
with NUM_ROOMS=1, verifying the full pipeline produces valid output files
and a structurally correct manifest.
"""

import json
import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.prompts.base import LLMRequest

# ---------------------------------------------------------------------------
# Canned LLM responses
# ---------------------------------------------------------------------------

_ENV_SEQUENCE = json.dumps([{"type": "village", "name": "Thornhaven"}])

_OVERARCHING_STORY = json.dumps({
    "title": "The Dark Tide",
    "synopsis": "A shadow cult spreads corruption through the coastal villages.",
    "faction": {
        "name": "Shadow Guild",
        "description": "A secretive order of dark sorcerers.",
        "history": "Founded in the deep caves beneath the coast.",
        "leader": "Lord Vex",
    },
    "escalation_arc": ["The cult's presence grows."],
    "climax": "Confront Lord Vex in his sanctum.",
    "final_boss_name": "Lord Vex",
    "final_boss_lore": "Once a village elder, now consumed by shadow magic.",
    "key_npc_names": ["Greta", "Old Sal"],
})

_ROOM_BEAT = json.dumps({
    "summary": "The adventurer arrives at a besieged fishing village.",
    "faction_presence": "Shadow Guild agents lurk in the tavern.",
    "escalation": 1,
    "characters": [],
    "mini_boss": {"name": "Shadow Acolyte", "description": "A robed cultist."},
    "conflicts": [],
})

_CLASSES = json.dumps([
    {
        "name": "Harbor Guard",
        "archetype": "warrior",
        "flavor_text": "A stalwart defender of the docks.",
        "starting_weapon": "Rusty Cutlass",
        "stats": {"STR": 16, "DEX": 14, "CON": 15, "INT": 10, "WIS": 10, "CHA": 12, "LUCK": 8},
        "abilities": [
            {"name": "Shield Bash", "description": "Slam with your shield."},
            {"name": "Battle Cry", "description": "Boost morale."},
            {"name": "Heavy Swing", "description": "A powerful overhead strike."},
            {"name": "Intimidate", "description": "Frighten the enemy."},
        ],
        "spells": [],
        "portrait_prompt": "a harbor guard",
        "ability_pool": [{"name": "Cleave", "description": "Hit multiple foes."}],
        "spell_pool": [],
    },
    {
        "name": "Tide Mage",
        "archetype": "mage",
        "flavor_text": "Commands the power of the sea.",
        "starting_weapon": "Driftwood Staff",
        "stats": {"STR": 8, "DEX": 12, "CON": 10, "INT": 16, "WIS": 14, "CHA": 10, "LUCK": 15},
        "abilities": [],
        "spells": [
            {"name": "Tidal Bolt", "description": "A blast of sea water."},
            {"name": "Frost Wave", "description": "A wave of icy cold."},
            {"name": "Whirlpool", "description": "A swirling vortex."},
            {"name": "Sea Shield", "description": "A barrier of water."},
        ],
        "portrait_prompt": "a tide mage",
        "ability_pool": [],
        "spell_pool": [{"name": "Tsunami", "description": "A massive wave."}],
    },
    {
        "name": "Shore Cleric",
        "archetype": "healer",
        "flavor_text": "Blessed by the sea goddess.",
        "starting_weapon": "Coral Mace",
        "stats": {"STR": 10, "DEX": 12, "CON": 13, "INT": 8, "WIS": 16, "CHA": 14, "LUCK": 12},
        "abilities": [],
        "spells": [
            {"name": "Healing Tide", "description": "Restore health with sea magic."},
            {"name": "Purify", "description": "Cleanse poison."},
            {"name": "Blessing", "description": "Grant a stat buff."},
            {"name": "Smite", "description": "Holy damage."},
        ],
        "portrait_prompt": "a shore cleric",
        "ability_pool": [],
        "spell_pool": [{"name": "Resurrect", "description": "Bring back from the brink."}],
    },
    {
        "name": "Dock Rat",
        "archetype": "jester",
        "flavor_text": "A cunning trickster of the wharves.",
        "starting_weapon": "Sharpened Hook",
        "stats": {"STR": 12, "DEX": 13, "CON": 12, "INT": 13, "WIS": 12, "CHA": 13, "LUCK": 15},
        "abilities": [],
        "spells": [],
        "portrait_prompt": "a dock rat jester",
        "ability_pool": [],
        "spell_pool": [],
    },
])

_SPELL_POOL = json.dumps([
    {"name": f"Spell {i}", "description": f"A generated spell number {i}."}
    for i in range(10)
])

_ITEMS = json.dumps({
    "food": [{"name": "Hardtack", "desc": "Dry ship biscuit.", "stamina_value": 10}],
    "drink": [{"name": "Grog", "desc": "Watered-down rum.", "stamina_value": 8}],
    "tools": [{"name": "Rusty Crowbar", "desc": "Good for prying.", "attribute": "bludgeon"}],
    "weapons": [{"name": "Barnacle Blade", "desc": "A corroded short sword."}],
    "spell_scrolls": [{"name": "Scroll of Mending", "desc": "Repairs minor wounds.", "spell_effect": "heal"}],
})

_NPC_BATCH = json.dumps([
    {"name": "Greta", "job": "innkeeper", "personality": "warm", "hobby": "cooking"},
])

_MONSTERS = json.dumps([
    {
        "name": "Goblin Scout",
        "species": "goblin",
        "hp": 25,
        "ac": 12,
        "damage_dice": "1d6",
        "level": 1,
        "abilities": [],
        "elemental_affinity": "dark",
        "description": "A sneaky goblin.",
    },
])

_COMBAT_EVENT = json.dumps([
    {"name": "Dock Ambush", "type": "combat", "description": "Goblins leap from the crates!"},
])

_PUZZLE_EVENT = json.dumps([
    {
        "name": "Locked Gate",
        "type": "puzzle",
        "description": "A rusty gate blocks the path.",
        "choices": [
            {"text": "Force it open", "stat": "STR", "dc": 12},
            {"text": "Walk away", "auto_success": True},
        ],
    },
])

_GENERIC_EVENT = json.dumps([
    {
        "name": "Strange Merchant",
        "type": "event",
        "description": "A hooded figure beckons from an alley.",
        "choices": [
            {"text": "Approach cautiously", "stat": "CHA", "dc": 10},
            {"text": "Ignore them", "auto_success": True},
        ],
    },
])

_QUEST = json.dumps({
    "type": "fetch",
    "title": "Lost Supplies",
    "description": "Find the missing supply crate near the docks.",
})

_SIMPLE_TREE = {
    "nodes": {
        "start": {
            "prompt": "Welcome to Thornhaven!",
            "choices": [
                {"text": "Tell me about this place.", "next_node_id": "lore"},
                {"text": "Goodbye.", "next_node_id": "end"},
            ],
        },
        "lore": {
            "prompt": "It is an old fishing village, besieged by shadows.",
            "choices": [{"text": "Interesting.", "next_node_id": "end"}],
        },
        "end": {
            "prompt": "Safe travels, adventurer!",
            "choices": [],
        },
    }
}

_QUEST_TREE = {
    "incomplete": _SIMPLE_TREE,
    "complete_success": {
        "nodes": {
            "start": {
                "prompt": "You did it!",
                "choices": [{"text": "Glad to help.", "next_node_id": "end"}],
            },
            "end": {"prompt": "Thank you!", "choices": []},
        }
    },
    "complete_failure": {
        "nodes": {
            "start": {
                "prompt": "You failed me.",
                "choices": [{"text": "Sorry.", "next_node_id": "end"}],
            },
            "end": {"prompt": "Leave me be.", "choices": []},
        }
    },
}

_DIALOGUE_TREE = json.dumps(_SIMPLE_TREE)
_QUEST_DIALOGUE_TREE = json.dumps(_QUEST_TREE)

_DIALOGUE_CONTEXT = json.dumps([
    {
        "opening_greeting": "Hello, traveler!",
        "exhausted_dialogue": "I have nothing more to say.",
        "personality_notes": ["friendly", "cautious"],
    },
])

_MUSIC_PROMPTS = json.dumps({
    "combat": "epic orchestral battle theme",
    "maze_village": "calm folk melody with acoustic guitar",
})

_NARRATIVE_TEXT = "You step into the village. The air smells of salt and smoke."
_PORTRAIT_TEXT = "A weathered innkeeper standing in a cozy tavern."


# ---------------------------------------------------------------------------
# LLM dispatcher
# ---------------------------------------------------------------------------

_call_log: list[str] = []


def _mock_llm(request: LLMRequest) -> str:
    """Dispatcher: returns canned JSON/text based on prompt content."""
    sys = request.system.lower()
    usr = request.user_message.lower()

    # --- Phase 0: Environment sequence ---
    if "environment" in sys and "sequence" in sys:
        _call_log.append("env_sequence")
        return _ENV_SEQUENCE

    # --- Phase 1: Story ---
    if "overarching" in sys and "story" in sys:
        _call_log.append("overarching_story")
        return _OVERARCHING_STORY
    if "story beat" in sys:
        _call_log.append("room_beat")
        return _ROOM_BEAT

    # --- Phase 3A: Classes ---
    if "player class" in sys or ("class" in sys and "archetype" in sys):
        _call_log.append("classes")
        return _CLASSES

    # --- Phase 3A-ii: Spell pools (system says "spells" but not "pool") ---
    if "spell" in sys and "name and description" in sys:
        _call_log.append("spell_pool")
        return _SPELL_POOL

    # --- Phase 4B: Dialogue tree (before NPC check since it also has "NPC" context) ---
    if "dialogue tree" in sys:
        _call_log.append("dialogue_tree")
        if "quest" in usr or "quest_type" in usr:
            return _QUEST_DIALOGUE_TREE
        return _DIALOGUE_TREE

    # --- Phase 4B: Dialogue context ---
    if "dialogue" in sys and ("greeting" in sys or "context" in sys or "opening" in sys):
        _call_log.append("dialogue_context")
        return _DIALOGUE_CONTEXT

    # --- Phase 6: Narrative (summary agent) ---
    if "narrator" in sys:
        _call_log.append("narrative")
        return _NARRATIVE_TEXT

    # --- Phase 7: Portrait/image descriptions ---
    if "portrait" in sys or "image" in sys or "diffusion" in sys:
        _call_log.append("portrait_desc")
        return _PORTRAIT_TEXT

    # --- Phase 3C: NPC backstory ---
    if "backstory" in sys:
        _call_log.append("npc_backstory")
        return "Greta grew up in the village by the sea."

    # --- Phase 4A: Event batches (system says "{type} encounters") ---
    if "puzzle" in sys and "encounters" in sys:
        _call_log.append("event_puzzle")
        return _PUZZLE_EVENT
    if "combat" in sys and "encounters" in sys:
        _call_log.append("event_combat")
        return _COMBAT_EVENT
    if "event" in sys and "encounters" in sys:
        _call_log.append("event_generic")
        return _GENERIC_EVENT

    # --- Phase 3C: NPCs (batch) ---
    if "npc" in sys:
        _call_log.append("npc_batch")
        return _NPC_BATCH

    # --- Phase 3D: Monsters ---
    if "monster" in sys:
        _call_log.append("monsters")
        return _MONSTERS

    # --- Phase 4A: Quests ---
    if "quest" in sys:
        _call_log.append("quest")
        return _QUEST

    # --- Phase 3B: Items ---
    if "item" in sys:
        _call_log.append("items")
        return _ITEMS

    # --- Phase 2: Music/SFX prompts ---
    if "music" in sys:
        _call_log.append("music_prompts")
        return _MUSIC_PROMPTS
    if "sfx" in sys or "sound effect" in sys:
        _call_log.append("sfx_prompts")
        return json.dumps({})

    # --- Weapon database ---
    if "weapon" in sys:
        _call_log.append("weapon_db")
        return json.dumps([])

    # --- Full story (alternate path) ---
    if "story" in sys:
        _call_log.append("story_fallback")
        return _OVERARCHING_STORY

    _call_log.append(f"UNMATCHED: sys={sys[:80]}")
    return "{}"


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def gen_dir(tmp_path):
    """Isolated DATA_DIR with all required subdirectories."""
    for sub in [
        "story", "classes", "npcs", "events", "items",
        "monsters", "quests", "rooms/room_0", "portraits",
        "portraits/npcs", "portraits/events", "portraits/classes",
        "portraits/monsters", "portraits/items", "portraits/maps",
        "sfx", "music", "saves", "player",
    ]:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    yield tmp_path
    from src.registry import registry
    registry._loaded = False


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def _build_patches(d: str, gen_dir):
    """Build the list of patch context managers for the pipeline test."""
    mock_img_backend = MagicMock()
    mock_img_backend.generate_and_save.return_value = True

    db_paths_override = {
        "npc": os.path.join(d, "npcs", "npcs.json"),
        "item": os.path.join(d, "items", "items.json"),
        "event": os.path.join(d, "events", "events.json"),
        "quest": os.path.join(d, "quests", "quests.json"),
        "monster": os.path.join(d, "monsters", "monsters.json"),
        "class": os.path.join(d, "classes", "classes.json"),
    }

    return [
        # LLM (3 import paths)
        patch("src.generate.generators.llm_primitives.generate", side_effect=_mock_llm),
        patch("src.generate.llm_executor.generate", side_effect=_mock_llm),
        patch("src.generate.summary_agent.generate", side_effect=_mock_llm),
        # Image (3 functions + backend fallback)
        patch("src.generate.image_client.generate_portraits_parallel_async",
              new_callable=AsyncMock, return_value=None),
        patch("src.generate.image_client.generate_player_portrait", return_value=None),
        patch("src.generate.image_client.generate_and_save_image", return_value=True),
        patch("src.generate.image_client.get_image_backend", return_value=mock_img_backend),
        # Audio
        patch("src.generate.music_client.generate_all_music_async",
              new_callable=AsyncMock, return_value={}),
        patch("src.generate.sfx_client.generate_all_sfx_async",
              new_callable=AsyncMock, return_value={}),
        # Config module
        patch.multiple("config",
                       DATA_DIR=d, NUM_ROOMS=1, WORLD_SEED=9999,
                       STORY_SEED="Test seed", GAME_MODE="offline_static",
                       GENERATE_GUIDE=False, LLM_BACKEND="api",
                       IMAGE_BACKEND="local", MUSIC_BACKEND="none",
                       LLM_CONCURRENCY=1, STORY_CONTEXT_LIMIT=500),
        # Pipeline path constants (bound at import time)
        patch("src.generate.pipeline.DATA_DIR", d),
        patch("src.generate.pipeline.STORY_PATH", str(gen_dir / "story" / "story.json")),
        patch("src.generate.pipeline.CLASS_PATH", str(gen_dir / "classes" / "classes.json")),
        patch("src.generate.pipeline.MANIFEST_PATH", str(gen_dir / "manifest.json")),
        patch("src.generate.pipeline.BIBLE_PATH", str(gen_dir / "world_bible.json")),
        patch("src.generate.pipeline.ITEM_ITEMS_PATH", str(gen_dir / "items" / "items.json")),
        # Pipeline config imports (bound at import time)
        patch("src.generate.pipeline.NUM_ROOMS", 1),
        patch("src.generate.pipeline.WORLD_SEED", 9999),
        patch("src.generate.pipeline.STORY_SEED", "Test seed"),
        patch("src.generate.pipeline.GAME_MODE", "offline_static"),
        patch("src.generate.pipeline.MAZE_WIDTH", 40),
        patch("src.generate.pipeline.MAZE_HEIGHT", 30),
        # db_constants paths (bound at import time)
        patch.dict("src.db_constants.DB_PATHS", db_paths_override),
        # Registry and world_editor DATA_DIR
        patch("src.registry.DATA_DIR", d),
        patch("src.generate.world_editor.DATA_DIR", d),
        patch("src.generate.world_editor.WORLD_BIBLE_PATH", str(gen_dir / "world_bible.json")),
    ]


def test_generate_world_produces_manifest(gen_dir):
    """Full pipeline with mocked AI produces a valid manifest and output files."""
    d = str(gen_dir)
    _call_log.clear()

    stack = ExitStack()
    for p in _build_patches(d, gen_dir):
        stack.enter_context(p)

    with stack:
        from src.generate.pipeline import generate_world
        generate_world()

    # --- File existence ---
    expected_files = [
        "manifest.json",
        "world_bible.json",
        "story/story.json",
        "classes/classes.json",
        "npcs/npcs.json",
        "events/events.json",
        "items/items.json",
        "narrative.json",
        "generation_stats.json",
        "rooms/room_0/maze.json",
    ]
    for path in expected_files:
        assert (gen_dir / path).exists(), f"Missing output file: {path}"

    # --- Manifest structure ---
    manifest = json.loads((gen_dir / "manifest.json").read_text())
    assert manifest["seed"] == 9999
    assert manifest["num_rooms"] == 1
    assert len(manifest["rooms"]) == 1
    assert "validation_report" in manifest
    assert manifest["validation_report"]["status"] in (
        "passed", "passed_with_warnings", "failed"
    )
    assert "generation_stats" in manifest

    # --- Classes ---
    classes = json.loads((gen_dir / "classes" / "classes.json").read_text())
    assert isinstance(classes, list)
    assert len(classes) == 4
    archetypes = {c["archetype"] for c in classes}
    assert archetypes == {"warrior", "mage", "healer", "jester"}

    # --- Story ---
    story = json.loads((gen_dir / "story" / "story.json").read_text())
    assert story["title"]
