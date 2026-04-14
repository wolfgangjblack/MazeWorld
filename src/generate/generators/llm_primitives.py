import ast
import json
import logging
import re

from src.prompts import get_prompt_set
from src.generate.llm_client import generate

_logger = logging.getLogger(__name__)


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3]
    return text.strip()


def generate_personality_primitive(environment: dict) -> dict:
    """
    Expects input of {"environment": {"name": "shadowleaf", "type": "forest"}}
    """
    prompts = get_prompt_set()
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")

    request = prompts.personality_generation(env, env_name)
    raw = generate(request)
    return _parse_personality(raw, env, env_name)


def _parse_personality(raw: str, env: str, env_name: str) -> dict:
    stripped = _strip_fences(raw)
    try:
        output = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        try:
            extracted = stripped.split("##Output:")[-1].split("\n========")[0].strip()
            output = ast.literal_eval(extracted)
        except Exception as e:
            return {"error": str(e)}
    output["environment"] = env
    output["environment_name"] = env_name
    return output


def generate_npc_convo(npc_personality_json: dict) -> str:
    """
    Generate an initial greeting for an NPC given their personality dict.
    """
    prompts = get_prompt_set()

    name = npc_personality_json.get("name", "npc")
    identity = prompts.conversation_identity(
        name=name,
        job=npc_personality_json.get("job", "peasant"),
        personality=npc_personality_json.get("personality", "dim"),
        hobby=npc_personality_json.get("hobby", "strolling"),
        env=npc_personality_json.get("environment", "city"),
        env_name=npc_personality_json.get("environment_name", "Starter Town"),
    )

    request = prompts.npc_greeting(name=name, identity=identity)
    raw = generate(request)
    return _extract_response(raw)


def generate_image_description(personality_document: dict) -> str:
    prompts = get_prompt_set()
    request = prompts.image_description(personality_document)
    raw = generate(request)
    description = _extract_response(raw)

    diffusion_prompt = (
        "masterpiece, best quality, very aesthetic, detailed, beautiful, "
        "appealing, attractive, fantasy illustration, stardew valley inspired, "
        f"pixel art, vivid colors, {description}"
    )
    return diffusion_prompt


def generate_environment_name(env_type: str) -> str:
    """Generate a thematic name for an environment type."""
    prompts = get_prompt_set()
    request = prompts.environment_name_generation(env_type)
    raw = generate(request)
    return _extract_response(raw)


def generate_event_primitive(environment: dict, event_type: str,
                             story_context: str = "") -> dict:
    """Generate a combat or puzzle event for the given environment."""
    prompts = get_prompt_set()
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")

    request = prompts.event_generation(env, env_name, event_type,
                                       story_context=story_context)
    raw = generate(request)
    return _parse_json_response(raw)


def generate_quest_primitive(environment: dict, npcs: list[dict],
                             items: list[dict], events: list[dict],
                             quest_type: str,
                             story_context: str = "") -> dict:
    """Generate a quest given available NPCs, items, events."""
    prompts = get_prompt_set()
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")

    request = prompts.quest_generation(env, env_name, npcs, items, events, quest_type,
                                       story_context=story_context)
    raw = generate(request)
    return _parse_json_response(raw)


def generate_story_primitive(story_seed: str, room_count: int,
                             environments: list[str]) -> dict:
    """Generate the overarching story from a seed, room count, and environment list."""
    prompts = get_prompt_set()
    request = prompts.story_generation(story_seed, room_count, environments)
    raw = generate(request)
    return _parse_json_response(raw)


def generate_story_quest_primitive(environment: dict, story_beat: str,
                                   faction_name: str, npcs: list[dict],
                                   items: list[dict], events: list[dict],
                                   quest_type: str,
                                   story_context: str = "") -> dict:
    """Generate a story-connected quest."""
    prompts = get_prompt_set()
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")
    request = prompts.story_quest_generation(
        env, env_name, story_beat, faction_name, npcs, items, events, quest_type,
        story_context=story_context,
    )
    raw = generate(request)
    return _parse_json_response(raw)


def generate_dialogue_tree(npc_personality: dict, quest_context: dict | None = None) -> dict:
    """Generate a multiple-choice dialogue tree for offline-static mode."""
    prompts = get_prompt_set()
    request = prompts.dialogue_tree_generation(npc_personality, quest_context)
    raw = generate(request)
    return _parse_json_response(raw)


