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
import os
import random
from datetime import datetime, timezone

from tqdm import tqdm

from config import (
    GAME_MODE,
    MAZE_HEIGHT,
    MAZE_WIDTH,
    NUM_ROOMS,
    STORY_SEED,
    WORLD_SEED,
)
from src.data.world_data import ENVIRONMENT_TYPES
from src.generate.pipeline_utils import (
    _build_items_list,
    _event_fallback,
    _generate_loot_table,
    _generate_shop_inventory,
    _validate_puzzle_abilities,
    _validate_puzzle_tools,
)
from src.generate.validator import ValidationReport
from src.models.maze import Maze, TileMeta
from src.models.story import (
    Faction,
    OverarchingStory,
    RoomStoryBeat,
)
from src.models.world_bible import EntityLore, RoomBible, WorldBible
from src.registry import registry
from src.utils.dataloader_utils import load_json_data

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
    "forest": "Whisperwood",
    "cave": "Gloomhollow",
    "dungeon": "Dreadkeep",
    "castle": "Whitespire",
    "house": "Hearthstead",
    "city": "Silverport",
    "village": "Millhaven",
    "mountain": "Stonepeak",
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
    "Player Guide",
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
            "faction": {
                "name": "The Shadow Cult",
                "description": "A secretive order.",
                "history": "Born from despair.",
                "leader": "The Faceless One",
            },
            "escalation_arc": [f"Escalation in room {i}" for i in range(num_rooms)],
            "climax": "Face the cult leader in a final showdown.",
            "final_boss_name": "The Faceless One",
            "final_boss_lore": "Once a revered priest, now consumed by shadow magic.",
            "key_npc_names": [],
        }

    faction_data = overarching_data.get("faction", {})
    faction = (
        Faction(
            name=faction_data.get("name", "The Shadow Cult"),
            description=faction_data.get("description", "A mysterious faction."),
            history=faction_data.get("history", ""),
            leader=faction_data.get("leader", "Unknown"),
        )
        if faction_data
        else None
    )

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

            beat_data = generate_room_story_beat(story_summary, environments[room_idx], room_idx, room_beats, num_rooms)
            if "error" not in beat_data:
                room_beats.append(beat_data)
                logger.info(
                    "Room %d beat: %s (escalation %d, boss: %s)",
                    room_idx,
                    environments[room_idx]["name"],
                    beat_data.get("escalation", room_idx + 1),
                    beat_data.get("mini_boss", {}).get("name", "none"),
                )
                continue
        except Exception as e:
            logger.warning("Room %d beat generation failed: %s", room_idx, e)
        room_beats.append(
            {
                "summary": f"The story continues in {environments[room_idx]['name']}.",
                "faction_presence": "The faction's influence grows.",
                "escalation": min(num_rooms, room_idx + 1),
                "characters": [],
                "mini_boss": {"name": "Lieutenant", "description": "A faction enforcer."},
                "conflicts": [],
            }
        )

    beats = []
    for ri, bd in enumerate(room_beats):
        beats.append(
            RoomStoryBeat(
                room_id=f"room_{ri}",
                summary=bd.get("summary", ""),
                faction_presence=bd.get("faction_presence"),
                escalation=bd.get("escalation", min(num_rooms, ri + 1)),
                boss_name=bd.get("mini_boss", {}).get("name", ""),
                boss_lore=bd.get("mini_boss", {}).get("description", ""),
            )
        )

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

    logger.info(
        "Story: %s (faction: %s, %d beats)", story.title, story.faction.name if story.faction else "none", len(beats)
    )

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


def _phase2_layouts(
    environments: list[dict], bible: WorldBible, story: "OverarchingStory"
) -> tuple[list[dict], dict, dict]:
    """Generate mazes + TileMeta for all rooms.

    Also generates music and SFX prompts at the end (two LLM calls) while all
    environment types are freshly known.
    Returns (layouts, music_prompts, sfx_prompts).
    """
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

        logger.info(
            "Room %d: %s (%s) — %d events, %d NPCs, %d items",
            room_idx,
            env["type"],
            env["name"],
            len(maze.get_tiles_by_type("event")),
            len(maze.get_tiles_by_type("npc")),
            len(maze.get_tiles_by_type("item")),
        )

        layouts.append(
            {
                "room_id": f"room_{room_idx}",
                "room_idx": room_idx,
                "room_level": room_idx + 1,
                "id_offset": room_idx * 1000,
                "environment": env["type"],
                "environment_name": env["name"],
                "maze": maze,
                "player_start": player_start,
                "room_dir": room_dir,
            }
        )

    # Generate music + SFX prompts immediately after layouts are done —
    # this is the earliest point where both story and unique env types are known.
    music_prompts: dict[str, str] = {}
    sfx_prompts: dict[str, dict] = {}

    unique_envs = list(dict.fromkeys(layout["environment"] for layout in layouts))
    story_summary = {
        "title": story.title,
        "faction_name": story.faction.name if story.faction else "",
        "faction_description": story.faction.description if story.faction else "",
        "climax": story.climax,
    }

    try:
        from src.generate.generators.llm_primitives import generate_music_prompts
        from src.generate.music_client import build_full_prompt_dict

        logger.info("Generating music prompts for envs: %s", unique_envs)
        llm_prompts = generate_music_prompts(story_summary, unique_envs)
        music_prompts = build_full_prompt_dict(llm_prompts)
        logger.info("Music prompts ready: %d tracks", len(music_prompts))
    except Exception as e:
        logger.warning("Music prompt generation failed: %s", e)

    try:
        from src.generate.generators.llm_primitives import generate_sfx_prompts
        from src.generate.sfx_client import build_full_sfx_prompt_dict

        env_details = [{"type": layout["environment"], "name": layout["environment_name"]} for layout in layouts]
        seen = set()
        unique_env_details = []
        for ed in env_details:
            if ed["type"] not in seen:
                seen.add(ed["type"])
                unique_env_details.append(ed)

        spell_elements = list(
            {rb.story_beat.split()[-1] if rb.story_beat else "" for rb in bible.rooms.values()} - {""}
        )
        if not spell_elements:
            spell_elements = ["fire", "water", "forest"]

        logger.info("Generating SFX prompts for envs=%s, elements=%s", unique_envs, spell_elements)
        llm_sfx = generate_sfx_prompts(story_summary, unique_env_details, spell_elements)
        sfx_prompts = build_full_sfx_prompt_dict(llm_sfx)
        logger.info("SFX prompts ready: %d effects", len(sfx_prompts))
    except Exception as e:
        logger.warning("SFX prompt generation failed: %s", e)

    return layouts, music_prompts, sfx_prompts


