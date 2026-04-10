"""Generation pipeline orchestrator — phased architecture.

Phases:
  0. Environment sequence (1 LLM call)
  1. Story generation: overarching + per-room beats (1 + N LLM calls)
  2. Room layouts + TileMeta placement (0 LLM calls)
  3A. Classes, weapons, spells, abilities (5 LLM calls)
  3B-D. Per-room entity generation: items, NPCs, monsters (3N LLM calls)
  4A-B. Per-room events/quests + dialogue (4-5N LLM calls)
  5. Validation (0 LLM calls)
  6. Narrative summary (N+3 LLM calls)
  7. Portrait images (0 LLM calls — image backend only)
  8. Manifest assembly (0 LLM calls)

Entry point: generate_world()
"""

import json
import logging
import math
import os
import random
from datetime import datetime, timezone

from tqdm import tqdm

from config import (
    WORLD_SEED, STORY_SEED, GAME_MODE, MAZE_WIDTH, MAZE_HEIGHT,
    NUM_ROOMS, EVENT_DENSITY, ITEM_DENSITY, NPC_DENSITY,
)
from src.data.world_data import ENVIRONMENT_TYPES
from src.models.maze import Maze, TileMeta
from src.models.world_bible import WorldBible, RoomBible, EntityLore
from src.models.story import (
    OverarchingStory, Faction, RoomStoryBeat,
)
from src.generate.validator import ValidationReport
from src.generate.pipeline_utils import (
    _retry_with_feedback, build_manifest, _build_items_json,
    _validate_puzzle_tools, _event_fallback,
    _generate_shop_inventory, _generate_loot_table,
    _consumable_mult, CONSUMABLE_SCALING, WEAPON_PRICE_BY_DICE,
    _validate_quest,
)
from src.registry import registry

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

DATA_DIR = "data"
MAZE_PATH = os.path.join(DATA_DIR, "maze", "maze.json")
NPC_PATH = os.path.join(DATA_DIR, "npcs", "npcs.json")
EVENT_PATH = os.path.join(DATA_DIR, "events", "events.json")
QUEST_PATH = os.path.join(DATA_DIR, "quests", "quests.json")
STORY_PATH = os.path.join(DATA_DIR, "story", "story.json")
CLASS_PATH = os.path.join(DATA_DIR, "classes", "classes.json")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")
BIBLE_PATH = os.path.join(DATA_DIR, "world_bible.json")
ITEM_ITEMS_PATH = os.path.join(DATA_DIR, "items", "items.json")

_FALLBACK_STORY_SEED = "A dark cult is gathering power in the shadows, corrupting the land."

_FALLBACK_ENV_NAMES = {
    "forest": "Whisperwood", "cave": "Gloomhollow", "dungeon": "Dreadkeep",
    "castle": "Whitespire", "house": "Hearthstead", "city": "Silverport",
    "village": "Millhaven", "mountain": "Stonepeak",
}

PHASE_NAMES = [
    "Environment Sequence",
    "Story Generation",
    "Room Layouts",
    "Classes & Equipment",
    "Entity Generation",
    "Events & Quests",
    "Validation",
    "Narrative",
    "Portraits",
    "Manifest",
]


# ---------------------------------------------------------------------------
# Phase 0: Environment Sequence
# ---------------------------------------------------------------------------

def _phase0_environments(story_seed: str, num_rooms: int) -> list[dict]:
    """Generate a narrative environment sequence via LLM. Fallback: random."""
    logger.info("Generating environment sequence for %d rooms...", num_rooms)
    try:
        from src.generate.generators.llm_primitives import generate_environment_sequence
        envs = generate_environment_sequence(story_seed, num_rooms, ENVIRONMENT_TYPES)
        if envs and len(envs) >= num_rooms:
            logger.info("Environments: %s", [e.get("name", e.get("type")) for e in envs])
            return envs[:num_rooms]
    except Exception as e:
        logger.warning("Environment sequence generation failed: %s", e)

    envs = []
    for t in random.choices(ENVIRONMENT_TYPES, k=num_rooms):
        envs.append({"type": t, "name": _FALLBACK_ENV_NAMES.get(t, "Unknown Land")})
    logger.info("Using fallback environments: %s", [e["name"] for e in envs])
    return envs


# ---------------------------------------------------------------------------
# Phase 1: Two-Pass Story Generation
# ---------------------------------------------------------------------------

