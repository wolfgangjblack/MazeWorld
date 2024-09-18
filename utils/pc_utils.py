import pygame
from config import GRID_SIZE
from utils.item_utils import Food, Drink, Tool

class PlayerCharacter:
    def __init__(self, start_x, start_y, color=(0, 0, 255)):
        """Initialize the player with a starting position and an empty inventory."""
        self.x = start_x
        self.y = start_y
        self.color = color
        
        #Inventory
        self.inventory = {  # Initial inventory with categories
            "bread": Food("bread", quantity=1),
            "water": Drink("water", quantity=2),
            "hammer": Tool("hammer", quantity=1)
        }        
        self.selected_item_index = 0  # Tracks the selected item in the inventory
        #Life Settings
        self.health = 100
        self.hunger = 100
        self.thirst = 100
        self.speed = 1
        
        #Max settings
        self.max_hunger = 100
        self.max_health = 100
        self.max_thirst = 100
        self.max_speed = 2.0
        

    def draw(self, screen):
        """Draw the player at its current position."""
        player_rect = pygame.Rect(self.x * GRID_SIZE, self.y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, self.color, player_rect)

    def move(self, event, maze):
        """Handle player movement and check for wall collisions."""
        new_x, new_y = self.x, self.y

        # Check for movement key presses and update position accordingly
        if event.key == pygame.K_LEFT:
            new_x -= 1
        elif event.key == pygame.K_RIGHT:
            new_x += 1
        elif event.key == pygame.K_UP:
            new_y -= 1
        elif event.key == pygame.K_DOWN:
            new_y += 1

        # Check if the new position is a wall
        if not maze.is_wall(new_x, new_y):
            self.x, self.y = new_x, new_y  # Update the player's position if it's not a wall
            
            self.hunger -= 1
            self.thirst -= 1
            
            self.hunger = max(0, self.hunger)
            self.thirst = max(0, self.thirst)
            
            self.apply_hunger_thirst_effects()

    def add_to_inventory(self, item, quantity=1):
        """Add an item to the player's inventory."""
        if item.name in self.inventory:
            self.inventory[item.name].quantity += quantity
        else:
            self.inventory[item.name] = item

    def remove_from_inventory(self, item_name):
        """Remove an item from the player's inventory."""
        if item_name in self.inventory:
            self.inventory[item_name].quantity -= 1
            if self.inventory[item_name].quantity <= 0:
                del self.inventory[item_name]

    def get_inventory(self):
        """Return the player's inventory as a list of tuples (item name, quantity)."""
        return [(item.name, item.quantity) for item in self.inventory.values()]

    def use_item(self):
        """Use the currently selected item."""
        inventory_items = list(self.inventory.values())
        
        if len(inventory_items) > 0:
            item = inventory_items[self.selected_item_index]
            message = item.use()  # Call the 'use' method of the item
            self.remove_from_inventory(item.name)  # Reduce the quantity
            
            #Apply item affects
            if isinstance(item, Food):
                self.hunger += item.nutrition_value
                self.hunger = min(self.hunger, self.max_hunger)
                self.health += item.health_value
                self.health = min(self.health, self.max_health)
                
            elif isinstance(item, Drink):
                self.thirst += item.hydration_value
                self.thirst = min(self.thirst, self.max_thirst)    
                self.health += item.health_value
                self.health = min(self.health, self.max_health)
            
            return message
        return "No item to use."

    def give_item(self):
        """Give the currently selected item."""
        inventory_items = list(self.inventory.values())
        if len(inventory_items) > 0:
            item = inventory_items[self.selected_item_index]
            message = item.give()  # Call the 'give' method of the item
            self.remove_from_inventory(item.name)  # Reduce the quantity
            return message
        return "No item to give."
    
    def update_hunger_and_thirst(self):
        """Decrease hunger and thirst over time."""
        self.hunger -= 0.05  # Adjust the rate as needed
        self.thirst -= 0.1

        # Ensure levels don't drop below zero
        self.hunger = max(0, self.hunger)
        self.thirst = max(0, self.thirst)

    def apply_hunger_thirst_effects(self):
        """Apply penalties based on hunger and thirst levels."""
        # Hunger effects
        if self.hunger == 0:
            self.health -= 1  # Lose health when starving
        elif self.hunger < 20:
            self.speed = self.base_speed * 0.8  # Reduce speed
        elif self.hunger < 80:
            self.speed = self.max_speed  # Normal speed

        # Thirst effects
        if self.thirst == 0:
            self.health -= 1 # Lose health faster when dehydrated
        
    def pick_up_item(self, maze):
        """Pick up an item if the player is on it."""
        cell_value = maze.grid[self.y][self.x]
        if cell_value == "food":
            new_food = Food("Bread", nutrition_value=20)
            self.add_to_inventory(new_food)
            maze.grid[self.y][self.x] = 0  # Remove the item from the maze
            return "Picked up food."
        elif cell_value == "drink":
            new_drink = Drink("Water", hydration_value=20)
            self.add_to_inventory(new_drink)
            maze.grid[self.y][self.x] = 0  # Remove the item from the maze
            return "Picked up drink."
        return ""

    def check_health(self):
        """Check if the player is alive."""
        if self.health <= 0:
            self.health = 0
            # Handle player death (e.g., end game or respawn)
            
    def draw_hud(self, screen):
        """Draw the hunger and thirst HUD."""
        # Hunger bar
        hunger_bar_width = 200
        hunger_bar_height = 20
        hunger_ratio = self.hunger / self.max_hunger
        hunger_rect = pygame.Rect(10, 10, hunger_bar_width * hunger_ratio, hunger_bar_height)
        pygame.draw.rect(screen, (255, 165, 0), hunger_rect)  # Orange color

        # Thirst bar
        thirst_bar_width = 200
        thirst_bar_height = 20
        thirst_ratio = self.thirst / self.max_thirst
        thirst_rect = pygame.Rect(10, 40, thirst_bar_width * thirst_ratio, thirst_bar_height)
        pygame.draw.rect(screen, (65, 105, 225), thirst_rect)  # Royal blue color

        # Health bar (optional)
        health_bar_width = 200
        health_bar_height = 20
        health_ratio = self.health / self.max_health
        health_rect = pygame.Rect(10, 70, health_bar_width * health_ratio, health_bar_height)
        pygame.draw.rect(screen, (255, 0, 0), health_rect)  # Red color

    def apply_buffs(self):
        """Apply buffs when hunger and thirst are high."""
        if self.hunger > 80 and self.thirst > 80:
            self.speed = self.max_speed  
        else:
            self.speed = self.base_speed  # Normal speed