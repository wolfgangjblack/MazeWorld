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
    def use(self):
        """Use the food item and feed the player."""
        return f"You ate the {self.name}. It feeds you."

class Drink(Item):
    """Represents drink items."""
    def use(self):
        """Use the drink item and reduce thirst."""
        return f"You drank the {self.name}. It quenches your thirst."

class Tool(Item):
    """Represents tool items."""
    def use(self):
        """Use the tool item."""
        return f"You used the {self.name}. It helps you with tasks."