def _phase1_story(story_seed: str, environments: list[dict]) -> tuple[OverarchingStory, WorldBible]:
    """Generate overarching story (1 call) + per-room beats (N calls)."""
    num_rooms = len(environments)
    logger.info("Generating overarching story...")

    overarching_data = None
    try:
        from src.generate.generators.llm_primitives import generate_overarching_story
        result = generate_overarching_story(story_seed, environments)
        if "error" not in result:
            overarching_data = result
    except Exception as e:
        logger.warning("Overarching story generation failed: %s", e)

    if not overarching_data:
        overarching_data = {
            "title": "The Shadow's Grasp",
            "synopsis": "A dark force spreads corruption through the land.",
            "faction": {"name": "The Shadow Cult", "description": "A secretive order.",
                        "history": "Born from despair.", "leader": "The Faceless One"},
            "escalation_arc": [f"Escalation in room {i}" for i in range(num_rooms)],
            "climax": "Face the cult leader in a final showdown.",
            "final_boss_name": "The Faceless One",
            "final_boss_lore": "Once a revered priest, now consumed by shadow magic.",
            "key_npc_names": [],
        }

    faction_data = overarching_data.get("faction", {})
    faction = Faction(
        name=faction_data.get("name", "The Shadow Cult"),
        description=faction_data.get("description", "A mysterious faction."),
        history=faction_data.get("history", ""),
        leader=faction_data.get("leader", "Unknown"),
    ) if faction_data else None

    # Build a slim story summary to pass to beat generation — avoids sending the
    # full model dump (~1600 tokens of empty arrays) as input to each beat call.
    story_summary = {
        "title": overarching_data.get("title", ""),
        "synopsis": overarching_data.get("synopsis", ""),
        "faction_name": overarching_data.get("faction", {}).get("name", ""),
        "faction_description": overarching_data.get("faction", {}).get("description", ""),
        "leader": overarching_data.get("faction", {}).get("leader", ""),
        "escalation_arc": overarching_data.get("escalation_arc", []),
        "climax": overarching_data.get("climax", ""),
        "final_boss_name": overarching_data.get("final_boss_name", ""),
        "key_npc_names": overarching_data.get("key_npc_names", []),
    }

    room_beats: list[dict] = []
    logger.info("Generating %d room story beats...", num_rooms)
    for room_idx in tqdm(range(num_rooms), desc="  Room Beats", unit="beat", leave=True):
        try:
            from src.generate.generators.llm_primitives import generate_room_story_beat
            beat_data = generate_room_story_beat(
                story_summary, environments[room_idx], room_idx, room_beats)
            if "error" not in beat_data:
                room_beats.append(beat_data)
                logger.info("Room %d beat: %s (escalation %d, boss: %s)",
                            room_idx, environments[room_idx]["name"],
                            beat_data.get("escalation", room_idx + 1),
                            beat_data.get("mini_boss", {}).get("name", "none"))
                continue
        except Exception as e:
            logger.warning("Room %d beat generation failed: %s", room_idx, e)
        room_beats.append({
            "summary": f"The story continues in {environments[room_idx]['name']}.",
            "faction_presence": "The faction's influence grows.",
            "escalation": min(5, room_idx + 1),
            "characters": [],
            "mini_boss": {"name": "Lieutenant", "description": "A faction enforcer."},
            "conflicts": [],
        })

    beats = []
    for ri, bd in enumerate(room_beats):
        beats.append(RoomStoryBeat(
            room_id=f"room_{ri}",
            summary=bd.get("summary", ""),
            faction_presence=bd.get("faction_presence"),
            escalation=bd.get("escalation", min(5, ri + 1)),
            boss_name=bd.get("mini_boss", {}).get("name", ""),
            boss_lore=bd.get("mini_boss", {}).get("description", ""),
        ))

    story = OverarchingStory(
        seed=story_seed,
        title=overarching_data.get("title", "The Dark Convergence"),
        synopsis=overarching_data.get("synopsis", "A dark force threatens the land."),
        faction=faction,
        escalation_arc=overarching_data.get("escalation_arc", []),
        climax=overarching_data.get("climax", "The final confrontation awaits."),
        final_boss_name=overarching_data.get("final_boss_name", "The Dark Lord"),
        final_boss_lore=overarching_data.get("final_boss_lore", ""),
        key_npc_names=overarching_data.get("key_npc_names", []),
        beats=beats,
    )

    logger.info("Story: %s (faction: %s, %d beats)",
                story.title, story.faction.name if story.faction else "none", len(beats))

    bible = WorldBible(story=story)
    for ri, env in enumerate(environments):
        rid = f"room_{ri}"
        beat = beats[ri] if ri < len(beats) else None
        bible.rooms[rid] = RoomBible(
            environment=env["type"],
            environment_name=env["name"],
            level=ri + 1,
            story_beat=beat.summary if beat else "",
            boss_name=beat.boss_name if beat else "",
            boss_lore=beat.boss_lore if beat else "",
        )

    bible.persist(BIBLE_PATH)
    logger.info("World Bible v1 written to %s", BIBLE_PATH)
    return story, bible


# ---------------------------------------------------------------------------
# Phase 2: Room Layouts
# ---------------------------------------------------------------------------

def _phase2_layouts(environments: list[dict], bible: WorldBible) -> list[dict]:
    """Generate mazes + TileMeta for all rooms. No LLM calls."""
    layouts = []
    for room_idx, env in enumerate(environments):
        room_dir = os.path.join(DATA_DIR, "rooms", f"room_{room_idx}")
        os.makedirs(room_dir, exist_ok=True)

        maze = Maze(environment=env["type"], environment_name=env["name"])
        maze.generate()

        open_spaces = maze.find_open_spaces()
        player_start = random.choice(open_spaces) if open_spaces else (1, 1)

        maze.build_tile_meta(player_start)
        maze.place_door(player_start)

        logger.info("Room %d: %s (%s) — %d events, %d NPCs, %d items",
                     room_idx, env["type"], env["name"],
                     len(maze.get_tiles_by_type("event")),
                     len(maze.get_tiles_by_type("npc")),
                     len(maze.get_tiles_by_type("item")))

        layouts.append({
            "room_id": f"room_{room_idx}",
            "room_idx": room_idx,
            "room_level": room_idx + 1,
            "id_offset": room_idx * 1000,
            "environment": env["type"],
            "environment_name": env["name"],
            "maze": maze,
            "player_start": player_start,
            "room_dir": room_dir,
        })

    return layouts


# ---------------------------------------------------------------------------
# Phase 3A: Classes, Weapons, Spells
# ---------------------------------------------------------------------------

def _phase3a_classes(environments: list[dict], story: OverarchingStory,
                     bible: WorldBible) -> list:
    """Generate player classes with stat rolling, weapons, spells, abilities."""
    from src.generate.class_gen import generate_classes

    first_env = environments[0] if environments else {"type": "forest", "name": "Unknown"}
    logger.info("Generating player classes for %s...", first_env["name"])
    player_classes = generate_classes(first_env["type"], first_env["name"])

    for pc in player_classes:
        bible.add_player_class(EntityLore(
            entity_type="player_class", name=pc.name,
            lore=pc.flavor_text, tags=[pc.archetype],
        ))

    logger.info("Generated %d player classes.", len(player_classes))
    return player_classes


