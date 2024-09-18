class Item:
    """Base class for all items."""
    def __init__(self, name, quantity=1):
        self.name = name
        self.quantity = quantity

    def use(self):
        """Use the item."""
        return f"You used the {self.name}."

    def give(self):
        """Give the item to someone."""
        return f"You gave away the {self.name}."

class Food(Item):
    """Represents food items."""
    def __init__(self, name, quantity=1, nutrition_value=10, health_value=0):
        super().__init__(name, quantity)
        self.nutrition_value = nutrition_value
        self.health_value = health_value
        
    def use(self, player):
        """Use the food item and feed the player."""
        player.hunger += self.nutrition_value
        player.hunger = min(player.hunger, player.max_hunger)
        player.health += self.health_value
        player.health = min(player.health, player.max_health)
        return f"You ate the {self.name}. It fills your stomach."

class Drink(Item):
    """Represents drink items."""
    def __init__(self, name, quantity=1, hydration_value=10, health_value=0):
        super().__init__(name, quantity)
        self.hydration_value = hydration_value
        self.health_value = health_value
        
    def use(self, player):
        """Use the drink item and reduce thirst."""
        player.thirst += self.hydration_value
        player.thirst = min(player.thirst, player.max_thirst)
        player.health += self.health_value
        player.health = min(player.health, player.max_health)
        return f"You drank the {self.name}. It quenches your thirst."

class Tool(Item):
    """Represents tool items."""
    def __init__(self, name, quantity=1):
        super().__init__(name, quantity)
        
    def use(self):
        """Use the tool item."""
        return f"You used the {self.name}. It helps you with tasks."
