"""Validator prompts for LLM-based content validation.

These prompts support the Validator stage of the Gen -> Check -> Validate chain.
Validators perform deep logic and balance validation beyond structural checks.
"""

from src.prompts.base import LLMRequest


def event_validate_prompt(event_data: dict, tool_attributes: set, env_type: str) -> LLMRequest:
    """Prompt to validate event solvability and balance."""
    return LLMRequest(
        system=(
            "You are a game balance validator for a fantasy RPG called MazeWorld. "
            "Validate the following event for solvability and difficulty balance. "
            "Respond with a JSON object: {\"passed\": true/false, \"reasons\": [\"...\"]}"
        ),
        user_message=(
            f"Event: {event_data}\n"
            f"Available tool attributes: {list(tool_attributes)}\n"
            f"Environment: {env_type}\n\n"
            "Validate: Is this event solvable? If it's a puzzle, can the player solve it "
            "with available tools? Is the difficulty appropriate for the environment level?"
        ),
        max_tokens=300,
    )


def quest_validate_prompt(
    quest_data: dict, npc_ids: set, item_ids: set, event_ids: set,
) -> LLMRequest:
    """Prompt to validate quest completability in the world state."""
    return LLMRequest(
        system=(
            "You are a game balance validator for a fantasy RPG called MazeWorld. "
            "Validate quest completability given the current world state. "
            "Respond with a JSON object: {\"passed\": true/false, \"reasons\": [\"...\"]}"
        ),
        user_message=(
            f"Quest: {quest_data}\n"
            f"Available NPC IDs: {list(npc_ids)[:20]}\n"
            f"Available Item IDs: {list(item_ids)[:20]}\n"
            f"Available Event IDs: {list(event_ids)[:20]}\n\n"
            "Validate: Can this quest be completed? Are all referenced entities available? "
            "Is the quest chain depth reasonable (max 2 prerequisites)?"
        ),
        max_tokens=300,
    )


def class_validate_prompt(class_data: dict) -> LLMRequest:
    """Prompt to validate a player class for balance and completeness."""
    return LLMRequest(
        system=(
            "You are a game balance validator for a fantasy RPG called MazeWorld. "
            "Validate the following player class for stat balance, ability coverage, "
            "and thematic coherence. Total stat budget must equal 72. "
            "Respond with a JSON object: {\"passed\": true/false, \"reasons\": [\"...\"]}"
        ),
        user_message=(
            f"Class: {class_data}\n\n"
            "Validate: Does the stat total equal 72? Are primary stats 14-18, "
            "secondary 11-14, dump 6-10? Does the class have enough abilities/spells?"
        ),
        max_tokens=300,
    )


def monster_validate_prompt(monster_data: dict, room_level: int) -> LLMRequest:
    """Prompt to validate monster combat readiness and level appropriateness."""
    return LLMRequest(
        system=(
            "You are a game balance validator for a fantasy RPG called MazeWorld. "
            "Validate this monster for combat readiness and level-appropriate stats. "
            "Respond with a JSON object: {\"passed\": true/false, \"reasons\": [\"...\"]}"
        ),
        user_message=(
            f"Monster: {monster_data}\n"
            f"Room level: {room_level}\n\n"
            "Validate: Does the monster have valid HP, AC, and attack dice? "
            "Are the stats appropriate for the room level?"
        ),
        max_tokens=300,
    )
