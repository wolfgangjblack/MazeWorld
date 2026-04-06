"""Combat data models — CombatAction and CombatState enums.

Single source of truth for combat enumerations used by
CombatController, CombatView, and GameController.
"""

from enum import Enum


class CombatAction(str, Enum):
    ATTACK = "attack"
    MULTI_ATTACK = "multi_attack"
    CAST_SPELL = "cast_spell"
    USE_ITEM = "use_item"
    FLEE = "flee"
    REST = "rest"
    GAMBLE = "gamble"  # Jester only
    SWAP_WEAPON = "swap_weapon"


class CombatState(str, Enum):
    ONGOING = "ongoing"
    VICTORY = "victory"
    DEFEAT = "defeat"
    FLED = "fled"
