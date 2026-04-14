"""Story data models — OverarchingStory, RoomStoryBeat, Faction, and story entities."""

from typing import Optional

from pydantic import BaseModel, Field


class Faction(BaseModel):
    name: str
    description: str
    history: str = ""
    leader: str = ""
    threat_level: int = 1


class StoryNPC(BaseModel):
    """A story-important NPC generated during Step 1 (story generation)."""
    name: str
    role: str = ""  # e.g. "ally", "betrayer", "quest_giver", "faction_leader"
    backstory: str = ""  # Full lore paragraph
    room_id: str = ""  # Room they appear in
    personality: str = ""
    job: str = ""


class StoryItem(BaseModel):
    """A story-important item generated during Step 1."""
    name: str
    description: str = ""
    lore: str = ""  # Full lore paragraph — why it matters to the story
    room_id: str = ""


class StoryMonster(BaseModel):
    """A story-important monster (e.g. faction member, room boss)."""
    name: str
    description: str = ""
    lore: str = ""  # Full lore paragraph — why it guards this area, its history
    room_id: str = ""
    is_boss: bool = False
    species: str = ""


class RoomStoryBeat(BaseModel):
    room_id: str
    summary: str
    faction_presence: Optional[str] = None
    escalation: int = 1  # 1-5, rises as player progresses
    boss_name: str = ""
    boss_lore: str = ""


class OverarchingStory(BaseModel):
    seed: str = ""
    title: str = ""
    synopsis: str = ""
    faction: Optional[Faction] = None
    escalation_arc: list[str] = Field(default_factory=list)
    climax: str = ""
    final_boss_name: str = ""
    final_boss_lore: str = ""
    key_npc_names: list[str] = Field(default_factory=list)
    beats: list[RoomStoryBeat] = Field(default_factory=list)
    # Story-important entities generated upfront in Step 1
    story_npcs: list[StoryNPC] = Field(default_factory=list)
    story_items: list[StoryItem] = Field(default_factory=list)
    story_monsters: list[StoryMonster] = Field(default_factory=list)
