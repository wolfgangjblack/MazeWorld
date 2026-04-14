"""Save/load serialization manager.

Handles serializing full game state to JSON and restoring it.
Save files go to saves/ directory, keyed by seed + character name + class.
"""

import json
import os
import re
from datetime import datetime
from typing import Optional

from config import DATA_DIR
from src.models.save import SaveMetadata, SaveState

SAVE_DIR = os.path.join(DATA_DIR, "saves")


def _ensure_save_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)


def _save_filename(seed: int, character_name: str, character_class: str) -> str:
    """Generate a unique save filename with timestamp."""
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", character_name.lower())
    safe_class = re.sub(r"[^a-zA-Z0-9_]", "_", character_class.lower())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"save_{seed}_{safe_name}_{safe_class}_{ts}.json"


def _save_path(seed: int, character_name: str, character_class: str) -> str:
    return os.path.join(SAVE_DIR, _save_filename(seed, character_name, character_class))


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def serialize_player(player) -> dict:
    """Serialize PlayerCharacter to a dict."""
    data = {
        "x": player.x,
        "y": player.y,
        "name": player.name,
        "level": player.level,
        "health": player.health,
        "stamina": player.stamina,
        "max_health": player.max_health,
        "max_stamina": player.max_stamina,
        "speed": player.speed,
        "max_speed": player.max_speed,
        "money": player.money,
        "equipped_weapon": player.equipped_weapon,
        "armor": player.armor,
        "selected_item_index": player.selected_item_index,
        "active_quests": list(player.active_quests),
        "completed_quests": list(player.completed_quests),
        "failed_quests": list(player.failed_quests),
        "learned_spells": list(player.learned_spells),
        "profile_image": player.profile_image,
        "combat_record": dict(player.combat_record),
        "encounter_record": dict(player.encounter_record),
        "title": player.title,
    }

    # Player class
    if player.player_class:
        data["player_class"] = player.player_class.model_dump()

    # Inventory - serialize each item with its type
    inv = {}
    for item_name, item in player.inventory.items():
        item_dict = item.model_dump()
        item_dict["_item_type"] = type(item).__name__
        inv[item_name] = item_dict
    data["inventory"] = inv

    # Abilities and spells
    data["abilities"] = [a.model_dump() if hasattr(a, "model_dump") else a for a in player.abilities]
    data["spells"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in player.spells]

    # Active buffs
    data["active_buffs"] = [b.model_dump() for b in player.active_buffs]

    return data


