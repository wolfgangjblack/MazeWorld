import pygame
from config import GRID_SIZE
from utils.item_utils import Food, Drink, Tool

class PlayerCharacter:
    def __init__(self, start_x, start_y, color=(0, 0, 255)):
        """Initialize the player with a starting position and an empty inventory."""
        self.x = start_x
        self.y = start_y
        self.color = color
        self.inventory = {  # Initial inventory with categories
            "bread": Food("bread", quantity=1),
            "water": Drink("water", quantity=2),
            "hammer": Tool("hammer", quantity=1)
        }
        self.selected_item_index = 0  # Tracks the selected item in the inventory


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