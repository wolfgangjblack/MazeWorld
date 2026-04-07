import random
from typing import Optional
from pydantic import BaseModel


class Weapon(BaseModel):
    """A weapon used in combat.

    Types:
      heavy  - STR-based, 1d8-1d10 (warrior primary)
      light  - DEX-based, 1d4-1d6 (fast, lower damage)
      simple - STR or INT, 1d4-1d6 (mage/healer weapons)
      random - varies (jester)
    """

    name: str
    weapon_type: str  # "heavy" | "light" | "simple" | "random"
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
        weapon_type="random",
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

# Weapon type -> archetypes that get the full stat bonus
WEAPON_CLASS_AFFINITY: dict[str, list[str]] = {
    "heavy": ["warrior"],
    "light": ["rogue"],
    "simple": ["mage", "healer", "warrior"],
    "random": ["jester"],
}


def resolve_weapon_stat(weapon: Weapon | None) -> str:
    """Return the stat governing a weapon. Random weapons pick once."""
    if weapon is None:
        return "STR"
    if weapon.weapon_type == "random":
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
