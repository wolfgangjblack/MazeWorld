from config import GAME_MODE
from src.prompts import get_prompt_set
from src.generate.llm_client import generate


def generate_npc_response(npc, player_input: str) -> str:
    """Generate an NPC response.

    - First meeting: uses pre-generated opening_greeting if available.
    - Online / offline_local: live LLM for ongoing conversation.
    - Offline_static: returns choices from npc.dialogue_tree (no LLM call).
    """
    is_greeting = not player_input

    if not npc.has_met_player:
        if npc.opening_greeting:
            response = npc.opening_greeting
            npc.add_turn("npc", response)
            npc.has_met_player = True
            return f"{npc.name}: {response}"
        else:
            prompts = get_prompt_set()
            request = prompts.npc_greeting(name=npc.name, identity=npc.identity)
            raw = generate(request)
            response = _extract_response(raw)
            npc.add_turn("npc", response)
            npc.has_met_player = True
            if npc.is_appropriate(response):
                return f"{npc.name}: {response}"
            return npc.get_fallback_response()

    elif GAME_MODE == "offline_static" and npc.dialogue_tree:
        return _static_dialogue_response(npc, player_input)

    elif is_greeting:
        npc.add_turn("user", f"The player returns to speak with {npc.name}.")
        prompts = get_prompt_set()
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
        prompts = get_prompt_set()
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


def _static_dialogue_response(npc, player_input: str) -> str:
    """Navigate the pre-generated dialogue tree for offline-static mode."""
    tree = npc.dialogue_tree
    if not tree or "nodes" not in tree:
        return f"{npc.name}: ..."

    nodes = tree["nodes"]
    current_node_id = tree.get("_current", "start")
    node = nodes.get(current_node_id, nodes.get("start", {}))

    if player_input and node.get("choices"):
        for i, choice in enumerate(node["choices"]):
            if player_input.strip() == str(i + 1) or player_input.strip().lower() == choice["text"].lower():
                next_id = choice.get("next_node_id", "end")
                tree["_current"] = next_id
                next_node = nodes.get(next_id, {})
                prompt = next_node.get("prompt", "...")
                npc.add_turn("npc", prompt)
                return f"{npc.name}: {prompt}"

    prompt = node.get("prompt", "...")
    choices = node.get("choices", [])
    if choices:
        choice_text = "\n".join(f"  {i+1}. {c['text']}" for i, c in enumerate(choices))
        return f"{npc.name}: {prompt}\n{choice_text}"
    return f"{npc.name}: {prompt}"


def _extract_response(raw: str) -> str:
    """Extract the usable NPC response from raw LLM output."""
    if "##Output:" in raw:
        response = raw.split("##Output:")[-1].strip()
    else:
        response = raw.strip()
    return response.split("\n")[0].strip()
