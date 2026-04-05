"""WorldBible — cross-content reference index for the generated world."""

from pydantic import BaseModel, Field
from typing import Optional

from src.models.story import OverarchingStory


class EntityRef(BaseModel):
    entity_type: str  # "npc", "item", "monster", "encounter", "quest"
    room_id: str
    entity_id: str


class RoomBible(BaseModel):
    environment: str
    level: int = 1
    story_beat: str = ""
    maze_ref: str = ""
    npcs: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)
    monsters: list[str] = Field(default_factory=list)
    encounters: list[str] = Field(default_factory=list)
    quests: list[str] = Field(default_factory=list)
    gate_encounter_id: str = ""


class WorldBible(BaseModel):
    story: OverarchingStory = Field(default_factory=OverarchingStory)
    rooms: dict[str, RoomBible] = Field(default_factory=dict)
    entity_index: dict[str, EntityRef] = Field(default_factory=dict)