# ---------------------------------------------------------------------------
# Phase 3A: Classes, Weapons, Spells
# ---------------------------------------------------------------------------


def _phase3a_classes(environments: list[dict], story: OverarchingStory, bible: WorldBible) -> list:
    """Generate player classes with stat rolling, weapons, spells, abilities."""
    from src.generate.class_gen import generate_classes

    first_env = environments[0] if environments else {"type": "forest", "name": "Unknown"}
    logger.info("Generating player classes for %s...", first_env["name"])
    player_classes = generate_classes(first_env["type"], first_env["name"])

    for pc in player_classes:
        bible.add_player_class(
            EntityLore(
                entity_type="player_class",
                name=pc.name,
                lore=pc.flavor_text,
                tags=[pc.archetype],
            )
        )

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
            {"environment": {"type": env_type, "name": env_name}}, room_level, story_context=story_context
        )
        if "error" not in result:
            item_list = _build_items_list(result, room_level)
            if item_list:
                generated_items = {}
                item_id_base = 200 + id_offset
                for i, item_data in enumerate(item_list):
                    generated_items[str(item_id_base + i)] = item_data
    except Exception as e:
        logger.warning("Room %d item generation failed: %s", room_idx, e)

    items_path = os.path.join(layout["room_dir"], "items.json")
    if generated_items:
        with open(items_path, "w") as f:
            json.dump(generated_items, f, indent=2)
        registry._loaded = False
        registry._load_items_from(items_path)
        registry._loaded = True

        for item_id, item_data in generated_items.items():
            bible.add_item(
                room_id,
                EntityLore(
                    entity_type="item",
                    entity_id=item_id,
                    name=item_data.get("name", ""),
                    room_id=room_id,
                    lore=item_data.get("desc", ""),
                    tags=[item_data.get("category", "misc")],
                ),
            )

    item_tiles = maze.get_tiles_by_type("item")
    item_placements = []
    if generated_items:
        item_ids = list(generated_items.keys())
        for tile in item_tiles:
            chosen_id = int(random.choice(item_ids))
            x, y = tile.position
            maze.grid[y][x] = chosen_id
            item_placements.append({"x": x, "y": y, "item_id": chosen_id})

    logger.info("Room %d: %d items (%d placements).", room_idx, len(generated_items or {}), len(item_placements))
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
        npc_slots.append(
            {
                "position": list(tile.position),
                "role": tile.npc_role or "regular",
                "quest_type": tile.quest_type,
                "max_exchanges": tile.npc_max_exchanges,
            }
        )

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
        bible.add_npc(
            room_id,
            EntityLore(
                entity_type="npc",
                entity_id=str(npc_id_counter),
                name=npc_data["name"],
                room_id=room_id,
                lore=npc_data["backstory"],
                tags=[npc_data["type"]],
            ),
        )
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
            {"environment": {"type": env_type, "name": env_name}}, room_level, story_context
        )
        if monsters:
            monster_db = monsters
    except Exception as e:
        logger.warning("Room %d monster generation failed: %s", room_idx, e)

    if not monster_db:
        from src.models.monster import MONSTER_POOLS

        pool = MONSTER_POOLS.get(env_type, MONSTER_POOLS.get("city", ["Rat"]))
        for name in pool[:6]:
            monster_db.append(
                {
                    "name": name,
                    "species": name,
                    "description": f"A {name}.",
                    "level": room_level,
                    "is_boss": False,
                    "portrait_prompt": f"a {name.lower()} in a {env_type}, pixel art",
                }
            )

    for m in monster_db:
        bible.add_monster(
            room_id,
            EntityLore(
                entity_type="monster",
                name=m.get("name", ""),
                room_id=room_id,
                lore=m.get("backstory", m.get("description", "")),
                tags=["boss"] if m.get("is_boss") else ["generated"],
            ),
        )

    logger.info("Room %d: %d monsters generated.", room_idx, len(monster_db))
    return monster_db


# ---------------------------------------------------------------------------
# Enrichment pass: assign real DB objects to TileMeta after Phase 3
# ---------------------------------------------------------------------------