# ---------------------------------------------------------------------------
# Phase 3B: Items (per room)
# ---------------------------------------------------------------------------

def _phase3b_items(layout: dict, bible: WorldBible) -> tuple[dict | None, list[dict]]:
    """Generate items for a room and distribute across item tiles."""
    room_idx = layout["room_idx"]
    room_id = layout["room_id"]
    maze = layout["maze"]
    env_type = layout["environment"]
    env_name = layout["environment_name"]
    room_level = layout["room_level"]
    id_offset = layout["id_offset"]

    story_context = bible.get_cumulative_context(room_id)

    generated_items = None
    try:
        from src.generate.generators.llm_primitives import generate_item_primitive
        result = generate_item_primitive(
            {"environment": {"type": env_type, "name": env_name}},
            room_level, story_context=story_context)
        if "error" not in result:
            generated_items = _build_items_json(result, room_level)
    except Exception as e:
        logger.warning("Room %d item generation failed: %s", room_idx, e)

    item_id_base = 200 + id_offset
    if generated_items:
        rekeyed = {}
        for i, (_, item_data) in enumerate(sorted(generated_items.items())):
            rekeyed[str(item_id_base + i)] = item_data
        generated_items = rekeyed

    items_path = os.path.join(layout["room_dir"], "items.json")
    if generated_items:
        with open(items_path, "w") as f:
            json.dump(generated_items, f, indent=2)
        registry._loaded = False
        registry._load_items_from(items_path)
        registry._loaded = True

        for item_id, item_data in generated_items.items():
            bible.add_item(room_id, EntityLore(
                entity_type="item", entity_id=item_id,
                name=item_data.get("name", ""), room_id=room_id,
                lore=item_data.get("desc", ""),
                tags=[item_data.get("category", "misc")],
            ))

    item_tiles = maze.get_tiles_by_type("item")
    item_placements = []
    if generated_items:
        item_ids = list(generated_items.keys())
        for tile in item_tiles:
            chosen_id = int(random.choice(item_ids))
            x, y = tile.position
            maze.grid[y][x] = chosen_id
            item_placements.append({"x": x, "y": y, "item_id": chosen_id})
    else:
        from config import NUM_FOOD, NUM_DRINKS, NUM_TOOLS, NUM_WEAPONS, NUM_SPELL_SCROLLS
        maze.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS, NUM_WEAPONS, NUM_SPELL_SCROLLS)
        for y, row in enumerate(maze.grid):
            for x, cell in enumerate(row):
                if registry.is_item(cell):
                    item_placements.append({"x": x, "y": y, "item_id": cell})

    logger.info("Room %d: %d items (%d placements).",
                room_idx, len(generated_items or {}), len(item_placements))
    return generated_items, item_placements


# ---------------------------------------------------------------------------
# Phase 3C: NPCs (per room, batched)
# ---------------------------------------------------------------------------

def _phase3c_npcs(layout: dict, bible: WorldBible) -> list[dict]:
    """Generate all NPCs for a room in one batched LLM call."""
    room_idx = layout["room_idx"]
    room_id = layout["room_id"]
    maze = layout["maze"]
    env_type = layout["environment"]
    env_name = layout["environment_name"]
    id_offset = layout["id_offset"]

    npc_tiles = maze.get_tiles_by_type("npc")
    if not npc_tiles:
        return []

    story_context = bible.get_cumulative_context(room_id)
    room_story = bible.rooms.get(room_id, RoomBible(environment=env_type)).story_beat

    npc_slots = []
    for tile in npc_tiles:
        npc_slots.append({
            "position": list(tile.position),
            "role": tile.npc_role or "regular",
            "quest_type": tile.quest_type,
            "max_exchanges": tile.npc_max_exchanges,
        })

    npc_pool = []
    try:
        from src.generate.generators.llm_primitives import generate_npc_batch
        room_env = {"type": env_type, "name": env_name}
        llm_npcs = generate_npc_batch(room_env, room_story, npc_slots, story_context)
    except Exception as e:
        logger.warning("Room %d NPC batch generation failed: %s", room_idx, e)
        llm_npcs = []

    npc_id_counter = 100 + id_offset
    for i, tile in enumerate(npc_tiles):
        llm_data = llm_npcs[i] if i < len(llm_npcs) else {}
        x, y = tile.position

        _NPC_TYPE_MAP = {
            "merchant": "MerchantNPC",
            "quest": "RandomNPC",
            "combat_npc": "AggressiveNPC",
            "regular": "StaticNPC",
        }
        npc_type = _NPC_TYPE_MAP.get(tile.npc_role or "regular", "StaticNPC")

        npc_data = {
            "id": npc_id_counter,
            "type": npc_type,
            "name": llm_data.get("name", f"NPC_{npc_id_counter}"),
            "job": llm_data.get("job", "peasant"),
            "personality": llm_data.get("personality", "stoic"),
            "hobby": llm_data.get("hobby", "walking"),
            "backstory": llm_data.get("backstory", "A mysterious figure."),
            "environment": env_type,
            "environment_name": env_name,
            "opening_greeting": llm_data.get("opening_greeting", "Greetings, traveler."),
            "portrait_prompt": llm_data.get("portrait_prompt", f"a fantasy NPC in a {env_type}, pixel art"),
            "profile_image": None,
            "dialogue_tree": None,
            "quest_id": None,
            "quest_type": tile.quest_type,
            "quest_target_tile": list(tile.quest_target_tile) if tile.quest_target_tile else None,
            "max_exchanges": tile.npc_max_exchanges,
            "is_story_npc": tile.is_story_npc,
            "x": x,
            "y": y,
            "selected": True,
        }
        if tile.npc_role == "merchant":
            npc_data["shop_inventory"] = _generate_shop_inventory(registry)

        npc_pool.append(npc_data)
        bible.add_npc(room_id, EntityLore(
            entity_type="npc", entity_id=str(npc_id_counter),
            name=npc_data["name"], room_id=room_id,
            lore=npc_data["backstory"], tags=[npc_data["type"]],
        ))
        npc_id_counter += 1

    logger.info("Room %d: %d NPCs generated.", room_idx, len(npc_pool))
    return npc_pool


