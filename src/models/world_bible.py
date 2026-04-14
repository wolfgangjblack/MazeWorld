"""WorldBible — the living lore document for the generated world.

The Bible is the creative backbone: every generator reads it for context,
every generator writes back to it. It holds full lore paragraphs per entity,
not just structured data.
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from config import STORY_CONTEXT_LIMIT
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

    @staticmethod
    def room_index(room_id: str) -> int:
        """Extract the numeric index from a room_id like 'room_0'."""
        if "_" not in room_id:
            return 0
        try:
            return int(room_id.rsplit("_", 1)[-1])
        except ValueError:
            return 0

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

    def get_cumulative_context(self, room_id: str) -> str:
        """Return story context enriched with all *previous* rooms' generated content.

        For room_0 this is the same as get_story_context(). For room_N it
        includes NPCs, items, and monsters generated in rooms 0..N-1 so that
        generators for room N can build on what came before.

        The result is soft-capped at ``STORY_CONTEXT_LIMIT * 2`` characters to
        avoid unbounded growth in large worlds.
        """
        parts = [self.get_story_context(room_id)]

        current_idx = self.room_index(room_id)
        for prev_idx in range(current_idx):
            prev_id = f"room_{prev_idx}"
            prev_room = self.rooms.get(prev_id)
            if not prev_room:
                continue
            env_label = prev_room.environment_name or prev_room.environment
            header = f"\n--- Previously generated content (Room {prev_idx}: {env_label}) ---"
            prev_parts = [header]
            for npc in prev_room.npcs:
                if npc.name:
                    lore_snip = f" — {npc.lore[:120]}" if npc.lore else ""
                    prev_parts.append(f"  NPC: {npc.name}{lore_snip}")
            for item in prev_room.items:
                if item.name:
                    lore_snip = f" — {item.lore[:80]}" if item.lore else ""
                    prev_parts.append(f"  Item: {item.name}{lore_snip}")
            for mon in prev_room.monsters:
                if mon.name:
                    lore_snip = f" — {mon.lore[:80]}" if mon.lore else ""
                    prev_parts.append(f"  Monster: {mon.name}{lore_snip}")
            if len(prev_parts) > 1:
                parts.extend(prev_parts)

        result = "\n".join(parts)
        max_len = STORY_CONTEXT_LIMIT * 2
        if len(result) > max_len:
            result = result[:max_len] + "\n[...earlier rooms truncated]"
        return result

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
