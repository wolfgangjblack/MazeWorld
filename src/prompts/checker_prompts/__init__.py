"""Checker prompts for LLM-based content review.

These prompts support the Checker stage of the Gen -> Check -> Validate chain.
Checkers perform structural and thematic review of generated content.
"""

from src.prompts.base import LLMRequest


def event_check_prompt(event_data: dict, env_type: str, env_name: str) -> LLMRequest:
    """Prompt to review a generated event for theme and structural issues."""
    return LLMRequest(
        system=(
            "You are a game content reviewer for a fantasy RPG called MazeWorld. "
            "Review the following event data for structural issues and thematic fit. "
            "The event should match the environment theme. "
            "Respond with a JSON object: {\"passed\": true/false, \"issues\": [\"...\"]}"
        ),
        user_message=(
            f"Environment: {env_type} ({env_name})\n"
            f"Event: {event_data}\n\n"
            "Check: Does this event have a name, description, and type? "
            "Does it fit the environment theme? "
            "If combat, does it have monsters? If puzzle, does it have a walk-away option?"
        ),
        max_tokens=300,
    )


def quest_check_prompt(quest_data: dict, available_npcs: list, available_items: list) -> LLMRequest:
    """Prompt to review a generated quest for completability."""
    return LLMRequest(
        system=(
            "You are a game content reviewer for a fantasy RPG called MazeWorld. "
            "Review the following quest for completability given the available NPCs and items. "
            "Respond with a JSON object: {\"passed\": true/false, \"issues\": [\"...\"]}"
        ),
        user_message=(
            f"Quest: {quest_data}\n"
            f"Available NPCs: {[n.get('name', n.get('id')) for n in available_npcs]}\n"
            f"Available Items: {[i.get('name', i.get('id')) for i in available_items]}\n\n"
            "Check: Can this quest be completed with the available entities? "
            "Are all referenced NPCs and items present?"
        ),
        max_tokens=300,
    )


def npc_check_prompt(npc_data: dict, env_type: str, env_name: str) -> LLMRequest:
    """Prompt to review an NPC for thematic fit and personality coherence."""
    return LLMRequest(
        system=(
            "You are a game content reviewer for a fantasy RPG called MazeWorld. "
            "Review the following NPC for thematic fit with the environment. "
            "Respond with a JSON object: {\"passed\": true/false, \"issues\": [\"...\"]}"
        ),
        user_message=(
            f"Environment: {env_type} ({env_name})\n"
            f"NPC name: {npc_data.get('name')}\n"
            f"Job: {npc_data.get('job')}\n"
            f"Personality: {npc_data.get('personality')}\n"
            f"Greeting: {npc_data.get('opening_greeting', '')}\n\n"
            "Check: Does this NPC fit the environment? Is the personality coherent? "
            "Does the greeting make sense for the character?"
        ),
        max_tokens=300,
    )


def item_check_prompt(items_data: dict, env_type: str, env_name: str) -> LLMRequest:
    """Prompt to review generated items for thematic fit."""
    return LLMRequest(
        system=(
            "You are a game content reviewer for a fantasy RPG called MazeWorld. "
            "Review the following items for thematic fit with the environment. "
            "Respond with a JSON object: {\"passed\": true/false, \"issues\": [\"...\"]}"
        ),
        user_message=(
            f"Environment: {env_type} ({env_name})\n"
            f"Items: {items_data}\n\n"
            "Check: Do these items fit the environment theme? "
            "Does each item have a name and appropriate stats for its category?"
        ),
        max_tokens=300,
    )