# ---------------------------------------------------------------------------
# Phase 3D: Monsters (per room)
# ---------------------------------------------------------------------------

def _phase3d_monsters(layout: dict, bible: WorldBible) -> list[dict]:
    """Generate monster database for a room via LLM."""
    room_idx = layout["room_idx"]
    room_id = layout["room_id"]
    env_type = layout["environment"]
    env_name = layout["environment_name"]
    room_level = layout["room_level"]

    story_context = bible.get_cumulative_context(room_id)
    monster_db = []
    try:
        from src.generate.generators.llm_primitives import generate_monster_primitive
        monsters = generate_monster_primitive(
            {"environment": {"type": env_type, "name": env_name}},
            room_level, story_context)
        if monsters:
            monster_db = monsters
    except Exception as e:
        logger.warning("Room %d monster generation failed: %s", room_idx, e)

    if not monster_db:
        from src.models.monster import MONSTER_POOLS
        pool = MONSTER_POOLS.get(env_type, MONSTER_POOLS.get("city", ["Rat"]))
        for name in pool[:6]:
            monster_db.append({"name": name, "species": name, "description": f"A {name}.",
                               "level": room_level, "is_boss": False,
                               "portrait_prompt": f"a {name.lower()} in a {env_type}, pixel art"})

    for m in monster_db:
        bible.add_monster(room_id, EntityLore(
            entity_type="monster", name=m.get("name", ""),
            room_id=room_id, lore=m.get("backstory", m.get("description", "")),
            tags=["boss"] if m.get("is_boss") else ["generated"],
        ))

    logger.info("Room %d: %d monsters generated.", room_idx, len(monster_db))
    return monster_db


# ---------------------------------------------------------------------------
# Phase 4A helpers
# ---------------------------------------------------------------------------

# Build a position→event_id index for O(1) quest target lookup.
def _build_event_pos_index(event_list: list[dict],
                           event_tiles: list) -> dict:
    """Return a dict mapping tile position tuples to event IDs."""
    index: dict[tuple, str] = {}
    for tile in event_tiles:
        evt_id = None
        for e in event_list:
            # Match by checking if the tile's position was used to generate this event.
            # Events are assigned IDs sequentially; we match on recorded tile position.
            if e.get("_tile_pos") == list(tile.position):
                evt_id = e["id"]
                break
        if evt_id:
            index[tile.position] = evt_id
    return index


# Quest success/failure templates — derived from quest type, no LLM call.
_QUEST_SUCCESS = {
    "combat_event": "You've done it. The threat is gone — here's what I promised.",
    "solve_puzzle": "I knew you could figure it out. Take this for your trouble.",
    "fetch_item": "You found it! This means more to me than you know. Please, take this.",
    "follower_same": "We made it. I'm safe now, thanks to you. Take this for your bravery.",
    "follower_next": "You got me through. I won't forget this. Here is your reward.",
    "combat_npc": "You bested me. I yield. A deal is a deal — take your prize.",
    "solve_event": "I couldn't have done that alone. You've earned this.",
}
_QUEST_FAILURE = {
    "combat_event": "It's over... they were too strong. I'm sorry, I have nothing left to give.",
    "solve_puzzle": "It's still blocked. Come back when you have what you need.",
    "fetch_item": "Without it, I can't help you. Maybe another time.",
    "follower_same": "I... I can't go on. Leave me here.",
    "follower_next": "We didn't make it. Perhaps fate has other plans.",
    "combat_npc": "Ha — you weren't ready for me. Come back when you're stronger.",
    "solve_event": "You couldn't handle it. The situation remains unsolved.",
}


def _monster_dict_to_model(m: dict, room_level: int):
    """Convert an LLM monster dict (with hp_range/ac_range) to a Monster model."""
    from src.models.monster import Monster
    hp_range = m.get("hp_range", [8 + room_level * 2, 15 + room_level * 3])
    ac_range = m.get("ac_range", [9 + room_level, 12 + room_level])
    hp = random.randint(int(hp_range[0]), int(hp_range[1]))
    ac = random.randint(int(ac_range[0]), int(ac_range[1]))
    return Monster(
        name=m.get("name", "Unknown"),
        species=m.get("species", m.get("name", "creature")),
        description=m.get("description", ""),
        hp=hp,
        max_hp=hp,
        ac=ac,
        damage_type=m.get("damage_type", "physical"),
        elemental_affinity=m.get("elemental_affinity"),
        level=room_level,
        portrait_prompt=m.get("portrait_prompt"),
    )


# ---------------------------------------------------------------------------
# Phase 4A: Events & Quests (per room, batched by type)
# ---------------------------------------------------------------------------

