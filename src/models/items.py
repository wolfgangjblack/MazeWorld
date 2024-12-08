from typing import Optional
from pydantic import BaseModel

class ItemStats(BaseModel):
    nutrition_value: int = 0
    hydration_value: int = 0 
    health_value: int = 0
    uses: int = 1
    attribute: Optional[str] = None


class Item(BaseModel):
    """Base class for all items."""    
    category: str
    name: str
    desc: str
    quantity: int = 1
    item_stats : ItemStats

    def use(self):
        """Use the item."""
        return f"You used the {self.name}."

    def give(self):
        """Give the item to someone."""
        return f"You gave away the {self.name}."
    
    def clone(self):
        return self.model_copy(deep = True)


class Food(Item):
    """Represents food items."""
    
    def use(self, player):
        """Feed the player."""
        player.hunger = min(player.hunger + self.item_stats.nutrition_value, player.max_hunger)
        player.health = min(player.health + self.item_stats.health_value, player.max_health)
        return f"You ate the {self.name}. You feel better."
        

class Drink(Item):
    """Represents drink items."""
    def use(self, player):
        """Quench the player's thirst."""
        player.thirst = min(player.thirst + self.item_stats.hydration_value, player.max_thirst)
        player.health = min(player.health + self.item_stats.health_value, player.max_health)
        return f"You drank the {self.name}. It quenches your thirst."
    
class Tool(Item):
    """Represents tool items.
    1. Types can be 'bludgeon', 'cutting', 'digging', 'climbing'
    2. Use nutrition, thirst values to indicate costs of using tools - Note these should be negative
    3. Uses is the number of times the tool can be used before it breaks. 
    """
        
    def use(self, player):
        """Use the tool. Tools can have negative nutrition/hydration values and a limited number of uses."""
        # Apply costs:
        player.hunger = max(0, player.hunger + self.item_stats.nutrition_value)
        player.thirst = max(0, player.thirst + self.item_stats.hydration_value)

        # Decrement uses
        self.item_stats.uses -= 1
        if self.item_stats.uses <= 0:
            # The tool breaks
            return f"The {self.name} broke."
        
        return f"You used the {self.name}. It still seems useful"