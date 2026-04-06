"""Monster model for MazeWorld encounters.

Monsters are generated at world-build time with environment-themed names,
stats that scale by room level, and optional abilities (poison/stun/elemental).

Compatibility: the combat controller (Phase 3) uses ``species`` / ``display_name``
and calls ``is_alive`` as a property.  This module keeps those working while
adding Phase 5 features (abilities, status effects, environment pools).
"""

import random
import uuid as _uuid
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class MonsterAbility(BaseModel):
    """A battle-scoped ability a monster can use."""
    name: str                           # "poison", "stun", "fire_breath", etc.
    effect_type: str = "damage"         # "damage" | "poison" | "stun"
    damage_dice: str = "1d4"            # Dice expression for ability damage
    damage_type: str = "physical"       # "physical" | "fire" | "water" | "forest" | "light" | "dark"
    duration: int = 0                   # Turns of lingering effect (0 = instant)
    chance: float = 0.3                 # Probability monster uses this instead of basic attack


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

    id: str = Field(default_factory=lambda: str(_uuid.uuid4()))
    species: str = ""
    name: Optional[str] = None
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    ac: int = 10
    str_mod: int = 0
    dex_mod: int = 0
    attack_name: str = "attack"
    damage_dice: int = 6               # kept as int for Phase 3 combat compat
    damage_dice_expr: str = "1d6"      # dice expression used by Phase 5
    damage_type: str = "physical"
    elemental_affinity: Optional[str] = None
    magic_resistance: int = 0
    abilities: List[MonsterAbility] = Field(default_factory=list)
    loot_table: List[LootDrop] = Field(default_factory=list)
    description: str = ""
    profile_image: Optional[str] = None
    portrait_prompt: Optional[str] = None

    time_availability: str = "always"  # "day", "night", or "always"

    # Battle state (not persisted)
    status_effects: Dict[str, int] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

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
        self.status_effects[effect_name] = max(
            self.status_effects.get(effect_name, 0), duration
        )

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
            data["abilities"] = [
                MonsterAbility(**a) if isinstance(a, dict) else a
                for a in data["abilities"]
            ]
        if "loot_table" in data:
            data["loot_table"] = [
                LootDrop(**e) if isinstance(e, dict) else e
                for e in data["loot_table"]
            ]
        return cls(**data)


# -- Level scaling tables (per PDR section 4.4) --

LEVEL_SCALING = {
    1: {"hp": (8, 12),  "ac": (10, 12), "damage_dice": ["1d4", "1d6"],  "str_mod": (0, 1), "dex_mod": (0, 1)},
    2: {"hp": (12, 20), "ac": (11, 13), "damage_dice": ["1d6", "1d8"],  "str_mod": (1, 2), "dex_mod": (0, 2)},
    3: {"hp": (18, 25), "ac": (12, 15), "damage_dice": ["1d6", "1d10"], "str_mod": (1, 3), "dex_mod": (1, 2)},
    4: {"hp": (25, 30), "ac": (13, 16), "damage_dice": ["1d8", "1d12"], "str_mod": (2, 4), "dex_mod": (1, 3)},
}

# Environment-themed monster pools
MONSTER_POOLS = {
    "forest":  ["Wolf", "Treant", "Spider", "Bandit", "Bear", "Vine Serpent"],
    "cave":    ["Bat Swarm", "Slime", "Rock Golem", "Cave Troll", "Blind Crawler", "Crystal Beetle"],
    "dungeon": ["Skeleton", "Wraith", "Mimic", "Dungeon Spider", "Cultist", "Animated Armor"],
    "castle":  ["Knight", "Guard Dog", "Gargoyle", "Phantom", "Rat King", "Cursed Squire"],
    "house":   ["Giant Rat", "Poltergeist", "Feral Cat", "Possessed Doll", "Swarm of Spiders", "Shadow"],
    "city":    ["Thug", "Sewer Rat", "Corrupt Guard", "Pickpocket", "Alley Hound", "Street Brawler"],
}

