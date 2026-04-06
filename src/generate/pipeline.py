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
)
from src.models.maze import Maze
from src.models.monster import generate_encounter_monsters
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


def _validate_puzzle_tools(event_list: list[dict], reg) -> None:
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


def generate_world():
    """Main generation pipeline. Writes all data to data/."""
    logger.info("=== MazeWorld World Generator ===")
    logger.info("Seed: %s, Mode: %s", WORLD_SEED, GAME_MODE)

    if WORLD_SEED != -1:
        random.seed(WORLD_SEED)

    registry.load()

    phase_bar = tqdm(PHASES, desc="Overall progress", unit="phase",
                     bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} phases [{elapsed}<{remaining}]")

    # --- 1. Generate maze ---
    phase_bar.set_postfix_str("Maze layout")
    maze = Maze()
    maze.generate()
    env_name = _llm_generate_env_name(maze.environment)
    maze.environment_name = env_name
    logger.info("Environment: %s (%s)", maze.environment, env_name)
    phase_bar.update(1)

    # --- 2. Place event tiles ---
    phase_bar.set_postfix_str("Event tiles")
    maze.place_event_tiles()
    event_positions = []
    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if cell == maze.event_tile_id:
                event_positions.append((x, y))
    phase_bar.update(1)

    # --- 3. Generate & place items ---
    phase_bar.set_postfix_str("Item generation")
    generated_items = _llm_generate_items(maze.environment, env_name, room_level=1)
    if generated_items:
        os.makedirs(os.path.dirname(ITEM_ITEMS_PATH), exist_ok=True)
        with open(ITEM_ITEMS_PATH, "w") as f:
            json.dump(generated_items, f, indent=2)
        registry._loaded = False
        registry._load_items()
        registry._loaded = True
        logger.info("LLM-generated %d environment-themed items.", len(generated_items))
    else:
        logger.info("Using static items from items.json (LLM generation skipped or failed).")

    phase_bar.set_postfix_str("Item placement")
    maze.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS, NUM_WEAPONS, NUM_SPELL_SCROLLS)
    item_placements = []
    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if registry.is_item(cell):
                item_placements.append({"x": x, "y": y, "item_id": cell})
    phase_bar.update(1)

    # --- 4. Compute zones ---
    phase_bar.set_postfix_str("Zone mapping")
    npc_zones = _compute_zones(MAZE_WIDTH, MAZE_HEIGHT, 10)
    quest_zones = _compute_zones(MAZE_WIDTH, MAZE_HEIGHT, 20)
    logger.info("NPC zones: %d, Quest zones: %d", len(npc_zones), len(quest_zones))
    phase_bar.update(1)

    # --- 5. Generate NPC pool ---
    phase_bar.set_postfix_str("NPC pool")
    total_npcs = len(npc_zones) * 3
    npc_pool = []
    npc_id_counter = 100
    open_spaces = maze.find_open_spaces()

    npc_bar = tqdm(total=total_npcs, desc="  NPCs (personality+greeting+portrait)",
                   unit="npc", leave=True)
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
            # Generate shop inventory for merchants
            if npc_type == "MerchantNPC":
                shop_items = _generate_shop_inventory(registry)
                npc_data["shop_inventory"] = shop_items

            zone_npcs.append(npc_data)
            npc_id_counter += 1
            npc_bar.update(1)

        # Prefer selecting the merchant if this is a merchant zone
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
    logger.info("Total NPCs: %d, Active: %d", len(npc_pool), len(active_npcs))
    phase_bar.update(1)

    # --- 6. Player start ---
    phase_bar.set_postfix_str("Player start")
    if open_spaces:
        player_start = random.choice(open_spaces)
        open_spaces.remove(player_start)
    else:
        player_start = (1, 1)
    phase_bar.update(1)

    # --- 7. Generate overarching story ---
    phase_bar.set_postfix_str("Story generation")
    story_seed = STORY_SEED or _FALLBACK_STORY_SEED
    story_data = _llm_generate_story(
        story_seed, 1, [maze.environment],
    )
    if story_data:
        from src.models.story import OverarchingStory, Faction, RoomStoryBeat
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
        from src.models.story import OverarchingStory, Faction, RoomStoryBeat
        story = OverarchingStory(
            seed=story_seed,
            title="The Shadow's Grasp",
            synopsis="A dark cult spreads corruption through the land. Only a brave adventurer can stop them.",
            faction=Faction(
                name="The Shadow Cult",
                description="A secretive order seeking to plunge the world into darkness.",
                leader="The Faceless One",
            ),
            escalation_arc=["Whispers of darkness", "The cult reveals itself"],
            climax="Face the cult leader in a final showdown.",
            final_boss_name="The Faceless One",
            key_npc_names=["The Faceless One"],
            beats=[RoomStoryBeat(
                room_id="room_0",
                summary="Signs of cult activity are everywhere.",
                faction_presence="Cult symbols etched into walls, nervous townsfolk.",
                escalation=3,
            )],
        )
    logger.info("Story: %s (faction: %s)", story.title,
                story.faction.name if story.faction else "none")
    phase_bar.update(1)

    # --- 8. Generate events (combat with monsters, puzzle, event encounters) ---
    phase_bar.set_postfix_str("Events")
    event_list = []

    # Compute room levels based on distance from player start
    def _room_level_for_pos(x, y):
        dist = abs(x - player_start[0]) + abs(y - player_start[1])
        max_dist = MAZE_WIDTH + MAZE_HEIGHT
        fraction = dist / max(1, max_dist)
        return min(4, max(1, int(fraction * 4) + 1))

    # Collect available tool attributes for puzzle solvability checks
    available_tool_attrs = set()
    for p in item_placements:
        item_obj = registry.get_item(p["item_id"])
        if item_obj:
            stats = getattr(item_obj, 'item_stats', None)
            if stats and getattr(stats, 'attribute', None):
                available_tool_attrs.add(stats.attribute)

    all_item_ids = registry.item_ids()
    event_bar = tqdm(event_positions, desc="  Events (data+image+monsters)",
                     unit="evt", leave=True)
    for idx, (ex, ey) in enumerate(event_bar):
        # Weight encounter types: 50% combat, 25% puzzle, 25% event
        roll = random.random()
        if roll < 0.50:
            event_type = "combat"
        elif roll < 0.75:
            event_type = "puzzle"
        else:
            event_type = "event"

        event_data = _llm_generate_event(maze.environment, env_name, event_type)
        event_data["id"] = f"evt_{idx:03d}"
        event_data["type"] = event_type
        if "name" not in event_data:
            event_data["name"] = f"Event {idx}"
        if "description" not in event_data:
            event_data["description"] = "Something happens!"

        room_level = _room_level_for_pos(ex, ey)

        if event_type == "combat":
            monsters = generate_encounter_monsters(maze.environment, room_level)
            event_data["monsters"] = [m.to_dict() for m in monsters]
            event_data["room_level"] = room_level
            if event_data["name"].startswith("Event ") and monsters:
                event_data["name"] = f"{monsters[0].name} Encounter"
            if not event_data.get("description") or event_data["description"] == "Something happens!":
                names = ", ".join(m.name for m in monsters)
                event_data["description"] = f"You are ambushed by {names}!"
            # Loot tables and money drops
            if all_item_ids:
                difficulty = event_data.get("difficulty", 3)
                event_data["loot_table"] = _generate_loot_table(all_item_ids, difficulty)
                event_data["money_drop"] = [difficulty * 2, difficulty * 8]

        elif event_type == "event":
            choices = event_data.get("choices", [])
            has_walk = any(c.get("auto_success") for c in choices)
            if not has_walk:
                choices.append({"text": "Walk away", "auto_success": True})
            event_data["choices"] = choices
            event_data["failure_damage_type"] = random.choice(["health", "hunger", "thirst"])
            event_data["failure_damage_range"] = [3 + room_level, 8 + room_level * 2]

        elif event_type == "puzzle":
            choices = event_data.get("choices", [])
            solvable = False
            for c in choices:
                if c.get("auto_success"):
                    continue
                if c.get("tool_attribute") in available_tool_attrs:
                    solvable = True
                    break
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

    # Validate puzzle events reference tools that actually exist
    _validate_puzzle_tools(event_list, registry)

    event_position_map = []
    for idx, (ex, ey) in enumerate(event_positions):
        event_position_map.append({"x": ex, "y": ey, "event_id": event_list[idx]["id"]})
    phase_bar.update(1)

    # --- 9. Generate quests (3x density pool with minimums) ---
    phase_bar.set_postfix_str("Quests")
    quest_list = []
    quest_id_counter = 0

    items_for_quest = [{"id": p["item_id"], "name": registry.get_item_name(p["item_id"])}
                       for p in item_placements]
    events_for_quest = [{"id": e["id"], "name": e["name"]} for e in event_list]
    combat_events_for_quest = [{"id": e["id"], "name": e["name"]}
                               for e in event_list if e.get("type") == "combat"]
    npcs_for_quest = [{"id": n["id"], "name": n["name"]} for n in active_npcs]

    # Story context
    faction_name = story.faction.name if story.faction else ""
    story_beat_text = story.beats[0].summary if story.beats else ""

    def _build_quest_data(quest_type, llm_quest, is_story=False):
        nonlocal quest_id_counter
        quest_data = {
            "id": f"q_{quest_id_counter:03d}",
            "type": quest_type,
            "title": llm_quest.get("title", f"Quest {quest_id_counter}") if llm_quest else f"Quest {quest_id_counter}",
            "description": llm_quest.get("description", f"A {quest_type} quest.") if llm_quest else f"A {quest_type} quest.",
            "giver_npc_id": (llm_quest.get("giver_npc_id") if llm_quest and llm_quest.get("giver_npc_id")
                             else (random.choice(npcs_for_quest)["id"] if npcs_for_quest else 100)),
            "room_id": "room_0",
            "is_story_quest": is_story,
            "reward": {"item_id": random.choice(items_for_quest)["id"] if items_for_quest else 200},
            "failure_penalty": {"hp_damage": random.choice([0, 5, 10]),
                                "hunger_damage": random.choice([0, 5]),
                                "thirst_damage": random.choice([0, 5])},
            "prerequisite_quest_id": None,
            "portrait_prompt": None,
            "profile_image": None,
        }
        return quest_data

    def _populate_quest_fields(quest_data, quest_type, zone_x, zone_y):
        """Fill in type-specific fields. Returns False if quest should be skipped."""
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

    quest_bar = tqdm(quest_zones, desc="  Quests (3x pool + minimums)", unit="zone", leave=True)
    for zone_x, zone_y in quest_bar:
        # --- Generate 3x density pool ---
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
            quest_data = _build_quest_data(quest_type, llm_quest, is_story=False)
            if _populate_quest_fields(quest_data, quest_type, zone_x, zone_y):
                if _validate_quest(quest_data, npc_pool, item_placements, event_list, quest_list + pool):
                    pool.append(quest_data)

        # --- Ensure minimums: 1 story quest ---
        has_story = any(q.get("is_story_quest") for q in pool)
        if not has_story and faction_name:
            story_type = random.choice(STORY_QUEST_TYPES)
            story_llm = _llm_generate_story_quest(
                maze.environment, env_name, story_beat_text, faction_name,
                npcs_for_quest, items_for_quest, events_for_quest, story_type,
            )
            story_qdata = _build_quest_data(story_type, story_llm, is_story=True)
            if _populate_quest_fields(story_qdata, story_type, zone_x, zone_y):
                if _validate_quest(story_qdata, npc_pool, item_placements, event_list, quest_list + pool):
                    pool.append(story_qdata)

        # --- Ensure minimum: 1 faction combat quest if combat events exist ---
        has_combat = any(q.get("type") == "combat" for q in pool)
        if not has_combat and combat_events_for_quest:
            combat_qdata = _build_quest_data("combat", None, is_story=True)
            target_evt = random.choice(combat_events_for_quest)
            combat_qdata["target_event_id"] = target_evt["id"]
            combat_qdata["title"] = f"Purge the {faction_name}: {target_evt['name']}"
            combat_qdata["description"] = f"The {faction_name} has corrupted creatures. Defeat the {target_evt['name']}."
            if _validate_quest(combat_qdata, npc_pool, item_placements, event_list, quest_list + pool):
                pool.append(combat_qdata)

        # --- Select from pool: pick 1 per zone (random from pool) ---
        if pool:
            selected = random.choice(pool)
            selected["id"] = f"q_{quest_id_counter:03d}"
            giver_npc = next((n for n in npc_pool
                              if n["id"] == selected["giver_npc_id"]), None)
            if giver_npc:
                giver_npc["quest_id"] = selected["id"]
            quest_list.append(selected)
            quest_id_counter += 1

    # --- Generate multi-step quest chains (1 per world, linking 2-3 sub-quests) ---
    # TODO: Multi-step quests should be generated as a cohesive chain during
    # the generation phase — not assembled by picking the first N quests.
    # The LLM should generate the multi-step quest as a special type with
    # sub-quests that form a logical narrative arc (e.g., dialogue -> fetch -> combat).
    # This requires a dedicated story_quest_generation call that produces the
    # parent + sub-quests together, ensuring type diversity and narrative coherence.
    # Current approach is a placeholder that links arbitrary quests.
    if len(quest_list) >= 3:
        sub_ids = [q["id"] for q in quest_list[:3]]
        multi_quest = {
            "id": f"q_{quest_id_counter:03d}",
            "type": "multi_step",
            "title": f"The {faction_name} Conspiracy" if faction_name else "A Grand Adventure",
            "description": f"Unravel the {faction_name}'s plot through a series of connected tasks." if faction_name else "Complete a chain of connected quests.",
            "giver_npc_id": quest_list[0]["giver_npc_id"],
            "room_id": "room_0",
            "is_story_quest": True,
            "reward": {"item_id": random.choice(items_for_quest)["id"] if items_for_quest else 200,
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
    logger.info("Generated %d quests (%d story quests).",
                len(quest_list),
                sum(1 for q in quest_list if q.get("is_story_quest")))
    phase_bar.update(1)

    # --- 10. Offline static dialogue trees ---
    phase_bar.set_postfix_str("Dialogue trees")
    if GAME_MODE == "offline_static":
        dialogue_bar = tqdm(active_npcs, desc="  Dialogue trees", unit="npc", leave=True)
        for npc in dialogue_bar:
            dialogue_bar.set_postfix_str(npc.get("name", ""))
            quest_ctx = next((q for q in quest_list if q["id"] == npc.get("quest_id")), None)
            npc["dialogue_tree"] = _llm_generate_dialogue_tree(npc, quest_ctx)
        dialogue_bar.close()
    phase_bar.update(1)

    # --- 11. Player classes ---
    phase_bar.set_postfix_str("Player classes")
    from src.generate.class_gen import generate_classes
    player_classes = generate_classes(maze.environment, env_name)
    class_data_list = []
    for pc in player_classes:
        cd = pc.model_dump()
        class_data_list.append(cd)
    logger.info("Generated %d player classes.", len(player_classes))
    phase_bar.update(1)

    # --- 12. Portrait generation (try, skip on failure) ---
    phase_bar.set_postfix_str("Portraits")
    portrait_steps = ["NPC portraits", "Event illustrations",
                      "Item descriptions", "Item portraits", "Player portrait",
                      "Class portraits"]
    try:
        from src.generate.image_client import (
            generate_npc_portraits, generate_event_illustrations,
            generate_item_portraits, generate_player_portrait,
            generate_and_save_image,
        )
        from src.generate.generators.llm_primitives import (
            generate_player_image_description, generate_item_image_description,
        )

        portrait_bar = tqdm(total=len(portrait_steps), desc="  Portraits",
                            unit="step", leave=True)

        portrait_bar.set_postfix_str(f"NPC portraits ({len(active_npcs)})")
        npc_db = {str(n["id"]): n for n in npc_pool if n.get("selected")}
        generate_npc_portraits(npc_db)
        portrait_bar.update(1)

        portrait_bar.set_postfix_str(f"Event illustrations ({len(event_list)})")
        event_db = {e["id"]: e for e in event_list}
        generate_event_illustrations(event_db)
        portrait_bar.update(1)

        item_db = {}
        unique_items = set()
        for placement in item_placements:
            unique_items.add(placement["item_id"])
        portrait_bar.set_postfix_str(f"Item descriptions ({len(unique_items)})")
        for placement in item_placements:
            iid = placement["item_id"]
            if str(iid) not in item_db:
                item_obj = registry.get_item(iid)
                if item_obj:
                    item_dict = {"id": iid, "name": item_obj.name, "desc": item_obj.desc}
                    try:
                        item_dict["portrait_prompt"] = generate_item_image_description(item_dict)
                    except Exception:
                        item_dict["portrait_prompt"] = f"a fantasy game item: {item_obj.name}, pixel art"
                    item_db[str(iid)] = item_dict
        portrait_bar.update(1)

        portrait_bar.set_postfix_str(f"Item portraits ({len(item_db)})")
        generate_item_portraits(item_db)
        portrait_bar.update(1)

        portrait_bar.set_postfix_str("Player portrait")
        try:
            player_prompt = generate_player_image_description()
        except Exception:
            player_prompt = "a young adventurer, pixel art, fantasy portrait"
        player_portrait_path = generate_player_portrait(player_prompt)
        portrait_bar.update(1)

        portrait_bar.set_postfix_str(f"Class portraits ({len(class_data_list)})")
        from src.generate.image_client import generate_class_portraits
        class_portrait_db = {}
        for i, cd in enumerate(class_data_list):
            prompt = cd.get("portrait_prompt") or f"a {cd['archetype']} character, fantasy pixel art"
            class_portrait_db[str(i)] = {"portrait_prompt": prompt, "name": cd.get("name", "")}
        generate_class_portraits(class_portrait_db)
        for i, cd in enumerate(class_data_list):
            cd["portrait_path"] = class_portrait_db[str(i)].get("profile_image")
        portrait_bar.update(1)

        portrait_bar.set_postfix_str("Environment portrait")
        env_portrait_prompt = f"a {maze.environment} landscape, fantasy pixel art, wide angle, atmospheric"
        env_portrait_path = os.path.join("data/portraits", "environment.png")
        if not generate_and_save_image(env_portrait_prompt, env_portrait_path):
            env_portrait_path = None
        portrait_bar.update(1)

        portrait_bar.close()
        portraits_generated = True
        logger.info("Portraits generated successfully.")
    except Exception as e:
        logger.warning("Portrait generation skipped: %s", e)
        portraits_generated = False
        player_portrait_path = None
        env_portrait_path = None
    phase_bar.update(1)

    # --- 13. NPC positions for home coords ---
    phase_bar.set_postfix_str("NPC positions")
    npc_positions = {}
    for npc in active_npcs:
        npc_positions[str(npc["id"])] = [npc.get("x", 0), npc.get("y", 0)]
    phase_bar.update(1)

    # --- 14. Write data files ---
    phase_bar.set_postfix_str("Write files")

    os.makedirs(os.path.dirname(MAZE_PATH), exist_ok=True)
    maze.save_to_json(MAZE_PATH, extra={
        "npc_positions": npc_positions,
        "player_start": list(player_start),
        "item_placements": item_placements,
        "event_positions": event_position_map,
    })

    os.makedirs(os.path.dirname(NPC_PATH), exist_ok=True)
    with open(NPC_PATH, "w") as f:
        json.dump(npc_pool, f, indent=2)

    os.makedirs(os.path.dirname(EVENT_PATH), exist_ok=True)
    with open(EVENT_PATH, "w") as f:
        json.dump(event_list, f, indent=2)

    os.makedirs(os.path.dirname(QUEST_PATH), exist_ok=True)
    with open(QUEST_PATH, "w") as f:
        json.dump(quest_list, f, indent=2)

    os.makedirs(os.path.dirname(STORY_PATH), exist_ok=True)
    with open(STORY_PATH, "w") as f:
        json.dump(story.model_dump(), f, indent=2)

    os.makedirs(os.path.dirname(CLASS_PATH), exist_ok=True)
    with open(CLASS_PATH, "w") as f:
        json.dump(class_data_list, f, indent=2)

    # --- Build and write WorldBible ---
    from src.generate.world_editor import build_world_bible, cross_validate, write_world_bible
    bible = build_world_bible(
        story=story,
        npc_pool=npc_pool,
        event_list=event_list,
        quest_list=quest_list,
        item_placements=item_placements,
        event_position_map=event_position_map,
        maze_environment=maze.environment,
    )
    xval_issues = cross_validate(bible, npc_pool, event_list, quest_list, item_placements)
    if xval_issues:
        logger.warning("WorldBible cross-validation issues: %s", xval_issues)
    world_bible_path = write_world_bible(bible)

    manifest = {
        "world_seed": WORLD_SEED,
        "environment": maze.environment,
        "environment_name": env_name,
        "maze_width": MAZE_WIDTH,
        "maze_height": MAZE_HEIGHT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "npc_pool_size": len(npc_pool),
        "active_npc_count": len(active_npcs),
        "quest_count": len(quest_list),
        "event_count": len(event_list),
        "class_count": len(class_data_list),
        "portraits_generated": portraits_generated,
        "player_portrait": player_portrait_path,
        "environment_portrait": env_portrait_path,
        "game_mode": GAME_MODE,
        "story_title": story.title,
        "faction_name": story.faction.name if story.faction else "",
        "story_seed": story.seed,
        "world_bible": world_bible_path,
        "world_bible_entities": len(bible.entity_index),
        "cross_validation_issues": len(xval_issues),
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    phase_bar.update(1)
    phase_bar.close()

    logger.info("=== Generation Complete ===")
    logger.info("  Environment: %s (%s)", maze.environment, env_name)
    logger.info("  NPCs: %d pool / %d active", len(npc_pool), len(active_npcs))
    logger.info("  Events: %d", len(event_list))
    logger.info("  Quests: %d", len(quest_list))
    logger.info("  WorldBible: %d entities indexed", len(bible.entity_index))
    logger.info("  Portraits: %s", "yes" if portraits_generated else "no (prompts saved)")
    logger.info("  Manifest: %s", MANIFEST_PATH)
