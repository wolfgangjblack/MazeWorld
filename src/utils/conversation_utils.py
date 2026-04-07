from config import GAME_MODE
from src.prompts import get_prompt_set
from src.generate.llm_client import generate

# LLM failure fallback
_LLM_FAILURE_RESPONSE = "No... I can not talk about that..."


def check_dialogue_exhaustion(npc, player_input: str, quest_context: dict | None = None) -> bool:
    """Check if an NPC's dialogue should be exhausted after a player reply.

    Evaluates (via simple heuristics for offline, LLM for online):
    - Is this quest-related? Has the user solved/answered the quest?
    - Does the NPC have more to tell from a game perspective?
    - Is the player behaving/helping?

    If the NPC is done or annoyed, returns True (exhaust dialogue).
    """
    if getattr(npc, "dialogue_exhausted", False):
        return True

    turn_count = len(npc.interaction_history)
    max_turns = getattr(npc, "max_dialogue_turns", 10)

    # Hard limit: too many turns = exhausted
    if turn_count >= max_turns:
        return True

    # If quest is completed, NPC has nothing more to say
    if quest_context and quest_context.get("status") == "completed":
        return True

    # For offline modes, use simple turn-based exhaustion
    if GAME_MODE == "offline_static":
        # Static NPCs exhaust when dialogue tree reaches "end" node
        tree = getattr(npc, "dialogue_tree", None)
        if tree and tree.get("_current") == "end":
            return True
        return False

    # For LLM modes, check if the conversation is going nowhere
    if turn_count >= 6 and not quest_context:
        # Non-quest NPC with 6+ turns — exhaust
        return True

    return False


def generate_npc_response(npc, player_input: str, story_context: str = "",
                          quest_context: dict | None = None) -> str:
    """Generate an NPC response.

    - First meeting: uses pre-generated opening_greeting if available.
    - Online / offline_local: live LLM for ongoing conversation.
    - Offline_static: returns choices from npc.dialogue_tree (no LLM call).
    - *story_context*: optional story summary (faction, beats) injected into prompts.
    - *quest_context*: optional quest dict for quest-related NPCs.

    Dialogue exhaustion: after the NPC is done or annoyed, falls back to
    finished_dialogue text FOREVER (prevents token burn).
    """
    # If dialogue is already exhausted, always return finished text
    if getattr(npc, "dialogue_exhausted", False):
        finished = getattr(npc, "finished_dialogue", "I have nothing more to say.")
        return f"{npc.name}: {finished}"

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
            if not response:
                response = _LLM_FAILURE_RESPONSE
            npc.add_turn("npc", response)
            npc.has_met_player = True
            if npc.is_appropriate(response):
                return f"{npc.name}: {response}"
            return npc.get_fallback_response()

    elif GAME_MODE == "offline_static" and npc.dialogue_tree:
        result = _static_dialogue_response(npc, player_input)
        # Check exhaustion after static dialogue
        if check_dialogue_exhaustion(npc, player_input, quest_context):
            npc.dialogue_exhausted = True
        return result

    elif is_greeting:
        npc.add_turn("user", f"The player returns to speak with {npc.name}.")
        prompts = get_prompt_set()
        request = prompts.npc_response(
            identity=npc.identity,
            history=npc.get_recent_history(),
            npc_name=npc.name,
            player_input="The player returns to speak with you.",
            story_context=story_context,
        )
        try:
            raw = generate(request)
            response = _extract_response(raw)
        except Exception:
            response = _LLM_FAILURE_RESPONSE
        if not response:
            response = _LLM_FAILURE_RESPONSE
        npc.add_turn("npc", response)
    else:
        npc.add_turn("user", player_input)
        prompts = get_prompt_set()
        request = prompts.npc_response(
            identity=npc.identity,
            history=npc.get_recent_history(),
            npc_name=npc.name,
            player_input=player_input,
            story_context=story_context,
        )
        try:
            raw = generate(request)
            response = _extract_response(raw)
        except Exception:
            response = _LLM_FAILURE_RESPONSE
        if not response:
            response = _LLM_FAILURE_RESPONSE
        npc.add_turn("npc", response)

    # Check exhaustion after LLM response
    if check_dialogue_exhaustion(npc, player_input, quest_context):
        npc.dialogue_exhausted = True

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


def has_dialogue_choices(npc) -> bool:
    """Return True if the NPC's current dialogue tree node has choices."""
    if GAME_MODE != "offline_static" or not npc or not npc.dialogue_tree:
        return False
    tree = npc.dialogue_tree
    nodes = tree.get("nodes", {})
    current_node_id = tree.get("_current", "start")
    node = nodes.get(current_node_id, nodes.get("start", {}))
    return bool(node.get("choices"))


def _extract_response(raw: str) -> str:
    """Extract the usable NPC response from raw LLM output."""
    if "##Output:" in raw:
        response = raw.split("##Output:")[-1].strip()
    else:
        response = raw.strip()
    return response.split("\n")[0].strip()