from src.models.weapon import WEAPON_DICE_BY_ROOM
from src.models.spell import ELEMENT_ADVANTAGE

WEAPON_TYPE_TO_DAMAGE_TYPE: dict[str, list[str]] = {
    "heavy":  ["slashing", "bludgeoning"],
    "light":  ["piercing", "slashing"],
    "simple": ["bludgeoning", "piercing"],
    "wild":   ["slashing", "piercing", "bludgeoning"],
}

WEAPON_TYPE_TO_CATEGORY: dict[str, str] = {
    "heavy": "martial",
    "light": "martial",
    "simple": "simple",
    "wild": "martial",
}

_ELEMENTAL_TYPES = list(ELEMENT_ADVANTAGE.keys())


def _weapon_dice_for_level(room_level: int) -> list[str]:
    capped = min(room_level, max(WEAPON_DICE_BY_ROOM.keys()))
    return list(set(WEAPON_DICE_BY_ROOM.get(capped, WEAPON_DICE_BY_ROOM[1]).values()))


def generate_item_primitive(environment: dict, room_level: int = 1,
                            story_context: str = "") -> dict:
    """Generate environment-themed items via LLM. Returns dict with category arrays."""
    import random as _rng

    prompts = get_prompt_set()
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")

    request = prompts.item_generation(env, env_name, room_level,
                                      story_context=story_context)
    raw = generate(request)
    result = _parse_json_response(raw)

    if "error" in result:
        return result

    dice_pool = _weapon_dice_for_level(room_level)
    for weapon in result.get("weapons", []):
        weapon["attack_dice"] = _rng.choice(dice_pool)
        wt = weapon.get("weapon_type", "simple")
        weapon["damage_type"] = _rng.choice(WEAPON_TYPE_TO_DAMAGE_TYPE.get(wt, ["bludgeoning"]))
        weapon["weapon_category"] = WEAPON_TYPE_TO_CATEGORY.get(wt, "simple")
        weapon["magic_element"] = _rng.choice(_ELEMENTAL_TYPES) if _rng.random() < 0.05 else None

    return result


def generate_item_image_description(item_data: dict) -> str:
    """Generate a diffusion prompt for an item portrait."""
    prompts = get_prompt_set()
    request = prompts.item_image_description(item_data)
    raw = generate(request)
    description = _extract_response(raw)
    return (
        "masterpiece, best quality, very aesthetic, detailed, beautiful, "
        "fantasy illustration, stardew valley inspired, pixel art, vivid colors, "
        f"game item icon, {description}"
    )


def generate_event_image_description(event_data: dict) -> str:
    """Generate a diffusion prompt for an event illustration."""
    prompts = get_prompt_set()
    request = prompts.event_image_description(event_data)
    raw = generate(request)
    description = _extract_response(raw)
    return (
        "masterpiece, best quality, very aesthetic, detailed, beautiful, "
        "fantasy illustration, stardew valley inspired, pixel art, vivid colors, "
        f"scene illustration, {description}"
    )


def generate_player_image_description() -> str:
    """Generate a diffusion prompt for the player character portrait."""
    prompts = get_prompt_set()
    request = prompts.player_image_description()
    raw = generate(request)
    description = _extract_response(raw)
    return (
        "masterpiece, best quality, very aesthetic, detailed, beautiful, "
        "fantasy illustration, stardew valley inspired, pixel art, vivid colors, "
        f"character portrait, {description}"
    )


def generate_player_classes(environment: dict) -> list[dict]:
    """Generate 4 player class options themed to the environment.

    Returns a list of 4 dicts, one per archetype.
    """
    prompts = get_prompt_set()
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")

    request = prompts.class_generation(env, env_name)
    raw = generate(request)
    return _parse_class_array(raw)


def generate_class_portrait_description(class_data: dict) -> str:
    """Generate a diffusion prompt for a class portrait."""
    prompts = get_prompt_set()
    request = prompts.class_portrait_description(class_data)
    raw = generate(request)
    description = _extract_response(raw)
    return (
        "masterpiece, best quality, very aesthetic, detailed, beautiful, "
        "fantasy illustration, stardew valley inspired, pixel art, vivid colors, "
        f"character portrait, {description}"
    )


