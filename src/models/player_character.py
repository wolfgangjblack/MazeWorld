import random
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from src.registry import registry


def stat_modifier(value: int) -> int:
    """D&D-style modifier: (stat - 10) // 2."""
    return (value - 10) // 2


class ActiveBuff(BaseModel):
    """A temporary stat buff active during combat."""
    stat: str
    value: int
    turns_remaining: int


class PlayerCharacter(BaseModel):
    x: int
    y: int
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

    # --- RPG stats (Phase 2) ---
    player_class: str = "warrior"  # "warrior" | "mage" | "healer" | "jester"
    level: int = 1
    STR: int = 10
    DEX: int = 10
    CON: int = 10
    INT: int = 10
    WIS: int = 10
    CHA: int = 10
    LUCK: int = 10
    armor: int = 0  # flat armor value added to AC

    # Combat equipment — stored as dicts to avoid circular import; resolved at runtime
    weapon: Optional[Any] = None  # Weapon instance
    spells: List[Any] = Field(default_factory=list)  # list of Spell instances
    active_buffs: List[ActiveBuff] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
        
    def initialize_inventory(self):
        self.inventory = {
            name: item.clone()
            for name, item in registry.starter_inventory.items()
        }
        
    def move(self, dx: int, dy: int, maze):
        new_x = self.x + dx
        new_y = self.y + dy
        
        if not maze.is_wall(new_x, new_y):
            self.x = new_x
            self.y = new_y
            self.hunger = max(0, self.hunger - 1)
            self.thirst = max(0, self.thirst -1)
            self.apply_hunger_thirst_effects()

    def add_to_inventory(self, item):
        """Add an item to the player's inventory."""
        if item.name in self.inventory:
            self.inventory[item.name].quantity += item.quantity
        else:
            self.inventory[item.name] = item
            
    def remove_from_inventory(self, item_name):
        """Remove an item from the player's inventory."""
        if item_name in self.inventory:
            self.inventory[item_name].quantity -= 1
            if self.inventory[item_name].quantity == 0:
                del self.inventory[item_name]

    def get_inventory(self):
        """Return the player's inventory as a list of tuples (item name, quantity)."""
        return [(item.name, item.quantity) for item in self.inventory.values()]

    def use_item(self):
        """Use the currently selected item."""
        inventory_items = list(self.inventory.values())
        if inventory_items:
            item = inventory_items[self.selected_item_index]
            from src.models.items import EscortItem
            if isinstance(item, EscortItem):
                return item.use(self)
            message = item.use(self)
            self.remove_from_inventory(item.name)
            return message
        return "No item to use."

    def give_item(self):
        """Give the currently selected item."""
        inventory_items = list(self.inventory.values())
        if len(inventory_items) > 0:
            item = inventory_items[self.selected_item_index]
            from src.models.items import EscortItem
            if isinstance(item, EscortItem):
                return item.give()
            message = item.give()
            self.remove_from_inventory(item.name)
            return message
        return "No item to give."
    
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
        cell_value = maze.grid[self.y][self.x]
        if registry.is_item(cell_value):
            item_template = registry.get_item(cell_value)
            item = item_template.clone()
            self.add_to_inventory(item)
            maze.grid[self.y][self.x] = 0  # Remove the item from the maze
            return f"Picked up {item.name}."
        return ""
    
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

    # --- Combat helpers ---

    def get_stat_mod(self, stat_name: str) -> int:
        """Return the D&D-style modifier for a stat, including active buffs."""
        base = getattr(self, stat_name, 10)
        buff_bonus = sum(b.value for b in self.active_buffs if b.stat == stat_name)
        return stat_modifier(base + buff_bonus)

    def get_ac(self) -> int:
        """Armor class: 10 + armor + DEX mod."""
        return 10 + self.armor + self.get_stat_mod("DEX")

    def roll_initiative(self) -> int:
        return random.randint(1, 20) + self.get_stat_mod("DEX")

    def roll_attack(self) -> int:
        """1d20 + weapon stat mod + level mod."""
        if self.weapon is None:
            return random.randint(1, 20) + self.get_stat_mod("STR") + (self.level - 1)
        return random.randint(1, 20) + self.get_stat_mod(self.weapon.stat) + (self.level - 1)

    def roll_weapon_damage(self) -> int:
        """Roll weapon damage dice + weapon stat modifier."""
        if self.weapon is None:
            return max(1, random.randint(1, 4) + self.get_stat_mod("STR"))
        base = self.weapon.roll_damage()
        return max(1, base + self.get_stat_mod(self.weapon.stat))

    def roll_magic_attack(self) -> int:
        """1d20 + INT (mage) or WIS (healer) + level mod."""
        if self.player_class == "healer":
            return random.randint(1, 20) + self.get_stat_mod("WIS") + (self.level - 1)
        return random.randint(1, 20) + self.get_stat_mod("INT") + (self.level - 1)

    def get_jester_mod(self, normal_stat: str) -> int:
        """Jester modifier rule: avg(LUCK mod, normal stat mod)."""
        luck_mod = self.get_stat_mod("LUCK")
        normal_mod = self.get_stat_mod(normal_stat)
        return (luck_mod + normal_mod) // 2

    def can_afford_spell(self, spell) -> bool:
        return self.hunger >= spell.hunger_cost and self.thirst >= spell.thirst_cost

    def pay_spell_cost(self, spell):
        self.hunger = max(0, self.hunger - spell.hunger_cost)
        self.thirst = max(0, self.thirst - spell.thirst_cost)

    def apply_buff(self, stat: str, value: int, duration: int):
        self.active_buffs.append(ActiveBuff(stat=stat, value=value, turns_remaining=duration))

    def tick_buffs(self):
        """Decrement buff durations at end of player's turn. Remove expired."""
        for buff in self.active_buffs:
            buff.turns_remaining -= 1
        self.active_buffs = [b for b in self.active_buffs if b.turns_remaining > 0]

    def is_alive(self) -> bool:
        return self.health > 0
