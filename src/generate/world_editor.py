"""World Editor — builds the WorldBible from all generated content pools.

Cross-validates references between quests, NPCs, items, and encounters.
Produces a ``WorldBible`` model that is serialised to ``data/world_bible.json``.

The Bible is built **incrementally** during generation: after each room's
content is generated, ``add_room_to_bible()`` appends that room's entities.
Multi-room worlds accumulate lore so that later rooms can reference earlier
content for narrative coherence.
"""

import json
import logging
import os

from src.models.story import OverarchingStory
from src.models.world_bible import EntityRef, RoomBible, WorldBible

logger = logging.getLogger(__name__)

WORLD_BIBLE_PATH = os.path.join("data", "world_bible.json")


def create_world_bible(story: OverarchingStory) -> WorldBible:
    """Create an empty WorldBible seeded with the overarching story."""
    return WorldBible(story=story)


def add_room_to_bible(
    bible: WorldBible,
    *,
    room_id: str,
    room_level: int,
    maze_environment: str,
    story_beat: str = "",
    npc_pool: list[dict] | None = None,
    event_list: list[dict] | None = None,
    quest_list: list[dict] | None = None,
    item_placements: list[dict] | None = None,
    gate_encounter_id: str = "",
) -> None:
    """Append a room's entities to the WorldBible (mutates *bible* in place).

    This is the incremental counterpart to ``build_world_bible()``.  It is
    called once per room *during* generation so that subsequent rooms can
    read the Bible for lore context.
    """
    npc_pool = npc_pool or []
    event_list = event_list or []
    quest_list = quest_list or []
    item_placements = item_placements or []

    room = RoomBible(
        environment=maze_environment,
        level=room_level,
        story_beat=story_beat,
        gate_encounter_id=gate_encounter_id,
    )

    # --- Index NPCs ---
    active_npcs = [n for n in npc_pool if n.get("selected")]
    for npc in active_npcs:
        npc_id_str = str(npc["id"])
        room.npcs.append(npc_id_str)
        bible.entity_index[f"npc:{npc_id_str}"] = EntityRef(
            entity_type="npc", room_id=room_id, entity_id=npc_id_str,
        )

    # --- Index items ---
    seen_items: set[int] = set()
    for placement in item_placements:
        item_id = placement["item_id"]
        if item_id not in seen_items:
            item_id_str = str(item_id)
            room.items.append(item_id_str)
            bible.entity_index[f"item:{item_id_str}"] = EntityRef(
                entity_type="item", room_id=room_id, entity_id=item_id_str,
            )
            seen_items.add(item_id)

    # --- Index events (encounters) ---
    for event in event_list:
        eid = event["id"]
        room.encounters.append(eid)
        bible.entity_index[f"encounter:{eid}"] = EntityRef(
            entity_type="encounter", room_id=room_id, entity_id=eid,
        )
        # Index monsters within combat events
        if event.get("type") == "combat":
            for midx, monster in enumerate(event.get("monsters", [])):
                monster_id = f"{eid}_m{midx}"
                room.monsters.append(monster_id)
                bible.entity_index[f"monster:{monster_id}"] = EntityRef(
                    entity_type="monster", room_id=room_id, entity_id=monster_id,
                )

    # --- Index quests ---
    for quest in quest_list:
        qid = quest["id"]
        room.quests.append(qid)
        bible.entity_index[f"quest:{qid}"] = EntityRef(
            entity_type="quest", room_id=room_id, entity_id=qid,
        )

    bible.rooms[room_id] = room


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

    This is the *legacy* single-shot builder kept for backward compat.
    New code should use ``create_world_bible()`` + ``add_room_to_bible()``.
    """
    bible = create_world_bible(story)

    beat_text = ""
    if story.beats:
        beat_text = story.beats[0].summary

    add_room_to_bible(
        bible,
        room_id="room_0",
        room_level=1,
        maze_environment=maze_environment,
        story_beat=beat_text,
        npc_pool=npc_pool,
        event_list=event_list,
        quest_list=quest_list,
        item_placements=item_placements,
    )
    return bible


def get_bible_context(bible: WorldBible) -> dict:
    """Extract a serialisable lore-context dict for passing to LLM generators.

    Generators read this to produce narratively connected content.
    """
    rooms_summary = []
    for rid, room in bible.rooms.items():
        rooms_summary.append({
            "room_id": rid,
            "environment": room.environment,
            "level": room.level,
            "story_beat": room.story_beat,
            "npc_count": len(room.npcs),
            "item_count": len(room.items),
            "encounter_count": len(room.encounters),
            "quest_count": len(room.quests),
            "monster_count": len(room.monsters),
        })

    story = bible.story
    return {
        "story_title": story.title,
        "story_synopsis": story.synopsis,
        "faction_name": story.faction.name if story.faction else "",
        "faction_description": story.faction.description if story.faction else "",
        "climax": story.climax,
        "final_boss": story.final_boss_name,
        "rooms": rooms_summary,
        "total_npcs": sum(len(r.npcs) for r in bible.rooms.values()),
        "total_quests": sum(len(r.quests) for r in bible.rooms.values()),
    }


def cross_validate(bible: WorldBible, npc_pool: list[dict],
                   event_list: list[dict], quest_list: list[dict],
                   item_placements: list[dict]) -> list[str]:
    """Run cross-content validation checks. Returns list of issues found."""
    from src.generate.checker import check_quest_references

    npc_ids = {str(n["id"]) for n in npc_pool if n.get("selected")}
    event_ids = {e["id"] for e in event_list}
    item_ids = {p["item_id"] for p in item_placements}

    issues: list[str] = []

    # --- Quest reference validation ---
    for quest in quest_list:
        normalized = dict(quest)
        for key in ("giver_npc_id", "escort_npc_id", "target_npc_id"):
            if key in normalized:
                normalized[key] = str(normalized[key])

        issues.extend(check_quest_references(
            normalized,
            npc_ids=npc_ids,
            item_ids=item_ids,
            event_ids=event_ids,
            label=f"Quest {quest['id']}",
        ))

    # --- Gate encounter per non-final room ---
    room_ids = sorted(bible.rooms.keys())
    for rid in room_ids[:-1] if len(room_ids) > 1 else []:
        room = bible.rooms[rid]
        if not room.gate_encounter_id:
            issues.append(f"{rid}: missing gate encounter for non-final room")

    # --- Story quest presence per room ---
    story_quests_by_room: dict[str, int] = {rid: 0 for rid in room_ids}
    for quest in quest_list:
        if quest.get("is_story_quest"):
            qroom = quest.get("room_id", "room_0")
            if qroom in story_quests_by_room:
                story_quests_by_room[qroom] += 1
    for rid, count in story_quests_by_room.items():
        if count == 0:
            issues.append(f"{rid}: no story quest present")

    # --- NPC presence per room ---
    for rid, room in bible.rooms.items():
        if len(room.npcs) == 0:
            issues.append(f"{rid}: no active NPCs")

    # --- Encounter presence per room ---
    for rid, room in bible.rooms.items():
        if len(room.encounters) == 0:
            issues.append(f"{rid}: no encounters")

    return issues


def write_world_bible(bible: WorldBible, path: str = WORLD_BIBLE_PATH) -> str:
    """Serialise the WorldBible to JSON. Returns the path written."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(bible.model_dump(), f, indent=2)
    logger.info("WorldBible written to %s (%d entities indexed).",
                path, len(bible.entity_index))
    return path
