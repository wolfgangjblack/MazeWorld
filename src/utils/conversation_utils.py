from src.prompts import get_prompt_set
from src.generate.llm_client import generate


def generate_npc_response(npc, player_input: str) -> str:
    prompts = get_prompt_set()
    is_greeting = not player_input

    if not npc.has_met_player:
        request = prompts.npc_greeting(name=npc.name, identity=npc.identity)
        raw = generate(request)
        response = _extract_response(raw)
        npc.add_turn("npc", response)
        npc.has_met_player = True
    elif is_greeting:
        npc.add_turn("user", f"The player returns to speak with {npc.name}.")
        request = prompts.npc_response(
            identity=npc.identity,
            history=npc.get_recent_history(),
            npc_name=npc.name,
            player_input="The player returns to speak with you.",
        )
        raw = generate(request)
        response = _extract_response(raw)
        npc.add_turn("npc", response)
    else:
        npc.add_turn("user", player_input)
        request = prompts.npc_response(
            identity=npc.identity,
            history=npc.get_recent_history(),
            npc_name=npc.name,
            player_input=player_input,
        )
        raw = generate(request)
        response = _extract_response(raw)
        npc.add_turn("npc", response)

    if npc.is_appropriate(response):
        return f"{npc.name}: {response}"
    return npc.get_fallback_response()


def _extract_response(raw: str) -> str:
    """Extract the usable NPC response from raw LLM output."""
    if "##Output:" in raw:
        response = raw.split("##Output:")[-1].strip()
    else:
        response = raw.strip()
    return response.split("\n")[0].strip()
