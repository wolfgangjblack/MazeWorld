import random
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from src.models.spell import Spell
from src.registry import registry

StatName = Literal["STR", "DEX", "CON", "INT", "WIS", "CHA", "LUCK"]
STAT_NAMES: list[StatName] = ["STR", "DEX", "CON", "INT", "WIS", "CHA", "LUCK"]
STAT_BUDGET = 95

# Archetype stat role assignments: primary stats get 14-18, secondary 11-14, dump 6-10
ARCHETYPE_STAT_ROLES = {
    "warrior": {"primary": ["STR", "CON"], "secondary": ["DEX", "CHA"], "dump": ["INT", "WIS"]},
    "mage": {"primary": ["INT"], "secondary": ["WIS", "DEX"], "dump": ["STR", "CON", "CHA"]},
    "healer": {"primary": ["WIS"], "secondary": ["CHA", "CON"], "dump": ["STR", "DEX", "INT"]},
    "jester": {"primary": ["LUCK"], "secondary": ["STR", "DEX", "CON", "INT", "WIS", "CHA"], "dump": []},
}

# Weapon category soft-restriction: only matching archetypes get the stat bonus.
# Any class CAN equip any weapon in an allowed category, but mismatched = 0 stat bonus.
# Jester uses avg(LUCK mod, weapon stat mod) for any weapon instead.
ARCHETYPE_WEAPON_CATEGORIES: dict[str, set[str]] = {
    "warrior": {"simple", "martial"},
    "mage": {"simple"},
    "healer": {"simple"},
    "jester": set(),  # jester uses luck rule for all weapons
}


ABILITY_DISTRIBUTIONS = {
    "warrior": {
        "starting": [
            {"purpose": "break", "stat": "STR"},
            {"purpose": "intimidate", "stat": "CHA"},
            {"purpose": "bash", "stat": "STR"},
            {"purpose": "rally", "stat": "CHA"},
        ],
        "pool": [
            {"purpose": "climb", "stat": "STR"},
            {"purpose": "detect", "stat": "WIS"},
            {"purpose": "grapple", "stat": "STR"},
            {"purpose": "warcry", "stat": "CHA"},
        ],
    },
    "mage": {"starting": [], "pool": []},
    "healer": {"starting": [], "pool": []},
    "jester": {"starting": [], "pool": []},
}

ABILITY_STAMINA_BY_PURPOSE = {
    "break": 8,
    "bash": 5,
    "intimidate": 3,
    "rally": 5,
    "climb": 4,
    "detect": 3,
    "grapple": 6,
    "warcry": 7,
}


def roll_ability_skeleton(slot: dict) -> dict:
    """Pre-roll an ability's mechanical identity."""
    purpose = slot["purpose"]
    stat = slot["stat"]
    stamina_cost = ABILITY_STAMINA_BY_PURPOSE.get(purpose, 4)
    return {
        "purpose": purpose,
        "stat": stat,
        "stamina_cost": stamina_cost,
    }


def stat_modifier(value: int) -> int:
    """D&D-style modifier: (stat - 10) // 2."""
    return (value - 10) // 2


class ActiveBuff(BaseModel):
    """A temporary stat buff active during combat."""

    stat: str
    value: int
    turns_remaining: int


class Stats(BaseModel):
    """D&D-style stat block for player classes."""

    STR: int = 10
    DEX: int = 10
    CON: int = 10
    INT: int = 10
    WIS: int = 10
    CHA: int = 10
    LUCK: int = 10

    def modifier(self, stat: StatName) -> int:
        return (getattr(self, stat) - 10) // 2

    def total(self) -> int:
        return self.STR + self.DEX + self.CON + self.INT + self.WIS + self.CHA + self.LUCK

    def as_dict(self) -> dict[str, int]:
        return {s: getattr(self, s) for s in STAT_NAMES}

    def validate_guardrails(self, archetype: str) -> list[str]:
        """Check stat values against archetype guardrails. Returns list of violations."""
        roles = ARCHETYPE_STAT_ROLES.get(archetype, {})
        errors = []
        for stat in roles.get("primary", []):
            val = getattr(self, stat)
            if not (14 <= val <= 18):
                errors.append(f"{stat}={val} not in primary range 14-18")
        for stat in roles.get("secondary", []):
            val = getattr(self, stat)
            if archetype == "jester":
                if not (11 <= val <= 15):
                    errors.append(f"{stat}={val} not in secondary range 11-15")
            else:
                if not (12 <= val <= 16):
                    errors.append(f"{stat}={val} not in secondary range 12-16")
        for stat in roles.get("dump", []):
            val = getattr(self, stat)
            if not (8 <= val <= 12):
                errors.append(f"{stat}={val} not in dump range 8-12")
        if self.total() != STAT_BUDGET:
            errors.append(f"total={self.total()} != budget {STAT_BUDGET}")
        return errors


