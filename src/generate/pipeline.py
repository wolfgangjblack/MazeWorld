"""Generation pipeline orchestrator.

This module replaces world_gen.py as the entry point for content generation.
The generate_world() function is imported and called from main.py.
"""

import json
import logging
import os
import random
from datetime import datetime, timezone

from tqdm import tqdm

from config import (
    WORLD_SEED, STORY_SEED, GAME_MODE, MAZE_WIDTH, MAZE_HEIGHT,
    NUM_FOOD, NUM_DRINKS, NUM_TOOLS, NUM_WEAPONS, NUM_SPELL_SCROLLS,
    NUM_ROOMS,
)
from src.models.maze import Maze
from src.models.monster import generate_encounter_monsters
from src.generate.validator import ValidationReport
from src.registry import registry

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

PHASES = [
    "Maze layout",
    "Event tiles",
    "Item placement",
    "Zone mapping",
    "NPC pool",
    "Player start",
    "Story generation",
    "Events",
    "Quests",
    "Dialogue trees",
    "Player classes",
    "Portraits",
    "NPC positions",
    "Write files",
]

NPC_TYPES = ["StaticNPC", "RandomNPC", "AggressiveNPC"]
MERCHANT_CHANCE = 0.15  # Chance per zone to spawn a merchant instead of a regular NPC
QUEST_TYPES = ["fetch", "escort", "delivery", "dialogue", "combat"]
STORY_QUEST_TYPES = ["fetch", "combat", "dialogue", "delivery"]
QUEST_DENSITY_MULTIPLIER = 3  # generate 3x pool, then select

DATA_DIR = "data"
MAZE_PATH = os.path.join(DATA_DIR, "maze", "maze.json")
NPC_PATH = os.path.join(DATA_DIR, "npcs", "npcs.json")
EVENT_PATH = os.path.join(DATA_DIR, "events", "events.json")
QUEST_PATH = os.path.join(DATA_DIR, "quests", "quests.json")
STORY_PATH = os.path.join(DATA_DIR, "story", "story.json")
CLASS_PATH = os.path.join(DATA_DIR, "classes", "classes.json")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")

_FALLBACK_STORY_SEED = "A dark cult is gathering power in the shadows, corrupting the land."

MAX_RETRIES = 3


def _retry_with_feedback(generate_fn, validate_fn, fallback, label: str = "content",
                          max_retries: int = MAX_RETRIES):
    """Generate content with retry-on-validation-failure.

    1. Call *generate_fn()* to produce content.
    2. Call *validate_fn(content)* → (passed: bool, reasons: list[str]).
    3. On failure, retry up to *max_retries* times, passing failure reasons back
       to the generator via *generate_fn(feedback=reasons)*.
    4. On exhaustion, return *fallback*.
    """
    feedback: list[str] | None = None
    for attempt in range(1, max_retries + 1):
        try:
            content = generate_fn(feedback=feedback) if feedback else generate_fn()
        except Exception as e:
            logger.warning("[%s] attempt %d generation error: %s", label, attempt, e)
            feedback = [str(e)]
            continue

        passed, reasons = validate_fn(content)
        if passed:
            logger.info("[%s] passed validation on attempt %d.", label, attempt)
            return content

        logger.warning("[%s] attempt %d failed validation: %s", label, attempt, reasons)
        feedback = reasons

    logger.warning("[%s] exhausted %d retries, using fallback.", label, max_retries)
    return fallback


def build_manifest(
    *,
    seed: int,
    story_seed: str,
    game_mode: str,
    num_rooms: int,
    environments: list[str],
    generated_at: str,
    validation: dict,
    active_npc_count: int,
    item_count: int,
    quest_count: int,
    event_list: list[dict],
    npc_pool: list[dict],
    player_portrait_path: str | None,
    env_portrait_path: str | None,
    environment: str,
    env_name: str,
    maze_width: int,
    maze_height: int,
    class_count: int,
    portraits_generated: bool,
    story_title: str,
    faction_name: str,
) -> dict:
    """Build the manifest dict written to data/manifest.json.

    All counting logic (images, monsters) lives here so it's testable
    without running the full pipeline.
    """
    image_count = sum(1 for p in [player_portrait_path, env_portrait_path] if p)
    image_count += sum(1 for n in npc_pool if n.get("portrait"))

    monster_count = sum(
        len(e.get("monsters", []))
        for e in event_list if e.get("event_type") == "combat"
    )

    return {
        "seed": seed,
        "story_seed": story_seed,
        "game_mode": game_mode,
        "num_rooms": num_rooms,
        "environments": environments,
        "generated_at": generated_at,
        "validation": validation,
        "content_index": {
            "rooms": num_rooms,
            "npcs": active_npc_count,
            "items": item_count,
            "quests": quest_count,
            "encounters": len(event_list),
            "monsters": monster_count,
            "images": image_count,
            "music_tracks": 0,
        },
        # Extended fields (non-PDR, kept for registry/debug use)
        "environment": environment,
        "environment_name": env_name,
        "maze_width": maze_width,
        "maze_height": maze_height,
        "npc_pool_size": len(npc_pool),
        "class_count": class_count,
        "portraits_generated": portraits_generated,
        "player_portrait": player_portrait_path,
        "environment_portrait": env_portrait_path,
        "story_title": story_title,
        "faction_name": faction_name,
    }


def _compute_zones(width: int, height: int, zone_size: int) -> list[tuple[int, int]]:
    """Return a list of (zone_x, zone_y) top-left corners for the given zone grid."""
    zones = []
    for zy in range(0, height, zone_size):
        for zx in range(0, width, zone_size):
            zones.append((zx, zy))
    return zones


def _llm_generate_personality(env_type: str, env_name: str) -> dict:
    """Call LLM to generate a personality dict. Returns dict or fallback."""
    try:
        from src.generate.generators.llm_primitives import generate_personality_primitive
        result = generate_personality_primitive({
            "environment": {"type": env_type, "name": env_name}
        })
        if "error" not in result:
            return result
    except Exception as e:
        logger.warning("LLM personality generation failed: %s", e)

    from src.data.world_data import NAMES, PERSONALITIES, JOBS, HOBBIES
    return {
        "name": random.choice(NAMES),
        "job": random.choice(JOBS.get(env_type, JOBS["city"])),
        "personality": random.choice(PERSONALITIES),
        "hobby": random.choice(HOBBIES.get(env_type, HOBBIES["city"])),
        "environment": env_type,
        "environment_name": env_name,
    }


