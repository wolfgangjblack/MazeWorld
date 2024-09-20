import pygame
from config import GRID_SIZE, HUD_HEIGHT, SCREEN_WIDTH
from utils.item_utils import Food, Drink, Tool, ENTITY_IDS, item_registry
from utils.display_utils import game_to_screen

class PlayerCharacter:
    def __init__(self, start_x, start_y, color=(0, 0, 255)):
        """Initialize the player with a starting position and an empty inventory."""
        self.x = start_x
        self.y = start_y
        self.color = color
        
        #Inventory
        self.inventory = {  # Initial inventory with categories
            "bread": Food("bread", quantity=1, nutrition_value=15),
            "water": Drink("water", quantity=2, hydration_value=20),
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
        screen_x, screen_y = game_to_screen(self.x, self.y)
        player_rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)
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

    def add_to_inventory(self, item):
        """Add an item to the player's inventory."""
        if item.name in self.inventory:
            self.inventory[item.name].quantity += item.quantity
        else:
            self.inventory[item.name] = item

    def get_inventory(self):
        """Return the player's inventory as a list of tuples (item name, quantity)."""
        return [(item.name, item.quantity) for item in self.inventory.values()]

    def use_item(self):
        """Use the currently selected item."""
        inventory_items = list(self.inventory.values())
        if inventory_items:
            item = inventory_items[self.selected_item_index]
            message = item.use(self)  # Pass the player instance to the item's use method
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
            self.speed = self.speed * 0.8  # Reduce speed
        elif self.hunger < 80:
            self.speed = self.max_speed  # Normal speed

        # Thirst effects
        if self.thirst == 0:
            self.health -= 1 # Lose health faster when dehydrated

    def is_item_at_player_position(self, maze):
        """Check if there is an item at the player's current position."""
        cell_value = maze.grid[self.y][self.x]
        return cell_value in item_registry  # item_registry contains item IDs

    def pick_up_item(self, maze):
        """Pick up an item if the player is on it."""
        cell_value = maze.grid[self.y][self.x]
        if cell_value in item_registry:
            item_template = item_registry[cell_value]
            # Clone the item to avoid shared references
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
            
    def draw_hud(self, screen):
        """Draw the hunger, thirst, and health HUD at the top of the screen."""
        # HUD settings
        bar_width = (SCREEN_WIDTH - 80) // 3  # Adjust spacing as needed
        bar_height = 20
        spacing = 20  # Space between bars
        hud_y = (HUD_HEIGHT - bar_height) // 2  # Center the bars vertically within the HUD area

        # Positions for each bar
        hunger_x = 20
        thirst_x = hunger_x + bar_width + spacing
        health_x = thirst_x + bar_width + spacing

        # Hunger bar
        hunger_ratio = self.hunger / self.max_hunger
        hunger_rect = pygame.Rect(hunger_x, hud_y, bar_width * hunger_ratio, bar_height)
        pygame.draw.rect(screen, (255, 165, 0), hunger_rect)  # Orange color
        # Hunger bar border
        pygame.draw.rect(screen, (255, 255, 255), (hunger_x, hud_y, bar_width, bar_height), 2)

        # Thirst bar
        thirst_ratio = self.thirst / self.max_thirst
        thirst_rect = pygame.Rect(thirst_x, hud_y, bar_width * thirst_ratio, bar_height)
        pygame.draw.rect(screen, (65, 105, 225), thirst_rect)  # Royal blue color
        # Thirst bar border
        pygame.draw.rect(screen, (255, 255, 255), (thirst_x, hud_y, bar_width, bar_height), 2)

        # Health bar
        health_ratio = self.health / self.max_health
        health_rect = pygame.Rect(health_x, hud_y, bar_width * health_ratio, bar_height)
        pygame.draw.rect(screen, (255, 0, 0), health_rect)  # Red color
        # Health bar border
        pygame.draw.rect(screen, (255, 255, 255), (health_x, hud_y, bar_width, bar_height), 2)

        # Fonts and labels
        font = pygame.font.SysFont(None, 24)

        # Hunger text
        hunger_label = font.render("Hunger", True, (255, 255, 255))
        hunger_label_rect = hunger_label.get_rect(center=(hunger_x + bar_width // 2, hud_y - 15))
        screen.blit(hunger_label, hunger_label_rect)

        hunger_value = font.render(f"{int(self.hunger)} / {self.max_hunger}", True, (255, 255, 255))
        hunger_value_rect = hunger_value.get_rect(center=(hunger_x + bar_width // 2, hud_y + bar_height + 15))
        screen.blit(hunger_value, hunger_value_rect)

        # Thirst text
        thirst_label = font.render("Thirst", True, (255, 255, 255))
        thirst_label_rect = thirst_label.get_rect(center=(thirst_x + bar_width // 2, hud_y - 15))
        screen.blit(thirst_label, thirst_label_rect)

        thirst_value = font.render(f"{int(self.thirst)} / {self.max_thirst}", True, (255, 255, 255))
        thirst_value_rect = thirst_value.get_rect(center=(thirst_x + bar_width // 2, hud_y + bar_height + 15))
        screen.blit(thirst_value, thirst_value_rect)

        # Health text
        health_label = font.render("Health", True, (255, 255, 255))
        health_label_rect = health_label.get_rect(center=(health_x + bar_width // 2, hud_y - 15))
        screen.blit(health_label, health_label_rect)

        health_value = font.render(f"{int(self.health)} / {self.max_health}", True, (255, 255, 255))
        health_value_rect = health_value.get_rect(center=(health_x + bar_width // 2, hud_y + bar_height + 15))
        screen.blit(health_value, health_value_rect)

    def apply_buffs(self):
        """Apply buffs when hunger and thirst are high."""
        if self.hunger > 80 and self.thirst > 80:
            self.speed = self.max_speed  
        else:
            self.speed = self.base_speed  # Normal speed
            
    def get_nearby_npc(self, npcs):
        """Return an NPC if one is adjacent to the player."""
        for npc in npcs:
            if abs(npc.x - self.x) + abs(npc.y - self.y) == 1:
                return npc
        return None
