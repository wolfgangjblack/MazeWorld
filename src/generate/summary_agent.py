"""Summary agent — reads the World Bible and generates player-facing narrative text.

Produces:
  - Quick story screen text (story synopsis + current room intro)
  - Room transition narrative paragraphs
  - Game over paragraph
  - Victory paragraph
  - Portrait prompts enriched with Bible context
"""

from __future__ import annotations

import logging

from src.models.world_bible import WorldBible
from src.models.story import OverarchingStory
from src.generate.llm_client import generate
from src.prompts.base import LLMRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------

_NARRATIVE_SYSTEM = (
    "You are a narrator for a fantasy dungeon-crawler video game. "
    "Write immersive, concise player-facing text. Keep responses under 3 sentences "
    "unless asked for more. Use second person (\"you\"). Match the tone of the "
    "world lore provided. Do not break the fourth wall."
)


def generate_story_synopsis(bible: WorldBible) -> str:
    """Generate a player-facing story synopsis from the World Bible."""
    story = bible.story
    if not story.title:
        return "Your adventure awaits. Explore the maze and survive."

    context = _build_story_context(story)
    request = LLMRequest(
        system=_NARRATIVE_SYSTEM,
        user_message=(
            f"World lore:\n{context}\n\n"
            "Write a short story synopsis (3-5 sentences) for the player's "
            "quick-story screen. Cover the overarching threat, the faction involved, "
            "and what the player must do."
        ),
        max_tokens=200,
    )
    try:
        return generate(request).strip()
    except Exception:
        logger.warning("LLM synopsis generation failed; using fallback")
        return story.synopsis or f"{story.title} — a tale of danger and discovery."


def generate_room_intro(bible: WorldBible, room_id: str,
                        env_name: str, env_type: str) -> str:
    """Generate a narrative paragraph for entering a new room."""
    story = bible.story
    room = bible.rooms.get(room_id)
    beat = room.story_beat if room else ""

    context = _build_story_context(story)
    request = LLMRequest(
        system=_NARRATIVE_SYSTEM,
        user_message=(
            f"World lore:\n{context}\n\n"
            f"The player enters a new area: {env_name} (a {env_type}).\n"
            f"Story beat for this room: {beat}\n\n"
            "Write a short atmospheric paragraph (2-3 sentences) describing "
            "what the player sees and feels as they enter this area."
        ),
        max_tokens=150,
    )
    try:
        return generate(request).strip()
    except Exception:
        logger.warning("LLM room intro generation failed; using fallback")
        return beat or f"You enter {env_name}. A {env_type} stretches before you."


def generate_game_over_text(bible: WorldBible, player_name: str,
                            player_class: str) -> str:
    """Generate a somber game-over paragraph."""
    story = bible.story
    context = _build_story_context(story)
    request = LLMRequest(
        system=_NARRATIVE_SYSTEM,
        user_message=(
            f"World lore:\n{context}\n\n"
            f"The player ({player_name} the {player_class}) has died.\n"
            "Write a somber, story-contextual game over paragraph (2-3 sentences). "
            "Reference what their death means for the world."
        ),
        max_tokens=150,
    )
    try:
        return generate(request).strip()
    except Exception:
        logger.warning("LLM game over generation failed; using fallback")
        return (
            f"{player_name} the {player_class} has fallen. "
            "The darkness spreads unchecked."
        )


def generate_victory_text(bible: WorldBible, player_name: str,
                          player_class: str) -> str:
    """Generate a victory paragraph — story resolution."""
    story = bible.story
    context = _build_story_context(story)
    request = LLMRequest(
        system=_NARRATIVE_SYSTEM,
        user_message=(
            f"World lore:\n{context}\n\n"
            f"The player ({player_name} the {player_class}) has won!\n"
            "Write a triumphant victory paragraph (2-3 sentences). "
            "Describe what the player accomplished and how the world is saved."
        ),
        max_tokens=150,
    )
    try:
        return generate(request).strip()
    except Exception:
        logger.warning("LLM victory generation failed; using fallback")
        return (
            f"{player_name} the {player_class} stands victorious! "
            "The threat is vanquished, and peace returns to the land."
        )


# ---------------------------------------------------------------------------
# Bible-enriched portrait prompts
# ---------------------------------------------------------------------------

_PORTRAIT_STYLE = "nano-banana fantasy game aesthetic, detailed portrait"


def build_npc_portrait_prompt(npc_data: dict, bible: WorldBible,
                              room_id: str = "") -> str:
    """Build a portrait prompt for an NPC using Bible context."""
    name = npc_data.get("name", "NPC")
    personality = npc_data.get("personality", "")
    job = npc_data.get("job", "")
    room = bible.rooms.get(room_id)
    env = room.environment if room else "dungeon"

    parts = [f"portrait of {name}"]
    if job:
        parts.append(f"a {job}")
    if personality:
        parts.append(personality[:60])
    parts.append(f"in a {env} environment")
    parts.append(_PORTRAIT_STYLE)
    return ", ".join(parts)


