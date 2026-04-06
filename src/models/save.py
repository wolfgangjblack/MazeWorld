"""Save state serialization model — full game state snapshot."""

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
    room_id: str = "room_1"

    # Player state
    player_data: dict = Field(default_factory=dict)

    # Maze state
    maze_grid: list = Field(default_factory=list)
    maze_environment: str = ""
    maze_environment_name: str = ""

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

    # Timing
    time_played_seconds: float = 0.0
