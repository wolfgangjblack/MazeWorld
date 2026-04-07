"""Base Generator class for Bible-driven content generation.

Every entity generator inherits from this. The contract:
  1. Read the WorldBible for context (story beats, existing entities)
  2. Generate content (LLM call or fallback)
  3. Write results back to the Bible
"""

import logging
from abc import ABC, abstractmethod

from src.models.world_bible import WorldBible, EntityLore

logger = logging.getLogger(__name__)


class Generator(ABC):
    """Base class for all entity generators."""

    def __init__(self, bible: WorldBible, room_id: str, room_level: int = 1):
        self.bible = bible
        self.room_id = room_id
        self.room_level = room_level
        self._story_context = bible.get_story_context(room_id)
        room = bible.get_room(room_id)
        self.environment = room.environment if room else "city"
        self.environment_name = room.environment_name if room else "Unknown"

    @abstractmethod
    async def generate(self) -> list:
        """Generate entities. Returns list of generated objects."""
        ...

    def _write_to_bible(self, entity_type: str, name: str, lore: str,
                        entity_id: str = "", tags: list[str] | None = None):
        """Write a generated entity back to the Bible."""
        entry = EntityLore(
            entity_type=entity_type,
            entity_id=entity_id,
            name=name,
            room_id=self.room_id,
            lore=lore,
            tags=tags or [],
        )
        if entity_type == "npc":
            self.bible.add_npc(self.room_id, entry)
        elif entity_type == "item":
            self.bible.add_item(self.room_id, entry)
        elif entity_type == "monster":
            self.bible.add_monster(self.room_id, entry)
        elif entity_type == "player_class":
            self.bible.add_player_class(entry)
