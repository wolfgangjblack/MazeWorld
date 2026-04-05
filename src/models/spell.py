import random
from typing import Optional
from pydantic import BaseModel


# Elemental advantage chart
# fire > forest > water > fire; light <> dark (mutual)
ELEMENT_ADVANTAGE = {
    "fire": "forest",
    "forest": "water",
    "water": "fire",
    "light": "dark",
    "dark": "light",
}

SUPER_EFFECTIVE_MULT = 1.5
RESISTED_MULT = 0.5


def elemental_multiplier(attack_element: str, defender_element: Optional[str]) -> float:
    """Return the damage multiplier for attack_element vs defender_element."""
    if not defender_element or not attack_element:
        return 1.0
    if ELEMENT_ADVANTAGE.get(attack_element) == defender_element:
        return SUPER_EFFECTIVE_MULT
    if ELEMENT_ADVANTAGE.get(defender_element) == attack_element:
        return RESISTED_MULT
    return 1.0


class Spell(BaseModel):
    """A spell that can be cast in combat.

    spell_type:
      "damage_single"  - deal damage to 1 target   (costs 5 hunger)
      "damage_multi"   - deal damage to all targets (costs 10 hunger)
      "heal"           - restore HP to self          (costs 8 thirst)
      "buff_stat"      - +2 to a stat for N turns    (costs 5 thirst)
      "buff_sustain"   - restore hunger/thirst/turn   (costs 5 hunger)
    """

    name: str
    spell_type: str
    element: str  # "fire" | "water" | "forest" | "light" | "dark"
    stat: str  # governing stat: "INT" or "WIS"
    damage_dice: int = 0  # 0 for non-damage spells
    heal_amount: int = 0  # for healing spells
    buff_stat: Optional[str] = None  # which stat to buff
    buff_value: int = 2  # how much the buff adds
    buff_duration: int = 3  # turns
    hunger_cost: int = 0
    thirst_cost: int = 0
    targets: str = "single"  # "single" | "multi" | "self"
    description: str = ""

    def roll_damage(self) -> int:
        """Roll spell damage: 1d{damage_dice}."""
        if self.damage_dice <= 0:
            return 0
        return random.randint(1, self.damage_dice)


# Default spell cost table (from PDR)
SPELL_COSTS = {
    "damage_single": {"hunger": 5, "thirst": 0},
    "damage_multi": {"hunger": 10, "thirst": 0},
    "heal": {"hunger": 0, "thirst": 8},
    "buff_stat": {"hunger": 0, "thirst": 5},
    "buff_sustain": {"hunger": 5, "thirst": 0},
    "warrior_multi": {"hunger": 8, "thirst": 0},
    "warrior_utility": {"hunger": 5, "thirst": 0},
}
