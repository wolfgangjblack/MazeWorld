"""World Editor — builds the WorldBible from all generated content pools.

Cross-validates references between quests, NPCs, items, and encounters.
Produces a ``WorldBible`` model that is serialised to ``data/world_bible.json``.
"""

import json
import logging
import os
from typing import Optional

from src.models.story import OverarchingStory
from src.models.world_bible import EntityRef, RoomBible, WorldBible

logger = logging.getLogger(__name__)

WORLD_BIBLE_PATH = os.path.join("data", "world_bible.json")


def build_world_bible(
    story: OverarchingStory,
    npc_pool: list[dict],
    event_list: list[dict],
    quest_list: list[dict],
    item_placements: list[dict],
    event_position_map: list[dict],
    maze_environment: str,
) -> WorldBible:
    """Assemble the WorldBible cross-reference index from generated pools.

    Parameters
    ----------
    story : OverarchingStory
        The generated overarching story.
    npc_pool : list[dict]
        All generated NPCs (both selected and unselected).
    event_list : list[dict]
        Generated events (combat/puzzle/event).
    quest_list : list[dict]
        Generated quests.
    item_placements : list[dict]
        Items placed on the map (x, y, item_id).
    event_position_map : list[dict]
        Event positions (x, y, event_id).
    maze_environment : str
        The environment type of the maze.

    Returns
    -------
    WorldBible
    """
    bible = WorldBible(story=story)
    entity_index: dict[str, EntityRef] = {}

    # Single-room world uses "room_0"
    room_id = "room_0"
    room = RoomBible(environment=maze_environment, level=1)

    if story.beats:
        room.story_beat = story.beats[0].summary

    # --- Index NPCs ---
    active_npcs = [n for n in npc_pool if n.get("selected")]
    for npc in active_npcs:
        npc_id_str = str(npc["id"])
        room.npcs.append(npc_id_str)
        entity_index[f"npc:{npc_id_str}"] = EntityRef(
            entity_type="npc",
            room_id=room_id,
            entity_id=npc_id_str,
        )

    # --- Index items ---
    seen_items: set[int] = set()
    for placement in item_placements:
        item_id = placement["item_id"]
        if item_id not in seen_items:
            item_id_str = str(item_id)
            room.items.append(item_id_str)
            entity_index[f"item:{item_id_str}"] = EntityRef(
                entity_type="item",
                room_id=room_id,
                entity_id=item_id_str,
            )
            seen_items.add(item_id)

    # --- Index events (encounters) ---
    for event in event_list:
        eid = event["id"]
        room.encounters.append(eid)
        entity_index[f"encounter:{eid}"] = EntityRef(
            entity_type="encounter",
            room_id=room_id,
            entity_id=eid,
        )

        # Index monsters within combat events
        if event.get("type") == "combat":
            for midx, monster in enumerate(event.get("monsters", [])):
                monster_id = f"{eid}_m{midx}"
                room.monsters.append(monster_id)
                entity_index[f"monster:{monster_id}"] = EntityRef(
                    entity_type="monster",
                    room_id=room_id,
                    entity_id=monster_id,
                )

    # --- Index quests ---
    for quest in quest_list:
        qid = quest["id"]
        room.quests.append(qid)
        entity_index[f"quest:{qid}"] = EntityRef(
            entity_type="quest",
            room_id=room_id,
            entity_id=qid,
        )

    bible.rooms[room_id] = room
    bible.entity_index = entity_index

    return bible


def cross_validate(bible: WorldBible, npc_pool: list[dict],
                   event_list: list[dict], quest_list: list[dict],
                   item_placements: list[dict]) -> list[str]:
    """Run cross-content validation checks. Returns list of issues found."""
    issues: list[str] = []
    npc_ids = {str(n["id"]) for n in npc_pool if n.get("selected")}
    event_ids = {e["id"] for e in event_list}
    item_ids = {p["item_id"] for p in item_placements}

    for quest in quest_list:
        qid = quest["id"]
        # Giver NPC exists
        if str(quest.get("giver_npc_id", "")) not in npc_ids:
            issues.append(f"Quest {qid}: giver NPC {quest.get('giver_npc_id')} missing")

        qtype = quest.get("type", "")
        if qtype == "fetch":
            for ti in quest.get("target_items", []):
                if ti.get("item_id") not in item_ids:
                    issues.append(f"Quest {qid}: fetch item {ti.get('item_id')} not on map")
        elif qtype == "combat":
            if quest.get("target_event_id") not in event_ids:
                issues.append(f"Quest {qid}: target event {quest.get('target_event_id')} missing")
        elif qtype == "escort":
            if str(quest.get("escort_npc_id", "")) not in npc_ids:
                issues.append(f"Quest {qid}: escort NPC {quest.get('escort_npc_id')} missing")
        elif qtype == "delivery":
            if quest.get("delivery_item_id") not in item_ids:
                issues.append(f"Quest {qid}: delivery item {quest.get('delivery_item_id')} missing")
            if str(quest.get("target_npc_id", "")) not in npc_ids:
                issues.append(f"Quest {qid}: target NPC {quest.get('target_npc_id')} missing")

    return issues


def write_world_bible(bible: WorldBible, path: str = WORLD_BIBLE_PATH) -> str:
    """Serialise the WorldBible to JSON. Returns the path written."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(bible.model_dump(), f, indent=2)
    logger.info("WorldBible written to %s (%d entities indexed).",
                path, len(bible.entity_index))
    return path