def _phase4a_events(layout: dict, bible: WorldBible,
                    monster_db: list[dict], npc_pool: list[dict],
                    item_placements: list[dict]) -> tuple[list[dict], list[dict]]:
    """Generate events batched by type + reconcile NPC quest stubs."""
    room_idx = layout["room_idx"]
    room_id = layout["room_id"]
    maze = layout["maze"]
    env_type = layout["environment"]
    env_name = layout["environment_name"]
    room_level = layout["room_level"]

    story_context = bible.get_cumulative_context(room_id)
    room_story = bible.rooms.get(room_id, RoomBible(environment=env_type)).story_beat
    room_env = {"type": env_type, "name": env_name}

    event_tiles = maze.get_tiles_by_type("event")
    event_list = []
    event_id_prefix = f"r{room_idx}_"

    # Separate regular and boss monsters for combat assignment
    regular_monsters = [m for m in monster_db if not m.get("is_boss")]
    boss_monsters = [m for m in monster_db if m.get("is_boss")]

    for event_type in ["combat", "puzzle", "event"]:
        typed_tiles = [t for t in event_tiles if t.event_type == event_type]
        if not typed_tiles:
            continue

        event_slots = []
        for t in typed_tiles:
            event_slots.append({
                "position": list(t.position),
                "is_story_related": t.is_story_related,
                "is_multi_combat": t.is_multi_combat,
                "multi_combat_count": t.multi_combat_count,
                "time_gate": t.time_gate,
            })

        llm_events = []
        try:
            from src.generate.generators.llm_primitives import generate_event_batch
            llm_events = generate_event_batch(room_env, room_story, event_type,
                                              event_slots, story_context)
        except Exception as e:
            logger.warning("Room %d %s event batch failed: %s", room_idx, event_type, e)

        for i, tile in enumerate(typed_tiles):
            idx = len(event_list)
            llm_data = llm_events[i] if i < len(llm_events) else _event_fallback(event_type)

            event_data = {
                "id": f"{event_id_prefix}evt_{idx:03d}",
                "type": event_type,
                "name": llm_data.get("name", f"Event {idx}"),
                "description": llm_data.get("description", "Something happens!"),
                "difficulty": llm_data.get("difficulty", 3),
                "portrait_prompt": llm_data.get("portrait_prompt",
                                                f"a {event_type} scene in a {env_type}, pixel art"),
                "profile_image": None,
                "time_gate": tile.time_gate,
                "_tile_pos": list(tile.position),  # used by quest reconciliation lookup
            }

            if event_type == "combat":
                count = tile.multi_combat_count if tile.is_multi_combat else 1
                all_monsters = []
                if regular_monsters:
                    selected = random.choices(regular_monsters,
                                              k=min(count, len(regular_monsters)))
                    all_monsters = [_monster_dict_to_model(m, room_level) for m in selected]
                else:
                    from src.models.monster import generate_encounter_monsters
                    for _ in range(count):
                        all_monsters.extend(generate_encounter_monsters(env_type, room_level))
                event_data["monsters"] = [m.to_dict() for m in all_monsters]
                event_data["room_level"] = room_level
                all_item_ids = registry.item_ids()
                if all_item_ids:
                    diff = event_data["difficulty"]
                    event_data["loot_table"] = _generate_loot_table(all_item_ids, diff)
                    event_data["money_drop"] = [diff * 2, diff * 8]

            elif event_type == "puzzle":
                choices = llm_data.get("choices", [])
                if not any(c.get("auto_success") for c in choices):
                    choices.append({"text": "Walk away", "auto_success": True})
                event_data["choices"] = choices
                event_data["correct_tool"] = llm_data.get("correct_tool")
                event_data["correct_ability"] = llm_data.get("correct_ability")

            elif event_type == "event":
                choices = llm_data.get("choices", [])
                if not any(c.get("auto_success") for c in choices):
                    choices.append({"text": "Walk away", "auto_success": True})
                event_data["choices"] = choices
                event_data["failure_damage_type"] = llm_data.get(
                    "failure_damage_type", random.choice(["health", "hunger", "thirst"]))
                event_data["failure_damage_range"] = llm_data.get(
                    "failure_damage_range", [3 + room_level, 8 + room_level * 2])

            event_list.append(event_data)

    # Build position→event lookup for quest reconciliation
    pos_to_event: dict[tuple, dict] = {}
    for e in event_list:
        pos = e.pop("_tile_pos", None)  # remove internal field
        if pos:
            pos_to_event[tuple(pos)] = e

    # --- Quest reconciliation: handle all 7 quest types ---
    quest_list = []
    for npc in npc_pool:
        qtype = npc.get("quest_type")
        if not qtype:
            continue

        npc_first_name = npc.get("name", "").split()[0] or "Unknown"
        base_quest = {
            "id": f"{event_id_prefix}q_{len(quest_list):03d}",
            "type": qtype,
            "title": f"{npc_first_name}'s Request",
            "description": f"{npc.get('name', 'Someone')} needs your help.",
            "giver_npc_id": npc["id"],
            "room_id": room_id,
            "is_story_quest": npc.get("is_story_npc", False),
            "reward": {"xp": 25 + room_level * 10, "item_id": None},
            "failure_penalty": {"hp_damage": max(0, room_level * 2)},
            "success_dialogue": _QUEST_SUCCESS.get(qtype, "Thank you, traveler."),
            "failure_dialogue": _QUEST_FAILURE.get(qtype, "I needed your help."),
            "prerequisite_quest_id": None,
            "portrait_prompt": None,
            "profile_image": None,
        }

        target_pos = tuple(npc["quest_target_tile"]) if npc.get("quest_target_tile") else None

        if qtype in ("combat_event", "solve_puzzle", "solve_event") and target_pos:
            target_event = pos_to_event.get(target_pos)
            base_quest["target_event_id"] = target_event["id"] if target_event else None

        elif qtype == "fetch_item":
            item_tile_list = maze.get_tiles_by_type("item")
            if item_tile_list:
                t = random.choice(item_tile_list)
                base_quest["target_tile"] = list(t.position)
                base_quest["item_category"] = t.item_category

        elif qtype in ("follower_same", "follower_next"):
            base_quest["target_position"] = (list(maze.door_position)
                                              if maze.door_position else None)
            base_quest["escort_npc_id"] = npc["id"]
            base_quest["crosses_room"] = (qtype == "follower_next")

        elif qtype == "combat_npc":
            # NPC is also a combatant — give them stats and add to monster_db
            npc["type"] = "AggressiveNPC"
            npc_monster = {
                "name": npc.get("name", "Hostile NPC"),
                "species": "npc",
                "description": npc.get("backstory", f"A hostile {npc.get('job', 'figure')}."),
                "hp_range": [10 + room_level * 3, 15 + room_level * 5],
                "ac_range": [9 + room_level, 12 + room_level],
                "damage_type": "physical",
                "elemental_affinity": None,
                "weakness": None,
                "abilities": [],
                "is_boss": False,
                "portrait_prompt": npc.get("portrait_prompt",
                                           "a hostile NPC, pixel art fantasy"),
            }
            monster_db.append(npc_monster)
            base_quest["target_npc_id"] = npc["id"]

        quest_list.append(base_quest)
        npc["quest_id"] = base_quest["id"]

    story_count = sum(1 for q in quest_list if q.get("is_story_quest"))
    logger.info("Room %d: %d events, %d quests (%d story).",
                room_idx, len(event_list), len(quest_list), story_count)
    return event_list, quest_list


