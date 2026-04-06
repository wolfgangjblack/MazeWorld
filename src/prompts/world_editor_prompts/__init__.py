"""World Editor prompts for LLM-based cross-content validation and Bible building.

These prompts support the World Editor role which builds and maintains the
WorldBible — the cross-content reference index ensuring narrative coherence.
"""

from src.prompts.base import LLMRequest


def cross_validate_prompt(bible_context: dict, quest_list: list, npc_names: list) -> LLMRequest:
    """Prompt to cross-validate world content for narrative coherence."""
    return LLMRequest(
        system=(
            "You are the World Editor for a fantasy RPG called MazeWorld. "
            "Your job is to cross-validate all generated content for narrative coherence. "
            "Check that quests reference valid NPCs, items, and events. "
            "Check that the story arc is consistent across rooms. "
            "Respond with a JSON object: {\"issues\": [\"...\"], \"suggestions\": [\"...\"]}"
        ),
        user_message=(
            f"World context: {bible_context}\n"
            f"Quests: {quest_list[:10]}\n"
            f"NPC names: {npc_names[:20]}\n\n"
            "Cross-validate: Are quest references valid? Does the story flow between rooms? "
            "Are there any narrative inconsistencies or orphaned references?"
        ),
        max_tokens=500,
    )


def bible_lore_prompt(
    story_title: str, story_synopsis: str, faction_name: str,
    room_environment: str, room_level: int, story_beat: str,
) -> LLMRequest:
    """Prompt to generate lore context for the World Bible.

    Used to provide narrative guidance to content generators so they produce
    thematically coherent content connected to the overarching story.
    """
    return LLMRequest(
        system=(
            "You are the World Editor for MazeWorld. Generate a brief lore context "
            "that content generators should reference when creating NPCs, items, events, "
            "and quests for this room. Include faction presence, environmental flavor, "
            "and narrative hooks that connect to the overarching story. "
            "Respond with a JSON object: {\"lore_context\": \"...\", \"themes\": [\"...\"], "
            "\"naming_hints\": [\"...\"]}"
        ),
        user_message=(
            f"Story: {story_title} — {story_synopsis}\n"
            f"Faction: {faction_name}\n"
            f"Room environment: {room_environment} (level {room_level})\n"
            f"Story beat: {story_beat}\n\n"
            "Generate lore context for this room's content generators."
        ),
        max_tokens=400,
    )


def story_consistency_prompt(
    story: dict, rooms_generated: list[dict],
) -> LLMRequest:
    """Prompt to check story consistency across all generated rooms."""
    return LLMRequest(
        system=(
            "You are the World Editor for MazeWorld. Review the story arc and all "
            "generated rooms for consistency. Check that escalation progresses, "
            "faction presence makes sense, and the narrative builds toward the climax. "
            "Respond with a JSON object: {\"consistent\": true/false, \"issues\": [\"...\"]}"
        ),
        user_message=(
            f"Story: {story}\n"
            f"Rooms generated: {rooms_generated}\n\n"
            "Check story consistency: Does escalation progress? "
            "Is faction presence coherent? Does the narrative build properly?"
        ),
        max_tokens=400,
    )
