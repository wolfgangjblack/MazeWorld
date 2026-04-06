import random
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field
from src.registry import registry

StatName = Literal["STR", "DEX", "CON", "INT", "WIS", "CHA", "LUCK"]
STAT_NAMES: list[StatName] = ["STR", "DEX", "CON", "INT", "WIS", "CHA", "LUCK"]
STAT_BUDGET = 72

# Archetype stat role assignments: primary stats get 14-18, secondary 11-14, dump 6-10
ARCHETYPE_STAT_ROLES = {
    "warrior": {"primary": ["STR", "CON"], "secondary": ["DEX", "CHA"], "dump": ["INT", "WIS"]},
    "mage":    {"primary": ["INT"],        "secondary": ["WIS", "DEX"], "dump": ["STR", "CON", "CHA"]},
    "healer":  {"primary": ["WIS"],        "secondary": ["CHA", "CON"], "dump": ["STR", "DEX", "INT"]},
    "jester":  {"primary": ["LUCK"],       "secondary": ["STR", "DEX", "CON", "INT", "WIS", "CHA"], "dump": []},
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
            if not (11 <= val <= 14):
                errors.append(f"{stat}={val} not in secondary range 11-14")
        for stat in roles.get("dump", []):
            val = getattr(self, stat)
            if not (6 <= val <= 10):
                errors.append(f"{stat}={val} not in dump range 6-10")
        if self.total() != STAT_BUDGET:
            errors.append(f"total={self.total()} != budget {STAT_BUDGET}")
        return errors


class Ability(BaseModel):
    name: str
    description: str
    stat: StatName = "STR"
    cost_hunger: int = 0
    cost_thirst: int = 0


class Spell(BaseModel):
    name: str
    description: str
    element: str = "fire"
    damage_dice: str = "1d6"
    spell_type: str = "damage"  # damage | healing | buff | utility
    cost_hunger: int = 5
    cost_thirst: int = 0


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
    hunger: int = 100
    thirst: int = 100
    speed: float = 1.0
    max_hunger: int = 100
    max_health: int = 100
    max_thirst: int = 100
    max_speed: float = 2.0
    selected_item_index: int = 0
    inventory: Dict[str, object] = Field(default_factory=dict)
    profile_image: Optional[str] = None
    active_quests: List[str] = Field(default_factory=list)
    completed_quests: List[str] = Field(default_factory=list)
    failed_quests: List[str] = Field(default_factory=list)
    followers: List[Any] = Field(default_factory=list)  # List[Follower]
    abilities: List[Any] = Field(default_factory=list)
    spells: List[Any] = Field(default_factory=list)
    equipped_weapon: str = ""
    armor: int = 0  # flat armor value added to AC
    weapon: Optional[Any] = None  # Weapon instance (resolved at runtime)
    active_buffs: List[ActiveBuff] = Field(default_factory=list)

    # --- Phase 4: Items, Inventory & Shops ---
    money: int = 0
    equipped_weapon: Optional[str] = None
    learned_spells: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def _get_inv_manager(self):
        """Lazy-init InventoryManager bound to this player's inventory."""
        if not hasattr(self, '_inv_manager') or self._inv_manager is None:
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

    def level_up_choices(self) -> list:
        """Return available abilities/spells to pick from on level-up."""
        if not self.player_class:
            return []
        known_names = {a.name for a in self.abilities} | {s.name for s in self.spells}
        choices = []
        for a in self.player_class.ability_pool:
            if a.name not in known_names:
                choices.append(("ability", a))
        for s in self.player_class.spell_pool:
            if s.name not in known_names:
                choices.append(("spell", s))
        return choices

    def apply_level_up(self, choice_type: str, choice):
        """Apply a level-up choice (ability or spell)."""
        self.level += 1
        if choice_type == "ability":
            self.abilities.append(choice)
        elif choice_type == "spell":
            self.spells.append(choice)

    def initialize_inventory(self):
        from config import STARTING_MONEY
        self.inventory = {
            name: item.clone()
            for name, item in registry.starter_inventory.items()
        }
        self.money = STARTING_MONEY
        
    def move(self, dx: int, dy: int, maze, survival_system=None):
        new_x = self.x + dx
        new_y = self.y + dy

        if not maze.is_wall(new_x, new_y):
            self.x = new_x
            self.y = new_y
            if survival_system is not None:
                survival_system.on_move(self)
            else:
                # Legacy fallback
                self.hunger = max(0, self.hunger - 1)
                self.thirst = max(0, self.thirst - 1)
                self.apply_hunger_thirst_effects()

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
    
    def update_hunger_and_thirst(self):
        """Decrease hunger and thirst over time."""
        self.hunger = max(0, self.hunger - 0.05)
        self.thirst = max(0, self.thirst - 0.1)

    def apply_hunger_thirst_effects(self):
        """Apply penalties based on hunger and thirst levels."""
        # Hunger effects
        if self.hunger == 0:
            self.health -= 1  # Lose health when starving
        elif self.hunger < 20:
            self.speed = self.speed * 0.8  # Reduce speed
        elif self.hunger < 80:
            self.speed = self.max_speed  # Normal speed

        # Thirst effects
        if self.thirst == 0:
            self.health -= 1 # Lose health faster when dehydrated

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

    def apply_buffs(self):
        """Apply buffs when hunger and thirst are high."""
        if self.hunger > 80 and self.thirst > 80:
            self.speed = self.max_speed  
        else:
            self.speed = self.speed  # Normal speed
            
    def get_nearby_npc(self, npcs):
        """Return an NPC if one is adjacent to the player."""
        for npc in npcs:
            if abs(npc.x - self.x) + abs(npc.y - self.y) == 1:
                return npc
        return None

    def accept_quest(self, quest_id: str):
        if quest_id not in self.active_quests:
            self.active_quests.append(quest_id)

    def complete_quest(self, quest_id: str):
        if quest_id in self.active_quests:
            self.active_quests.remove(quest_id)
            self.completed_quests.append(quest_id)

    def has_completed(self, quest_id: str) -> bool:
        return quest_id in self.completed_quests

    def fail_quest(self, quest_id: str):
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

    def get_follower_by_quest(self, quest_id: str):
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
        if self.weapon.weapon_type == "random":
            from src.models.weapon import RANDOM_WEAPON_STATS
            return random.choice(RANDOM_WEAPON_STATS)
        return self.weapon.stat

    def roll_attack(self) -> int:
        """1d20 + weapon stat mod + level mod."""
        stat = self._resolve_weapon_stat()
        return random.randint(1, 20) + self.get_stat_mod(stat) + (self.level - 1)

    def roll_weapon_damage(self) -> int:
        """Roll weapon damage dice + weapon stat modifier."""
        stat = self._resolve_weapon_stat()
        if self.weapon is None:
            return max(1, random.randint(1, 4) + self.get_stat_mod(stat))
        base = self.weapon.roll_damage()
        return max(1, base + self.get_stat_mod(stat))

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
        return self.hunger >= getattr(spell, 'hunger_cost', getattr(spell, 'cost_hunger', 0)) and \
               self.thirst >= getattr(spell, 'thirst_cost', getattr(spell, 'cost_thirst', 0))

    def pay_spell_cost(self, spell):
        h_cost = getattr(spell, 'hunger_cost', getattr(spell, 'cost_hunger', 0))
        t_cost = getattr(spell, 'thirst_cost', getattr(spell, 'cost_thirst', 0))
        self.hunger = max(0, self.hunger - h_cost)
        self.thirst = max(0, self.thirst - t_cost)

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
