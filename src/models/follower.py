"""Follower data model — NPC companions that travel with the player."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field

MAX_FOLLOWERS = 2


class Follower(BaseModel):
    npc_id: int
    name: str
    quest_id: Optional[int] = None
    joined_in_room: int = 0
    destination_room: int = 0
    personality: str = ""
    farewell_text: str = "Farewell, and thank you."
    dialogue_hints: List[str] = Field(default_factory=list)
    profile_image: Optional[str] = None
    description: str = ""
    original_npc: Any = Field(default=None, exclude=True)

    def get_hint(self) -> str:
        """Return a random hint from this follower, or a generic line."""
        if self.dialogue_hints:
            import random

            return random.choice(self.dialogue_hints)
        return f"{self.name} has nothing to say right now."

    def should_leave(self, current_room: int) -> bool:
        """Follower leaves if player moves past their destination room."""
        return current_room > self.destination_room
