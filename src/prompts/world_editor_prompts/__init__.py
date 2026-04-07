"""World editor prompt templates for coherence checking.

These prompts are available for future LLM-assisted gameplay auditing.
The current gameplay_audit() in world_editor.py uses rule-based logic;
these templates provide structure for deeper narrative coherence checks.
"""

GAMEPLAY_AUDIT_PROMPT = (
    "You are the Gameplay Agent for MazeWorld. Review the generated world and "
    "confirm that the overarching story, entities, and quests are coherent.\n\n"
    "World Bible:\n{bible_json}\n\n"
    "Check:\n"
    "1. Does the overarching story have a clear faction, escalation, and climax?\n"
    "2. Do story quests reference the faction and advance the narrative?\n"
    "3. Are all quest items, NPCs, and events present in the world?\n"
    "4. Do multi-step quests form logical chains?\n"
    "5. Are monster encounters appropriately themed and scaled?\n"
    "6. Is the mix of time-gated encounters reasonable (~20%)?\n\n"
    "Return JSON: {{\"issues\": [{{\"severity\": \"warning\"|\"error\", "
    "\"message\": \"...\", \"entity_id\": \"...\"}}]}}"
)

NARRATIVE_COHERENCE_PROMPT = (
    "Review the narrative coherence of this room.\n"
    "Environment: {environment}\n"
    "Story beat: {story_beat}\n"
    "NPCs: {npc_names}\n"
    "Quests: {quest_titles}\n"
    "Faction: {faction_name}\n\n"
    "Check:\n"
    "1. Do the NPCs and quests fit the story beat?\n"
    "2. Is the faction's presence reflected in encounters and quests?\n"
    "3. Do quest rewards make narrative sense?\n\n"
    "Return JSON: {{\"coherent\": true/false, \"suggestions\": [...]}}"
)

CROSS_ROOM_QUEST_PROMPT = (
    "Validate cross-room quest completability.\n"
    "Quest: {quest_json}\n"
    "Current room: {current_room}\n"
    "Next room entities: {next_room_entities}\n\n"
    "Check:\n"
    "1. Quest target is in the current room or at most 1 room ahead\n"
    "2. No backtracking required\n"
    "3. Quest can be completed with available resources\n\n"
    "Return JSON: {{\"completable\": true/false, \"reasons\": [...]}}"
)
