"""Follower data model — NPC companions that travel with the player."""

from pydantic import BaseModel
from typing import Optional


class Follower(BaseModel):
    npc_id: int
    name: str
    quest_id: Optional[str] = None
    joined_in_room: int = 1
