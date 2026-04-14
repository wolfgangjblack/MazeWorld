"""Save state serialization model — full game state snapshot."""

from typing import Optional

from pydantic import BaseModel, Field


class SaveMetadata(BaseModel):
    """Display info shown in save file lists."""

    character_name: str = "Adventurer"
    character_class: str = ""
    room_level: int = 1
    time_played_seconds: float = 0.0
    last_save_date: str = ""
    seed: int = -1


class SaveState(BaseModel):
    """Full game state snapshot for save/load."""

    # Version for forward-compat validation
    version: int = 1

    # Metadata (for display in load screen)
    metadata: SaveMetadata = Field(default_factory=SaveMetadata)

    # World identity
    seed: int = -1
    current_room: int = 0
    total_rooms: int = 1

    # Player state
    player_data: dict = Field(default_factory=dict)

    # Maze state
    maze_grid: list = Field(default_factory=list)
    maze_environment: str = ""
    maze_environment_name: str = ""
    maze_door_position: Optional[list] = None
    maze_door_revealed: bool = False
    maze_gate_encounter_id: Optional[int] = None

    # NPC states (position, dialogue history, has_met_player, shop inventory)
    npc_states: list[dict] = Field(default_factory=list)

    # Event states (which are resolved, monster HP for active combats)
    event_states: dict = Field(default_factory=dict)

    # Quest states (status, current_step for multi-step)
    quest_states: dict = Field(default_factory=dict)

    # Follower data
    follower_data: list[dict] = Field(default_factory=list)

    # Event position map (tile positions to event IDs)
    event_position_map: dict = Field(default_factory=dict)

    # Fog of war revealed tiles
    fog_data: dict = Field(default_factory=dict)

    # Day/night cycle state
    day_night_data: dict = Field(default_factory=dict)

    # Room progression
    gate_cleared: bool = False
    gc_stats: dict = Field(
        default_factory=lambda: {
            "monsters_killed": 0,
            "items_used": 0,
            "rooms_cleared": 0,
        }
    )

    # Timing
    time_played_seconds: float = 0.0