def _llm_generate_greeting(personality: dict) -> str:
    """Call LLM to generate an opening greeting. Returns string or fallback."""
    try:
        from src.generate.generators.llm_primitives import generate_npc_convo
        return generate_npc_convo(personality)
    except Exception as e:
        logger.warning("LLM greeting generation failed: %s", e)
    return f"Greetings, traveler. I am {personality.get('name', 'someone')}."


def _llm_generate_image_desc(personality: dict) -> str:
    """Call LLM to get a portrait prompt for an NPC."""
    try:
        from src.generate.generators.llm_primitives import generate_image_description
        return generate_image_description(personality)
    except Exception as e:
        logger.warning("LLM image description failed: %s", e)
    return "a fantasy character portrait, pixel art"


def _llm_generate_env_name(env_type: str) -> str:
    """Call LLM to generate a thematic environment name."""
    try:
        from src.generate.generators.llm_primitives import generate_environment_name
        name = generate_environment_name(env_type)
        if name and len(name) < 50:
            return name
    except Exception as e:
        logger.warning("LLM env name generation failed: %s", e)
    fallback_names = {
        "forest": "Whisperwood", "cave": "Gloomhollow", "dungeon": "Dreadkeep",
        "castle": "Whitespire", "house": "Hearthstead", "city": "Silverport",
    }
    return fallback_names.get(env_type, "Unknown Land")


def _event_fallback(event_type: str) -> dict:
    """Static fallback event when LLM generation fails."""
    if event_type == "combat":
        return {
            "name": random.choice(["Goblin", "Giant Rat", "Skeleton", "Slime", "Bandit"]),
            "description": "A hostile creature attacks!",
            "difficulty": random.randint(2, 4),
            "damage_type": random.choice(["health", "hunger", "thirst"]),
            "damage_range": [5, 15],
        }
    return {
        "name": random.choice(["Locked Chest", "Crumbling Bridge", "Strange Rune", "Trapped Door"]),
        "description": "A mysterious obstacle blocks your path...",
        "difficulty": random.randint(1, 3),
        "choices": [
            {"text": "Try to force through", "stat_check": "health", "dc": 12, "auto_success": False},
            {"text": "Walk away", "auto_success": True},
        ],
    }


def _llm_generate_event(env_type: str, env_name: str, event_type: str) -> dict:
    """Call LLM to generate an event with retry-on-failure. Returns dict or fallback."""
    from src.generate.checker import EventChecker
    checker = EventChecker()

    def _generate(feedback: list[str] | None = None):
        from src.generate.generators.llm_primitives import generate_event_primitive
        ctx = {"environment": {"type": env_type, "name": env_name}}
        if feedback:
            ctx["retry_feedback"] = "; ".join(feedback)
        result = generate_event_primitive(ctx, event_type)
        if "error" in result:
            raise ValueError(result["error"])
        result.setdefault("type", event_type)
        return result

    def _validate(content):
        cr = checker.check(content)
        return cr.passed, cr.issues

    return _retry_with_feedback(
        _generate, _validate, _event_fallback(event_type),
        label=f"event:{event_type}",
    )


def _llm_generate_event_image(event_data: dict) -> str:
    """Call LLM to get a portrait prompt for an event."""
    try:
        from src.generate.generators.llm_primitives import generate_event_image_description
        return generate_event_image_description(event_data)
    except Exception as e:
        logger.warning("LLM event image description failed: %s", e)
    return "a fantasy encounter scene, pixel art"


def _llm_generate_dialogue_tree(npc_personality: dict, quest_context: dict | None = None) -> dict:
    """Call LLM to generate a dialogue tree for offline-static mode."""
    try:
        from src.generate.generators.llm_primitives import generate_dialogue_tree
        result = generate_dialogue_tree(npc_personality, quest_context)
        if "error" not in result and "nodes" in result:
            return result
    except Exception as e:
        logger.warning("LLM dialogue tree generation failed: %s", e)

    name = npc_personality.get("name", "NPC")
    return {
        "nodes": {
            "start": {
                "prompt": f"{name} looks at you expectantly.",
                "choices": [
                    {"text": "Tell me about yourself.", "next_node_id": "about"},
                    {"text": "Goodbye.", "next_node_id": "end"},
                ],
            },
            "about": {
                "prompt": f"I'm {name}, a {npc_personality.get('job', 'nobody')} around here.",
                "choices": [
                    {"text": "Interesting. Goodbye.", "next_node_id": "end"},
                ],
            },
            "end": {
                "prompt": "Farewell, traveler.",
                "choices": [],
            },
        }
    }


def _llm_generate_story(story_seed: str, room_count: int,
                        environments: list[str]) -> dict | None:
    """Call LLM to generate the overarching story. Returns dict or None."""
    try:
        from src.generate.generators.llm_primitives import generate_story_primitive
        result = generate_story_primitive(story_seed, room_count, environments)
        if "error" not in result:
            return result
    except Exception as e:
        logger.warning("LLM story generation failed: %s", e)
    return None


def _llm_generate_story_quest(env_type: str, env_name: str, story_beat: str,
                               faction_name: str, npcs: list, items: list,
                               events: list, quest_type: str) -> dict | None:
    """Call LLM to generate a story-connected quest."""
    try:
        from src.generate.generators.llm_primitives import generate_story_quest_primitive
        result = generate_story_quest_primitive(
            {"environment": {"type": env_type, "name": env_name}},
            story_beat, faction_name, npcs, items, events, quest_type,
        )
        if "error" not in result:
            return result
    except Exception as e:
        logger.warning("LLM story quest generation failed: %s", e)
    return None


def _llm_generate_quest(env_type: str, env_name: str, npcs: list, items: list,
                        events: list, quest_type: str) -> dict | None:
    """Call LLM to generate quest title/description with retry. Returns dict or None."""

    def _generate(feedback: list[str] | None = None):
        from src.generate.generators.llm_primitives import generate_quest_primitive
        ctx = {"environment": {"type": env_type, "name": env_name}}
        if feedback:
            ctx["retry_feedback"] = "; ".join(feedback)
        result = generate_quest_primitive(ctx, npcs, items, events, quest_type)
        if "error" in result:
            raise ValueError(result["error"])
        return result

    def _validate(content):
        if not content or not isinstance(content, dict):
            return False, ["Empty or invalid quest data"]
        if not content.get("title"):
            return False, ["Missing quest title"]
        return True, []

    return _retry_with_feedback(_generate, _validate, None, label=f"quest:{quest_type}")


