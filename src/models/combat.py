"""Combat data models — CombatState, TurnOrder, Action.

Populated in Phase 2 when the combat system is built.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class CombatAction(str, Enum):
    ATTACK = "attack"
    MULTI_ATTACK = "multi_attack"
    CAST_SPELL = "cast_spell"
    USE_ITEM = "use_item"
    FLEE = "flee"
    REST = "rest"


class CombatState(BaseModel):
    """Tracks the state of an active combat encounter."""
    active: bool = False
    turn_index: int = 0
    combatants: list = Field(default_factory=list)
    round_number: int = 1
