import random
from typing import Optional

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Weapon type / category / triangle tables
# ---------------------------------------------------------------------------

WEAPON_TYPES = {
    "heavy": {"stat": "STR", "weight": 0.18},
    "light": {"stat": "DEX", "weight": 0.18},
    "sacred": {"stat": "CON", "weight": 0.18},
    "arcane": {"stat": "INT", "weight": 0.18},
    "enchanted": {"stat": "WIS", "weight": 0.18},
    "wild": {"stat": "LUCK", "weight": 0.10},
}

WEAPON_CATEGORIES = {
    "simple": {"weight": 0.60, "access": {"warrior", "mage", "healer", "jester"}},
    "martial": {"weight": 0.40, "access": {"warrior", "jester"}},
}

PHYSICAL_DAMAGE_TYPES = ["slashing", "piercing", "bludgeoning"]
MAGIC_ELEMENTS = ["fire", "water", "forest", "light", "dark"]

RANDOM_WEAPON_STATS = ["STR", "DEX", "CON", "INT", "WIS"]


# ---------------------------------------------------------------------------
# Dice progression algorithm (shared with spells via DIE_PROGRESSION)
# ---------------------------------------------------------------------------

DIE_PROGRESSION = [
    (1, 4),
    (1, 6),
    (1, 8),
    (1, 10),
    (1, 12),
    (2, 6),
    (2, 8),
    (2, 10),
    (2, 12),
    (3, 6),
    (3, 8),
    (3, 10),
    (3, 12),
    (4, 6),
    (4, 8),
    (4, 10),
    (4, 12),
]

WEAPON_TYPE_BASE_TIER = {
    "heavy": 2,
    "light": 1,
    "sacred": 1,
    "arcane": 0,
    "enchanted": 0,
    "wild": 1,
}


def compute_weapon_dice(room_level: int, weapon_type: str) -> tuple[int, int]:
    """Compute (num_dice, die_sides) for a weapon type at a given room level."""
    base = WEAPON_TYPE_BASE_TIER.get(weapon_type, 1)
    tier = base + (room_level - 1)
    tier = min(tier, len(DIE_PROGRESSION) - 1)
    return DIE_PROGRESSION[tier]


# ---------------------------------------------------------------------------
# Weapon model
# ---------------------------------------------------------------------------


class Weapon(BaseModel):
    """A weapon used in combat.

    Types (weapon_type -- governs stat scaling):
      heavy     - STR-based, highest base damage
      light     - DEX-based, fast attacks
      sacred    - CON-based, holy/divine weapons
      arcane    - INT-based, magical implements
      enchanted - WIS-based, mystical weapons
      wild      - LUCK + random stat, jester only

    Categories (weapon_category -- governs equip restrictions):
      simple  - any class can equip
      martial - warrior and jester only
    """

    name: str
    weapon_type: str = "heavy"
    stat: str = "STR"
    num_dice: int = 1
    die_sides: int = 6
    damage_bonus: int = 0
    damage_type: str = "slashing"
    weapon_category: str = "simple"
    magic_element: Optional[str] = None
    description: str = ""
    profile_image: Optional[str] = None
    portrait_prompt: Optional[str] = None

    def roll_damage(self) -> int:
        """Roll weapon damage: {num_dice}d{die_sides} + damage_bonus."""
        return sum(random.randint(1, self.die_sides) for _ in range(self.num_dice)) + self.damage_bonus

    @property
    def dice_expr(self) -> str:
        return f"{self.num_dice}d{self.die_sides}"


# ---------------------------------------------------------------------------
# Starter weapons (one per archetype)
# ---------------------------------------------------------------------------

STARTER_WEAPONS = {
    "warrior": Weapon(
        name="Iron Sword",
        weapon_type="heavy",
        stat="STR",
        num_dice=1,
        die_sides=8,
        damage_type="slashing",
        weapon_category="martial",
        description="A simple Iron weapon.",
    ),
    "mage": Weapon(
        name="Oak Staff",
        weapon_type="arcane",
        stat="INT",
        num_dice=1,
        die_sides=4,
        damage_type="bludgeoning",
        weapon_category="simple",
        description="A simple Iron weapon.",
    ),
    "healer": Weapon(
        name="Iron Mace",
        weapon_type="sacred",
        stat="CON",
        num_dice=1,
        die_sides=6,
        damage_type="bludgeoning",
        weapon_category="simple",
        description="A simple Iron weapon.",
    ),
    "jester": Weapon(
        name="Trick Blade",
        weapon_type="wild",
        stat="DEX",
        num_dice=1,
        die_sides=6,
        damage_type="slashing",
        weapon_category="martial",
        description="A simple Iron weapon.",
    ),
}


# ---------------------------------------------------------------------------
# Step-down for warrior multi-attack
# ---------------------------------------------------------------------------


