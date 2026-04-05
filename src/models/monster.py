import random
from typing import List, Optional
from pydantic import BaseModel, Field


class LootDrop(BaseModel):
    """A possible item drop from a monster."""
    item_id: int
    probability: float = 0.5  # 0.0-1.0


class Monster(BaseModel):
    """An enemy encountered in combat.

    Monsters have D&D-lite stats used by the combat controller for
    initiative, attack rolls, AC, and damage.
    """

    id: str
    name: str
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    ac: int = 10  # 10 + armor + DEX mod
    str_mod: int = 0  # STR modifier (not raw stat)
    dex_mod: int = 0
    damage_dice: int = 4  # e.g. 4 = 1d4
    damage_type: str = "physical"  # "physical" | element name
    elemental_affinity: Optional[str] = None  # weakness/resistance element
    magic_resistance: int = 0  # added to DC for magic attacks
    abilities: List[str] = Field(default_factory=list)  # battle-scoped only
    loot_table: List[LootDrop] = Field(default_factory=list)
    description: str = ""
    profile_image: Optional[str] = None
    portrait_prompt: Optional[str] = None

    def roll_initiative(self) -> int:
        return random.randint(1, 20) + self.dex_mod

    def roll_attack(self) -> int:
        return random.randint(1, 20) + self.str_mod

    def roll_damage(self) -> int:
        return random.randint(1, self.damage_dice) + max(self.str_mod, 0)

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int):
        self.hp = max(0, self.hp - amount)

    def roll_loot(self) -> List[int]:
        """Roll loot table, return list of item_ids that dropped."""
        drops = []
        for drop in self.loot_table:
            if random.random() < drop.probability:
                drops.append(drop.item_id)
        return drops


# Level scaling guidelines from PDR
LEVEL_SCALING = {
    1: {"hp": (8, 12), "ac": (10, 12), "dice": (4, 6)},
    2: {"hp": (12, 20), "ac": (11, 13), "dice": (6, 8)},
    3: {"hp": (18, 25), "ac": (12, 15), "dice": (6, 10)},
    4: {"hp": (25, 30), "ac": (13, 16), "dice": (8, 12)},
}


def create_scaled_monster(
    id: str,
    name: str,
    level: int,
    damage_type: str = "physical",
    elemental_affinity: Optional[str] = None,
    loot_table: Optional[List[LootDrop]] = None,
) -> Monster:
    """Create a monster with stats scaled to its level."""
    level_key = min(level, 4)
    scales = LEVEL_SCALING.get(level_key, LEVEL_SCALING[1])
    hp = random.randint(*scales["hp"])
    ac = random.randint(*scales["ac"])
    dice = random.choice(range(scales["dice"][0], scales["dice"][1] + 1, 2)) or scales["dice"][0]
    str_mod = max(0, level - 1)
    dex_mod = max(0, (level - 1) // 2)

    return Monster(
        id=id,
        name=name,
        level=level,
        hp=hp,
        max_hp=hp,
        ac=ac,
        str_mod=str_mod,
        dex_mod=dex_mod,
        damage_dice=dice,
        damage_type=damage_type,
        elemental_affinity=elemental_affinity,
        magic_resistance=level,
        loot_table=loot_table or [],
    )
