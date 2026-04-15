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


# ---------------------------------------------------------------------------
# Spell dice progression (shares DIE_PROGRESSION from weapon.py)
# ---------------------------------------------------------------------------

SPELL_TYPE_BASE_TIER = {
    "damage_single": 1,
    "damage_multi": 0,
    "heal": 1,
}


def compute_spell_dice(available_at_room: int, spell_type: str) -> tuple[int, int]:
    """Compute (num_dice, die_sides) for a spell based on when it's learned."""
    from src.models.weapon import DIE_PROGRESSION

    base = SPELL_TYPE_BASE_TIER.get(spell_type, 1)
    tier = base + available_at_room
    tier = min(tier, len(DIE_PROGRESSION) - 1)
    return DIE_PROGRESSION[tier]


def compute_stamina_cost(
    die_sides: int = 0, num_dice: int = 1, targets: str = "single", spell_type: str = "damage_single"
) -> int:
    """Derive stamina cost from spell dice and type. Scales naturally to any level."""
    if spell_type == "heal":
        return 3 + num_dice + (die_sides // 4)
    if spell_type in ("buff_stat", "buff_sustain"):
        return 2 + num_dice
    base = 1 + num_dice + (die_sides // 3)
    if targets == "multi" or spell_type == "damage_multi":
        return min(15, base * 2)
    return base


# ---------------------------------------------------------------------------
# Spell distribution tables (used by skeleton pre-roll)
# ---------------------------------------------------------------------------

SPELL_DISTRIBUTIONS = {
    "mage": {
        "starting": [
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_multi", "targets": "multi"},
            {"spell_type": "buff_stat", "targets": "self"},
        ],
        "pool": [
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_multi", "targets": "multi"},
            {"spell_type": "buff_stat", "targets": "self"},
            {"spell_type": "buff_sustain", "targets": "self"},
        ],
    },
    "healer": {
        "starting": [
            {"spell_type": "heal", "targets": "self"},
            {"spell_type": "buff_stat", "targets": "self"},
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "buff_sustain", "targets": "self"},
        ],
        "pool": [
            {"spell_type": "heal", "targets": "self"},
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "buff_stat", "targets": "self"},
            {"spell_type": "damage_multi", "targets": "multi"},
        ],
    },
    "warrior": {"starting": [], "pool": []},
    "jester": {"starting": [], "pool": []},
}

ARCHETYPE_SPELL_STAT = {
    "mage": "INT",
    "healer": "WIS",
    "warrior": "STR",
    "jester": "LUCK",
}


def roll_spell_skeleton(
    archetype: str, slot: dict, available_at_room: int = 0, class_element: str = "fire"
) -> dict:
    """Pre-roll a spell's mechanical identity."""
    spell_type = slot["spell_type"]
    targets = slot["targets"]
    stat = ARCHETYPE_SPELL_STAT.get(archetype, "INT")

    if spell_type in ("damage_single", "damage_multi", "heal"):
        num_dice, die_sides = compute_spell_dice(available_at_room, spell_type)
    else:
        num_dice, die_sides = 0, 0

    stamina_cost = compute_stamina_cost(die_sides, num_dice, targets, spell_type)

    return {
        "spell_type": spell_type,
        "element": class_element,
        "stat": stat,
        "targets": targets,
        "num_dice": num_dice,
        "die_sides": die_sides,
        "stamina_cost": stamina_cost,
        "available_at_room": available_at_room,
    }


def roll_jester_spell_skeletons(all_pool_skeletons: list[dict]) -> list[dict]:
    """Jester steals 0-3 random spells from other archetypes' pools."""
    count = random.randint(0, 3)
    stolen = [dict(s) for s in random.sample(all_pool_skeletons, min(count, len(all_pool_skeletons)))]
    for s in stolen:
        s["stat"] = "LUCK"
    return stolen


# ---------------------------------------------------------------------------
# Spell model
# ---------------------------------------------------------------------------


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
    num_dice: int = 0
    die_sides: int = 0
    heal_amount: int = 0
    buff_stat: Optional[str] = None
    buff_value: int = 2
    buff_duration: int = 3
    stamina_cost: int = 0
    targets: str = "single"  # "single" | "multi" | "self"
    description: str = ""

    def roll_damage(self) -> int:
        """Roll spell damage: {num_dice}d{die_sides}."""
        if self.num_dice <= 0 or self.die_sides <= 0:
            return 0
        return sum(random.randint(1, self.die_sides) for _ in range(self.num_dice))

    @property
    def dice_expr(self) -> str:
        if self.num_dice <= 0:
            return "0"
        return f"{self.num_dice}d{self.die_sides}"
