"""Story data models — OverarchingStory, RoomStoryBeat, Faction."""

from pydantic import BaseModel, Field
from typing import Optional


class Faction(BaseModel):
    name: str
    description: str
    leader: str = ""
    threat_level: int = 1


class RoomStoryBeat(BaseModel):
    room_id: str
    summary: str
    faction_presence: Optional[str] = None
    escalation: int = 1  # 1-5, rises as player progresses


class OverarchingStory(BaseModel):
    seed: str = ""
    title: str = ""
    synopsis: str = ""
    faction: Optional[Faction] = None
    escalation_arc: list[str] = Field(default_factory=list)
    climax: str = ""
    final_boss_name: str = ""
    key_npc_names: list[str] = Field(default_factory=list)
    beats: list[RoomStoryBeat] = Field(default_factory=list)