def step_down_weapon_dice(weapon) -> tuple[int, int]:
    """Step down: reduce die_sides by 2 (min 4). If already at min, reduce num_dice."""
    if weapon is None:
        return 1, 4
    n, s = weapon.num_dice, weapon.die_sides
    if s > 4:
        return n, s - 2
    if n > 1:
        return n - 1, s
    return 1, 4


def roll_dice_expr(dice_expr: str) -> int:
    """Roll a dice expression like '2d8' and return the total."""
    try:
        num_str, sides_str = dice_expr.split("d")
        num, sides = int(num_str), int(sides_str)
        return sum(random.randint(1, sides) for _ in range(num))
    except (ValueError, TypeError):
        return random.randint(1, 6)


# ---------------------------------------------------------------------------
# Weapon category access (archetype-keyed, used by weapon_stat_bonus)
# ---------------------------------------------------------------------------

WEAPON_CATEGORY_ACCESS: dict[str, set[str]] = {
    "warrior": {"simple", "martial"},
    "jester": {"simple", "martial"},
    "mage": {"simple"},
    "healer": {"simple"},
}


def resolve_weapon_stat(weapon: "Weapon | None") -> str:
    """Return the stat governing a weapon. Wild weapons pick a random stat each time."""
    if weapon is None:
        return "STR"
    if weapon.weapon_type == "wild":
        return random.choice(RANDOM_WEAPON_STATS)
    return weapon.stat


def weapon_stat_bonus(player, weapon: "Weapon | None", resolved_stat: str | None = None) -> int:
    """Compute the stat bonus a player gets from their weapon.

    - Matching category: full stat modifier from weapon.stat
    - Jester: (stat_mod + LUCK mod) // 2 for any weapon
    - Mismatched category: 0 (can still use the weapon, just no stat bonus)
    """
    if weapon is None:
        return player.get_stat_mod("STR")

    archetype = ""
    if player.player_class:
        archetype = player.player_class.archetype

    stat_name = resolved_stat or resolve_weapon_stat(weapon)

    if archetype == "jester":
        luck_mod = player.get_stat_mod("LUCK")
        normal_mod = player.get_stat_mod(stat_name)
        return (luck_mod + normal_mod) // 2

    allowed = WEAPON_CATEGORY_ACCESS.get(archetype, {"simple"})
    if weapon.weapon_category in allowed:
        return player.get_stat_mod(stat_name)

    return 0


def _parse_dice_expr(expr: str) -> tuple[int, int]:
    """Parse '2d6' into (2, 6). Returns (1, 6) on failure."""
    try:
        n, s = expr.split("d")
        return int(n), int(s)
    except (ValueError, AttributeError):
        return 1, 6


def weapon_from_inventory_item(item) -> Weapon:
    """Convert an items.py::Weapon into a weapon.py::Weapon for combat use."""
    dice_str = item.item_stats.attack_dice or "1d6"
    num, sides = _parse_dice_expr(dice_str)
    return Weapon(
        name=item.name,
        weapon_type=getattr(item, "weapon_type", "heavy"),
        stat=item.item_stats.stat_modifier or "STR",
        num_dice=num,
        die_sides=sides,
        damage_type=getattr(item, "damage_type", "physical"),
        weapon_category=getattr(item, "weapon_category", "simple"),
        magic_element=getattr(item, "magic_element", None),
    )


# ---------------------------------------------------------------------------
# Weapon skeleton pre-roll (used by pipeline before LLM call)
# ---------------------------------------------------------------------------


def roll_weapon_skeleton(
    room_level: int,
    room_idx: int = 0,
    room_id: str = "",
    environment: str = "",
    environment_name: str = "",
) -> dict:
    """Pre-roll a weapon's mechanical identity with room context."""
    types = list(WEAPON_TYPES.keys())
    weights = [WEAPON_TYPES[t]["weight"] for t in types]
    wtype = random.choices(types, weights=weights, k=1)[0]

    cats = list(WEAPON_CATEGORIES.keys())
    cat_weights = [WEAPON_CATEGORIES[c]["weight"] for c in cats]
    category = random.choices(cats, weights=cat_weights, k=1)[0]

    damage_type = random.choice(PHYSICAL_DAMAGE_TYPES)

    magic_element = None
    if random.random() < 0.10:
        magic_element = random.choice(MAGIC_ELEMENTS)

    stat = WEAPON_TYPES[wtype]["stat"]
    num_dice, die_sides = compute_weapon_dice(room_level, wtype)

    return {
        "weapon_type": wtype,
        "weapon_category": category,
        "damage_type": damage_type,
        "stat_modifier": stat,
        "num_dice": num_dice,
        "die_sides": die_sides,
        "attack_dice": f"{num_dice}d{die_sides}",
        "magic_element": magic_element,
        "room_level": room_level,
        "room_idx": room_idx,
        "room_id": room_id,
        "environment": environment,
        "environment_name": environment_name,
    }