def _build_identity(personality: dict) -> str:
    """Build the identity string the same way NPC.build_identity does."""
    from src.prompts import get_prompt_set
    prompts = get_prompt_set()
    return prompts.conversation_identity(
        name=personality.get("name", "NPC"),
        job=personality.get("job", "peasant"),
        personality=personality.get("personality", "dim"),
        hobby=personality.get("hobby", "strolling"),
        env=personality.get("environment", "city"),
        env_name=personality.get("environment_name", "Unknown"),
    )


def _validate_quest(quest: dict, npc_pool: list, item_placements: list,
                     event_list: list, existing_quests: list) -> bool:
    """Check that a quest is completable given the world state."""
    qtype = quest.get("type", "")
    npc_ids = {n["id"] for n in npc_pool if n.get("selected")}
    item_ids_on_map = {p["item_id"] for p in item_placements}
    event_ids = {e["id"] for e in event_list}
    existing_quest_ids = {q["id"] for q in existing_quests}

    if quest.get("giver_npc_id") not in npc_ids:
        return False

    if qtype == "fetch":
        for ti in quest.get("target_items", []):
            if ti.get("item_id") not in item_ids_on_map:
                return False
    elif qtype == "escort":
        if quest.get("escort_npc_id") not in npc_ids:
            return False
    elif qtype == "delivery":
        if quest.get("delivery_item_id") not in item_ids_on_map:
            return False
        if quest.get("target_npc_id") not in npc_ids:
            return False
    elif qtype == "combat":
        if quest.get("target_event_id") not in event_ids:
            return False
    elif qtype == "dialogue_gated":
        prereq = quest.get("prerequisite_quest_id")
        if prereq and prereq not in existing_quest_ids:
            return False

    prereq = quest.get("prerequisite_quest_id")
    if prereq:
        depth = 1
        check = prereq
        while check and depth <= 2:
            parent = next((q for q in existing_quests if q["id"] == check), None)
            if parent is None:
                return False
            check = parent.get("prerequisite_quest_id")
            depth += 1
        if depth > 2:
            return False

    return True


ITEM_ITEMS_PATH = os.path.join(DATA_DIR, "items", "items.json")

# Weapon price ranges by dice tier
WEAPON_PRICE_BY_DICE = {
    "1d4": (8, 15), "1d6": (16, 25), "1d8": (28, 45),
    "1d10": (40, 55), "2d4": (25, 35), "1d12": (55, 70),
}


def _llm_generate_items(env_type: str, env_name: str, room_level: int = 1) -> dict | None:
    """Call LLM to generate environment-themed items. Returns items dict keyed by ID, or None."""
    try:
        from src.generate.generators.llm_primitives import generate_item_primitive
        result = generate_item_primitive(
            {"environment": {"type": env_type, "name": env_name}},
            room_level,
        )
        if "error" in result:
            logger.warning("LLM item generation returned error: %s", result["error"])
            return None
        return _build_items_json(result, room_level)
    except Exception as e:
        logger.warning("LLM item generation failed: %s", e)
        return None


def _build_items_json(llm_result: dict, room_level: int) -> dict:
    """Convert LLM-generated item pools into the items.json format keyed by ID."""
    items = {}
    item_id = 200

    for raw in llm_result.get("food", [])[:4]:
        items[str(item_id)] = {
            "category": "food",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "room_level": room_level,
            "item_stats": {
                "nutrition_value": raw.get("nutrition_value", 15),
                "hydration_value": 0,
                "health_value": raw.get("health_value", 0),
                "uses": 1,
                "price": random.randint(5, 15),
            },
        }
        item_id += 1

    item_id = 300
    for raw in llm_result.get("drink", [])[:4]:
        items[str(item_id)] = {
            "category": "drink",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "room_level": room_level,
            "item_stats": {
                "nutrition_value": 0,
                "hydration_value": raw.get("hydration_value", 15),
                "health_value": raw.get("health_value", 0),
                "uses": 1,
                "price": random.randint(5, 15),
            },
        }
        item_id += 1

    item_id = 400
    for raw in llm_result.get("tools", [])[:3]:
        items[str(item_id)] = {
            "category": "tool",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "room_level": room_level,
            "item_stats": {
                "attribute": raw.get("attribute", "bludgeon"),
                "nutrition_value": -5,
                "hydration_value": -5,
                "health_value": 0,
                "uses": 3,
                "price": random.randint(10, 25),
            },
        }
        item_id += 1

    item_id = 500
    for raw in llm_result.get("weapons", [])[:3]:
        dice = raw.get("attack_dice", "1d4")
        lo, hi = WEAPON_PRICE_BY_DICE.get(dice, (10, 30))
        items[str(item_id)] = {
            "category": "weapon",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "weapon_type": raw.get("weapon_type", "simple"),
            "room_level": room_level,
            "item_stats": {
                "attack_dice": dice,
                "stat_modifier": raw.get("stat_modifier", "STR"),
                "price": random.randint(lo, hi),
            },
        }
        item_id += 1

    item_id = 600
    for raw in llm_result.get("spell_scrolls", [])[:2]:
        items[str(item_id)] = {
            "category": "spell_scroll",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "spell_effect": raw.get("spell_effect", "generic"),
            "room_level": room_level,
            "item_stats": {
                "health_value": 25 if raw.get("spell_effect") == "heal" else 0,
                "nutrition_value": 30 if raw.get("spell_effect") == "sustain" else 0,
                "hydration_value": 30 if raw.get("spell_effect") == "sustain" else 0,
                "price": random.randint(20, 40),
            },
        }
        item_id += 1

    return items


def _validate_puzzle_tools(
    event_list: list[dict], reg, report: ValidationReport | None = None,
) -> None:
    """Ensure puzzle events only reference tool attributes that exist in the registry."""
    from src.models.items import Tool
    available_attrs = set()
    for item in reg.item_registry.values():
        if isinstance(item, Tool) and item.item_stats.attribute:
            available_attrs.add(item.item_stats.attribute)

    for event in event_list:
        if event.get("type") != "puzzle":
            continue
        for choice in event.get("choices", []):
            attr = choice.get("tool_attribute")
            if attr and attr not in available_attrs:
                if report:
                    report.add_warning(
                        f"Puzzle choice referenced invalid tool_attribute '{attr}'; replaced",
                        entity_id=event.get("id", ""),
                        phase="events",
                    )
                if available_attrs:
                    choice["tool_attribute"] = random.choice(list(available_attrs))
                else:
                    choice["tool_attribute"] = None


