"""Save state serialization model."""

from pydantic import BaseModel, Field


class SaveState(BaseModel):
    """Full game state snapshot for save/load."""
    seed: int = -1
    room_id: str = "room_1"
    player_data: dict = Field(default_factory=dict)
    inventory_data: dict = Field(default_factory=dict)
    quest_log: list[dict] = Field(default_factory=list)
    npc_states: list[dict] = Field(default_factory=list)
    time_ticks: int = 0
    rooms_cleared: list[str] = Field(default_factory=list)
