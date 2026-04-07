"""Validator prompt templates for content validation.

These prompts are available for future LLM-assisted validation passes.
Current validators use rule-based logic; these templates provide the
structure for deeper semantic validation if needed.
"""

NPC_VALIDATE_PROMPT = (
    "Validate this NPC is complete and coherent for a {environment} world.\n"
    "NPC: {npc_json}\n\n"
    "Hard rules:\n"
    "- Must have a name, identity, and opening_greeting\n"
    "- MerchantNPCs must have shop_inventory with valid items\n"
    "- Personality must be appropriate (no offensive content)\n"
    "- Job must fit the {environment} environment\n\n"
    "Return JSON: {{\"passed\": true/false, \"reasons\": [...]}}"
)

MONSTER_VALIDATE_PROMPT = (
    "Validate this monster for room level {level} in a {environment} setting.\n"
    "Monster: {monster_json}\n\n"
    "Hard rules:\n"
    "- HP must be within level {level} scaling range\n"
    "- AC must be reasonable (not too high or low)\n"
    "- Abilities must be battle-scoped only\n"
    "- Loot table items must exist in the world\n"
    "- Monster must be thematically appropriate for {environment}\n\n"
    "Return JSON: {{\"passed\": true/false, \"reasons\": [...]}}"
)

ITEM_VALIDATE_PROMPT = (
    "Validate this item for a {environment} world at room level {level}.\n"
    "Item: {item_json}\n\n"
    "Hard rules:\n"
    "- Category must be one of: food, drink, tool, weapon, spell_scroll\n"
    "- Weapons must have attack_dice and stat_modifier\n"
    "- Tools must have an attribute and uses > 0\n"
    "- Food/drink must restore something (nutrition/hydration/health)\n"
    "- Stats should scale with room level\n\n"
    "Return JSON: {{\"passed\": true/false, \"reasons\": [...]}}"
)

EVENT_VALIDATE_PROMPT = (
    "Validate this encounter is solvable and complete.\n"
    "Event: {event_json}\n"
    "Available tool attributes: {tool_attributes}\n\n"
    "Hard rules:\n"
    "- Combat events must have monsters\n"
    "- Puzzles must have at least one solvable path with available tools\n"
    "- Events must have a walk-away option\n"
    "- time_gate must be 'day', 'night', or null\n\n"
    "Return JSON: {{\"passed\": true/false, \"reasons\": [...]}}"
)

QUEST_VALIDATE_PROMPT = (
    "Validate this quest is completable within the current world state.\n"
    "Quest: {quest_json}\n"
    "Available NPCs: {npc_ids}\n"
    "Available items on map: {item_ids}\n"
    "Available events: {event_ids}\n"
    "Existing quests: {quest_ids}\n\n"
    "Hard rules:\n"
    "- Giver NPC must exist and be active\n"
    "- Fetch quest items must exist on the map\n"
    "- Combat quest target event must exist\n"
    "- Escort quest NPC must exist\n"
    "- Delivery quest item and target NPC must exist\n"
    "- Prerequisite quest chain depth <= 2\n\n"
    "Return JSON: {{\"passed\": true/false, \"reasons\": [...]}}"
)
