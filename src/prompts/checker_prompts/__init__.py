"""Checker prompt templates for content validation.

These prompts are used by checkers to ask the LLM to review generated content
for theme coherence, quality, and required fields. Currently checkers use
rule-based logic; these templates are available for future LLM-assisted checking.
"""

NPC_CHECK_PROMPT = (
    "Review this NPC for a {environment} environment.\n"
    "NPC: {npc_json}\n\n"
    "Check:\n"
    "1. Name fits the {environment} setting\n"
    "2. Job/personality make sense for the environment\n"
    "3. Opening greeting is in-character\n"
    "4. No inappropriate content\n\n"
    "Return JSON: {{\"passed\": true/false, \"issues\": [...]}}"
)

MONSTER_CHECK_PROMPT = (
    "Review this monster for a {environment} environment at room level {level}.\n"
    "Monster: {monster_json}\n\n"
    "Check:\n"
    "1. Name/species fits the {environment} setting\n"
    "2. Stats are within level {level} scaling guidelines\n"
    "3. Abilities make thematic sense\n"
    "4. Loot table items exist in the world\n\n"
    "Return JSON: {{\"passed\": true/false, \"issues\": [...]}}"
)

ITEM_CHECK_PROMPT = (
    "Review this item for a {environment} environment at room level {level}.\n"
    "Item: {item_json}\n\n"
    "Check:\n"
    "1. Name fits the {environment} setting\n"
    "2. Category is correct (food/drink/tool/weapon/spell_scroll)\n"
    "3. Stats are reasonable for the item type\n"
    "4. Description makes sense\n\n"
    "Return JSON: {{\"passed\": true/false, \"issues\": [...]}}"
)

EVENT_CHECK_PROMPT = (
    "Review this encounter for a {environment} environment.\n"
    "Event: {event_json}\n\n"
    "Check:\n"
    "1. Name and description fit the {environment} setting\n"
    "2. Difficulty is appropriate for the encounter type\n"
    "3. Combat events have valid monsters\n"
    "4. Puzzle/event encounters have at least one solvable path\n"
    "5. Walk-away option exists for puzzles/events\n\n"
    "Return JSON: {{\"passed\": true/false, \"issues\": [...]}}"
)

QUEST_CHECK_PROMPT = (
    "Review this quest for a {environment} environment.\n"
    "Quest: {quest_json}\n"
    "Available NPCs: {npc_ids}\n"
    "Available items: {item_ids}\n"
    "Available events: {event_ids}\n\n"
    "Check:\n"
    "1. Quest title and description fit the environment\n"
    "2. All referenced NPCs, items, and events exist\n"
    "3. Quest is completable given available entities\n"
    "4. Reward makes sense for quest difficulty\n\n"
    "Return JSON: {{\"passed\": true/false, \"issues\": [...]}}"
)
