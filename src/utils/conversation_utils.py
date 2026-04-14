import json
import logging
import random

from config import GAME_MODE
from src.prompts import get_prompt_set
from src.prompts.base import LLMRequest
from src.generate.llm_client import generate

logger = logging.getLogger(__name__)

# LLM failure fallback
_LLM_FAILURE_RESPONSE = "No... I can not talk about that..."

# Minimum turns before the LLM exhaustion check kicks in
_LLM_EXHAUSTION_MIN_TURNS = 3


def _llm_check_exhaustion(npc, player_input: str, quest_context: dict | None = None) -> bool:
    """Use an LLM call to decide if the NPC's dialogue should end.

    Returns True if the LLM judges the conversation should be exhausted.
    Falls back to False (continue) on any error.
    """
    history_text = "\n".join(
        f"{'Player' if t['role'] == 'user' else npc.name}: {t['content']}"
        for t in npc.interaction_history[-6:]
    )

    quest_info = ""
    if quest_context:
        quest_info = (
            f"Active quest: \"{quest_context.get('title', 'unknown')}\" "
            f"(type: {quest_context.get('type', '?')}, "
            f"status: {quest_context.get('status', 'active')}). "
        )

    request = LLMRequest(
        system=(
            "You are a game-master adjudicating NPC dialogue in a fantasy RPG. "
            "Given the conversation history, decide whether the NPC should end "
            "the dialogue. Answer ONLY 'yes' or 'no'.\n\n"
            "Answer 'yes' (exhaust dialogue) if ANY of these are true:\n"
            "- The quest topic has been fully addressed\n"
            "- The NPC has nothing more useful to say\n"
            "- The player is being abusive, off-topic, or not engaging\n"
            "- The conversation is going in circles\n\n"
            "Answer 'no' (continue dialogue) if:\n"
            "- The NPC still has quest-relevant information to share\n"
            "- The player is actively engaging and making progress"
        ),
        user_message=(
            f"NPC: {npc.name} ({getattr(npc, 'job', 'unknown')} — "
            f"{getattr(npc, 'personality', 'unknown')})\n"
            f"{quest_info}\n"
            f"Recent conversation:\n{history_text}\n\n"
            f"Player's latest input: \"{player_input}\"\n\n"
            "Should the NPC end this conversation? (yes/no)"
        ),
        max_tokens=10,
    )

    try:
        raw = generate(request)
        answer = raw.strip().lower()
        return answer.startswith("yes")
    except Exception as e:
        logger.warning("LLM exhaustion check failed, using heuristic fallback: %s", e)
        # Heuristic fallback: non-quest NPCs exhaust after 6+ turns
        turn_count = len(npc.interaction_history)
        if turn_count >= 6 and not quest_context:
            return True
        return False


def check_dialogue_exhaustion(npc, player_input: str, quest_context: dict | None = None) -> bool:
    """Check if an NPC's dialogue should be exhausted after a player reply.

    - offline_static: heuristic (dialogue tree end node, turn count)
    - online / offline_local: LLM call after minimum turns, with heuristic fallback
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

    # For offline_static, use simple heuristics (no LLM)
    if GAME_MODE == "offline_static":
        tree = getattr(npc, "dialogue_tree", None)
        if tree and tree.get("_current") == "end":
            return True
        return False

    # For online / offline_local: use LLM after a few turns
    if turn_count >= _LLM_EXHAUSTION_MIN_TURNS:
        return _llm_check_exhaustion(npc, player_input, quest_context)

    return False


def generate_npc_response(npc, player_input: str, story_context: str = "",
                          quest_context: dict | None = None,
                          player=None) -> str:
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
            quest_context=quest_context,
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
            quest_context=quest_context,
        )
        try:
            raw = generate(request)
            response, cha_data = _extract_response_with_cha(raw)
        except Exception:
            response = _LLM_FAILURE_RESPONSE
            cha_data = None
        if not response:
            response = _LLM_FAILURE_RESPONSE

        # CHA check: d20 + CHA mod vs NPC's current DC (online mode only)
        if cha_data and quest_context and player:
            npc.current_dc = max(8, min(20, cha_data.get("dc_next", npc.current_dc)))
            cha_mod = player.get_stat_modifier("CHA") if hasattr(player, 'get_stat_modifier') else 0
            roll = random.randint(1, 20) + cha_mod
            if roll < npc.current_dc:
                npc.dialogue_exhausted = True
                dismissal = _generate_dismissal(npc, cha_data.get("tone", "rude"))
                npc.add_turn("npc", dismissal)
                return f"{npc.name}: {dismissal}"

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


def _extract_response_with_cha(raw: str) -> tuple[str, dict | None]:
    """Extract NPC response text and optional CHA evaluation JSON from last line."""
    lines = raw.strip().split("\n")
    cha_data = None
    if lines:
        last = lines[-1].strip()
        if last.startswith("{") and "dc_next" in last:
            try:
                cha_data = json.loads(last)
                lines = lines[:-1]
            except json.JSONDecodeError:
                pass
    response_text = _extract_response("\n".join(lines))
    return response_text, cha_data


def _generate_dismissal(npc, tone: str) -> str:
    """Generate a personality-appropriate dismissal when CHA check fails."""
    request = LLMRequest(
        system=npc.identity or f"You are {npc.name}, a fantasy NPC.",
        user_message=(
            f"The player has been {tone}. End the conversation with a brief, "
            "in-character dismissal (1 sentence). You don't want to talk anymore."
        ),
        max_tokens=60,
    )
    try:
        raw = generate(request)
        return _extract_response(raw)
    except Exception:
        return "I don't think I want to talk anymore."