def _enrich_tile_meta(layouts: list[dict], room_results: list[dict], class_data_list: list[dict]):
    """Fill TileMeta requirement slots and combat assignments from real DBs.

    Called between Phase 3D and Phase 4A, after all databases are populated.
    """
    # Collect class ability/spell names across all archetypes
    all_abilities = []
    all_spells = []
    for cd in class_data_list:
        for ab in cd.get("abilities", []):
            all_abilities.append(ab["name"] if isinstance(ab, dict) else ab.name)
        for ab in cd.get("ability_pool", []):
            all_abilities.append(ab["name"] if isinstance(ab, dict) else ab.name)
        for sp in cd.get("spells", []):
            all_spells.append(sp["name"] if isinstance(sp, dict) else sp.name)
        for sp in cd.get("spell_pool", []):
            all_spells.append(sp["name"] if isinstance(sp, dict) else sp.name)
    all_abilities = list(dict.fromkeys(all_abilities))
    all_spells = list(dict.fromkeys(all_spells))

    # Tool attributes from item registry
    from src.models.items import Tool

    tool_attrs = list(
        {
            item.item_stats.attribute
            for item in registry.item_registry.values()
            if isinstance(item, Tool) and item.item_stats.attribute
        }
    ) or ["bludgeon", "cutting", "digging", "climbing"]

    for layout, rr in zip(layouts, room_results):
        maze = layout["maze"]
        monster_db = rr["monster_db"]
        regular_monsters = [m for m in monster_db if not m.get("is_boss")]
        item_names = []
        if rr.get("generated_items"):
            item_names = [v.get("name", "") for v in rr["generated_items"].values() if v.get("name")]

        tile_meta = maze.tile_meta
        combat_tile_map: dict[tuple, "TileMeta"] = {}

        for tile in tile_meta:
            if tile.tile_type != "event":
                continue

            if tile.event_type == "combat":
                # Assign monsters from DB
                count = tile.assigned_monster_count
                if regular_monsters:
                    chosen = random.choices(regular_monsters, k=min(count, len(regular_monsters)))
                    tile.assigned_monsters = [m.get("name", "Unknown") for m in chosen]
                else:
                    tile.assigned_monsters = ["Unknown Creature"]
                combat_tile_map[tile.position] = tile

            elif tile.requires_type and not tile.requires_ref:
                # Fill requirement ref from the appropriate pool
                if tile.requires_type == "tool" and tool_attrs:
                    tile.requires_ref = random.choice(tool_attrs)
                elif tile.requires_type == "ability" and all_abilities:
                    tile.requires_ref = random.choice(all_abilities)
                elif tile.requires_type == "spell" and all_spells:
                    tile.requires_ref = random.choice(all_spells)
                elif tile.requires_type == "item" and item_names:
                    tile.requires_ref = random.choice(item_names)

        # Wire NPC quest tiles to their target combat tile's monsters
        for tile in tile_meta:
            if tile.tile_type != "npc" or not tile.quest_target_tile:
                continue
            target = combat_tile_map.get(tile.quest_target_tile)
            if target and target.assigned_monsters:
                tile.quest_target_monsters = list(target.assigned_monsters)

        # Designate gate/boss tile: pick combat tile closest to door
        door_pos = maze.door_position
        if door_pos and combat_tile_map:
            room_idx = layout["room_idx"]
            num_rooms = len(layouts)
            is_final = room_idx == num_rooms - 1

            boss_monsters = [m for m in monster_db if m.get("is_boss")]
            sorted_tiles = sorted(
                combat_tile_map.values(),
                key=lambda t: abs(t.position[0] - door_pos[0]) + abs(t.position[1] - door_pos[1]),
            )
            gate_tile = sorted_tiles[0]

            if is_final:
                gate_tile.is_climax_boss = True
                gate_tile.is_gate = True
                if boss_monsters:
                    gate_tile.assigned_monsters = [boss_monsters[0].get("name", "Final Boss")]
                    gate_tile.assigned_monster_count = 1
            else:
                gate_tile.is_gate = True
                if boss_monsters:
                    gate_tile.assigned_monsters = [boss_monsters[0].get("name", "Gate Guardian")]
                    gate_tile.assigned_monster_count = 1

    logger.info("Enrichment pass complete: assigned monsters, requirements, and gate/boss tiles.")


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

EVENTS_PER_CHUNK = 10

_COMBAT_NAME_TEMPLATES = [
    "Ambush: {monsters}",
    "Encounter: {monsters}",
    "{monsters} Attack",
    "Hostile {monsters}",
]

_COMBAT_STORY_TEMPLATES = [
    "Faction Patrol: {monsters}",
    "Cult Enforcers: {monsters}",
    "{monsters} (faction scouts)",
]


_GENERIC_PORTRAIT_PREFIXES = ("a puzzle scene in", "a event scene in", "a combat scene in")


def _is_generic_portrait_prompt(prompt: str) -> bool:
    """Return True if the portrait prompt is a generic fallback template."""
    lower = prompt.lower().strip()
    return any(lower.startswith(p) for p in _GENERIC_PORTRAIT_PREFIXES)


def _item_has_attr(item_id: int, attr: str) -> bool:
    """Check if an item in the registry has a given tool attribute."""
    try:
        item = registry.get_item(item_id)
        if item:
            stats = getattr(item, "item_stats", None)
            if stats and getattr(stats, "attribute", None) == attr:
                return True
    except Exception:
        pass
    return False


def _build_combat_event(tile, event_id, env_type, env_name, room_level, monster_db, story_related, faction_name=""):
    """Build a combat event programmatically from tile.assigned_monsters."""
    monster_names = tile.assigned_monsters or ["Unknown Creature"]
    count = len(monster_names)

    if count > 1:
        monsters_str = (
            f"{count} {monster_names[0]}s" if len(set(monster_names)) == 1 else ", ".join(dict.fromkeys(monster_names))
        )
    else:
        monsters_str = monster_names[0]

    if story_related and faction_name:
        template = random.choice(_COMBAT_STORY_TEMPLATES)
    else:
        template = random.choice(_COMBAT_NAME_TEMPLATES)
    name = template.format(monsters=monsters_str)

    # Build monster models from DB by name
    db_by_name = {m.get("name", ""): m for m in monster_db}
    all_monsters = []
    for mn in monster_names:
        m_data = db_by_name.get(mn)
        if m_data:
            all_monsters.append(_monster_dict_to_model(m_data, room_level))
        else:
            from src.models.monster import generate_encounter_monsters

            all_monsters.extend(generate_encounter_monsters(env_type, room_level))

    first_desc = db_by_name.get(monster_names[0], {}).get("description", "")
    description = first_desc or f"A hostile encounter in the {env_name}."

    difficulty = min(5, max(1, room_level + (1 if tile.is_multi_combat else 0)))

    event_data = {
        "id": event_id,
        "type": "combat",
        "name": name,
        "description": description,
        "difficulty": difficulty,
        "portrait_prompt": f"{monsters_str} in a {env_type} environment, fantasy pixel art, combat scene",
        "profile_image": None,
        "time_gate": tile.time_gate,
        "x": tile.position[0],
        "y": tile.position[1],
        "_tile_pos": list(tile.position),
        "monsters": [m.to_dict() for m in all_monsters],
        "room_level": room_level,
    }

    all_item_ids = registry.item_ids()
    if all_item_ids:
        event_data["loot_table"] = _generate_loot_table(all_item_ids, difficulty)
        event_data["money_drop"] = [difficulty * 2, difficulty * 8]

    return event_data


