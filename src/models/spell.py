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


# Physical damage type triangle
# slashing > piercing > bludgeoning > slashing
PHYSICAL_TYPES = ["slashing", "piercing", "bludgeoning"]

PHYSICAL_ADVANTAGE = {
    "slashing": "piercing",
    "piercing": "bludgeoning",
    "bludgeoning": "slashing",
}


def physical_multiplier(attack_type: str, defender_type: Optional[str]) -> float:
    """Return the damage multiplier for physical attack_type vs defender_type."""
    if not defender_type or not attack_type:
        return 1.0
    if attack_type == "physical" or defender_type == "physical":
        return 1.0
    if PHYSICAL_ADVANTAGE.get(attack_type) == defender_type:
        return SUPER_EFFECTIVE_MULT
    if PHYSICAL_ADVANTAGE.get(defender_type) == attack_type:
        return RESISTED_MULT
    return 1.0


# Stamina cost derived from damage dice (explicit table + fallback)
SPELL_STAMINA_BY_DICE = {4: 2, 6: 4, 8: 5, 10: 7}


def compute_stamina_cost(spell_type: str, damage_dice: int = 0, targets: str = "single") -> int:
    """Derive stamina cost from spell type and damage dice."""
    if spell_type == "heal":
        return 5
    if spell_type == "buff_stat":
        return 3
    if spell_type == "buff_sustain":
        return 2
    base = SPELL_STAMINA_BY_DICE.get(damage_dice, max(2, damage_dice // 2))
    if targets == "multi" or spell_type == "damage_multi":
        return min(10, base * 2)
    return base


class Spell(BaseModel):
    """A spell that can be cast in combat.

    spell_type:
      "damage_single"  - deal damage to 1 target
      "damage_multi"   - deal damage to all targets
      "heal"           - restore HP to self
      "buff_stat"      - +2 to a stat for N turns
      "buff_sustain"   - restore stamina per turn
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
    stamina_cost: int = 0
    targets: str = "single"  # "single" | "multi" | "self"
    description: str = ""

    def roll_damage(self) -> int:
        """Roll spell damage: 1d{damage_dice}."""
        if self.damage_dice <= 0:
            return 0
        return random.randint(1, self.damage_dice)


SPELL_COSTS = {
    "damage_single": 4,
    "damage_multi": 8,
    "heal": 5,
    "buff_stat": 3,
    "buff_sustain": 2,
    "warrior_multi": 6,
    "warrior_utility": 3,
}