def _parse_class_array(raw: str) -> list[dict]:
    """Parse a JSON array of class definitions from LLM output."""
    stripped = _strip_fences(raw)
    for candidate in [stripped, raw]:
        start = candidate.find("[")
        end = candidate.rfind("]") + 1
        if start != -1 and end > start:
            snippet = candidate[start:end]
            try:
                result = json.loads(snippet)
                if isinstance(result, list):
                    return result
            except (json.JSONDecodeError, ValueError):
                try:
                    result = ast.literal_eval(snippet)
                    if isinstance(result, list):
                        return result
                except Exception:
                    pass
    return []


def generate_npc_batch(room_env: dict, room_story: str,
                       npc_slots: list[dict],
                       story_context: str) -> list[dict]:
    """Generate all NPCs for a room in a single batched call."""
    prompts = get_prompt_set()
    request = prompts.npc_batch_generation(room_env, room_story, npc_slots, story_context)
    raw = generate(request)
    return _parse_json_array(raw)


def generate_event_batch(room_env: dict, room_story: str,
                         event_type: str, event_slots: list[dict],
                         story_context: str,
                         previous_summaries: list[str] | None = None,
                         available_abilities: list[str] | None = None,
                         available_spells: list[str] | None = None,
                         available_tools: list[str] | None = None) -> list[dict]:
    """Generate a batch of events of the same type for a room."""
    import logging
    _logger = logging.getLogger(__name__)

    prompts = get_prompt_set()
    request = prompts.event_batch_generation(
        room_env, room_story, event_type, event_slots, story_context,
        previous_summaries=previous_summaries,
        available_abilities=available_abilities,
        available_spells=available_spells,
        available_tools=available_tools,
    )
    raw = generate(request)
    results = _parse_json_array(raw)
    if len(results) < len(event_slots):
        _logger.warning("Event batch returned %d/%d events for type '%s'",
                        len(results), len(event_slots), event_type)
    return results


def generate_dialogue_context(room_env: dict, room_story: str,
                              npc_data: list[dict],
                              story_context: str) -> list[dict]:
    """Generate dialogue context (greeting, exhaustion, personality notes) for online mode."""
    prompts = get_prompt_set()
    request = prompts.dialogue_context_generation(room_env, room_story, npc_data, story_context)
    raw = generate(request)
    return _parse_json_array(raw)


def generate_weapon_database(environments: list[dict],
                             num_rooms: int) -> list[dict]:
    """Generate the full weapon database across all rooms."""
    prompts = get_prompt_set()
    request = prompts.weapon_database_generation(environments, num_rooms)
    raw = generate(request)
    return _parse_json_array(raw)


def generate_spell_database(class_type: str, environments: list[dict],
                            num_rooms: int) -> list[dict]:
    """Generate spells for a class (mage or healer)."""
    prompts = get_prompt_set()
    request = prompts.spell_database_generation(class_type, environments, num_rooms)
    raw = generate(request)
    return _parse_json_array(raw)


def generate_utility_abilities(environments: list[dict],
                               num_rooms: int) -> list[dict]:
    """Generate utility abilities usable by any class."""
    prompts = get_prompt_set()
    request = prompts.utility_ability_generation(environments, num_rooms)
    raw = generate(request)
    return _parse_json_array(raw)


def generate_environment_sequence(story_seed: str, num_rooms: int,
                                  known_types: list[str]) -> list[dict]:
    """Generate a narrative environment sequence for the world."""
    prompts = get_prompt_set()
    request = prompts.environment_sequence_generation(story_seed, num_rooms, known_types)
    raw = generate(request)
    result = _parse_json_array(raw)
    if result and all(isinstance(r, dict) and "type" in r and "name" in r for r in result):
        return result[:num_rooms]
    return []


def generate_overarching_story(story_seed: str,
                               environments: list[dict]) -> dict:
    """Generate the high-level story arc (no per-room beats)."""
    prompts = get_prompt_set()
    request = prompts.overarching_story_generation(story_seed, environments)
    raw = generate(request)
    return _parse_json_response(raw)


def generate_room_story_beat(overarching_story: dict, room_env: dict,
                             room_index: int,
                             prior_beats: list[dict],
                             num_rooms: int = 5) -> dict:
    """Generate a detailed story beat for a single room."""
    prompts = get_prompt_set()
    request = prompts.room_story_beat_generation(
        overarching_story, room_env, room_index, prior_beats, num_rooms)
    raw = generate(request)
    return _parse_json_response(raw)