def _generate_shop_inventory(reg) -> list[dict]:
    """Generate a random shop inventory from available items in the registry."""
    shop = []
    all_ids = reg.item_ids()
    num_items = random.randint(4, 8)
    selected_ids = random.sample(all_ids, min(num_items, len(all_ids)))
    for item_id in selected_ids:
        item = reg.get_item(item_id)
        if item:
            price = item.item_stats.price if item.item_stats.price > 0 else random.randint(5, 30)
            shop.append({
                "item_id": item_id,
                "price": price,
                "stock": random.randint(1, 5),
            })
    return shop


def _generate_loot_table(item_ids: list[int], difficulty: int) -> list[dict]:
    """Generate a loot table for a combat event based on difficulty."""
    num_entries = min(random.randint(1, 3), len(item_ids))
    loot = []
    for item_id in random.sample(item_ids, num_entries):
        drop_chance = round(random.uniform(0.1, 0.3 + difficulty * 0.1), 2)
        loot.append({"item_id": item_id, "drop_chance": min(drop_chance, 1.0)})
    return loot


def _generate_room(room_idx: int, num_rooms: int, story, room_dir: str,
                    all_class_options: list | None = None):
    """Generate all content for a single room. Returns room metadata dict."""
    room_level = room_idx + 1
    room_id = f"room_{room_idx}"
    id_offset = room_idx * 1000  # Offset IDs to avoid collisions across rooms

    # --- Maze ---
    maze = Maze()
    maze.generate()
    env_name = _llm_generate_env_name(maze.environment)
    maze.environment_name = env_name
    logger.info("Room %d: %s (%s)", room_idx, maze.environment, env_name)

    # --- Event tiles ---
    maze.place_event_tiles()
    event_positions = []
    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if cell == maze.event_tile_id:
                event_positions.append((x, y))

    # --- Items ---
    item_id_base = 200 + id_offset
    generated_items = _llm_generate_items(maze.environment, env_name, room_level=room_level)
    if generated_items:
        # Re-key items with room-specific offset
        rekeyed = {}
        for i, (_, item_data) in enumerate(sorted(generated_items.items())):
            rekeyed[str(item_id_base + i)] = item_data
        generated_items = rekeyed

    items_path = os.path.join(room_dir, "items.json")
    os.makedirs(room_dir, exist_ok=True)
    if generated_items:
        with open(items_path, "w") as f:
            json.dump(generated_items, f, indent=2)
        # Reload items so registry has this room's items for placement
        registry._loaded = False
        registry._load_items_from(items_path)
        registry._loaded = True
        logger.info("Room %d: LLM-generated %d items.", room_idx, len(generated_items))
    else:
        logger.info("Room %d: Using static items.", room_idx)

    maze.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS, NUM_WEAPONS, NUM_SPELL_SCROLLS)
    item_placements = []
    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if registry.is_item(cell):
                item_placements.append({"x": x, "y": y, "item_id": cell})

    # --- Zones ---
    npc_zones = _compute_zones(MAZE_WIDTH, MAZE_HEIGHT, 10)
    quest_zones = _compute_zones(MAZE_WIDTH, MAZE_HEIGHT, 20)

    # --- NPC pool ---
    npc_pool = []
    npc_id_counter = 100 + id_offset
    open_spaces = maze.find_open_spaces()

    npc_bar = tqdm(total=len(npc_zones) * 3,
                   desc=f"  Room {room_idx} NPCs", unit="npc", leave=True)
    for zone_x, zone_y in npc_zones:
        zone_npcs = []
        is_merchant_zone = random.random() < MERCHANT_CHANCE
        for i in range(3):
            personality = _llm_generate_personality(maze.environment, env_name)
            greeting = _llm_generate_greeting(personality)
            portrait_prompt = _llm_generate_image_desc(personality)
            identity = _build_identity(personality)

            npc_type = "MerchantNPC" if (is_merchant_zone and i == 0) else random.choice(NPC_TYPES)

            npc_data = {
                "id": npc_id_counter,
                "type": npc_type,
                "name": personality.get("name", f"NPC_{npc_id_counter}"),
                "job": "merchant" if npc_type == "MerchantNPC" else personality.get("job", "peasant"),
                "personality": personality.get("personality", "stoic"),
                "hobby": personality.get("hobby", "walking"),
                "environment": maze.environment,
                "environment_name": env_name,
                "identity": identity,
                "description": personality.get("description", ""),
                "opening_greeting": greeting,
                "portrait_prompt": portrait_prompt,
                "profile_image": None,
                "dialogue_tree": None,
                "quest_id": None,
                "zone": [zone_x, zone_y],
                "selected": False,
            }
            if npc_type == "MerchantNPC":
                shop_items = _generate_shop_inventory(registry)
                npc_data["shop_inventory"] = shop_items

            zone_npcs.append(npc_data)
            npc_id_counter += 1
            npc_bar.update(1)

        if is_merchant_zone:
            selected = zone_npcs[0]
        else:
            selected = random.choice(zone_npcs)
        selected["selected"] = True

        zone_open = [
            (x, y) for (x, y) in open_spaces
            if zone_x <= x < zone_x + 10 and zone_y <= y < zone_y + 10
        ]
        if zone_open:
            sx, sy = random.choice(zone_open)
            selected["x"] = sx
            selected["y"] = sy
            if (sx, sy) in open_spaces:
                open_spaces.remove((sx, sy))
        else:
            selected["selected"] = False

        npc_pool.extend(zone_npcs)

    npc_bar.close()
    active_npcs = [n for n in npc_pool if n.get("selected")]
    logger.info("Room %d: NPCs %d pool / %d active", room_idx, len(npc_pool), len(active_npcs))

    # --- Player start ---
    if open_spaces:
        player_start = random.choice(open_spaces)
        open_spaces.remove(player_start)
    else:
        player_start = (1, 1)

    # --- Events ---
    event_list = []
    event_id_prefix = f"r{room_idx}_"

    available_tool_attrs = set()
    for p in item_placements:
        item_obj = registry.get_item(p["item_id"])
        if item_obj:
            stats = getattr(item_obj, 'item_stats', None)
            if stats and getattr(stats, 'attribute', None):
                available_tool_attrs.add(stats.attribute)

    all_item_ids = registry.item_ids()
    event_bar = tqdm(event_positions, desc=f"  Room {room_idx} Events",
                     unit="evt", leave=True)
    for idx, (ex, ey) in enumerate(event_bar):
        roll = random.random()
        if roll < 0.50:
            event_type = "combat"
        elif roll < 0.75:
            event_type = "puzzle"
        else:
            event_type = "event"

        event_data = _llm_generate_event(maze.environment, env_name, event_type)
        event_data["id"] = f"{event_id_prefix}evt_{idx:03d}"
        event_data["type"] = event_type
        if "name" not in event_data:
            event_data["name"] = f"Event {idx}"
        if "description" not in event_data:
            event_data["description"] = "Something happens!"

        if event_type == "combat":
            monsters = generate_encounter_monsters(maze.environment, room_level)
            event_data["monsters"] = [m.to_dict() for m in monsters]
            event_data["room_level"] = room_level
            if event_data["name"].startswith("Event ") and monsters:
                event_data["name"] = f"{monsters[0].name} Encounter"
            if not event_data.get("description") or event_data["description"] == "Something happens!":
                names = ", ".join(m.name for m in monsters)
                event_data["description"] = f"You are ambushed by {names}!"
            if all_item_ids:
                difficulty = event_data.get("difficulty", 3)
                event_data["loot_table"] = _generate_loot_table(all_item_ids, difficulty)
                event_data["money_drop"] = [difficulty * 2, difficulty * 8]

        elif event_type == "event":
            choices = event_data.get("choices", [])
            if not any(c.get("auto_success") for c in choices):
                choices.append({"text": "Walk away", "auto_success": True})
            event_data["choices"] = choices
            event_data["failure_damage_type"] = random.choice(["health", "hunger", "thirst"])
            event_data["failure_damage_range"] = [3 + room_level, 8 + room_level * 2]

        elif event_type == "puzzle":
            choices = event_data.get("choices", [])
            solvable = any(
                c.get("tool_attribute") in available_tool_attrs
                for c in choices if not c.get("auto_success")
            )
            if not solvable and available_tool_attrs and choices:
                attr = random.choice(list(available_tool_attrs))
                choices.insert(0, {
                    "text": f"Use a {attr} tool",
                    "tool_attribute": attr,
                    "dc": 8 + room_level,
                    "auto_success": False,
                })
            if not any(c.get("auto_success") for c in choices):
                choices.append({"text": "Leave it alone", "auto_success": True})
            event_data["choices"] = choices

        event_data["portrait_prompt"] = _llm_generate_event_image(event_data)
        event_data["profile_image"] = None
        event_list.append(event_data)

    _validate_puzzle_tools(event_list, registry)

    event_position_map = []
    for idx, (ex, ey) in enumerate(event_positions):
        event_position_map.append({"x": ex, "y": ey, "event_id": event_list[idx]["id"]})

    # --- Gate encounter (for non-final rooms) ---
    gate_encounter_id = None
    if room_idx < num_rooms - 1:
        gate_id = f"{event_id_prefix}gate"
        gate_level = room_level + 1  # Stronger than normal encounters
        gate_monsters = generate_encounter_monsters(maze.environment, gate_level)
        # Make gate monsters tougher
        for m in gate_monsters:
            m.hp = int(m.hp * 1.5)
            m.max_hp = m.hp
        gate_event = {
            "id": gate_id,
            "type": "combat",
            "name": f"Gate Guardian of {env_name}",
            "description": f"A powerful guardian blocks the exit from {env_name}!",
            "difficulty": min(5, room_level + 2),
            "monsters": [m.to_dict() for m in gate_monsters],
            "room_level": gate_level,
            "is_gate": True,
            "portrait_prompt": _llm_generate_event_image({
                "name": f"Gate Guardian of {env_name}",
                "description": "A powerful boss monster guarding a door",
            }),
            "profile_image": None,
        }
        if all_item_ids:
            gate_event["loot_table"] = _generate_loot_table(all_item_ids, gate_level)
            gate_event["money_drop"] = [gate_level * 5, gate_level * 15]
        event_list.append(gate_event)
        gate_encounter_id = gate_id
        maze.gate_encounter_id = gate_id

    # --- Door placement (for non-final rooms) ---
    if room_idx < num_rooms - 1:
        maze.place_door(player_start)

    # --- Quests ---
    quest_list = []
    quest_id_counter = id_offset

    items_for_quest = [{"id": p["item_id"], "name": registry.get_item_name(p["item_id"])}
                       for p in item_placements]
    events_for_quest = [{"id": e["id"], "name": e["name"]} for e in event_list
                        if not e.get("is_gate")]
    combat_events_for_quest = [{"id": e["id"], "name": e["name"]}
                               for e in event_list
                               if e.get("type") == "combat" and not e.get("is_gate")]
    npcs_for_quest = [{"id": n["id"], "name": n["name"]} for n in active_npcs]

    faction_name = story.faction.name if story.faction else ""
    # Find story beat for this room
    room_beat = next((b for b in story.beats if b.room_id == room_id), None)
    story_beat_text = room_beat.summary if room_beat else (
        story.beats[0].summary if story.beats else "")

    def _build_quest_data_room(quest_type, llm_quest, is_story=False):
        nonlocal quest_id_counter
        quest_data = {
            "id": f"{event_id_prefix}q_{quest_id_counter:03d}",
            "type": quest_type,
            "title": llm_quest.get("title", f"Quest {quest_id_counter}") if llm_quest else f"Quest {quest_id_counter}",
            "description": llm_quest.get("description", f"A {quest_type} quest.") if llm_quest else f"A {quest_type} quest.",
            "giver_npc_id": (llm_quest.get("giver_npc_id") if llm_quest and llm_quest.get("giver_npc_id")
                             else (random.choice(npcs_for_quest)["id"] if npcs_for_quest else 100 + id_offset)),
            "room_id": room_id,
            "is_story_quest": is_story,
            "reward": {"item_id": random.choice(items_for_quest)["id"] if items_for_quest else 200 + id_offset},
            "failure_penalty": {"hp_damage": random.choice([0, 5, 10]),
                                "hunger_damage": random.choice([0, 5]),
                                "thirst_damage": random.choice([0, 5])},
            "prerequisite_quest_id": None,
            "portrait_prompt": None,
            "profile_image": None,
        }
        return quest_data

    def _populate_quest_fields_room(quest_data, quest_type, zone_x, zone_y):
        if quest_type == "fetch" and items_for_quest:
            target = random.choice(items_for_quest)
            quest_data["target_items"] = [{"item_id": target["id"], "count": 1}]
            if not quest_data.get("is_story_quest"):
                quest_data["title"] = f"Gather {target['name']}"
                quest_data["description"] = f"Find and bring back a {target['name']}."
        elif quest_type == "escort" and len(active_npcs) >= 2:
            escort_npc = random.choice([n for n in active_npcs
                                        if n["id"] != quest_data["giver_npc_id"]])
            zone_open = [
                (x, y) for (x, y) in maze.find_open_spaces()
                if not (zone_x <= x < zone_x + 20 and zone_y <= y < zone_y + 20)
            ]
            if zone_open:
                target = random.choice(zone_open)
                quest_data["escort_npc_id"] = escort_npc["id"]
                quest_data["target_zone"] = list(target)
                if not quest_data.get("is_story_quest"):
                    quest_data["title"] = f"Escort {escort_npc['name']}"
                    quest_data["description"] = f"Take {escort_npc['name']} to safety."
            else:
                return False
        elif quest_type == "delivery" and items_for_quest and len(active_npcs) >= 2:
            delivery_item = random.choice(items_for_quest)
            target_npc = random.choice([n for n in active_npcs
                                        if n["id"] != quest_data["giver_npc_id"]])
            quest_data["delivery_item_id"] = delivery_item["id"]
            quest_data["target_npc_id"] = target_npc["id"]
            if not quest_data.get("is_story_quest"):
                quest_data["title"] = f"Deliver {delivery_item['name']}"
                quest_data["description"] = f"Bring a {delivery_item['name']} to {target_npc['name']}."
        elif quest_type == "combat" and combat_events_for_quest:
            target_event = random.choice(combat_events_for_quest)
            quest_data["target_event_id"] = target_event["id"]
            if not quest_data.get("is_story_quest"):
                quest_data["title"] = f"Defeat the {target_event['name']}"
                quest_data["description"] = f"Find and defeat the {target_event['name']}."
        elif quest_type == "dialogue":
            giver = next((n for n in active_npcs
                          if n["id"] == quest_data["giver_npc_id"]), None)
            quest_data["dc"] = random.randint(10, 15)
            quest_data["dialogue_tree"] = {
                "prompt": "What business do you have with me?",
                "choices": [
                    {"text": "I need your help.", "next_node_id": "success"},
                    {"text": "Never mind.", "next_node_id": "fail"},
                ],
            }
            quest_data["can_fail"] = True
            quest_data["can_retry"] = True
            if not quest_data.get("is_story_quest"):
                quest_data["title"] = f"Convince {giver['name'] if giver else 'the NPC'}"
                quest_data["description"] = "Use your words carefully."
        else:
            return False
        return True

    quest_bar = tqdm(quest_zones, desc=f"  Room {room_idx} Quests", unit="zone", leave=True)
    for zone_x, zone_y in quest_bar:
        pool = []
        target_count = QUEST_DENSITY_MULTIPLIER
        attempts = 0
        while len(pool) < target_count and attempts < target_count * 5:
            attempts += 1
            quest_type = random.choice(QUEST_TYPES)
            llm_quest = _llm_generate_quest(
                maze.environment, env_name,
                npcs_for_quest, items_for_quest, events_for_quest, quest_type,
            )
            quest_data = _build_quest_data_room(quest_type, llm_quest, is_story=False)
            if _populate_quest_fields_room(quest_data, quest_type, zone_x, zone_y):
                if _validate_quest(quest_data, npc_pool, item_placements, event_list, quest_list + pool):
                    pool.append(quest_data)

        has_story_q = any(q.get("is_story_quest") for q in pool)
        if not has_story_q and faction_name:
            story_type = random.choice(STORY_QUEST_TYPES)
            story_llm = _llm_generate_story_quest(
                maze.environment, env_name, story_beat_text, faction_name,
                npcs_for_quest, items_for_quest, events_for_quest, story_type,
            )
            story_qdata = _build_quest_data_room(story_type, story_llm, is_story=True)
            if _populate_quest_fields_room(story_qdata, story_type, zone_x, zone_y):
                if _validate_quest(story_qdata, npc_pool, item_placements, event_list, quest_list + pool):
                    pool.append(story_qdata)

        has_combat = any(q.get("type") == "combat" for q in pool)
        if not has_combat and combat_events_for_quest:
            combat_qdata = _build_quest_data_room("combat", None, is_story=True)
            target_evt = random.choice(combat_events_for_quest)
            combat_qdata["target_event_id"] = target_evt["id"]
            combat_qdata["title"] = f"Purge the {faction_name}: {target_evt['name']}"
            combat_qdata["description"] = f"The {faction_name} has corrupted creatures. Defeat the {target_evt['name']}."
            if _validate_quest(combat_qdata, npc_pool, item_placements, event_list, quest_list + pool):
                pool.append(combat_qdata)

        if pool:
            sel = random.choice(pool)
            sel["id"] = f"{event_id_prefix}q_{quest_id_counter:03d}"
            giver_npc = next((n for n in npc_pool
                              if n["id"] == sel["giver_npc_id"]), None)
            if giver_npc:
                giver_npc["quest_id"] = sel["id"]
            quest_list.append(sel)
            quest_id_counter += 1

    if len(quest_list) >= 3:
        sub_ids = [q["id"] for q in quest_list[:3]]
        multi_quest = {
            "id": f"{event_id_prefix}q_{quest_id_counter:03d}",
            "type": "multi_step",
            "title": f"The {faction_name} Conspiracy" if faction_name else "A Grand Adventure",
            "description": f"Unravel the {faction_name}'s plot through a series of connected tasks." if faction_name else "Complete a chain of connected quests.",
            "giver_npc_id": quest_list[0]["giver_npc_id"],
            "room_id": room_id,
            "is_story_quest": True,
            "reward": {"item_id": random.choice(items_for_quest)["id"] if items_for_quest else 200 + id_offset,
                       "xp": 50, "story_info": "A crucial revelation about the faction's plans."},
            "failure_penalty": {"hp_damage": 10, "hunger_damage": 5, "thirst_damage": 5},
            "sub_quest_ids": sub_ids,
            "current_step": 0,
            "prerequisite_quest_id": None,
            "portrait_prompt": None,
            "profile_image": None,
        }
        quest_list.append(multi_quest)
        quest_id_counter += 1

    quest_bar.close()
    logger.info("Room %d: %d quests (%d story).", room_idx, len(quest_list),
                sum(1 for q in quest_list if q.get("is_story_quest")))

    # --- Dialogue trees ---
    if GAME_MODE == "offline_static":
        for npc in active_npcs:
            quest_ctx = next((q for q in quest_list if q["id"] == npc.get("quest_id")), None)
            npc["dialogue_tree"] = _llm_generate_dialogue_tree(npc, quest_ctx)

    # --- NPC positions ---
    npc_positions = {}
    for npc in active_npcs:
        npc_positions[str(npc["id"])] = [npc.get("x", 0), npc.get("y", 0)]

    # --- Write per-room files ---
    maze_path = os.path.join(room_dir, "maze.json")
    maze.save_to_json(maze_path, extra={
        "npc_positions": npc_positions,
        "player_start": list(player_start),
        "item_placements": item_placements,
        "event_positions": event_position_map,
    })

    npc_path = os.path.join(room_dir, "npcs.json")
    with open(npc_path, "w") as f:
        json.dump(npc_pool, f, indent=2)

    event_path = os.path.join(room_dir, "events.json")
    with open(event_path, "w") as f:
        json.dump(event_list, f, indent=2)

    quest_path = os.path.join(room_dir, "quests.json")
    with open(quest_path, "w") as f:
        json.dump(quest_list, f, indent=2)

    return {
        "room_id": room_id,
        "room_idx": room_idx,
        "room_level": room_level,
        "environment": maze.environment,
        "environment_name": env_name,
        "npc_pool": npc_pool,
        "active_npcs": active_npcs,
        "event_list": event_list,
        "quest_list": quest_list,
        "item_placements": item_placements,
        "gate_encounter_id": gate_encounter_id,
        "player_start": player_start,
        "maze": maze,
        "generated_items": generated_items,
    }