# ---------------------------------------------------------------------------
# Phase 4B: Dialogue
# ---------------------------------------------------------------------------

def _phase4b_dialogue(layout: dict, npc_pool: list[dict],
                      bible: WorldBible) -> list[dict]:
    """Generate dialogue context (online) or full trees (offline-static)."""
    room_idx = layout["room_idx"]
    room_id = layout["room_id"]
    env_type = layout["environment"]
    env_name = layout["environment_name"]
    room_env = {"type": env_type, "name": env_name}
    room_story = bible.rooms.get(room_id, RoomBible(environment=env_type)).story_beat
    story_context = bible.get_cumulative_context(room_id)

    if GAME_MODE == "online":
        try:
            from src.generate.generators.llm_primitives import generate_dialogue_context
            npc_data_for_llm = [{"npc_name": n["name"], "job": n["job"],
                                 "personality": n["personality"],
                                 "quest_type": n.get("quest_type"),
                                 "max_exchanges": n.get("max_exchanges", 5)}
                                for n in npc_pool]
            dialogue_data = generate_dialogue_context(
                room_env, room_story, npc_data_for_llm, story_context)
            for i, npc in enumerate(npc_pool):
                if i < len(dialogue_data):
                    d = dialogue_data[i]
                    npc["opening_greeting"] = d.get("greeting", npc.get("opening_greeting", ""))
                    npc["exhausted_dialogue"] = d.get("exhausted_dialogue", "I have nothing more to say.")
                    npc["personality_notes"] = d.get("personality_notes", [])
        except Exception as e:
            logger.warning("Room %d dialogue context generation failed: %s", room_idx, e)
            for npc in npc_pool:
                npc["exhausted_dialogue"] = "I have nothing more to say."
                npc["personality_notes"] = []
    elif GAME_MODE == "offline_static":
        from src.generate.generators.llm_primitives import generate_dialogue_tree
        for npc in npc_pool:
            try:
                quest_ctx = {"quest_id": npc.get("quest_id"), "quest_type": npc.get("quest_type")}
                tree = generate_dialogue_tree(npc, quest_ctx if npc.get("quest_id") else None)
                if "error" not in tree and "nodes" in tree:
                    npc["dialogue_tree"] = tree
            except Exception as e:
                logger.warning("Room %d NPC %s dialogue tree failed: %s",
                               room_idx, npc.get("name"), e)

    logger.info("Room %d: Dialogue generated for %d NPCs (%s mode).",
                room_idx, len(npc_pool), GAME_MODE)
    return npc_pool


# ---------------------------------------------------------------------------
# Phase 5: Validation
# ---------------------------------------------------------------------------

def _phase5_validate(bible: WorldBible, room_results: list[dict],
                     story: OverarchingStory) -> ValidationReport:
    """Run structural validation checks."""
    report = ValidationReport()
    from src.generate.world_editor import editor_coherence_check, cross_validate, gameplay_audit

    editor_issues = editor_coherence_check(bible, room_results)
    if editor_issues:
        logger.warning("Editor coherence: %d issues", len(editor_issues))
        for issue in editor_issues:
            logger.warning("  - %s", issue)

    all_npcs = [n for rr in room_results for n in rr["npc_pool"]]
    all_events = [e for rr in room_results for e in rr["event_list"]]
    all_quests = [q for rr in room_results for q in rr["quest_list"]]
    all_placements = [p for rr in room_results for p in rr["item_placements"]]

    xval_issues = cross_validate(bible, all_npcs, all_events, all_quests, all_placements)
    if xval_issues:
        logger.warning("Cross-validation: %d issues", len(xval_issues))

    audit_issues = gameplay_audit(bible, all_npcs, all_events, all_quests, all_placements)
    if audit_issues:
        logger.info("Gameplay audit: %d issues.", len(audit_issues))
        for issue in audit_issues:
            severity = issue.get("severity", "warning")
            if severity == "error":
                report.add_major(issue["message"], entity_id=issue.get("entity_id", ""),
                                 phase="gameplay_audit")
            else:
                report.add_warning(issue["message"], entity_id=issue.get("entity_id", ""),
                                   phase="gameplay_audit")
    else:
        logger.info("Gameplay audit: all checks passed.")

    return report


