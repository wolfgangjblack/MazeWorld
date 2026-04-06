"""Monster data models."""

import uuid as _uuid

from pydantic import BaseModel, Field
from typing import Optional


class LootDrop(BaseModel):
    item_id: int
    probability: float = 0.5


class Monster(BaseModel):
    id: str = Field(default_factory=lambda: str(_uuid.uuid4()))
    species: str
    name: Optional[str] = None
    environment: str
    level: int = 1
    hp: int = 10
    ac: int = 10
    STR: int = 10
    DEX: int = 10
    attack_name: str = "attack"
    damage_dice: str = "1d6"
    damage_type: str = "physical"
    elemental_affinity: Optional[str] = None
    abilities: list[str] = Field(default_factory=list)
    loot_table: list[LootDrop] = Field(default_factory=list)
    portrait_path: Optional[str] = None
