"""Monster model for MazeWorld encounters.

Monsters are generated at world-build time with environment-themed names,
stats that scale by room level, and optional abilities (poison/stun/elemental).

Compatibility: the combat controller (Phase 3) uses ``species`` / ``display_name``
and calls ``is_alive`` as a property.  This module keeps those working while
adding Phase 5 features (abilities, status effects, environment pools).
"""

import os
import random
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from config import DATA_DIR


class MonsterAbility(BaseModel):
    """A battle-scoped ability a monster can use."""

    name: str  # "poison", "stun", "fire_breath", etc.
    effect_type: str = "damage"  # "damage" | "poison" | "stun"
    damage_dice: str = "1d4"  # Dice expression for ability damage
    damage_type: str = "physical"  # "physical" | "fire" | "water" | "forest" | "light" | "dark"
    duration: int = 0  # Turns of lingering effect (0 = instant)
    chance: float = 0.3  # Probability monster uses this instead of basic attack


class LootDrop(BaseModel):
    """A possible item drop from a monster."""

    item_id: int
    probability: float = 0.5  # 0.0-1.0


# Keep LootEntry as alias for backward compat with Phase 5 serialisation helpers
LootEntry = LootDrop


class Monster(BaseModel):
    """An enemy encountered in combat.

    ``species`` is the creature kind (e.g. "Wolf", "Goblin") used by the
    Phase 3 combat controller.  Phase 5 code that passes ``name`` will
    automatically populate ``species`` via ``model_post_init``.
    """

    id: int = 0
    species: str = ""
    name: Optional[str] = None
    level: int = 1
    hp: int = 10
    max_hp: int = 0
    ac: int = 10
    str_mod: int = 0
    dex_mod: int = 0
    attack_name: str = "attack"
    damage_dice: int = 6  # kept as int for Phase 3 combat compat
    damage_dice_expr: str = "1d6"  # dice expression used by Phase 5
    damage_type: str = "physical"
    elemental_affinity: Optional[str] = None
    physical_type: Optional[str] = None  # "slashing" | "piercing" | "bludgeoning"
    magic_resistance: int = 0
    abilities: List[MonsterAbility] = Field(default_factory=list)
    loot_table: List[LootDrop] = Field(default_factory=list)
    description: str = ""
    backstory: str = ""  # Full lore paragraph — why it guards this area
    time_availability: str = "always"  # "always" | "night_only" | "day_only"
    profile_image: Optional[str] = None
    portrait_prompt: Optional[str] = None

    # Battle state (not persisted)
    status_effects: Dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context):
        if self.max_hp == 0:
            self.max_hp = self.hp
        # If species was not provided but name was, use name as species
        if not self.species and self.name:
            self.species = self.name
        # If name was not provided but species was, use species as name
        if not self.name and self.species:
            self.name = self.species
        # Sync damage_dice int from expression if only expression was given
        if self.damage_dice_expr and self.damage_dice == 6:
            parsed = _parse_dice_sides(self.damage_dice_expr)
            if parsed:
                self.damage_dice = parsed

    @property
    def display_name(self) -> str:
        """Name for UI display: the unique name if set, otherwise the species."""
        return self.name or self.species

    # -- Combat interface (Phase 3 compat) --

    def roll_initiative(self) -> int:
        return random.randint(1, 20) + self.dex_mod

    def roll_attack(self) -> int:
        return random.randint(1, 20) + self.str_mod

    def roll_damage(self, dice_expr: Optional[str] = None) -> int:
        """Roll damage.  Without args uses the int damage_dice (Phase 3 style).
        Pass a dice expression string to use Phase 5 dice rolling."""
        if dice_expr:
            return _roll_dice(dice_expr)
        return random.randint(1, self.damage_dice) + max(self.str_mod, 0)

    @property
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

    # -- Phase 5 extensions --

    def choose_action(self) -> dict:
        """Simple AI: pick ability by chance, else basic attack."""
        for ability in self.abilities:
            if random.random() < ability.chance:
                return {"type": "ability", "ability": ability}
        return {"type": "attack"}

    def apply_status(self, effect_name: str, duration: int):
        self.status_effects[effect_name] = max(self.status_effects.get(effect_name, 0), duration)

    def tick_status_effects(self) -> List[str]:
        """Decrement status timers; return list of expired effects."""
        expired = []
        for effect in list(self.status_effects):
            self.status_effects[effect] -= 1
            if self.status_effects[effect] <= 0:
                del self.status_effects[effect]
                expired.append(effect)
        return expired

    def is_stunned(self) -> bool:
        return "stun" in self.status_effects

    def to_dict(self) -> dict:
        """Serialize for world_gen JSON output."""
        data = self.model_dump()
        data.pop("status_effects", None)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Monster":
        if "abilities" in data:
            data["abilities"] = [MonsterAbility(**a) if isinstance(a, dict) else a for a in data["abilities"]]
        if "loot_table" in data:
            data["loot_table"] = [LootDrop(**e) if isinstance(e, dict) else e for e in data["loot_table"]]
        return cls(**data)


# -- Level scaling tables (per PDR section 4.4) --

