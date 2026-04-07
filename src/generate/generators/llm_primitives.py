import ast
import json

from src.prompts import get_prompt_set
from src.generate.llm_client import generate


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
    try:
        output = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        try:
            extracted = raw.split("##Output:")[-1].split("\n========")[0].strip()
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


WEAPON_DICE_BY_LEVEL = {
    1: ["1d4", "1d6"],
    2: ["1d6", "1d8"],
    3: ["1d8", "1d10"],
    4: ["1d10", "1d12"],
}


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

    # Post-process: assign weapon dice scaled to room_level
    dice_pool = WEAPON_DICE_BY_LEVEL.get(room_level, WEAPON_DICE_BY_LEVEL[1])
    for weapon in result.get("weapons", []):
        weapon["attack_dice"] = _rng.choice(dice_pool)

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
    # Try to find a JSON array in the response
    for candidate in [raw]:
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


def generate_full_story_primitive(story_seed: str, room_count: int,
                                  environments: list[str]) -> dict:
    """Generate the full story arc + story-important entities for the World Bible."""
    prompts = get_prompt_set()
    request = prompts.full_story_generation(story_seed, room_count, environments)
    raw = generate(request)
    return _parse_json_response(raw)


def generate_monster_primitive(environment: dict, room_level: int,
                               story_context: str) -> list[dict]:
    """Generate environment-themed monsters with Bible context."""
    prompts = get_prompt_set()
    env = environment.get("environment", {}).get("type", "city")
    env_name = environment.get("environment", {}).get("name", "city")
    request = prompts.monster_generation(env, env_name, room_level, story_context)
    raw = generate(request)
    return _parse_json_array(raw)


def generate_npc_backstory(npc_data: dict, story_context: str) -> str:
    """Generate a rich backstory paragraph for an NPC using Bible context."""
    prompts = get_prompt_set()
    request = prompts.npc_backstory_generation(npc_data, story_context)
    raw = generate(request)
    return _extract_response(raw)


def _parse_json_array(raw: str) -> list[dict]:
    """Parse a JSON array from LLM output."""
    for candidate in [raw]:
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


def _extract_response(raw: str) -> str:
    """Extract the usable response from raw LLM output."""
    if "##Output:" in raw:
        response = raw.split("##Output:")[-1].strip()
    else:
        response = raw.strip()
    return response.split("\n")[0].strip()


def _parse_json_response(raw: str) -> dict:
    """Parse a JSON response from LLM output, with fallback to ast.literal_eval."""
    cleaned = _extract_response(raw)
    # Try to find JSON in the response
    for candidate in [cleaned, raw]:
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
