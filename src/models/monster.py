import random
from enum import Enum
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

    # Default loot: one generic drop with 40-60% probability
    if loot_table is None:
        drop_chance = random.uniform(0.4, 0.6)
        loot_table = [LootDrop(item_id=level * 100, probability=drop_chance)]

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
        loot_table=loot_table,
    )


# ---------------------------------------------------------------------------
# Encounter composition
# ---------------------------------------------------------------------------

class EncounterType(str, Enum):
    SOLO = "solo"    # 1 monster
    PACK = "pack"    # 2-4 weak monsters
    MIXED = "mixed"  # 1-2 strong + 2-3 weak


# Pool of monster templates for encounter generation
MONSTER_POOL = {
    "weak": [
        {"name": "Rat", "damage_type": "physical"},
        {"name": "Goblin", "damage_type": "physical"},
        {"name": "Bat", "damage_type": "physical"},
        {"name": "Imp", "damage_type": "fire", "elemental_affinity": "fire"},
        {"name": "Sprite", "damage_type": "forest", "elemental_affinity": "forest"},
    ],
    "strong": [
        {"name": "Orc", "damage_type": "physical"},
        {"name": "Fire Elemental", "damage_type": "fire", "elemental_affinity": "fire"},
        {"name": "Treant", "damage_type": "physical", "elemental_affinity": "forest"},
        {"name": "Water Serpent", "damage_type": "water", "elemental_affinity": "water"},
        {"name": "Shadow Knight", "damage_type": "physical", "elemental_affinity": "dark"},
    ],
}


def generate_encounter(
    player_level: int,
    encounter_type: Optional[EncounterType] = None,
) -> List[Monster]:
    """Generate a combat encounter scaled to the player's level.

    Args:
        player_level: The player's current level (determines monster scaling).
        encounter_type: Force a specific composition, or None for random selection.

    Returns:
        A list of Monster instances ready for CombatController.
    """
    if encounter_type is None:
        encounter_type = random.choice(list(EncounterType))

    monsters: List[Monster] = []
    counter = 0

    def _make(template: dict, level: int) -> Monster:
        nonlocal counter
        counter += 1
        return create_scaled_monster(
            id=f"enc-{counter}",
            name=template["name"],
            level=level,
            damage_type=template.get("damage_type", "physical"),
            elemental_affinity=template.get("elemental_affinity"),
        )

    if encounter_type == EncounterType.SOLO:
        template = random.choice(MONSTER_POOL["strong"])
        monsters.append(_make(template, player_level + 1))

    elif encounter_type == EncounterType.PACK:
        count = random.randint(2, 4)
        for _ in range(count):
            template = random.choice(MONSTER_POOL["weak"])
            monsters.append(_make(template, max(1, player_level - 1)))

    elif encounter_type == EncounterType.MIXED:
        strong_count = random.randint(1, 2)
        weak_count = random.randint(2, 3)
        for _ in range(strong_count):
            template = random.choice(MONSTER_POOL["strong"])
            monsters.append(_make(template, player_level))
        for _ in range(weak_count):
            template = random.choice(MONSTER_POOL["weak"])
            monsters.append(_make(template, max(1, player_level - 1)))

    return monsters