# ---------------------------------------------------------------------------
# Phase 6: Narrative
# ---------------------------------------------------------------------------

def _phase6_narrative(bible: WorldBible, room_results: list[dict]) -> dict:
    """Generate synopsis, room intros, game over, victory text."""
    narrative_data = {}
    try:
        from src.generate.summary_agent import (
            generate_story_synopsis, generate_room_intro,
            generate_game_over_text, generate_victory_text,
        )
        narrative_data["synopsis"] = generate_story_synopsis(bible)
        narrative_data["game_over"] = generate_game_over_text(bible, "the hero", "adventurer")
        narrative_data["victory"] = generate_victory_text(bible, "the hero", "adventurer")
        for rr in room_results:
            rid = rr["room_id"]
            narrative_data[f"room_intro_{rid}"] = generate_room_intro(
                bible, rid, rr["environment_name"], rr["environment"])
        logger.info("Narrative generated: %d entries.", len(narrative_data))
    except Exception as e:
        logger.warning("Narrative generation failed: %s", e)

    narrative_path = os.path.join(DATA_DIR, "narrative.json")
    with open(narrative_path, "w") as f:
        json.dump(narrative_data, f, indent=2)
    return narrative_data


# ---------------------------------------------------------------------------
# Phase 7: Portraits
# ---------------------------------------------------------------------------

def _phase7_portraits(room_results: list[dict], class_data_list: list[dict],
                      bible: WorldBible):
    """Generate portrait images from all portrait_prompts."""
    try:
        from src.generate.image_client import (
            generate_npc_portraits, generate_event_illustrations,
            generate_item_portraits, generate_player_portrait,
            generate_and_save_image, generate_class_portraits,
        )
        from src.generate.generators.llm_primitives import generate_player_image_description
        from src.generate.summary_agent import (
            build_npc_portrait_prompt, build_class_portrait_prompt,
            build_room_portrait_prompt, build_game_over_portrait_prompt,
        )

        for rr in tqdm(room_results, desc="  Room Portraits", unit="room", leave=True):
            rid = rr["room_id"]
            npc_db = {str(n["id"]): n for n in rr["npc_pool"]}
            for nd in npc_db.values():
                if not nd.get("portrait_prompt"):
                    nd["portrait_prompt"] = build_npc_portrait_prompt(nd, bible, room_id=rid)
            generate_npc_portraits(npc_db)
            event_db = {e["id"]: e for e in rr["event_list"]}
            generate_event_illustrations(event_db)

        try:
            player_prompt = generate_player_image_description()
        except Exception:
            player_prompt = "a young adventurer, pixel art, fantasy portrait"
        player_portrait_path = generate_player_portrait(player_prompt)

        class_portrait_db = {}
        for i, cd in enumerate(class_data_list):
            prompt = cd.get("portrait_prompt") or build_class_portrait_prompt(cd, bible)
            class_portrait_db[str(i)] = {"portrait_prompt": prompt, "name": cd.get("name", "")}
        generate_class_portraits(class_portrait_db)
        for i, cd in enumerate(class_data_list):
            cd["portrait_path"] = class_portrait_db[str(i)].get("profile_image")

        for rr in room_results:
            portrait_path = os.path.join("data/portraits", f"environment_{rr['room_idx']}.png")
            room_prompt = build_room_portrait_prompt(rr["room_id"], bible)
            generate_and_save_image(room_prompt, portrait_path)
            rr["environment_portrait"] = portrait_path

        gameover_path = os.path.join("data/portraits", "game_over.png")
        generate_and_save_image(build_game_over_portrait_prompt(bible), gameover_path)

        logger.info("Portraits generated successfully.")
        return True, player_portrait_path, gameover_path
    except Exception as e:
        logger.warning("Portrait generation skipped: %s", e)
        return False, None, None


# ---------------------------------------------------------------------------
# Phase 8: Write Files & Manifest
# ---------------------------------------------------------------------------

