"""Story data models — OverarchingStory, RoomStoryBeat, Faction."""

from pydantic import BaseModel, Field
from typing import Optional


class Faction(BaseModel):
    name: str
    description: str
    threat_level: int = 1


class RoomStoryBeat(BaseModel):
    room_id: str
    summary: str
    faction_presence: Optional[str] = None


class OverarchingStory(BaseModel):
    seed: str = ""
    title: str = ""
    synopsis: str = ""
    faction: Optional[Faction] = None
    beats: list[RoomStoryBeat] = Field(default_factory=list)
