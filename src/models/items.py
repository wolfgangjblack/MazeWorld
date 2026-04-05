from typing import Optional, Tuple
from pydantic import BaseModel

class ItemStats(BaseModel):
    nutrition_value: int = 0
    hydration_value: int = 0
    health_value: int = 0
    uses: int = 1
    attribute: Optional[str] = None
    price: int = 0
    attack_dice: Optional[str] = None  # e.g. "1d6", "2d4"
    stat_modifier: Optional[str] = None  # "STR", "DEX", "INT"


class Item(BaseModel):
    """Base class for all items."""
    category: str
    name: str
    desc: str
    quantity: int = 1
    item_stats: ItemStats
    profile_image: Optional[str] = None
    portrait_prompt: Optional[str] = None
    room_level: int = 1

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


class Weapon(Item):
    """Represents weapon items. Determines attack dice + stat modifier.
    Types: heavy (STR), light (DEX), simple (STR/INT).
    """
    weapon_type: str = "simple"  # "heavy", "light", "simple"

    def use(self, player):
        """Equip or unequip the weapon."""
        if player.equipped_weapon == self.name:
            player.equipped_weapon = None
            return f"You unequipped the {self.name}."
        player.equipped_weapon = self.name
        return f"You equipped the {self.name}."

    def roll_damage(self) -> int:
        """Roll attack dice and return damage value."""
        import random
        dice_str = self.item_stats.attack_dice or "1d4"
        try:
            num, sides = dice_str.split("d")
            total = sum(random.randint(1, int(sides)) for _ in range(int(num)))
        except (ValueError, TypeError):
            total = random.randint(1, 4)
        return total


class SpellScroll(Item):
    """Consumable single-use spell scroll.
    Solves events/quests/puzzles. Jester class can learn permanently.
    """
    spell_effect: str = "generic"  # describes what the spell does

    def use(self, player):
        """Use the spell scroll. Consumed on use."""
        player.health = min(player.health + self.item_stats.health_value, player.max_health)
        return f"You cast {self.name}! The scroll crumbles to dust."


class EscortItem(Item):
    """Represents an NPC being escorted. Cannot be consumed or dropped."""
    npc_id: int = 0
    target_zone: Tuple[int, int] = (0, 0)

    def use(self, player):
        return "\"Are we there yet?\""

    def give(self):
        return "You can't abandon your escort!"