def build_monster_portrait_prompt(monster_data: dict, bible: WorldBible,
                                  room_id: str = "") -> str:
    """Build a portrait prompt for a monster using Bible context."""
    species = monster_data.get("species", monster_data.get("name", "monster"))
    element = monster_data.get("elemental_affinity", "")
    room = bible.rooms.get(room_id)
    env = room.environment if room else "dungeon"
    story_role = monster_data.get("description", "")

    parts = [f"portrait of a {species}"]
    if element:
        parts.append(f"{element} elemental")
    parts.append(f"in a {env} setting")
    if story_role:
        parts.append(story_role[:60])
    parts.append(_PORTRAIT_STYLE)
    return ", ".join(parts)


def build_class_portrait_prompt(class_data: dict, bible: WorldBible) -> str:
    """Build a portrait prompt for a player class using Bible context."""
    name = class_data.get("name", "Adventurer")
    archetype = class_data.get("archetype", "warrior")
    flavor = class_data.get("flavor_text", "")
    env = class_data.get("environment", "dungeon")

    parts = [f"portrait of a {name} ({archetype})"]
    if flavor:
        parts.append(flavor[:60])
    parts.append(f"in a {env} world")
    parts.append(_PORTRAIT_STYLE)
    return ", ".join(parts)


def build_item_portrait_prompt(item_data: dict, bible: WorldBible,
                               room_id: str = "") -> str:
    """Build a portrait prompt for an item using Bible context."""
    name = item_data.get("name", "item")
    desc = item_data.get("desc", item_data.get("description", ""))
    room = bible.rooms.get(room_id)
    env = room.environment if room else "dungeon"

    parts = [f"a {name}"]
    if desc:
        parts.append(desc[:60])
    parts.append(f"in a {env} setting")
    parts.append(_PORTRAIT_STYLE)
    return ", ".join(parts)


def build_event_portrait_prompt(event_data: dict, bible: WorldBible,
                                room_id: str = "") -> str:
    """Build a portrait prompt for a puzzle or event encounter."""
    name = event_data.get("name", "encounter")
    desc = event_data.get("description", "")
    etype = event_data.get("type", "event")
    room = bible.rooms.get(room_id)
    env = room.environment if room else "dungeon"

    if etype == "puzzle":
        parts = [f"{name.lower()} blocking a {env} passage"]
        if desc:
            parts.append(desc[:80])
        parts.append("environmental obstacle scene")
    elif etype == "combat":
        parts = [f"{name.lower()} in a {env} environment"]
        if desc:
            parts.append(desc[:80])
        parts.append("fantasy combat scene")
    else:
        parts = [f"{name.lower()} in a {env} setting"]
        if desc:
            parts.append(desc[:80])
        parts.append("tense narrative encounter")

    parts.append(_PORTRAIT_STYLE)
    return ", ".join(parts)


def build_room_portrait_prompt(room_id: str, bible: WorldBible) -> str:
    """Build a portrait prompt for a room/environment using Bible context."""
    room = bible.rooms.get(room_id)
    if not room:
        return f"a fantasy dungeon room, {_PORTRAIT_STYLE}"

    parts = [f"a {room.environment} environment"]
    if room.story_beat:
        parts.append(room.story_beat[:80])
    parts.append("wide landscape view")
    parts.append(_PORTRAIT_STYLE)
    return ", ".join(parts)


def build_game_over_portrait_prompt(bible: WorldBible) -> str:
    """Build a dark/somber portrait prompt for the game over screen."""
    story = bible.story
    parts = ["dark somber scene"]
    if story.title:
        parts.append(f"from the world of {story.title}")
    parts.append("fallen hero, shadows consuming the land")
    parts.append(_PORTRAIT_STYLE)
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _build_story_context(story: OverarchingStory) -> str:
    """Build a compact context string from the story for LLM prompts."""
    parts = []
    if story.title:
        parts.append(f"Title: {story.title}")
    if story.synopsis:
        parts.append(f"Synopsis: {story.synopsis}")
    if story.faction:
        parts.append(
            f"Faction: {story.faction.name} — {story.faction.description}"
        )
        if story.faction.leader:
            parts.append(f"Leader: {story.faction.leader}")
    if story.climax:
        parts.append(f"Climax: {story.climax}")
    if story.final_boss_name:
        parts.append(f"Final boss: {story.final_boss_name}")
    return "\n".join(parts)