def _phase4a_events(
    layout: dict,
    bible: WorldBible,
    monster_db: list[dict],
    npc_pool: list[dict],
    item_placements: list[dict],
    class_data_list: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Generate events by type + reconcile NPC quest stubs.

    Combat events are built programmatically from assigned monsters.
    Puzzle and event encounters are chunked into groups of 10 for LLM calls.
    """
    room_idx = layout["room_idx"]
    room_id = layout["room_id"]
    maze = layout["maze"]
    env_type = layout["environment"]
    env_name = layout["environment_name"]
    room_level = layout["room_level"]

    story_context = bible.get_cumulative_context(room_id)
    room_story = bible.rooms.get(room_id, RoomBible(environment=env_type)).story_beat
    room_env = {"type": env_type, "name": env_name}

    faction_name = ""
    if bible.story and bible.story.faction:
        faction_name = bible.story.faction.name

    # Collect available databases for LLM context
    all_abilities = []
    all_spells = []
    tool_attrs = ["bludgeon", "cutting", "digging", "climbing"]
    if class_data_list:
        for cd in class_data_list:
            for ab in cd.get("abilities", []) + cd.get("ability_pool", []):
                n = ab["name"] if isinstance(ab, dict) else ab.name
                if n not in all_abilities:
                    all_abilities.append(n)
            for sp in cd.get("spells", []) + cd.get("spell_pool", []):
                n = sp["name"] if isinstance(sp, dict) else sp.name
                if n not in all_spells:
                    all_spells.append(n)

    from src.models.items import Tool

    registry_tools = [
        item.item_stats.attribute
        for item in registry.item_registry.values()
        if isinstance(item, Tool) and item.item_stats.attribute
    ]
    if registry_tools:
        tool_attrs = list(dict.fromkeys(registry_tools))

    event_tiles = maze.get_tiles_by_type("event")
    event_list = []
    event_id_prefix = f"r{room_idx}_"

    # --- Combat: build programmatically, no LLM ---
    combat_tiles = [t for t in event_tiles if t.event_type == "combat"]
    gate_event_id = None
    for tile in combat_tiles:
        idx = len(event_list)
        event_data = _build_combat_event(
            tile,
            f"{event_id_prefix}evt_{idx:03d}",
            env_type,
            env_name,
            room_level,
            monster_db,
            tile.is_story_related,
            faction_name,
        )
        if tile.is_gate:
            event_data["is_gate"] = True
            gate_event_id = event_data["id"]
        if tile.is_climax_boss:
            event_data["is_climax_boss"] = True
        event_list.append(event_data)

    if gate_event_id:
        maze.gate_encounter_id = gate_event_id
        logger.info("Room %d gate encounter: %s", room_idx, gate_event_id)

    # --- Puzzle & Event: chunked LLM generation with summaries ---
    for event_type in ["puzzle", "event"]:
        typed_tiles = [t for t in event_tiles if t.event_type == event_type]
        if not typed_tiles:
            continue

        accumulated_summaries: list[str] = []

        for chunk_start in range(0, len(typed_tiles), EVENTS_PER_CHUNK):
            chunk_tiles = typed_tiles[chunk_start : chunk_start + EVENTS_PER_CHUNK]
            chunk_slots = []
            for t in chunk_tiles:
                slot = {
                    "position": list(t.position),
                    "is_story_related": t.is_story_related,
                    "time_gate": t.time_gate,
                }
                if t.requires_type and t.requires_ref:
                    slot["requires_type"] = t.requires_type
                    slot["requires_ref"] = t.requires_ref
                chunk_slots.append(slot)

            llm_events = []
            try:
                from src.generate.generators.llm_primitives import generate_event_batch

                llm_events = generate_event_batch(
                    room_env,
                    room_story,
                    event_type,
                    chunk_slots,
                    story_context,
                    accumulated_summaries,
                    all_abilities,
                    all_spells,
                    tool_attrs,
                )
            except Exception as e:
                logger.warning(
                    "Room %d %s chunk %d failed: %s", room_idx, event_type, chunk_start // EVENTS_PER_CHUNK, e
                )

            for i, tile in enumerate(chunk_tiles):
                idx = len(event_list)
                llm_data = (
                    llm_events[i]
                    if i < len(llm_events)
                    else _event_fallback(event_type, env_type, room_level, tool_attrs, all_abilities, all_spells)
                )

                event_data = {
                    "id": f"{event_id_prefix}evt_{idx:03d}",
                    "type": event_type,
                    "name": llm_data.get("name", f"Event {idx}"),
                    "description": llm_data.get("description", "Something happens!"),
                    "difficulty": llm_data.get("difficulty", 3),
                    "portrait_prompt": llm_data.get(
                        "portrait_prompt", f"a {event_type} scene in a {env_type}, pixel art"
                    ),
                    "profile_image": None,
                    "time_gate": tile.time_gate,
                    "x": tile.position[0],
                    "y": tile.position[1],
                    "_tile_pos": list(tile.position),
                }

                difficulty = event_data["difficulty"]
                event_data["money_drop"] = [difficulty * 2, difficulty * 6]
                event_data["reward_chance"] = min(0.8, 0.4 + difficulty * 0.1)

                all_item_ids = registry.item_ids()
                correct_tool_attr = None

                if event_type == "puzzle":
                    choices = llm_data.get("choices", [])
                    if not any(c.get("auto_success") for c in choices):
                        choices.append({"text": "Walk away", "auto_success": True})
                    event_data["choices"] = choices
                    event_data["correct_tool"] = llm_data.get("correct_tool") or (
                        tile.requires_ref if tile.requires_type == "tool" else None
                    )
                    event_data["correct_ability"] = llm_data.get("correct_ability") or (
                        tile.requires_ref if tile.requires_type == "ability" else None
                    )
                    correct_tool_attr = event_data.get("correct_tool")

                elif event_type == "event":
                    choices = llm_data.get("choices", [])
                    if not any(c.get("auto_success") for c in choices):
                        choices.append({"text": "Slip away quietly", "auto_success": True})
                    event_data["choices"] = choices
                    event_data["failure_damage_type"] = llm_data.get(
                        "failure_damage_type", random.choice(["health", "stamina"])
                    )
                    event_data["failure_damage_range"] = llm_data.get(
                        "failure_damage_range", [3 + room_level, 8 + room_level * 2]
                    )
                    event_data["correct_ability"] = llm_data.get("correct_ability")
                    event_data["correct_spell"] = llm_data.get("correct_spell")

                if all_item_ids:
                    eligible_ids = all_item_ids
                    if correct_tool_attr:
                        from src.models.items import Tool

                        eligible_ids = [iid for iid in all_item_ids if not _item_has_attr(iid, correct_tool_attr)]
                    if eligible_ids:
                        num = min(random.randint(1, 2), len(eligible_ids))
                        event_data["loot_table"] = [
                            {"item_id": iid, "drop_chance": round(random.uniform(0.15, 0.35), 2)}
                            for iid in random.sample(eligible_ids, num)
                        ]

                # Accumulate summary for next chunk
                summary = llm_data.get("summary") or f"{event_data['name']}: {event_data['description'][:60]}"
                accumulated_summaries.append(summary)

                event_list.append(event_data)

    # Validate tool/ability references against real data
    _validate_puzzle_tools(event_list, registry)
    _validate_puzzle_abilities(event_list, all_abilities)

    # Enforce event choice structure (ensure walk-away exists)
    for e in event_list:
        if e.get("type") == "event":
            choices = e.get("choices", [])
            if not any(c.get("auto_success") for c in choices):
                choices.append({"text": "Slip away quietly", "auto_success": True})
            e["choices"] = choices
        if e.get("type") == "puzzle":
            choices = e.get("choices", [])
            if not any(c.get("auto_success") for c in choices):
                choices.append({"text": "Turn back and find another route", "auto_success": True})
            e["choices"] = choices

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
            base_quest["target_position"] = list(maze.door_position) if maze.door_position else None
            base_quest["escort_npc_id"] = npc["id"]
            base_quest["crosses_room"] = qtype == "follower_next"

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
                "portrait_prompt": npc.get("portrait_prompt", "a hostile NPC, pixel art fantasy"),
            }
            monster_db.append(npc_monster)
            base_quest["target_npc_id"] = npc["id"]

        quest_list.append(base_quest)
        npc["quest_id"] = base_quest["id"]

    story_count = sum(1 for q in quest_list if q.get("is_story_quest"))
    logger.info("Room %d: %d events, %d quests (%d story).", room_idx, len(event_list), len(quest_list), story_count)
    return event_list, quest_list


# ---------------------------------------------------------------------------
# Phase 4B: Dialogue
# ---------------------------------------------------------------------------


def _phase4b_dialogue(
    layout: dict, npc_pool: list[dict], bible: WorldBible, quest_list: list[dict] | None = None
) -> list[dict]:
    """Generate dialogue context and dialogue trees for all NPCs.

    Both steps always run regardless of GAME_MODE — the pipeline generates
    all data; GAME_MODE only controls which data is used at runtime.
    """
    room_idx = layout["room_idx"]
    room_id = layout["room_id"]
    env_type = layout["environment"]
    env_name = layout["environment_name"]
    room_env = {"type": env_type, "name": env_name}
    room_story = bible.rooms.get(room_id, RoomBible(environment=env_type)).story_beat
    story_context = bible.get_cumulative_context(room_id)
    quest_list = quest_list or []

    # Step A: dialogue context (greetings, personality notes, exhausted text)
    try:
        from src.generate.generators.llm_primitives import generate_dialogue_context

        npc_data_for_llm = [
            {
                "npc_name": n["name"],
                "job": n["job"],
                "personality": n["personality"],
                "quest_type": n.get("quest_type"),
                "max_exchanges": n.get("max_exchanges", 5),
            }
            for n in npc_pool
        ]
        dialogue_data = generate_dialogue_context(room_env, room_story, npc_data_for_llm, story_context)
        for i, npc in enumerate(npc_pool):
            if i < len(dialogue_data):
                d = dialogue_data[i]
                npc["opening_greeting"] = d.get("greeting", npc.get("opening_greeting", ""))
                npc["exhausted_dialogue"] = d.get("exhausted_dialogue", "I have nothing more to say.")
                npc["personality_notes"] = d.get("personality_notes", [])
    except Exception as e:
        logger.warning("Room %d dialogue context generation failed: %s", room_idx, e)
        for npc in npc_pool:
            npc.setdefault("exhausted_dialogue", "I have nothing more to say.")
            npc.setdefault("personality_notes", [])

    # Step B: dialogue trees (pre-generated for offline_static; stored for all modes)
    from src.generate.generators.llm_primitives import generate_dialogue_tree

    for npc in npc_pool:
        try:
            quest_ctx = None
            if npc.get("quest_id"):
                quest_obj = next((q for q in quest_list if q["id"] == npc["quest_id"]), None)
                if quest_obj:
                    quest_ctx = {
                        "quest_id": quest_obj["id"],
                        "quest_type": quest_obj["type"],
                        "title": quest_obj.get("title", ""),
                        "description": quest_obj.get("description", ""),
                        "success_dialogue": quest_obj.get("success_dialogue", ""),
                        "failure_dialogue": quest_obj.get("failure_dialogue", ""),
                        "room_story": room_story,
                        "story_context": story_context[:1000],
                    }
            tree = generate_dialogue_tree(npc, quest_ctx)
            if "error" in tree:
                continue
            if "incomplete" in tree:
                inc = tree["incomplete"]
                if isinstance(inc, dict) and "nodes" in inc:
                    npc["dialogue_tree"] = inc
                    npc["dialogue_tree_incomplete"] = inc
                comp = tree.get("complete_success")
                if isinstance(comp, dict) and "nodes" in comp:
                    npc["dialogue_tree_complete"] = comp
                fail = tree.get("complete_failure")
                if isinstance(fail, dict) and "nodes" in fail:
                    npc["dialogue_tree_failed"] = fail
            elif "nodes" in tree:
                npc["dialogue_tree"] = tree
        except Exception as e:
            logger.warning("Room %d NPC %s dialogue tree failed: %s", room_idx, npc.get("name"), e)

    logger.info("Room %d: Dialogue generated for %d NPCs.", room_idx, len(npc_pool))
    return npc_pool


# ---------------------------------------------------------------------------
# Phase 5: Validation
# ---------------------------------------------------------------------------


def _phase5_validate(bible: WorldBible, room_results: list[dict], story: OverarchingStory) -> ValidationReport:
    """Run structural validation checks."""
    report = ValidationReport()
    from src.generate.world_editor import cross_validate, editor_coherence_check, gameplay_audit

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
                report.add_major(issue["message"], entity_id=issue.get("entity_id", ""), phase="gameplay_audit")
            else:
                report.add_warning(issue["message"], entity_id=issue.get("entity_id", ""), phase="gameplay_audit")
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
            generate_game_over_text,
            generate_room_intro,
            generate_story_synopsis,
            generate_victory_text,
        )

        narrative_data["synopsis"] = generate_story_synopsis(bible)
        narrative_data["game_over"] = generate_game_over_text(bible, "the hero", "adventurer")
        narrative_data["victory"] = generate_victory_text(bible, "the hero", "adventurer")
        for rr in room_results:
            rid = rr["room_id"]
            narrative_data[f"room_intro_{rid}"] = generate_room_intro(
                bible, rid, rr["environment_name"], rr["environment"]
            )
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


def _phase7_portraits(
    room_results: list[dict],
    class_data_list: list[dict],
    bible: WorldBible,
    music_prompts: dict[str, str] | None = None,
    sfx_prompts: dict[str, dict] | None = None,
):
    """Generate portrait images, music tracks, and SFX in a single event loop.

    Phase A (sync): build all entity databases and prompt-enrich them.
    Phase B (async): one asyncio.run() runs portraits + music + SFX concurrently
                     via asyncio.gather, so fal_client never sees a closed loop.

    Returns (portraits_generated, player_portrait_path, gameover_path, victory_path, music_paths, sfx_paths).
    """
    import asyncio as _asyncio

    from src.generate.generators.llm_primitives import generate_player_image_description
    from src.generate.image_client import (
        generate_and_save_image,
        generate_player_portrait,
        generate_portraits_parallel_async,
    )
    from src.generate.music_client import generate_all_music_async
    from src.generate.sfx_client import generate_all_sfx_async
    from src.generate.summary_agent import (
        build_class_portrait_prompt,
        build_event_portrait_prompt,
        build_game_over_portrait_prompt,
        build_item_portrait_prompt,
        build_monster_portrait_prompt,
        build_npc_portrait_prompt,
        build_room_portrait_prompt,
    )

    portraits_generated = False
    player_portrait_path = None
    gameover_path = None
    music_paths: dict[str, str] = {}
    sfx_paths: dict[str, str] = {}

    # -----------------------------------------------------------------------
    # Phase A — sync: build all entity databases and enrich prompts
    # -----------------------------------------------------------------------
    npc_batches: list[tuple[dict, str, str]] = []
    event_batches: list[tuple[dict, str, str]] = []

    for rr in tqdm(room_results, desc="  Room Portraits", unit="room", leave=True):
        rid = rr["room_id"]
        npc_db = {str(n["id"]): n for n in rr["npc_pool"]}
        for nd in npc_db.values():
            if not nd.get("portrait_prompt"):
                nd["portrait_prompt"] = build_npc_portrait_prompt(nd, bible, room_id=rid)
        npc_batches.append((npc_db, "data/portraits/npcs", "npc_"))

        event_db = {e["id"]: e for e in rr["event_list"]}
        for ed in event_db.values():
            if not ed.get("portrait_prompt") or _is_generic_portrait_prompt(ed["portrait_prompt"]):
                ed["portrait_prompt"] = build_event_portrait_prompt(ed, bible, room_id=rid)
        event_batches.append((event_db, "data/portraits/events", "evt_"))

    # Monster portraits (deduplicate by name across rooms)
    monster_batches: list[tuple[dict, str, str]] = []
    seen_monster_names: set[str] = set()
    monster_portrait_db: dict[str, dict] = {}
    for rr in room_results:
        rid = rr["room_id"]
        for m in rr.get("monster_db", []):
            name = m.get("name", "")
            if name and name not in seen_monster_names:
                seen_monster_names.add(name)
                key = name.replace(" ", "_").lower()
                prompt = m.get("portrait_prompt") or build_monster_portrait_prompt(m, bible, room_id=rid)
                monster_portrait_db[key] = {
                    "portrait_prompt": prompt,
                    "name": name,
                    "_source": m,
                }
    if monster_portrait_db:
        monster_batches.append((monster_portrait_db, "data/portraits/monsters", "mon_"))

    # Item portraits (deduplicate by name across rooms)
    item_batches: list[tuple[dict, str, str]] = []
    item_portrait_db: dict[str, dict] = {}
    seen_item_names: set[str] = set()
    for rr in room_results:
        for item in rr.get("item_placements", []):
            iname = item.get("name", "")
            if iname and iname not in seen_item_names:
                seen_item_names.add(iname)
                ikey = iname.replace(" ", "_").lower()
                prompt = item.get("portrait_prompt") or build_item_portrait_prompt(item, bible)
                item_portrait_db[ikey] = {
                    "portrait_prompt": prompt,
                    "name": iname,
                    "_source": item,
                }
    if item_portrait_db:
        item_batches.append((item_portrait_db, "data/portraits/items", "item_"))

    class_portrait_db: dict = {}
    for i, cd in enumerate(class_data_list):
        prompt = cd.get("portrait_prompt") or build_class_portrait_prompt(cd, bible)
        class_portrait_db[str(i)] = {"portrait_prompt": prompt, "name": cd.get("name", "")}

    # -----------------------------------------------------------------------
    # Phase B — async: single event loop covers portraits + music + SFX
    # -----------------------------------------------------------------------
    async def _run_music():
        if music_prompts:
            return await generate_all_music_async(music_prompts)
        return {}

    async def _run_sfx():
        if sfx_prompts:
            return await generate_all_sfx_async(sfx_prompts)
        return {}

    async def _run_all_async():
        tasks = []
        # portrait tasks — one coroutine per room per entity type
        for npc_db, save_dir, prefix in npc_batches:
            tasks.append(generate_portraits_parallel_async(npc_db, save_dir, prefix))
        for event_db, save_dir, prefix in event_batches:
            tasks.append(generate_portraits_parallel_async(event_db, save_dir, prefix))
        tasks.append(generate_portraits_parallel_async(class_portrait_db, "data/portraits/classes", "class_"))
        for mon_db, save_dir, prefix in monster_batches:
            tasks.append(generate_portraits_parallel_async(mon_db, save_dir, prefix))
        for item_db, save_dir, prefix in item_batches:
            tasks.append(generate_portraits_parallel_async(item_db, save_dir, prefix))
        # audio tasks (music + SFX already run correctly together)
        music_idx = len(tasks)
        tasks.append(_run_music())
        sfx_idx = len(tasks)
        tasks.append(_run_sfx())

        results = await _asyncio.gather(*tasks, return_exceptions=True)

        # log any portrait failures
        for i, r in enumerate(results[:music_idx]):
            if isinstance(r, Exception):
                logger.warning("Portrait batch %d failed: %s", i, r)

        m = results[music_idx] if not isinstance(results[music_idx], Exception) else {}
        s = results[sfx_idx] if not isinstance(results[sfx_idx], Exception) else {}
        if isinstance(results[music_idx], Exception):
            logger.warning("Music generation failed: %s", results[music_idx])
        if isinstance(results[sfx_idx], Exception):
            logger.warning("SFX generation failed: %s", results[sfx_idx])
        return m, s

    try:
        music_paths, sfx_paths = _asyncio.run(_run_all_async())
        portraits_generated = True
        logger.info("Portraits generated successfully.")
        if music_paths:
            logger.info("Music generation complete: %d tracks.", len(music_paths))
        if sfx_paths:
            logger.info("SFX generation complete: %d effects.", len(sfx_paths))
    except Exception as e:
        logger.warning("Phase 7 async generation failed: %s", e)

    # Write back class portrait paths
    for i, cd in enumerate(class_data_list):
        cd["portrait_path"] = class_portrait_db[str(i)].get("profile_image")

    # Write back monster portrait paths to monster_db entries
    monster_name_to_image: dict[str, str] = {}
    for key, entry in monster_portrait_db.items():
        img = entry.get("profile_image")
        if img:
            monster_name_to_image[entry["name"]] = img
            src_m = entry.get("_source")
            if src_m:
                src_m["profile_image"] = img

    # Propagate monster portraits into combat event monster lists
    for rr in room_results:
        for evt in rr["event_list"]:
            if evt.get("type") != "combat":
                continue
            for m_dict in evt.get("monsters", []):
                mname = m_dict.get("name", "")
                if mname and mname in monster_name_to_image and not m_dict.get("profile_image"):
                    m_dict["profile_image"] = monster_name_to_image[mname]

    # Write back item portrait paths to item_placements entries
    item_name_to_image: dict[str, str] = {}
    for key, entry in item_portrait_db.items():
        img = entry.get("profile_image")
        if img:
            item_name_to_image[entry["name"]] = img
            src_item = entry.get("_source")
            if src_item:
                src_item["profile_image"] = img

    # Quest portrait reuse: link quest portraits to event/NPC portraits
    for rr in room_results:
        event_portraits = {e["id"]: e.get("profile_image") for e in rr["event_list"]}
        npc_portraits = {str(n["id"]): n.get("profile_image") for n in rr["npc_pool"]}
        for q in rr.get("quest_list", []):
            if q.get("profile_image"):
                continue
            target_event = q.get("target_event_id")
            if target_event and event_portraits.get(target_event):
                q["profile_image"] = event_portraits[target_event]
            elif q.get("escort_npc_id") and npc_portraits.get(str(q["escort_npc_id"])):
                q["profile_image"] = npc_portraits[str(q["escort_npc_id"])]
            elif q.get("target_npc_id") and npc_portraits.get(str(q["target_npc_id"])):
                q["profile_image"] = npc_portraits[str(q["target_npc_id"])]
            elif q.get("giver_npc_id") and npc_portraits.get(str(q["giver_npc_id"])):
                q["profile_image"] = npc_portraits[str(q["giver_npc_id"])]

    # -----------------------------------------------------------------------
    # Sync-only portraits (player, room environments, game-over, victory)
    # -----------------------------------------------------------------------
    try:
        player_prompt = generate_player_image_description()
    except Exception:
        player_prompt = "a young adventurer, pixel art, fantasy portrait"
    player_portrait_path = generate_player_portrait(player_prompt)

    for rr in room_results:
        portrait_path = os.path.join("data/portraits", f"environment_{rr['room_idx']}.png")
        room_prompt = build_room_portrait_prompt(rr["room_id"], bible)
        generate_and_save_image(room_prompt, portrait_path)
        rr["environment_portrait"] = portrait_path

    gameover_path = os.path.join("data/portraits", "game_over.png")
    generate_and_save_image(build_game_over_portrait_prompt(bible), gameover_path)

    victory_path = os.path.join("data/portraits", "victory.png")
    victory_prompt = (
        "A triumphant hero standing victorious, golden light, fantasy pixel art, celebration scene, epic achievement"
    )
    if bible.story and bible.story.synopsis:
        victory_prompt = (
            f"Victory scene: {bible.story.synopsis[:100]}, triumphant hero, golden light, fantasy pixel art"
        )
    generate_and_save_image(victory_prompt, victory_path)

    # Start screen / cover portrait
    start_portrait_path = os.path.join("data/portraits", "start_screen.png")
    start_prompt = "A dark fantasy world, epic landscape, mysterious castle silhouette, pixel art, game cover art"
    if bible.story:
        parts = [bible.story.title]
        if bible.story.synopsis:
            parts.append(bible.story.synopsis[:120])
        if bible.story.faction:
            parts.append(f"faction: {bible.story.faction.name}")
        start_prompt = f"{', '.join(parts)}, dark fantasy pixel art, epic game cover"
    generate_and_save_image(start_prompt, start_portrait_path)

    return (
        portraits_generated,
        player_portrait_path,
        gameover_path,
        victory_path,
        start_portrait_path,
        music_paths,
        sfx_paths,
    )


# ---------------------------------------------------------------------------
# Phase 8: Write Files & Manifest
# ---------------------------------------------------------------------------


def _flush_entity_db(room_results: list[dict], key: str, path: str):
    """Collect entities from all rooms by key and write to a global DB file."""
    all_entities = [e for rr in room_results for e in rr.get(key, [])]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(all_entities, f, indent=2)


def _write_room_files(layout: dict, npc_pool: list, event_list: list, quest_list: list, item_placements: list):
    """Write per-room JSON files."""
    room_dir = layout["room_dir"]
    maze = layout["maze"]
    player_start = layout["player_start"]

    npc_positions = {}
    for npc in npc_pool:
        npc_positions[str(npc["id"])] = [npc.get("x", 0), npc.get("y", 0)]

    event_position_map = []
    for e in event_list:
        if "x" in e and "y" in e:
            event_position_map.append(
                {
                    "x": e["x"],
                    "y": e["y"],
                    "event_id": e["id"],
                }
            )

    maze.save_to_json(
        os.path.join(room_dir, "maze.json"),
        extra={
            "npc_positions": npc_positions,
            "player_start": list(player_start),
            "item_placements": item_placements,
            "event_positions": event_position_map,
            "quest_ids": [q["id"] for q in quest_list],
        },
    )
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
    import src.generate.backends.llm_api as _llm_api_mod
    import src.generate.backends.llm_local as _llm_local_mod
    import src.generate.image_client as _img_mod
    import src.generate.music_client as _music_mod
    import src.generate.sfx_client as _sfx_mod
    from config import IMAGE_BACKEND, LLM_BACKEND, MUSIC_BACKEND
    from src.generate.generation_stats import GenerationStats

    stats = GenerationStats(
        llm_backend=LLM_BACKEND,
        image_backend=IMAGE_BACKEND,
        music_backend=MUSIC_BACKEND,
    )
    _llm_api_mod.set_stats(stats)
    _llm_local_mod.set_stats(stats)
    _img_mod.set_stats(stats)
    _music_mod.set_stats(stats)
    _sfx_mod.set_stats(stats)

    logger.info("=== MazeWorld World Generator ===")
    logger.info("Seed: %s, Mode: %s, Rooms: %d", WORLD_SEED, GAME_MODE, NUM_ROOMS)

    if WORLD_SEED != -1:
        random.seed(WORLD_SEED)

    registry.load()
    num_rooms = NUM_ROOMS
    story_seed = STORY_SEED or _FALLBACK_STORY_SEED

    phase_bar = tqdm(total=len(PHASE_NAMES), desc="World Generation", unit="phase", position=0, leave=True)

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

    # --- Phase 2: Layouts + Music/SFX Prompts ---
    advance(PHASE_NAMES[2])
    layouts, music_prompts, sfx_prompts = _phase2_layouts(environments, bible, story)
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
        room_results.append(
            {
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
            }
        )
    phase_bar.update(1)

    # --- Enrichment: assign real DB objects to TileMeta ---
    _enrich_tile_meta(layouts, room_results, class_data_list)

    # --- Phase 4: Events, Quests, Dialogue (per room) ---
    advance(PHASE_NAMES[5])
    for rr in tqdm(room_results, desc="  Content", unit="room", position=1, leave=True):
        layout = next(l for l in layouts if l["room_id"] == rr["room_id"])
        event_list, quest_list = _phase4a_events(
            layout, bible, rr["monster_db"], rr["npc_pool"], rr["item_placements"], class_data_list=class_data_list
        )
        rr["event_list"] = event_list
        rr["quest_list"] = quest_list
        rr["npc_pool"] = _phase4b_dialogue(layout, rr["npc_pool"], bible, quest_list=rr["quest_list"])
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

    # --- Phase 7: Portraits + Music + SFX ---
    advance(PHASE_NAMES[8])
    (
        portraits_generated,
        player_portrait_path,
        gameover_path,
        victory_path,
        start_portrait_path,
        music_paths,
        sfx_paths,
    ) = _phase7_portraits(room_results, class_data_list, bible, music_prompts=music_prompts, sfx_prompts=sfx_prompts)

    # Rewrite room files with updated profile_image paths from portrait generation
    for rr in room_results:
        layout = next(l for l in layouts if l["room_id"] == rr["room_id"])
        _write_room_files(layout, rr["npc_pool"], rr["event_list"], rr["quest_list"], rr["item_placements"])
    logger.info("Room files rewritten with portrait paths.")
    phase_bar.update(1)

    # --- Phase 8: Manifest ---
    advance(PHASE_NAMES[9])

    os.makedirs(os.path.dirname(STORY_PATH), exist_ok=True)
    with open(STORY_PATH, "w") as f:
        json.dump(story.model_dump(), f, indent=2)
    os.makedirs(os.path.dirname(CLASS_PATH), exist_ok=True)
    with open(CLASS_PATH, "w") as f:
        json.dump(class_data_list, f, indent=2)

    # Flush room-collected entities to global DBs (with portrait paths from phase 7)
    _flush_entity_db(room_results, "npc_pool", os.path.join(DATA_DIR, "npcs", "npcs.json"))
    _flush_entity_db(room_results, "event_list", os.path.join(DATA_DIR, "events", "events.json"))
    _flush_entity_db(room_results, "quest_list", os.path.join(DATA_DIR, "quests", "quests.json"))

    # Rebuild monster name-to-image map from room_results
    monster_name_to_image = {}
    for rr in room_results:
        for m in rr.get("monster_db", []):
            img = m.get("profile_image")
            if img and m.get("name"):
                monster_name_to_image[m["name"]] = img

    monster_path = os.path.join(DATA_DIR, "monsters", "monsters.json")
    if os.path.exists(monster_path):
        monster_db_global = load_json_data(monster_path)
        for mid, mdata in monster_db_global.items():
            img = monster_name_to_image.get(mdata.get("name", ""))
            if img:
                mdata["profile_image"] = img
        with open(monster_path, "w") as f:
            json.dump(monster_db_global, f, indent=2)

    # Rebuild item id-to-image map from item_placements
    item_id_to_image = {}
    for rr in room_results:
        for item in rr.get("item_placements", []):
            img = item.get("profile_image")
            item_id = item.get("item_id")
            if img and item_id is not None:
                item_id_to_image[str(item_id)] = img

    for rr in room_results:
        if rr.get("generated_items"):
            for iid, idata in rr["generated_items"].items():
                img = item_id_to_image.get(iid)
                if img:
                    idata["profile_image"] = img

    all_items = {}
    for rr in room_results:
        if rr.get("generated_items"):
            all_items.update(rr["generated_items"])
    if all_items:
        os.makedirs(os.path.dirname(ITEM_ITEMS_PATH), exist_ok=True)
        with open(ITEM_ITEMS_PATH, "w") as f:
            json.dump(all_items, f, indent=2)

    stats.finish()

    stats_path = os.path.join(DATA_DIR, "generation_stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats.to_dict(), f, indent=2)
    logger.info("Generation stats written to %s", stats_path)

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
        "victory_portrait": victory_path,
        "start_portrait": start_portrait_path,
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
                "environment_portrait": rr.get("environment_portrait"),
            }
            for rr in room_results
        ],
        "validation_report": report.to_dict(),
        "generation_stats": stats.to_dict(),
        "music": music_paths,
        "sfx": sfx_paths,
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    phase_bar.update(1)

    # --- Phase 9: Player Guide (optional) ---
    from config import GENERATE_GUIDE

    if GENERATE_GUIDE:
        advance(PHASE_NAMES[10])
        try:
            from src.generate.guide_builder import build_guide

            build_guide(data_dir=DATA_DIR, generate_pdf=True)
        except Exception as e:
            logger.warning("Guide generation failed: %s", e)
        phase_bar.update(1)

    phase_bar.close()

    logger.info("=== Generation Complete (%d rooms) ===", num_rooms)
    for rr in room_results:
        logger.info(
            "  Room %d: %s (%s) — %d NPCs, %d events, %d quests",
            rr["room_idx"],
            rr["environment"],
            rr["environment_name"],
            len(rr["npc_pool"]),
            len(rr["event_list"]),
            len(rr["quest_list"]),
        )
    logger.info("  Manifest: %s", MANIFEST_PATH)
    logger.info("  World Bible: %s", BIBLE_PATH)
    stats.log_summary(logger)
