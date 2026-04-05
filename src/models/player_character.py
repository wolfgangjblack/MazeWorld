from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from src.registry import registry
    
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
