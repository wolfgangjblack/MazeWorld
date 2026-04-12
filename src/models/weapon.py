import random
from typing import Optional
from pydantic import BaseModel


class Weapon(BaseModel):
    """A weapon used in combat.

    Types:
      heavy  - STR-based, 1d8-1d10 (warrior primary)
      light  - DEX-based, 1d4-1d6 (fast, lower damage)
      simple - STR or INT, 1d4-1d6 (mage/healer weapons)
      wild   - varies (wild card / jester)
    """

    name: str
    weapon_type: str  # "heavy" | "light" | "simple" | "wild"
    stat: str  # "STR" | "DEX" | "INT" — which stat drives attack/damage
    damage_dice: int  # number of sides on the damage die (e.g. 6 = 1d6)
    damage_bonus: int = 0  # flat bonus added to damage
    description: str = ""
    profile_image: Optional[str] = None
    portrait_prompt: Optional[str] = None

    def roll_damage(self) -> int:
        """Roll weapon damage: 1d{damage_dice} + damage_bonus."""
        return random.randint(1, self.damage_dice) + self.damage_bonus


# Starter weapons for quick prototyping / tests
STARTER_WEAPONS = {
    "warrior": Weapon(
        name="Iron Sword",
        weapon_type="heavy",
        stat="STR",
        damage_dice=8,
        description="A sturdy iron sword.",
    ),
    "mage": Weapon(
        name="Oak Staff",
        weapon_type="simple",
        stat="INT",
        damage_dice=4,
        description="A gnarled oak staff that hums with energy.",
    ),
    "healer": Weapon(
        name="Iron Mace",
        weapon_type="simple",
        stat="STR",
        damage_dice=6,
        description="A heavy mace favored by clerics.",
    ),
    "jester": Weapon(
        name="Trick Blade",
        weapon_type="wild",
        stat="DEX",
        damage_dice=6,
        description="A blade that seems to change shape when you're not looking.",
    ),
    "rogue": Weapon(
        name="Short Dagger",
        weapon_type="light",
        stat="DEX",
        damage_dice=4,
        description="A quick, light dagger favored by agile fighters.",
    ),
}


# Stats that a jester's random weapon can roll on each attack
RANDOM_WEAPON_STATS = ["STR", "DEX", "INT"]

# Room-by-room weapon dice progression (single attack)
WEAPON_DICE_BY_ROOM: dict[int, dict[str, str]] = {
    1: {"warrior": "1d8",  "mage": "1d4",  "healer": "1d6",  "jester": "1d6"},
    2: {"warrior": "1d10", "mage": "1d6",  "healer": "1d6",  "jester": "1d8"},
    3: {"warrior": "1d12", "mage": "1d6",  "healer": "1d8",  "jester": "1d8"},
    4: {"warrior": "2d6",  "mage": "1d8",  "healer": "1d8",  "jester": "1d10"},
    5: {"warrior": "2d8",  "mage": "1d8",  "healer": "1d10", "jester": "1d10"},
    6: {"warrior": "2d10", "mage": "1d10", "healer": "1d10", "jester": "1d12"},
}

# Warrior multi-attack dice (one step lower than single attack)
MULTI_ATTACK_DICE: dict[int, str] = {
    1: "1d6",
    2: "1d8",
    3: "1d10",
    4: "1d10",
    5: "1d12",
    6: "2d6",
}


def get_weapon_dice(room_level: int, archetype: str) -> str:
    """Return the dice expression for a weapon at a given room level and archetype."""
    capped = min(room_level, max(WEAPON_DICE_BY_ROOM.keys()))
    return WEAPON_DICE_BY_ROOM.get(capped, WEAPON_DICE_BY_ROOM[1]).get(
        archetype, WEAPON_DICE_BY_ROOM[1].get(archetype, "1d6")
    )


def get_multi_attack_dice(room_level: int) -> str:
    """Return the dice expression for warrior multi-attack at a given room level."""
    capped = min(room_level, max(MULTI_ATTACK_DICE.keys()))
    return MULTI_ATTACK_DICE.get(capped, MULTI_ATTACK_DICE[1])


_DICE_STEP_DOWN = {
    4: "1d4",
    6: "1d4",
    8: "1d6",
    10: "1d8",
    12: "1d10",
}


def step_down_weapon_dice(weapon) -> str:
    """Derive multi-attack dice from the equipped weapon (one step lower).

    Uses the weapon's damage_dice (int sides) to look up the reduced die.
    For multi-die weapons (damage_bonus > 0 or high dice), falls back to
    the MULTI_ATTACK_DICE room table using a heuristic room estimate.
    """
    if weapon is None:
        return "1d4"
    sides = weapon.damage_dice
    if sides in _DICE_STEP_DOWN:
        return _DICE_STEP_DOWN[sides]
    if sides > 12:
        return f"1d{sides - 2}"
    return "1d6"


def roll_dice_expr(dice_expr: str) -> int:
    """Roll a dice expression like '2d8' and return the total."""
    try:
        num_str, sides_str = dice_expr.split("d")
        num, sides = int(num_str), int(sides_str)
        return sum(random.randint(1, sides) for _ in range(num))
    except (ValueError, TypeError):
        return random.randint(1, 6)

# Weapon type -> archetypes that get the full stat bonus
WEAPON_CLASS_AFFINITY: dict[str, list[str]] = {
    "heavy": ["warrior"],
    "light": ["rogue"],
    "simple": ["mage", "healer", "warrior"],
    "wild": ["jester"],
}


def resolve_weapon_stat(weapon: Weapon | None) -> str:
    """Return the stat governing a weapon. Random weapons pick once."""
    if weapon is None:
        return "STR"
    if weapon.weapon_type == "wild":
        return random.choice(RANDOM_WEAPON_STATS)
    return weapon.stat


def weapon_stat_bonus(player, weapon: Weapon | None,
                      resolved_stat: str | None = None) -> int:
    """Compute the stat bonus a player gets from their weapon.

    - Matching class: full stat modifier from weapon.stat
    - Jester: (stat_mod + LUCK mod) // 2 for any weapon
    - Mismatched class: 0 (can still use the weapon, just no stat bonus)

    Pass *resolved_stat* to avoid re-rolling random weapons.
    """
    if weapon is None:
        return player.get_stat_mod("STR")

    archetype = ""
    if player.player_class:
        archetype = player.player_class.archetype

    stat_name = resolved_stat or resolve_weapon_stat(weapon)

    if archetype == "jester":
        # Jester uses average of normal stat mod and LUCK mod
        luck_mod = player.get_stat_mod("LUCK")
        normal_mod = player.get_stat_mod(stat_name)
        return (luck_mod + normal_mod) // 2

    affinities = WEAPON_CLASS_AFFINITY.get(weapon.weapon_type, [])
    if archetype in affinities:
        return player.get_stat_mod(stat_name)

    # Mismatched class: no stat bonus
    return 0
