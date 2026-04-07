"""World Editor — builds the WorldBible from all generated content pools.

Cross-validates references between quests, NPCs, items, and encounters.
Produces a ``WorldBible`` model that is serialised to ``data/world_bible.json``.
"""

import json
import logging
import os

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
    from src.generate.checker import check_quest_references

    npc_ids = {str(n["id"]) for n in npc_pool if n.get("selected")}
    event_ids = {e["id"] for e in event_list}
    item_ids = {p["item_id"] for p in item_placements}

    issues: list[str] = []
    for quest in quest_list:
        # Normalize NPC ID fields to strings for comparison
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

    return issues


def write_world_bible(bible: WorldBible, path: str = WORLD_BIBLE_PATH) -> str:
    """Serialise the WorldBible to JSON. Returns the path written."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(bible.model_dump(), f, indent=2)
    logger.info("WorldBible written to %s (%d entities indexed).",
                path, len(bible.entity_index))
    return path


# ---------------------------------------------------------------------------
# Gameplay Agent — coherence audit (Step 4b)
# ---------------------------------------------------------------------------


def gameplay_audit(
    bible: WorldBible,
    npc_pool: list[dict],
    event_list: list[dict],
    quest_list: list[dict],
    item_placements: list[dict],
) -> list[dict]:
    """Read the full Bible + all generated content and confirm coherence.

    Checks:
    - Overarching story + entities are coherent
    - Items, monsters, quests, multi-step quests make narrative sense
    - Quest chains are completable and not circular
    - Story quests exist and reference the faction
    - Kill quests point to existing combat events
    - Fetch quests reference items on the map
    - Time-gated encounters are a reasonable fraction (~20%)

    Returns a list of issue dicts for the manifest:
    ``[{"severity": "warning"|"error", "message": "...", "entity_id": "..."}]``
    """
    issues: list[dict] = []

    npc_ids = {n["id"] for n in npc_pool if n.get("selected")}
    item_ids_on_map = {p["item_id"] for p in item_placements}
    quest_ids = {q["id"] for q in quest_list}
    combat_event_ids = {e["id"] for e in event_list if e.get("type") == "combat"}

    # --- Story coherence ---
    if not bible.story.title:
        issues.append({
            "severity": "warning",
            "message": "Overarching story has no title",
            "entity_id": "",
        })

    faction = bible.story.faction
    if not faction:
        issues.append({
            "severity": "warning",
            "message": "No faction defined in overarching story",
            "entity_id": "",
        })

    story_quests = [q for q in quest_list if q.get("is_story_quest")]
    if not story_quests:
        issues.append({
            "severity": "warning",
            "message": "No story quests found — story progression may be broken",
            "entity_id": "",
        })

    # --- Quest reference integrity ---
    for quest in quest_list:
        qid = quest.get("id", "?")
        qtype = quest.get("type", "")

        giver = quest.get("giver_npc_id")
        if giver not in npc_ids:
            issues.append({
                "severity": "error",
                "message": f"Quest giver NPC {giver} does not exist",
                "entity_id": qid,
            })

        if qtype == "fetch":
            for ti in quest.get("target_items", []):
                if ti.get("item_id") not in item_ids_on_map:
                    issues.append({
                        "severity": "error",
                        "message": f"Fetch item {ti.get('item_id')} not on map",
                        "entity_id": qid,
                    })

        elif qtype == "combat":
            target = quest.get("target_event_id")
            if target and target not in combat_event_ids:
                issues.append({
                    "severity": "error",
                    "message": f"Combat quest target event {target} not found",
                    "entity_id": qid,
                })

        elif qtype == "escort":
            escort_npc = quest.get("escort_npc_id")
            if escort_npc and escort_npc not in npc_ids:
                issues.append({
                    "severity": "error",
                    "message": f"Escort NPC {escort_npc} does not exist",
                    "entity_id": qid,
                })

        elif qtype == "delivery":
            if quest.get("delivery_item_id") not in item_ids_on_map:
                issues.append({
                    "severity": "error",
                    "message": f"Delivery item {quest.get('delivery_item_id')} not on map",
                    "entity_id": qid,
                })
            if quest.get("target_npc_id") not in npc_ids:
                issues.append({
                    "severity": "error",
                    "message": f"Delivery target NPC {quest.get('target_npc_id')} not found",
                    "entity_id": qid,
                })

        # Multi-step chain integrity
        if qtype == "multi_step":
            sub_ids = quest.get("sub_quest_ids", [])
            for sub_id in sub_ids:
                if sub_id not in quest_ids:
                    issues.append({
                        "severity": "error",
                        "message": f"Multi-step sub-quest {sub_id} not found",
                        "entity_id": qid,
                    })

        # Prerequisite chain depth
        prereq = quest.get("prerequisite_quest_id")
        if prereq:
            depth = 0
            visited = set()
            check = prereq
            while check and depth < 10:
                if check in visited:
                    issues.append({
                        "severity": "error",
                        "message": f"Circular prerequisite chain detected at {check}",
                        "entity_id": qid,
                    })
                    break
                visited.add(check)
                parent = next((q for q in quest_list if q["id"] == check), None)
                if parent is None:
                    issues.append({
                        "severity": "error",
                        "message": f"Prerequisite quest {check} not found",
                        "entity_id": qid,
                    })
                    break
                check = parent.get("prerequisite_quest_id")
                depth += 1

    # --- Time-gated encounter ratio ---
    time_gated = [e for e in event_list if e.get("time_gate")]
    total_events = len(event_list)
    if total_events > 0:
        ratio = len(time_gated) / total_events
        if ratio > 0.4:
            issues.append({
                "severity": "warning",
                "message": f"Too many time-gated encounters: {len(time_gated)}/{total_events} "
                           f"({ratio:.0%}), target ~20%",
                "entity_id": "",
            })

    # --- Monster presence in combat events ---
    for event in event_list:
        if event.get("type") == "combat" and not event.get("monsters"):
            issues.append({
                "severity": "error",
                "message": f"Combat event {event.get('id')} has no monsters",
                "entity_id": event.get("id", ""),
            })

    # --- NPC quest assignments ---
    assigned_quests = {n.get("quest_id") for n in npc_pool if n.get("quest_id")}
    for qid in assigned_quests:
        if qid and qid not in quest_ids:
            issues.append({
                "severity": "warning",
                "message": f"NPC assigned to non-existent quest {qid}",
                "entity_id": qid,
            })

    return issues
