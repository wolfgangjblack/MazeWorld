import ast
import json

from src.prompts import get_prompt_set
from src.generate.llm_client import generate


def generate_personality_primative(environment: dict) -> dict:
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
    Expects input like:
    {'name': 'lyra', 'job': 'shaman', 'personality': 'whispering',
     'hobby': 'communicating with spirits', 'environment': 'forest',
     'environment_name': 'shadowleaf'}
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


def _extract_response(raw: str) -> str:
    """Extract the usable response from raw LLM output."""
    if "##Output:" in raw:
        response = raw.split("##Output:")[-1].strip()
    else:
        response = raw.strip()
    return response.split("\n")[0].strip()