def generate_music_prompts(story_summary: dict,
                           environments: list[str]) -> dict[str, str | None]:
    """Generate Lyra 3 music prompts for combat + one maze track per environment.

    Returns a dict keyed by track name (e.g. 'combat', 'maze_village') with
    prompt strings. Fixed tracks (puzzle_event, start_screen, victory, game_over)
    are returned as None — callers should fill those from FIXED_PROMPTS.
    """
    prompts = get_prompt_set()
    request = prompts.music_prompt_generation(story_summary, environments)
    raw = generate(request)
    result = _parse_json_response(raw)
    if "error" in result:
        return {}
    return result


def generate_sfx_prompts(story_summary: dict,
                         environments: list[dict],
                         spell_elements: list[str]) -> dict[str, dict]:
    """Generate ElevenLabs SFX prompts for weapons, spells, and ambience.

    Returns a dict keyed by sfx name with {prompt, duration, loop} specs.
    Fixed SFX (UI, dice, items) are NOT included — callers merge those separately.
    """
    prompts = get_prompt_set()
    request = prompts.sfx_prompt_generation(story_summary, environments, spell_elements)
    raw = generate(request)
    result = _parse_json_response(raw)
    if "error" in result:
        return {}
    return result


def generate_full_story_primitive(story_seed: str, room_count: int,
                                  environments: list[str]) -> dict:
    """Generate the full story arc + story-important entities for the World Bible."""
    prompts = get_prompt_set()
    request = prompts.full_story_generation(story_seed, room_count, environments)
    raw = generate(request)
    return _parse_json_response(raw)


def generate_monster_primitive(environment: dict, room_level: int,
                               story_context: str, total_rooms: int = 1) -> list[dict]:
    """Generate environment-themed monsters with Bible context."""
    prompts = get_prompt_set()
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")
    request = prompts.monster_generation(
        env, env_name, room_level, story_context, total_rooms=total_rooms)
    raw = generate(request)
    return _parse_json_array(raw)


def generate_npc_backstory(npc_data: dict, story_context: str) -> str:
    """Generate a rich backstory paragraph for an NPC using Bible context."""
    prompts = get_prompt_set()
    request = prompts.npc_backstory_generation(npc_data, story_context)
    raw = generate(request)
    return _extract_response(raw)


def _parse_json_array(raw: str) -> list[dict]:
    """Parse a JSON array from LLM output. Logs warning on failure."""
    stripped = _strip_fences(raw)
    for candidate in [stripped, raw]:
        start = candidate.find("[")
        end = candidate.rfind("]") + 1
        if start != -1 and end > start:
            snippet = candidate[start:end]
            try:
                result = json.loads(snippet)
                if isinstance(result, list):
                    return result
            except (json.JSONDecodeError, ValueError):
                try:
                    result = ast.literal_eval(snippet)
                    if isinstance(result, list):
                        return result
                except Exception:
                    pass

    # Truncation recovery: find last complete object boundary and parse partial array
    for candidate in [stripped, raw]:
        start = candidate.find("[")
        if start == -1:
            continue
        text = candidate[start:]
        last_brace = text.rfind("}")
        if last_brace > 0:
            truncated = text[:last_brace + 1] + "]"
            try:
                result = json.loads(truncated)
                if isinstance(result, list) and result:
                    _logger.info("Recovered %d items from truncated JSON response", len(result))
                    return result
            except (json.JSONDecodeError, ValueError):
                pass

    _logger.warning("Failed to parse JSON array from LLM response (%d chars): %.200s",
                    len(raw), raw)
    return []


def _extract_response(raw: str) -> str:
    """Extract the usable response from raw LLM output."""
    text = _strip_fences(raw)
    if "##Output:" in text:
        text = text.split("##Output:")[-1].strip()
    return text.split("\n")[0].strip()


def _parse_json_response(raw: str) -> dict:
    """Parse a JSON response from LLM output, with fallback to ast.literal_eval."""
    stripped = _strip_fences(raw)
    for candidate in [stripped, raw]:
        start = candidate.find("{")
        end = candidate.rfind("}") + 1
        if start != -1 and end > start:
            snippet = candidate[start:end]
            try:
                return json.loads(snippet)
            except (json.JSONDecodeError, ValueError):
                try:
                    result = ast.literal_eval(snippet)
                    if isinstance(result, dict):
                        return result
                except Exception:
                    pass
                continue
    return {"error": f"Could not parse JSON from: {raw[:200]}"}