ATTACK_NAMES = {
    "forest":  ["bite", "claw", "vine lash", "ambush strike"],
    "cave":    ["slam", "acid spit", "crush", "screech"],
    "dungeon": ["slash", "spectral touch", "bone strike", "dark bolt"],
    "castle":  ["sword strike", "charge", "stone fist", "spectral wail"],
    "house":   ["gnaw", "haunt", "scratch", "eerie touch"],
    "city":    ["punch", "shiv", "club swing", "tackle"],
}

ELEMENTAL_TYPES = ["fire", "water", "forest", "light", "dark"]

# Loot item pools by category (item IDs from items.json)
LOOT_POOLS = {
    "food":  [200, 201, 202, 203],
    "drink": [300, 301, 302, 303],
    "tool":  [400, 401, 402, 403],
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


def generate_monster(environment: str, room_level: int, name_override: str = None) -> Monster:
    """Generate a single monster scaled to room_level and themed to environment."""
    level = min(room_level, max(LEVEL_SCALING.keys()))
    scaling = LEVEL_SCALING.get(level, LEVEL_SCALING[1])

    pool = MONSTER_POOLS.get(environment, MONSTER_POOLS["city"])
    monster_name = name_override or random.choice(pool)

    attacks = ATTACK_NAMES.get(environment, ATTACK_NAMES["city"])

    hp = random.randint(*scaling["hp"])
    ac = random.randint(*scaling["ac"])
    str_mod = random.randint(*scaling["str_mod"])
    dex_mod = random.randint(*scaling["dex_mod"])
    damage_dice_expr = random.choice(scaling["damage_dice"])
    damage_dice_int = _parse_dice_sides(damage_dice_expr) or 6

    # Optional elemental affinity (~30% chance)
    elemental = random.choice(ELEMENTAL_TYPES) if random.random() < 0.3 else None

    # Optional ability (~25% chance per monster, higher at higher levels)
    abilities = []
    if random.random() < 0.15 + (level * 0.1):
        ability_type = random.choice(["poison", "stun", "elemental"])
        if ability_type == "poison":
            abilities.append(MonsterAbility(
                name="Poison",
                effect_type="poison",
                damage_dice="1d4",
                duration=2 + level // 2,
                chance=0.25,
            ))
        elif ability_type == "stun":
            abilities.append(MonsterAbility(
                name="Stun",
                effect_type="stun",
                damage_dice="0d0",
                duration=1,
                chance=0.2,
            ))
        elif ability_type == "elemental" and elemental:
            abilities.append(MonsterAbility(
                name=f"{elemental.title()} Blast",
                effect_type="damage",
                damage_dice=damage_dice_expr,
                damage_type=elemental,
                chance=0.3,
            ))

    # Loot table: 40-60% drop chance, 1-2 items
    loot = []
    if random.random() < 0.5 + (level * 0.05):
        category = random.choice(["food", "drink", "tool"])
        item_id = random.choice(LOOT_POOLS[category])
        loot.append(LootDrop(item_id=item_id, probability=0.4 + level * 0.05))

    return Monster(
        species=monster_name,
        name=monster_name,
        hp=hp,
        ac=ac,
        str_mod=str_mod,
        dex_mod=dex_mod,
        attack_name=random.choice(attacks),
        damage_dice=damage_dice_int,
        damage_dice_expr=damage_dice_expr,
        damage_type=elemental or "physical",
        elemental_affinity=elemental,
        magic_resistance=level,
        level=level,
        abilities=abilities,
        loot_table=loot,
        portrait_prompt=f"a {monster_name.lower()} monster in a {environment} setting, fantasy pixel art",
    )


def generate_encounter_monsters(environment: str, room_level: int) -> List[Monster]:
    """Generate a group of monsters for an encounter, scaled by room level.

    Composition types: solo, pack (2-4 weak), mixed (1-2 strong + 2-3 weak).
    """
    roll = random.random()
    if roll < 0.4:
        # Solo
        return [generate_monster(environment, room_level)]
    elif roll < 0.75:
        # Pack: 2-4 weaker monsters
        count = random.randint(2, min(4, 2 + room_level))
        weak_level = max(1, room_level - 1)
        return [generate_monster(environment, weak_level) for _ in range(count)]
    else:
        # Mixed: 1 strong + 2-3 weak
        strong = [generate_monster(environment, room_level)]
        weak_count = random.randint(2, 3)
        weak_level = max(1, room_level - 1)
        weak = [generate_monster(environment, weak_level) for _ in range(weak_count)]
        return strong + weak


# ---------------------------------------------------------------------------
# Backward-compat helpers used by Phase 3 encounter composition
# ---------------------------------------------------------------------------

def create_scaled_monster(
    species: str,
    level: int,
    damage_type: str = "physical",
    elemental_affinity: Optional[str] = None,
    loot_table: Optional[List[LootDrop]] = None,
    name: Optional[str] = None,
) -> Monster:
    """Create a monster with stats scaled to its level (Phase 3 API)."""
    level_key = min(level, 4)
    scales = LEVEL_SCALING.get(level_key, LEVEL_SCALING[1])
    hp = random.randint(*scales["hp"])
    ac = random.randint(*scales["ac"])
    dice_expr = random.choice(scales["damage_dice"])
    dice_int = _parse_dice_sides(dice_expr) or 6
    str_mod = random.randint(*scales["str_mod"])
    dex_mod = random.randint(*scales["dex_mod"])

    if loot_table is None:
        drop_chance = random.uniform(0.4, 0.6)
        loot_table = [LootDrop(item_id=level * 100, probability=drop_chance)]

    return Monster(
        species=species,
        name=name,
        level=level,
        hp=hp,
        max_hp=hp,
        ac=ac,
        str_mod=str_mod,
        dex_mod=dex_mod,
        damage_dice=dice_int,
        damage_dice_expr=dice_expr,
        damage_type=damage_type,
        elemental_affinity=elemental_affinity,
        magic_resistance=level,
        loot_table=loot_table,
    )


# ---------------------------------------------------------------------------
# Night monster variants
# ---------------------------------------------------------------------------

# Night-only monster pools (shadow/dark themed)
NIGHT_MONSTER_POOLS = {
    "forest":  ["Shadow Wolf", "Dark Treant", "Night Spider"],
    "cave":    ["Shadow Bat", "Dark Slime", "Night Crawler"],
    "dungeon": ["Shadow Wraith", "Dark Skeleton", "Night Phantom"],
    "castle":  ["Shadow Knight", "Dark Gargoyle", "Night Specter"],
    "house":   ["Shadow Rat", "Dark Poltergeist", "Night Shade"],
    "city":    ["Shadow Thug", "Dark Stalker", "Night Assassin"],
}


def generate_night_monster(environment: str, room_level: int) -> Monster:
    """Generate a night-only monster with dark elemental affinity and harder stats."""
    pool = NIGHT_MONSTER_POOLS.get(environment, NIGHT_MONSTER_POOLS["city"])
    monster = generate_monster(environment, room_level, name_override=random.choice(pool))
    monster.elemental_affinity = "dark"
    monster.damage_type = "dark"
    monster.time_availability = "night"
    monster.hp = int(monster.hp * 1.25)
    monster.max_hp = monster.hp
    monster.str_mod += 1
    return monster


def generate_night_variant(monster: Monster) -> Monster:
    """Return a harder night variant of an existing monster.

    +25% HP, +1 str_mod, dark elemental affinity, 'Nightstalker' name prefix.
    """
    data = monster.model_dump()
    data.pop("status_effects", None)
    data["id"] = str(_uuid.uuid4())
    data["hp"] = int(monster.hp * 1.25)
    data["max_hp"] = data["hp"]
    data["str_mod"] = monster.str_mod + 1
    data["elemental_affinity"] = "dark"
    data["damage_type"] = "dark"
    data["time_availability"] = "night"
    name = monster.name or monster.species
    if not name.startswith("Nightstalker"):
        data["name"] = f"Nightstalker {name}"
        data["species"] = f"Nightstalker {monster.species}"
    return Monster(**data)
