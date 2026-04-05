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
}