def generate_world():
    """Main generation pipeline. Writes all data to data/."""
    logger.info("=== MazeWorld World Generator ===")
    logger.info("Seed: %s, Mode: %s, Rooms: %d", WORLD_SEED, GAME_MODE, NUM_ROOMS)

    if WORLD_SEED != -1:
        random.seed(WORLD_SEED)

    registry.load()

    num_rooms = NUM_ROOMS
    room_results = []

    # --- Generate first room's maze briefly to get environment for story/classes ---
    # (We'll re-seed before actual generation so this peek doesn't consume randomness)
    rng_state = random.getstate()

    # --- Generate overarching story ---
    from src.data.world_data import ENVIRONMENT_TYPES
    story_seed = STORY_SEED or _FALLBACK_STORY_SEED
    environments = random.choices(ENVIRONMENT_TYPES, k=num_rooms)
    story_data = _llm_generate_story(story_seed, num_rooms, environments)

    from src.models.story import OverarchingStory, Faction, RoomStoryBeat
    if story_data:
        faction_data = story_data.get("faction", {})
        faction = Faction(
            name=faction_data.get("name", "The Shadow Cult"),
            description=faction_data.get("description", "A mysterious faction."),
            leader=faction_data.get("leader", "Unknown"),
        ) if faction_data else None
        beats = []
        for bd in story_data.get("beats", []):
            beats.append(RoomStoryBeat(
                room_id=bd.get("room_id", "room_0"),
                summary=bd.get("summary", ""),
                faction_presence=bd.get("faction_presence"),
                escalation=bd.get("escalation", 1),
            ))
        # Ensure we have a beat per room
        for ri in range(num_rooms):
            rid = f"room_{ri}"
            if not any(b.room_id == rid for b in beats):
                beats.append(RoomStoryBeat(
                    room_id=rid,
                    summary=f"The story continues in room {ri + 1}.",
                    escalation=min(5, ri + 1),
                ))
        story = OverarchingStory(
            seed=story_seed,
            title=story_data.get("title", "The Dark Convergence"),
            synopsis=story_data.get("synopsis", "A dark force threatens the land."),
            faction=faction,
            escalation_arc=story_data.get("escalation_arc", []),
            climax=story_data.get("climax", "The final confrontation awaits."),
            final_boss_name=story_data.get("final_boss_name", "The Dark Lord"),
            key_npc_names=story_data.get("key_npc_names", []),
            beats=beats,
        )
    else:
        beats = [RoomStoryBeat(
            room_id=f"room_{ri}",
            summary=f"Signs of darkness deepen in room {ri + 1}.",
            faction_presence="The cult's presence grows stronger.",
            escalation=min(5, ri + 1),
        ) for ri in range(num_rooms)]
        story = OverarchingStory(
            seed=story_seed,
            title="The Shadow's Grasp",
            synopsis="A dark cult spreads corruption through the land.",
            faction=Faction(
                name="The Shadow Cult",
                description="A secretive order seeking to plunge the world into darkness.",
                leader="The Faceless One",
            ),
            escalation_arc=["Whispers of darkness", "The cult reveals itself"],
            climax="Face the cult leader in a final showdown.",
            final_boss_name="The Faceless One",
            key_npc_names=["The Faceless One"],
            beats=beats,
        )
    logger.info("Story: %s (faction: %s, %d beats)",
                story.title, story.faction.name if story.faction else "none",
                len(story.beats))

    # --- Generate player classes (global, based on first room environment) ---
    from src.generate.class_gen import generate_classes
    first_env = environments[0] if environments else "forest"
    first_env_name = _llm_generate_env_name(first_env)
    player_classes = generate_classes(first_env, first_env_name)
    class_data_list = [pc.model_dump() for pc in player_classes]
    logger.info("Generated %d player classes.", len(player_classes))

    # Restore RNG state and generate rooms
    random.setstate(rng_state)

    # --- Generate each room ---
    for room_idx in range(num_rooms):
        room_dir = os.path.join(DATA_DIR, "rooms", f"room_{room_idx}")
        os.makedirs(room_dir, exist_ok=True)
        result = _generate_room(room_idx, num_rooms, story, room_dir)
        room_results.append(result)

    # --- Backward-compatible writes (room 0 data to legacy paths) ---
    r0 = room_results[0]
    os.makedirs(os.path.dirname(MAZE_PATH), exist_ok=True)
    r0["maze"].save_to_json(MAZE_PATH, extra={
        "npc_positions": {str(n["id"]): [n.get("x", 0), n.get("y", 0)]
                          for n in r0["active_npcs"]},
        "player_start": list(r0["player_start"]),
        "item_placements": r0["item_placements"],
        "event_positions": [{"x": ep["x"], "y": ep["y"], "event_id": ep["event_id"]}
                            for ep in r0["maze"].__dict__.get("_event_pos_map", [])],
    })
    # Load event_positions from the room's maze file for legacy compat
    r0_maze_path = os.path.join(DATA_DIR, "rooms", "room_0", "maze.json")
    if os.path.exists(r0_maze_path):
        import shutil
        # Copy room 0 files to legacy paths
        for fname, legacy in [("maze.json", MAZE_PATH), ("npcs.json", NPC_PATH),
                               ("events.json", EVENT_PATH), ("quests.json", QUEST_PATH)]:
            src = os.path.join(DATA_DIR, "rooms", "room_0", fname)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(legacy), exist_ok=True)
                shutil.copy2(src, legacy)

    # --- Combined items across all rooms ---
    all_items = {}
    for rr in room_results:
        if rr.get("generated_items"):
            all_items.update(rr["generated_items"])
    if all_items:
        os.makedirs(os.path.dirname(ITEM_ITEMS_PATH), exist_ok=True)
        with open(ITEM_ITEMS_PATH, "w") as f:
            json.dump(all_items, f, indent=2)

    # --- Write global data ---
    os.makedirs(os.path.dirname(STORY_PATH), exist_ok=True)
    with open(STORY_PATH, "w") as f:
        json.dump(story.model_dump(), f, indent=2)

    os.makedirs(os.path.dirname(CLASS_PATH), exist_ok=True)
    with open(CLASS_PATH, "w") as f:
        json.dump(class_data_list, f, indent=2)

    # --- Portraits (all rooms) ---
    portraits_generated = False
    player_portrait_path = None
    env_portrait_path = None
    try:
        from src.generate.image_client import (
            generate_npc_portraits, generate_event_illustrations,
            generate_item_portraits, generate_player_portrait,
            generate_and_save_image,
        )
        from src.generate.generators.llm_primitives import (
            generate_player_image_description, generate_item_image_description,
        )

        for rr in room_results:
            npc_db = {str(n["id"]): n for n in rr["npc_pool"] if n.get("selected")}
            generate_npc_portraits(npc_db)
            event_db = {e["id"]: e for e in rr["event_list"]}
            generate_event_illustrations(event_db)

        # Item portraits from combined registry
        registry._loaded = False
        registry._load_items()
        registry._loaded = True
        item_db = {}
        for rr in room_results:
            for p in rr["item_placements"]:
                iid = p["item_id"]
                if str(iid) not in item_db:
                    item_obj = registry.get_item(iid)
                    if item_obj:
                        item_dict = {"id": iid, "name": item_obj.name, "desc": item_obj.desc}
                        try:
                            item_dict["portrait_prompt"] = generate_item_image_description(item_dict)
                        except Exception:
                            item_dict["portrait_prompt"] = f"a fantasy game item: {item_obj.name}, pixel art"
                        item_db[str(iid)] = item_dict
        generate_item_portraits(item_db)

        try:
            player_prompt = generate_player_image_description()
        except Exception:
            player_prompt = "a young adventurer, pixel art, fantasy portrait"
        player_portrait_path = generate_player_portrait(player_prompt)

        from src.generate.image_client import generate_class_portraits
        class_portrait_db = {}
        for i, cd in enumerate(class_data_list):
            prompt = cd.get("portrait_prompt") or f"a {cd['archetype']} character, fantasy pixel art"
            class_portrait_db[str(i)] = {"portrait_prompt": prompt, "name": cd.get("name", "")}
        generate_class_portraits(class_portrait_db)
        for i, cd in enumerate(class_data_list):
            cd["portrait_path"] = class_portrait_db[str(i)].get("profile_image")

        # Per-room environment portraits
        for rr in room_results:
            env = rr["environment"]
            portrait_path = os.path.join("data/portraits", f"environment_{rr['room_idx']}.png")
            generate_and_save_image(
                f"a {env} landscape, fantasy pixel art, wide angle, atmospheric",
                portrait_path,
            )
            rr["environment_portrait"] = portrait_path

        # Game over portrait (dark/somber theme)
        gameover_portrait_path = os.path.join("data/portraits", "game_over.png")
        generate_and_save_image(
            "a fallen hero in darkness, somber memorial scene, "
            "dark fantasy pixel art, moody lighting, dramatic shadows",
            gameover_portrait_path,
        )

        # Legacy environment portrait (room 0)
        env_portrait_path = os.path.join("data/portraits", "environment.png")
        r0_env_portrait = room_results[0].get("environment_portrait")
        if r0_env_portrait and os.path.exists(r0_env_portrait):
            import shutil
            shutil.copy2(r0_env_portrait, env_portrait_path)

        portraits_generated = True
        logger.info("Portraits generated successfully.")
    except Exception as e:
        logger.warning("Portrait generation skipped: %s", e)

    # --- Re-write classes with portrait paths ---
    with open(CLASS_PATH, "w") as f:
        json.dump(class_data_list, f, indent=2)

    # --- Manifest ---
    room_manifest = []
    for rr in room_results:
        room_manifest.append({
            "room_id": rr["room_id"],
            "environment": rr["environment"],
            "environment_name": rr["environment_name"],
            "npc_count": len(rr["active_npcs"]),
            "event_count": len(rr["event_list"]),
            "quest_count": len(rr["quest_list"]),
            "gate_encounter_id": rr["gate_encounter_id"],
            "environment_portrait": rr.get("environment_portrait"),
        })

    manifest = {
        "world_seed": WORLD_SEED,
        "num_rooms": num_rooms,
        "environment": room_results[0]["environment"],
        "environment_name": room_results[0]["environment_name"],
        "maze_width": MAZE_WIDTH,
        "maze_height": MAZE_HEIGHT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "npc_pool_size": sum(len(rr["npc_pool"]) for rr in room_results),
        "active_npc_count": sum(len(rr["active_npcs"]) for rr in room_results),
        "quest_count": sum(len(rr["quest_list"]) for rr in room_results),
        "event_count": sum(len(rr["event_list"]) for rr in room_results),
        "class_count": len(class_data_list),
        "portraits_generated": portraits_generated,
        "player_portrait": player_portrait_path,
        "environment_portrait": env_portrait_path,
        "gameover_portrait": gameover_portrait_path,
        "game_mode": GAME_MODE,
        "story_title": story.title,
        "faction_name": story.faction.name if story.faction else "",
        "story_seed": story.seed,
        "rooms": room_manifest,
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info("=== Generation Complete (%d rooms) ===", num_rooms)
    for rr in room_results:
        logger.info("  Room %d: %s (%s) — %d NPCs, %d events, %d quests",
                     rr["room_idx"], rr["environment"], rr["environment_name"],
                     len(rr["active_npcs"]), len(rr["event_list"]),
                     len(rr["quest_list"]))
    logger.info("  Portraits: %s", "yes" if portraits_generated else "no")
    logger.info("  Manifest: %s", MANIFEST_PATH)