def _write_room_files(layout: dict, npc_pool: list, event_list: list,
                      quest_list: list, item_placements: list):
    """Write per-room JSON files."""
    room_dir = layout["room_dir"]
    maze = layout["maze"]
    player_start = layout["player_start"]

    npc_positions = {}
    for npc in npc_pool:
        npc_positions[str(npc["id"])] = [npc.get("x", 0), npc.get("y", 0)]

    event_position_map = []
    for e in event_list:
        event_position_map.append({"event_id": e["id"]})

    maze.save_to_json(os.path.join(room_dir, "maze.json"), extra={
        "npc_positions": npc_positions,
        "player_start": list(player_start),
        "item_placements": item_placements,
    })
    with open(os.path.join(room_dir, "npcs.json"), "w") as f:
        json.dump(npc_pool, f, indent=2)
    with open(os.path.join(room_dir, "events.json"), "w") as f:
        json.dump(event_list, f, indent=2)
    with open(os.path.join(room_dir, "quests.json"), "w") as f:
        json.dump(quest_list, f, indent=2)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_world():
    """Phased world generation pipeline with progress tracking."""
    logger.info("=== MazeWorld World Generator ===")
    logger.info("Seed: %s, Mode: %s, Rooms: %d", WORLD_SEED, GAME_MODE, NUM_ROOMS)

    if WORLD_SEED != -1:
        random.seed(WORLD_SEED)

    registry.load()
    num_rooms = NUM_ROOMS
    story_seed = STORY_SEED or _FALLBACK_STORY_SEED

    phase_bar = tqdm(total=len(PHASE_NAMES), desc="World Generation",
                     unit="phase", position=0, leave=True)

    def advance(name: str):
        phase_bar.set_description(f"World Gen: {name}")
        logger.info("=== %s ===", name)

    # --- Phase 0: Environment Sequence ---
    advance(PHASE_NAMES[0])
    environments = _phase0_environments(story_seed, num_rooms)
    phase_bar.update(1)

    # --- Phase 1: Story ---
    advance(PHASE_NAMES[1])
    story, bible = _phase1_story(story_seed, environments)
    phase_bar.update(1)

    # --- Phase 2: Layouts ---
    advance(PHASE_NAMES[2])
    layouts = _phase2_layouts(environments, bible)
    phase_bar.update(1)

    # --- Phase 3A: Classes & Equipment ---
    advance(PHASE_NAMES[3])
    player_classes = _phase3a_classes(environments, story, bible)
    class_data_list = [pc.model_dump() for pc in player_classes]
    phase_bar.update(1)

    # --- Phase 3B-D: Entity Generation (per room) ---
    advance(PHASE_NAMES[4])
    room_results = []
    for layout in tqdm(layouts, desc="  Entities", unit="room", position=1, leave=True):
        generated_items, item_placements = _phase3b_items(layout, bible)
        npc_pool = _phase3c_npcs(layout, bible)
        monster_db = _phase3d_monsters(layout, bible)
        bible.persist(BIBLE_PATH)
        room_results.append({
            "room_id": layout["room_id"],
            "room_idx": layout["room_idx"],
            "room_level": layout["room_level"],
            "environment": layout["environment"],
            "environment_name": layout["environment_name"],
            "maze": layout["maze"],
            "player_start": layout["player_start"],
            "room_dir": layout["room_dir"],
            "npc_pool": npc_pool,
            "monster_db": monster_db,
            "generated_items": generated_items,
            "item_placements": item_placements,
            "event_list": [],
            "quest_list": [],
        })
    phase_bar.update(1)

    # --- Phase 4: Events, Quests, Dialogue (per room) ---
    advance(PHASE_NAMES[5])
    for rr in tqdm(room_results, desc="  Content", unit="room", position=1, leave=True):
        layout = next(l for l in layouts if l["room_id"] == rr["room_id"])
        event_list, quest_list = _phase4a_events(
            layout, bible, rr["monster_db"], rr["npc_pool"], rr["item_placements"])
        rr["event_list"] = event_list
        rr["quest_list"] = quest_list
        rr["npc_pool"] = _phase4b_dialogue(layout, rr["npc_pool"], bible)
        _write_room_files(layout, rr["npc_pool"], event_list, quest_list, rr["item_placements"])
    phase_bar.update(1)

    # --- Phase 5: Validation ---
    advance(PHASE_NAMES[6])
    report = _phase5_validate(bible, room_results, story)
    phase_bar.update(1)

    # --- Phase 6: Narrative ---
    advance(PHASE_NAMES[7])
    narrative_data = _phase6_narrative(bible, room_results)
    phase_bar.update(1)

    # --- Phase 7: Portraits ---
    advance(PHASE_NAMES[8])
    portraits_generated, player_portrait_path, gameover_path = _phase7_portraits(
        room_results, class_data_list, bible)
    phase_bar.update(1)

    # --- Phase 8: Manifest ---
    advance(PHASE_NAMES[9])

    os.makedirs(os.path.dirname(STORY_PATH), exist_ok=True)
    with open(STORY_PATH, "w") as f:
        json.dump(story.model_dump(), f, indent=2)
    os.makedirs(os.path.dirname(CLASS_PATH), exist_ok=True)
    with open(CLASS_PATH, "w") as f:
        json.dump(class_data_list, f, indent=2)

    all_items = {}
    for rr in room_results:
        if rr.get("generated_items"):
            all_items.update(rr["generated_items"])
    if all_items:
        os.makedirs(os.path.dirname(ITEM_ITEMS_PATH), exist_ok=True)
        with open(ITEM_ITEMS_PATH, "w") as f:
            json.dump(all_items, f, indent=2)

    manifest = {
        "world_seed": WORLD_SEED,
        "num_rooms": num_rooms,
        "environments": [e["type"] for e in environments],
        "environment_names": [e["name"] for e in environments],
        "maze_width": MAZE_WIDTH,
        "maze_height": MAZE_HEIGHT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "npc_count": sum(len(rr["npc_pool"]) for rr in room_results),
        "quest_count": sum(len(rr["quest_list"]) for rr in room_results),
        "event_count": sum(len(rr["event_list"]) for rr in room_results),
        "class_count": len(class_data_list),
        "portraits_generated": portraits_generated,
        "player_portrait": player_portrait_path,
        "gameover_portrait": gameover_path,
        "game_mode": GAME_MODE,
        "story_title": story.title,
        "faction_name": story.faction.name if story.faction else "",
        "story_seed": story.seed,
        "rooms": [
            {
                "room_id": rr["room_id"],
                "environment": rr["environment"],
                "environment_name": rr["environment_name"],
                "npc_count": len(rr["npc_pool"]),
                "event_count": len(rr["event_list"]),
                "quest_count": len(rr["quest_list"]),
            }
            for rr in room_results
        ],
        "validation_report": report.to_dict(),
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    phase_bar.update(1)
    phase_bar.close()

    logger.info("=== Generation Complete (%d rooms) ===", num_rooms)
    for rr in room_results:
        logger.info("  Room %d: %s (%s) — %d NPCs, %d events, %d quests",
                     rr["room_idx"], rr["environment"], rr["environment_name"],
                     len(rr["npc_pool"]), len(rr["event_list"]),
                     len(rr["quest_list"]))
    logger.info("  Manifest: %s", MANIFEST_PATH)
    logger.info("  World Bible: %s", BIBLE_PATH)