def deserialize_player(data: dict):
    """Restore a PlayerCharacter from saved data."""
    from src.models.player import (
        Ability,
        ActiveBuff,
        PlayerCharacter,
        PlayerClass,
        Spell,
    )

    # Reconstruct inventory
    inventory = {}
    for item_name, item_dict in data.get("inventory", {}).items():
        item_type = item_dict.pop("_item_type", "Item")
        inventory[item_name] = _reconstruct_item(item_dict, item_type)

    # Reconstruct player class
    player_class = None
    if "player_class" in data and data["player_class"]:
        player_class = PlayerClass(**data["player_class"])

    # Reconstruct abilities and spells
    abilities = [Ability(**a) if isinstance(a, dict) else a for a in data.get("abilities", [])]
    spells = [Spell(**s) if isinstance(s, dict) else s for s in data.get("spells", [])]
    active_buffs = [ActiveBuff(**b) for b in data.get("active_buffs", [])]

    player = PlayerCharacter(
        x=data.get("x", 0),
        y=data.get("y", 0),
        name=data.get("name", "Adventurer"),
        player_class=player_class,
        level=data.get("level", 1),
        health=data.get("health", 100),
        stamina=data.get("stamina", min(100, (data.get("hunger", 50) + data.get("thirst", 50)) // 2)),
        max_health=data.get("max_health", 100),
        max_stamina=data.get("max_stamina", 100),
        speed=data.get("speed", 1.0),
        max_speed=data.get("max_speed", 2.0),
        money=data.get("money", 0),
        equipped_weapon=data.get("equipped_weapon"),
        armor=data.get("armor", 0),
        selected_item_index=data.get("selected_item_index", 0),
        active_quests=data.get("active_quests", []),
        completed_quests=data.get("completed_quests", []),
        failed_quests=data.get("failed_quests", []),
        learned_spells=data.get("learned_spells", []),
        profile_image=data.get("profile_image"),
        combat_record=data.get(
            "combat_record",
            {
                "monsters_killed": 0,
                "damage_dealt": 0,
                "damage_taken": 0,
                "combats_won": 0,
                "combats_fled": 0,
            },
        ),
        encounter_record=data.get(
            "encounter_record",
            {
                "puzzles_solved": 0,
                "puzzles_failed": 0,
                "events_resolved": 0,
                "events_failed": 0,
            },
        ),
        title=data.get("title", ""),
        inventory=inventory,
        abilities=abilities,
        spells=spells,
        active_buffs=active_buffs,
    )
    return player


def _reconstruct_item(item_dict: dict, item_type: str):
    """Reconstruct an Item subclass from serialized dict."""
    from src.models.items import (
        Drink,
        EscortItem,
        Food,
        Item,
        ItemStats,
        SpellScroll,
        Tool,
        Weapon,
    )

    TYPE_MAP = {
        "Item": Item,
        "Food": Food,
        "Drink": Drink,
        "Tool": Tool,
        "Weapon": Weapon,
        "SpellScroll": SpellScroll,
        "EscortItem": EscortItem,
    }

    cls = TYPE_MAP.get(item_type, Item)

    # Ensure item_stats is an ItemStats instance
    stats_data = item_dict.get("item_stats", {})
    if isinstance(stats_data, dict):
        item_dict["item_stats"] = ItemStats(**stats_data)

    # EscortItem needs tuple for target_zone
    if cls is EscortItem and "target_zone" in item_dict:
        tz = item_dict["target_zone"]
        if isinstance(tz, list):
            item_dict["target_zone"] = tuple(tz)

    return cls(**item_dict)


def serialize_npc(npc) -> dict:
    """Serialize an NPC's mutable state."""
    data = {
        "id": npc.id,
        "x": npc.x,
        "y": npc.y,
        "interaction_history": list(npc.interaction_history),
        "has_met_player": npc.has_met_player,
        "_npc_type": type(npc).__name__,
    }
    # MerchantNPC shop state
    if hasattr(npc, "shop_inventory"):
        data["shop_inventory"] = npc.shop_inventory
    # RandomNPC home position
    if hasattr(npc, "home_x"):
        data["home_x"] = npc.home_x
        data["home_y"] = npc.home_y
    # Dialogue state
    data["dialogue_exhausted"] = npc.dialogue_exhausted
    data["finished_dialogue"] = npc.finished_dialogue
    data["current_dc"] = getattr(npc, "current_dc", 10)
    if getattr(npc, "dialogue_tree_incomplete", None):
        data["_active_tree"] = (
            "complete"
            if npc.dialogue_tree is npc.dialogue_tree_complete
            else "failed"
            if npc.dialogue_tree is npc.dialogue_tree_failed
            else "incomplete"
        )
    if npc.dialogue_tree and "_current" in npc.dialogue_tree:
        data["_dialogue_current"] = npc.dialogue_tree["_current"]
    return data


def serialize_event(event) -> dict:
    """Serialize an event's mutable state."""
    data = {
        "id": event.id,
        "resolved": event.resolved,
    }
    # For combat events, save monster HP
    if hasattr(event, "monsters"):
        data["monster_states"] = [{"hp": m.hp, "status_effects": dict(m.status_effects)} for m in event.monsters]
        data["combat_started"] = event.combat_started
        data["player_fled"] = event.player_fled
    return data


def serialize_quest(quest) -> dict:
    """Serialize a quest's mutable state."""
    data = {
        "id": quest.id,
        "status": quest.status,
    }
    if hasattr(quest, "current_step"):
        data["current_step"] = quest.current_step
    return data


def serialize_follower(follower) -> dict:
    """Serialize a Follower."""
    return follower.model_dump()


# ---------------------------------------------------------------------------
# Save / Load / List / Delete
# ---------------------------------------------------------------------------


def save_game(game_controller, seed: int, time_played_seconds: float = 0.0) -> str:
    """Save full game state. Returns the save file path."""
    _ensure_save_dir()

    player = game_controller.player
    maze = game_controller.maze

    char_name = player.name
    char_class = player.player_class.name if player.player_class else "unknown"

    metadata = SaveMetadata(
        character_name=char_name,
        character_class=char_class,
        room_level=game_controller.current_room + 1,
        time_played_seconds=time_played_seconds,
        last_save_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        seed=seed,
    )

    # Serialize event position map with string keys for JSON
    epm = {}
    for (x, y), eid in game_controller.event_position_map.items():
        epm[f"{x},{y}"] = eid

    # Serialize fog and day/night state
    fog_data = {}
    if hasattr(game_controller, "fog") and game_controller.fog:
        fog_data = game_controller.fog.serialize()
    day_night_data = {}
    if hasattr(game_controller, "day_night") and game_controller.day_night:
        day_night_data = game_controller.day_night.serialize()

    # Serialize maze door/gate state
    door_pos = list(maze.door_position) if maze.door_position else None

    state = SaveState(
        version=1,
        metadata=metadata,
        seed=seed,
        current_room=game_controller.current_room,
        total_rooms=game_controller.total_rooms,
        player_data=serialize_player(player),
        maze_grid=[list(row) for row in maze.grid],
        maze_environment=maze.environment,
        maze_environment_name=getattr(maze, "environment_name", ""),
        maze_door_position=door_pos,
        maze_door_revealed=maze.door_revealed,
        maze_gate_encounter_id=maze.gate_encounter_id,
        npc_states=[serialize_npc(npc) for npc in game_controller.npcs],
        event_states={eid: serialize_event(evt) for eid, evt in game_controller.events.items()},
        quest_states={qid: serialize_quest(q) for qid, q in game_controller.quests.items()},
        follower_data=[serialize_follower(f) for f in player.followers],
        event_position_map=epm,
        fog_data=fog_data,
        day_night_data=day_night_data,
        gate_cleared=game_controller.gate_cleared,
        gc_stats=dict(game_controller.stats),
        time_played_seconds=time_played_seconds,
    )

    return _write_save(state, seed, char_name, char_class)


def save_game_to_path(
    game_controller,
    seed: int,
    time_played_seconds: float,
    filepath: str,
) -> str:
    """Save full game state to a specific file path (for overwriting)."""
    _ensure_save_dir()
    player = game_controller.player
    maze = game_controller.maze
    char_name = player.name
    char_class = player.player_class.name if player.player_class else "unknown"

    metadata = SaveMetadata(
        character_name=char_name,
        character_class=char_class,
        room_level=game_controller.current_room + 1,
        time_played_seconds=time_played_seconds,
        last_save_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        seed=seed,
    )

    epm = {}
    for (x, y), eid in game_controller.event_position_map.items():
        epm[f"{x},{y}"] = eid

    fog_data = {}
    if hasattr(game_controller, "fog") and game_controller.fog:
        fog_data = game_controller.fog.serialize()
    day_night_data = {}
    if hasattr(game_controller, "day_night") and game_controller.day_night:
        day_night_data = game_controller.day_night.serialize()

    door_pos = list(maze.door_position) if maze.door_position else None

    state = SaveState(
        version=1,
        metadata=metadata,
        seed=seed,
        current_room=game_controller.current_room,
        total_rooms=game_controller.total_rooms,
        player_data=serialize_player(player),
        maze_grid=[list(row) for row in maze.grid],
        maze_environment=maze.environment,
        maze_environment_name=getattr(maze, "environment_name", ""),
        maze_door_position=door_pos,
        maze_door_revealed=maze.door_revealed,
        maze_gate_encounter_id=maze.gate_encounter_id,
        npc_states=[serialize_npc(npc) for npc in game_controller.npcs],
        event_states={eid: serialize_event(evt) for eid, evt in game_controller.events.items()},
        quest_states={qid: serialize_quest(q) for qid, q in game_controller.quests.items()},
        follower_data=[serialize_follower(f) for f in player.followers],
        event_position_map=epm,
        fog_data=fog_data,
        day_night_data=day_night_data,
        gate_cleared=game_controller.gate_cleared,
        gc_stats=dict(game_controller.stats),
        time_played_seconds=time_played_seconds,
    )

    with open(filepath, "w") as f:
        json.dump(state.model_dump(), f, indent=2, default=str)
    return filepath


def _write_save(state: SaveState, seed: int, char_name: str, char_class: str) -> str:
    """Write a SaveState to a new timestamped file."""
    _ensure_save_dir()
    filepath = _save_path(seed, char_name, char_class)
    with open(filepath, "w") as f:
        json.dump(state.model_dump(), f, indent=2, default=str)
    return filepath


def load_game(filepath: str) -> Optional[SaveState]:
    """Load a save file. Returns SaveState or None if invalid."""
    real_path = os.path.realpath(filepath)
    real_save_dir = os.path.realpath(SAVE_DIR)
    if not real_path.startswith(real_save_dir + os.sep):
        return None
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        return SaveState(**data)
    except (json.JSONDecodeError, KeyError, TypeError, FileNotFoundError):
        return None
    except Exception:
        return None


def validate_save(filepath: str) -> bool:
    """Check if a save file is valid without fully loading it."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        return "version" in data and "player_data" in data
    except Exception:
        return False


def list_saves() -> list[dict]:
    """List all save files with metadata for display.

    Returns list of dicts with: filepath, character_name, character_class,
    room_level, time_played_seconds, last_save_date, seed.
    """
    _ensure_save_dir()
    saves = []
    for filename in sorted(os.listdir(SAVE_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(SAVE_DIR, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            meta = data.get("metadata", {})
            saves.append(
                {
                    "filepath": filepath,
                    "character_name": meta.get("character_name", "Unknown"),
                    "character_class": meta.get("character_class", ""),
                    "room_level": meta.get("room_level", 1),
                    "time_played_seconds": meta.get("time_played_seconds", 0),
                    "last_save_date": meta.get("last_save_date", ""),
                    "seed": meta.get("seed", -1),
                }
            )
        except Exception:
            continue  # Skip corrupt files
    return saves


def delete_save(filepath: str) -> bool:
    """Delete a save file. Returns True on success."""
    try:
        os.remove(filepath)
        return True
    except OSError:
        return False


def has_saves() -> bool:
    """Check if any save files exist (fast check, no JSON parsing)."""
    _ensure_save_dir()
    return any(f.endswith(".json") for f in os.listdir(SAVE_DIR))