class Ability(BaseModel):
    name: str
    description: str
    stat: StatName = "STR"
    stamina_cost: int = 0


class PlayerClass(BaseModel):
    name: str
    archetype: str  # "warrior" | "mage" | "healer" | "jester"
    flavor_text: str = ""
    environment: str = ""
    stats: Stats = Field(default_factory=Stats)
    starting_weapon: str = ""
    abilities: list[Ability] = Field(default_factory=list)
    spells: list[Spell] = Field(default_factory=list)
    portrait_path: Optional[str] = None
    portrait_prompt: Optional[str] = None
    # Pool of extra abilities available at level-up
    ability_pool: list[Ability] = Field(default_factory=list)
    spell_pool: list[Spell] = Field(default_factory=list)


class PlayerCharacter(BaseModel):
    x: int
    y: int
    name: str = "Adventurer"
    player_class: Optional[PlayerClass] = None
    level: int = 1
    color: Tuple[int, int, int] = (0, 0, 255)
    health: int = 100
    stamina: int = 100
    speed: float = 1.0
    max_health: int = 100
    max_stamina: int = 100
    max_speed: float = 2.0
    selected_item_index: int = 0
    inventory: Dict[str, object] = Field(default_factory=dict)
    profile_image: Optional[str] = None
    active_quests: List[int] = Field(default_factory=list)
    completed_quests: List[int] = Field(default_factory=list)
    failed_quests: List[int] = Field(default_factory=list)
    followers: List[Any] = Field(default_factory=list)  # List[Follower]
    abilities: List[Any] = Field(default_factory=list)
    spells: List[Any] = Field(default_factory=list)
    equipped_weapon: Optional[str] = None
    armor: int = 0  # flat armor value added to AC
    weapon: Optional[Any] = None  # Weapon instance (resolved at runtime)
    active_buffs: List[ActiveBuff] = Field(default_factory=list)

    # --- Phase 4: Items, Inventory & Shops ---
    money: int = 0
    learned_spells: List[str] = Field(default_factory=list)

    # --- Combat record ---
    combat_record: Dict[str, int] = Field(
        default_factory=lambda: {
            "monsters_killed": 0,
            "damage_dealt": 0,
            "damage_taken": 0,
            "combats_won": 0,
            "combats_fled": 0,
        }
    )
    encounter_record: Dict[str, int] = Field(
        default_factory=lambda: {
            "puzzles_solved": 0,
            "puzzles_failed": 0,
            "events_resolved": 0,
            "events_failed": 0,
        }
    )
    title: str = ""

    class Config:
        arbitrary_types_allowed = True

    def _get_inv_manager(self):
        """Lazy-init InventoryManager bound to this player's inventory."""
        if not hasattr(self, "_inv_manager") or self._inv_manager is None:
            from src.systems.inventory import InventoryManager

            self._inv_manager = InventoryManager(self.inventory, self)
        return self._inv_manager

    def apply_class(self, player_class: PlayerClass):
        """Apply a selected class to this character."""
        self.player_class = player_class
        self.abilities = list(player_class.abilities)
        self.spells = list(player_class.spells)
        self.equipped_weapon = player_class.starting_weapon
        if player_class.portrait_path:
            self.profile_image = player_class.portrait_path
        # Apply CON modifier to max HP: base 100 + 10 * CON modifier
        con_mod = player_class.stats.modifier("CON")
        self.max_health = max(50, 100 + 10 * con_mod)
        self.health = self.max_health

    def get_stat_modifier(self, stat: str) -> int:
        """Get modifier for a stat from the player's class."""
        if self.player_class:
            return self.player_class.stats.modifier(stat)
        return 0

    def level_up_choices(self, max_choices: int = 4) -> list:
        """Return available abilities/spells to pick from on level-up.

        Draws from ability_pool, spell_pool, and the shared spell pools file
        (if it exists). Results are capped at *max_choices* via random sampling.
        """
        if not self.player_class:
            return []

        known_names = {a.name for a in self.abilities} | {s.name for s in self.spells}
        choices: list[tuple[str, object]] = []

        for a in self.player_class.ability_pool:
            if a.name not in known_names:
                choices.append(("ability", a))

        for s in self.player_class.spell_pool:
            if s.name not in known_names:
                choices.append(("spell", s))

        # Load shared spell pools from disk
        pool_spells = self._load_spell_pool_choices(known_names)
        choices.extend(pool_spells)

        if len(choices) > max_choices:
            choices = random.sample(choices, max_choices)
        return choices

    def _load_spell_pool_choices(self, known_names: set[str]) -> list[tuple[str, Spell]]:
        """Load the shared spell pools and filter by archetype visibility."""
        import json
        import os

        pool_path = os.path.join(os.getenv("DATA_DIR", "data"), "classes", "spell_pools.json")
        if not os.path.exists(pool_path):
            return []

        try:
            with open(pool_path) as f:
                pools = json.load(f)
        except Exception:
            return []

        archetype = self.player_class.archetype if self.player_class else ""
        visible_pools = {
            "mage": ["mage_damage", "buff"],
            "healer": ["healer_damage", "heal", "buff"],
            "jester": ["mage_damage", "healer_damage", "heal", "buff"],
        }.get(archetype, [])

        results: list[tuple[str, Spell]] = []
        for pool_key in visible_pools:
            for sd in pools.get(pool_key, []):
                if sd.get("name", "") in known_names:
                    continue
                skel = dict(sd)
                skel.pop("available_at_room", None)
                try:
                    results.append(("spell", Spell(**skel)))
                except Exception:
                    pass
        return results

    def apply_level_up(self, choice_type: str, choice, room_level: int = 1):
        """Apply a level-up choice (ability or spell).

        For spells, dice are scaled to *room_level* at acquisition time.
        """
        from src.models.spell import compute_spell_dice, compute_stamina_cost

        self.level += 1
        if choice_type == "ability":
            self.abilities.append(choice)
        elif choice_type == "spell":
            if hasattr(choice, "spell_type") and choice.spell_type in ("damage_single", "damage_multi", "heal"):
                num_dice, die_sides = compute_spell_dice(room_level, choice.spell_type)
                stamina = compute_stamina_cost(die_sides, num_dice, choice.targets, choice.spell_type)
                choice = choice.model_copy(update={
                    "num_dice": num_dice,
                    "die_sides": die_sides,
                    "stamina_cost": stamina,
                })
            self.spells.append(choice)

    def initialize_inventory(self):
        from config import STARTING_MONEY

        self.inventory = {name: item.clone() for name, item in registry.starter_inventory.items()}
        self.money = STARTING_MONEY
        if self.equipped_weapon and self.equipped_weapon not in self.inventory:
            template = registry.get_item_by_name(self.equipped_weapon)
            if template:
                self.inventory[self.equipped_weapon] = template.clone()

    def move(self, dx: int, dy: int, maze, survival_system=None):
        new_x = self.x + dx
        new_y = self.y + dy

        if not maze.is_wall(new_x, new_y):
            self.x = new_x
            self.y = new_y

    def add_to_inventory(self, item):
        """Add an item to the player's inventory."""
        self._get_inv_manager().add(item)

    def remove_from_inventory(self, item_name):
        """Remove an item from the player's inventory."""
        self._get_inv_manager().remove(item_name)

    def get_inventory(self):
        """Return the player's inventory as a list of tuples (item name, quantity)."""
        return self._get_inv_manager().get_list()

    def use_item(self):
        """Use the currently selected item."""
        return self._get_inv_manager().use_selected(self.selected_item_index)

    def give_item(self):
        """Give the currently selected item."""
        return self._get_inv_manager().give_selected(self.selected_item_index)

    def pay_stamina(self, amount: int):
        """Deduct stamina, clamped to 0."""
        self.stamina = max(0, self.stamina - amount)

    def is_item_at_player_position(self, maze):
        """Check if there is an item at the player's current position."""
        cell_value = maze.grid[self.y][self.x]
        return registry.is_item(cell_value)

    def is_on_event_tile(self, maze):
        return maze.grid[self.y][self.x] == maze.event_tile_id

    def pick_up_item(self, maze):
        """Pick up an item if the player is on it."""
        return self._get_inv_manager().pick_up_from_maze(maze, self.x, self.y)

    def check_health(self):
        """Check if the player is alive."""
        if self.health <= 0:
            self.health = 0
            # Handle player death (e.g., end game or respawn)

    def get_nearby_npc(self, npcs):
        """Return an NPC if one is adjacent to the player."""
        for npc in npcs:
            if abs(npc.x - self.x) + abs(npc.y - self.y) == 1:
                return npc
        return None

    def accept_quest(self, quest_id: int):
        if quest_id not in self.active_quests:
            self.active_quests.append(quest_id)

    def complete_quest(self, quest_id: int):
        if quest_id in self.active_quests:
            self.active_quests.remove(quest_id)
            self.completed_quests.append(quest_id)

    def has_completed(self, quest_id: int) -> bool:
        return quest_id in self.completed_quests

    def fail_quest(self, quest_id: int):
        if quest_id in self.active_quests:
            self.active_quests.remove(quest_id)
        if quest_id not in self.failed_quests:
            self.failed_quests.append(quest_id)

    def add_follower(self, follower) -> bool:
        """Add a follower. Returns False if at max capacity."""
        from src.models.follower import MAX_FOLLOWERS

        if len(self.followers) >= MAX_FOLLOWERS:
            return False
        self.followers.append(follower)
        return True

    def remove_follower(self, npc_id: int):
        self.followers = [f for f in self.followers if f.npc_id != npc_id]

    def get_follower_by_quest(self, quest_id: int):
        for f in self.followers:
            if f.quest_id == quest_id:
                return f
        return None

    # --- Combat helpers ---

    def get_stat_mod(self, stat_name: str) -> int:
        """Return the D&D-style modifier for a stat, including active buffs."""
        if self.player_class:
            base = getattr(self.player_class.stats, stat_name, 10)
        else:
            base = 10
        buff_bonus = sum(b.value for b in self.active_buffs if b.stat == stat_name)
        return stat_modifier(base + buff_bonus)

    def get_ac(self) -> int:
        """Armor class: 10 + armor + DEX mod."""
        return 10 + self.armor + self.get_stat_mod("DEX")

    def roll_initiative(self) -> int:
        return random.randint(1, 20) + self.get_stat_mod("DEX")

    def _resolve_weapon_stat(self) -> str:
        """Return the stat governing the current weapon. Random weapons pick a random stat."""
        if self.weapon is None:
            return "STR"
        if self.weapon.weapon_type == "wild":
            from src.models.weapon import RANDOM_WEAPON_STATS

            return random.choice(RANDOM_WEAPON_STATS)
        return self.weapon.stat

    def _weapon_stat_bonus(self, stat: str) -> int:
        """Return the stat bonus for the current weapon, applying soft-restriction.

        - Matching category → full stat modifier
        - Jester → avg(LUCK mod, weapon stat mod)
        - Mismatched category → 0 (no stat bonus, just base damage)
        """
        archetype = self.player_class.archetype if self.player_class else "warrior"
        if archetype == "jester":
            return self.get_jester_mod(stat)
        category = self.weapon.weapon_category if self.weapon else "simple"
        allowed = ARCHETYPE_WEAPON_CATEGORIES.get(archetype, {"simple"})
        if category in allowed:
            return self.get_stat_mod(stat)
        return 0

    def roll_attack(self) -> int:
        """1d20 + weapon stat bonus + level mod. Soft-restricted by class."""
        stat = self._resolve_weapon_stat()
        return random.randint(1, 20) + self._weapon_stat_bonus(stat) + (self.level - 1)

    def roll_weapon_damage(self) -> int:
        """Roll weapon damage dice + weapon stat bonus. Soft-restricted by class."""
        stat = self._resolve_weapon_stat()
        if self.weapon is None:
            return max(1, random.randint(1, 4) + self._weapon_stat_bonus(stat))
        base = self.weapon.roll_damage()
        return max(1, base + self._weapon_stat_bonus(stat))

    def roll_magic_attack(self) -> int:
        """1d20 + INT (mage) or WIS (healer) + level mod."""
        archetype = self.player_class.archetype if self.player_class else "warrior"
        if archetype == "healer":
            return random.randint(1, 20) + self.get_stat_mod("WIS") + (self.level - 1)
        return random.randint(1, 20) + self.get_stat_mod("INT") + (self.level - 1)

    def get_jester_mod(self, normal_stat: str) -> int:
        """Jester modifier rule: avg(LUCK mod, normal stat mod)."""
        luck_mod = self.get_stat_mod("LUCK")
        normal_mod = self.get_stat_mod(normal_stat)
        return (luck_mod + normal_mod) // 2

    def can_afford_spell(self, spell) -> bool:
        return self.stamina >= spell.stamina_cost

    def pay_spell_cost(self, spell):
        self.stamina = max(0, self.stamina - spell.stamina_cost)

    def apply_buff(self, stat: str, value: int, duration: int):
        self.active_buffs.append(ActiveBuff(stat=stat, value=value, turns_remaining=duration))

    def tick_buffs(self):
        """Decrement buff durations at end of player's turn. Remove expired."""
        for buff in self.active_buffs:
            buff.turns_remaining -= 1
        self.active_buffs = [b for b in self.active_buffs if b.turns_remaining > 0]

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    # --- Phase 4: Items, Inventory & Shops ---

    def equip_weapon(self, weapon_name: str) -> str:
        """Equip a weapon from inventory."""
        return self._get_inv_manager().equip_weapon(weapon_name)

    def get_equipped_weapon(self):
        """Return the equipped Weapon object, or None."""
        return self._get_inv_manager().get_equipped_weapon()

    def add_money(self, amount: int):
        """Add money to the player's wallet."""
        self.money += amount

    def spend_money(self, amount: int) -> bool:
        """Spend money if the player has enough. Returns True on success."""
        if self.money >= amount:
            self.money -= amount
            return True
        return False

    def use_spell_scroll(self, scroll_name: str) -> str:
        """Use a spell scroll. Jesters learn the spell permanently instead of consuming."""
        return self._get_inv_manager().use_spell_scroll(scroll_name)
