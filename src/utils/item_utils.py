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
    
    def clone(self):
        return self.__class__(self.name, self.quantity)

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
    
    def clone(self):
        return Food(self.name, self.quantity, self.nutrition_value, self.health_value)

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
    
    def clone(self):
        return Drink(self.name, self.quantity, self.hydration_value, self.health_value)

class Tool(Item):
    """Represents tool items.
    1. Types can be 'bludgeon', 'cutting', 'digging', 'climbing'
    2. Hunger and thirst costs are the values deducted from the player's hunger and thirst levels when using the tool.
    3. Uses is the number of times the tool can be used before it breaks. 
    """
    def __init__(self, name, quantity=1, type = 'bludgeon', hunger_cost = 0, thirst_cost = 0, uses = 2):
        self.type = type
        self.hunger_cost = hunger_cost
        self.thirst_cost = thirst_cost
        self.uses = uses
        super().__init__(name, quantity)
        
    def use(self, player):
        """Use the tool item."""
        self.uses -= 1
        
        player.hunger -= self.hunger_cost
        player.hunger = max(player.hunger, 0)
        player.thirst -= self.thirst_cost
        player.thirst = max(player.thirst, 0)
        
        if self.uses == 0:
            ##Need to subtract item
            return f"The {self.name} broke."
        
        return f"You used the {self.name}. It helps you with tasks."
    
    def clone(self):
        return Tool(self.name, self.quantity, self.type, self.hunger_cost, self.thirst_cost, self.uses)
    
##
# For item registries, food will start with 200,
# drinks with 300, and tools with 400
## 

ENTITY_IDS = {
    200: "bread",
    201: "apple",
    202: "steak",
    203: "fried rice",
    300: "water",
    301: "juice",
    302: "tea",
    303: "coffee",
    400: "hammer",
    401: "saw",
    402: "pickaxe",
    403: "rope"
}

item_registry  = {
    200: Food('bread', nutrition_value=20),
    201: Food('apple', nutrition_value=10),
    202: Food('steak', nutrition_value=25, health_value=15),
    203: Food('fried rice', nutrition_value=30, health_value=30),
    300: Drink('water', hydration_value=10),
    301: Drink('juice', hydration_value=15, health_value=5),
    302: Drink('tea', hydration_value=20, health_value=10),
    303: Drink('coffee', hydration_value=10, health_value=5),
    400: Tool('hammer', type='bludgeon', hunger_cost=5, thirst_cost=5, uses=3),   
    401: Tool('saw', type='cutting', hunger_cost=5, thirst_cost=5, uses=3),
    402: Tool('pickaxe', type='digging', hunger_cost=5, thirst_cost=5, uses=3),
    403: Tool('rope', type='climbing', hunger_cost=5, thirst_cost=5, uses=3)
    }