"""WorldBible — the living lore document for the generated world.

The Bible is the creative backbone: every generator reads it for context,
every generator writes back to it. It holds full lore paragraphs per entity,
not just structured data.
"""

import json
from pathlib import Path
from pydantic import BaseModel, Field

from src.models.story import OverarchingStory


class EntityRef(BaseModel):
    """Legacy cross-reference entry. Kept for backward compatibility with world_editor."""
    entity_type: str  # "npc", "item", "monster", "encounter", "quest"
    room_id: str = ""
    entity_id: str = ""


class EntityLore(BaseModel):
    """Full lore entry for any entity in the world."""
    entity_type: str  # "npc", "item", "monster", "player_class"
    entity_id: str = ""
    name: str = ""
    room_id: str = ""
    lore: str = ""  # Full lore paragraph
    tags: list[str] = Field(default_factory=list)  # e.g. ["story", "faction", "boss"]


class RoomBible(BaseModel):
    environment: str
    environment_name: str = ""
    level: int = 1
    story_beat: str = ""
    boss_name: str = ""
    boss_lore: str = ""
    maze_ref: str = ""
    npcs: list[EntityLore] = Field(default_factory=list)
    items: list[EntityLore] = Field(default_factory=list)
    monsters: list[EntityLore] = Field(default_factory=list)
    encounters: list[str] = Field(default_factory=list)
    quests: list[str] = Field(default_factory=list)
    gate_encounter_id: str = ""


class WorldBible(BaseModel):
    story: OverarchingStory = Field(default_factory=OverarchingStory)
    rooms: dict[str, RoomBible] = Field(default_factory=dict)
    player_classes: list[EntityLore] = Field(default_factory=list)
    entity_index: dict[str, EntityRef] = Field(default_factory=dict)  # Legacy compat

    # --- Read helpers ---

    def get_room(self, room_id: str) -> RoomBible | None:
        return self.rooms.get(room_id)

    def get_story_context(self, room_id: str) -> str:
        """Return a textual summary of story context for a room's generators."""
        parts = [f"Title: {self.story.title}", f"Synopsis: {self.story.synopsis}"]
        if self.story.faction:
            parts.append(
                f"Faction: {self.story.faction.name} — {self.story.faction.description}"
            )
            if self.story.faction.history:
                parts.append(f"Faction history: {self.story.faction.history}")
        beat = next((b for b in self.story.beats if b.room_id == room_id), None)
        if beat:
            parts.append(f"Room story beat: {beat.summary}")
            if beat.boss_name:
                parts.append(f"Room boss: {beat.boss_name} — {beat.boss_lore}")
        # Include story NPCs for this room
        for npc in self.story.story_npcs:
            if npc.room_id == room_id:
                parts.append(f"Story NPC: {npc.name} — {npc.backstory}")
        # Include story items
        for item in self.story.story_items:
            if item.room_id == room_id:
                parts.append(f"Story item: {item.name} — {item.lore}")
        # Include story monsters
        for mon in self.story.story_monsters:
            if mon.room_id == room_id:
                parts.append(f"Story monster: {mon.name} — {mon.lore}")
        return "\n".join(parts)

    def get_all_npc_names(self) -> list[str]:
        """Return all NPC names across all rooms."""
        names = []
        for room in self.rooms.values():
            names.extend(e.name for e in room.npcs if e.name)
        return names

    # --- Write helpers ---

    def add_npc(self, room_id: str, lore: EntityLore):
        if room_id in self.rooms:
            self.rooms[room_id].npcs.append(lore)

    def add_item(self, room_id: str, lore: EntityLore):
        if room_id in self.rooms:
            self.rooms[room_id].items.append(lore)

    def add_monster(self, room_id: str, lore: EntityLore):
        if room_id in self.rooms:
            self.rooms[room_id].monsters.append(lore)

    def add_player_class(self, lore: EntityLore):
        self.player_classes.append(lore)

    # --- Persistence ---

    def persist(self, path: str = "data/world_bible.json"):
        """Write the Bible to disk."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)

    @classmethod
    def load(cls, path: str = "data/world_bible.json") -> "WorldBible":
        """Load a Bible from disk."""
        with open(path) as f:
            return cls.model_validate(json.load(f))