LEVEL_SCALING = {
    1: {"hp": (8, 12), "ac": (10, 12), "damage_dice": ["1d4", "1d6"], "str_mod": (0, 1), "dex_mod": (0, 1)},
    2: {"hp": (12, 20), "ac": (11, 13), "damage_dice": ["1d6", "1d8"], "str_mod": (1, 2), "dex_mod": (0, 2)},
    3: {"hp": (18, 25), "ac": (12, 15), "damage_dice": ["1d6", "1d10"], "str_mod": (1, 3), "dex_mod": (1, 2)},
    4: {"hp": (25, 30), "ac": (13, 16), "damage_dice": ["1d8", "1d12"], "str_mod": (2, 4), "dex_mod": (1, 3)},
}


def instantiate_monster(template: dict, room_level: int) -> "Monster":
    """Create a live Monster instance from a DB template, rolling stats fresh.

    Uses template hp_range/ac_range and LEVEL_SCALING for str_mod/dex_mod/damage_dice.
    """
    scaling = LEVEL_SCALING.get(min(room_level, max(LEVEL_SCALING)), LEVEL_SCALING[1])
    hp_range = template.get("hp_range", list(scaling["hp"]))
    ac_range = template.get("ac_range", list(scaling["ac"]))
    hp = random.randint(int(hp_range[0]), int(hp_range[1]))
    ac = random.randint(int(ac_range[0]), int(ac_range[1]))
    str_mod = random.randint(*scaling["str_mod"])
    dex_mod = random.randint(*scaling["dex_mod"])
    damage_dice_expr = random.choice(scaling["damage_dice"])

    abilities = []
    for ab in template.get("abilities", []):
        if isinstance(ab, dict) and ab.get("name"):
            try:
                abilities.append(MonsterAbility(**ab))
            except Exception:
                pass
        elif isinstance(ab, MonsterAbility):
            abilities.append(ab)

    return Monster(
        id=template.get("id", 0),
        name=template.get("name", "Unknown"),
        species=template.get("species", template.get("name", "creature")),
        description=template.get("description", ""),
        backstory=template.get("backstory", ""),
        hp=hp,
        max_hp=hp,
        ac=ac,
        str_mod=str_mod,
        dex_mod=dex_mod,
        damage_dice_expr=damage_dice_expr,
        damage_type=template.get("damage_type", "physical"),
        elemental_affinity=template.get("elemental_affinity"),
        physical_type=template.get("physical_type"),
        time_availability=template.get("time_availability", "always"),
        abilities=abilities,
        level=room_level,
        profile_image=template.get("profile_image"),
        portrait_prompt=template.get("portrait_prompt"),
    )


# Environment-themed monster pools
MONSTER_POOLS = {
    "forest": ["Wolf", "Treant", "Spider", "Bandit", "Bear", "Vine Serpent"],
    "cave": ["Bat Swarm", "Slime", "Rock Golem", "Cave Troll", "Blind Crawler", "Crystal Beetle"],
    "dungeon": ["Skeleton", "Wraith", "Mimic", "Dungeon Spider", "Cultist", "Animated Armor"],
    "castle": ["Knight", "Guard Dog", "Gargoyle", "Phantom", "Rat King", "Cursed Squire"],
    "house": ["Giant Rat", "Poltergeist", "Feral Cat", "Possessed Doll", "Swarm of Spiders", "Shadow"],
    "city": ["Thug", "Sewer Rat", "Corrupt Guard", "Pickpocket", "Alley Hound", "Street Brawler"],
}

ENVIRONMENT_PHYSICAL_TYPES: dict[str, list[str]] = {
    "forest": ["slashing", "slashing", "piercing"],
    "cave": ["bludgeoning", "bludgeoning", "piercing"],
    "dungeon": ["slashing", "piercing", "slashing"],
    "castle": ["slashing", "piercing", "slashing"],
    "house": ["piercing", "piercing", "bludgeoning"],
    "city": ["bludgeoning", "bludgeoning", "slashing"],
    "village": ["bludgeoning", "piercing", "slashing"],
}


def _parse_dice_sides(expr: str) -> Optional[int]:
    """Extract the die size from '1d6' -> 6.  Returns None on failure."""
    expr = expr.strip().lower()
    if "d" not in expr:
        return None
    parts = expr.split("d")
    try:
        return int(parts[1])
    except (ValueError, IndexError):
        return None


def _roll_dice(expr: str) -> int:
    """Parse and roll a dice expression like '2d6' or '1d4'."""
    expr = expr.strip().lower()
    if "d" not in expr:
        return int(expr) if expr.isdigit() else 0
    parts = expr.split("d")
    try:
        num = int(parts[0]) if parts[0] else 1
        sides = int(parts[1])
    except (ValueError, IndexError):
        return 0
    if num == 0 or sides == 0:
        return 0
    return sum(random.randint(1, sides) for _ in range(num))


def _try_assign_portrait(monster: "Monster") -> None:
    """Look up an existing portrait file by normalized name and assign it."""
    if getattr(monster, "profile_image", None):
        return
    portrait_dir = os.path.join(DATA_DIR, "portraits", "monsters")
    if not os.path.isdir(portrait_dir):
        return
    key = monster.name.replace(" ", "_").lower()
    candidate = os.path.join(portrait_dir, f"mon_{key}.png")
    if os.path.exists(candidate):
        monster.profile_image = candidate
