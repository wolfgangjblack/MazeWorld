import pygame
import random
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, NUM_FOOD, NUM_DRINKS, NUM_TOOLS 
from utils.maze_utils import Maze
from utils.pc_utils import PlayerCharacter
from utils.npc_utils import StaticNPC, RandomNPC, AggressiveNPC
from utils.dialogue_utils import draw_dialogue_box, player_near_npc, handle_npc_response
from utils.item_utils import item_registry, ENTITY_IDS

# Initialize pygame
pygame.init()
pygame.font.init()    

# Create the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# Initialize and generate the maze
maze = Maze()
maze.generate()
maze.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS)

# Find open spaces for player and NPC placemen
# # Helper function to get a random open space
def get_random_open_space():
    space = random.choice(open_spaces)
    open_spaces.remove(space)  # Remove the chosen space to prevent reuse
    return space

def draw_inventory(screen, font, player):
    """Draw the inventory over the game screen."""
    # Inventory background
    pygame.draw.rect(screen, (200, 200, 200), pygame.Rect(100, 100, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200))
    
    # Inventory items
    inventory = player.get_inventory()
    for index, (item, quantity) in enumerate(inventory):
        color = (255, 0, 0) if index == player.selected_item_index else (0, 0, 0)
        item_text = f"{quantity}x {item}"
        text_surface = font.render(item_text, True, color)
        screen.blit(text_surface, (150, 150 + index * 40))
    
    # Instruction to exit
    exit_text = font.render("Press 'Esc' to exit", True, (0, 0, 0))
    screen.blit(exit_text, (150, SCREEN_HEIGHT - 150))

open_spaces = maze.find_open_spaces()

# Initialize player at a random open space
player_pos = list(get_random_open_space())  # Use list to modify position later

# Create the player character
player = PlayerCharacter(start_x=player_pos[0], start_y=player_pos[1])

# Initialize NPCs at random open spaces
static_npc = StaticNPC(x=0, y=0, image_path='path_to_image')
static_npc.prepare()
static_npc.x, static_npc.y = get_random_open_space()

random_npc = RandomNPC(x=0, y=0, home_x=0, home_y=0, image_path='path_to_image')
random_npc.x, random_npc.y = get_random_open_space()
random_npc.home_x, random_npc.home_y = random_npc.x, random_npc.y
random_npc.prepare()

aggressive_npc = AggressiveNPC(x=0, y=0, image_path='path_to_image')
aggressive_npc.x, aggressive_npc.y = get_random_open_space()
aggressive_npc.prepare()
npcs = [static_npc, random_npc, aggressive_npc]
    
# Font for text rendering
font = pygame.font.Font(None, 32)

# Game loop
running = True

# Dialogue state
dialogue_active = False
inventory_active = False
input_active = False
current_npc = None
user_input = ""
npc_message = ""
item_message = None
item_message_active = False

while running:
    screen.fill(BLACK)

    if inventory_active:
        # Draw inventory if it's active
        draw_inventory(screen, font, player)
    else:
        # Draw the maze
        maze.draw(screen)

        # Update and draw NPCs
        static_npc.draw(screen)
        random_npc.update(maze)
        random_npc.draw(screen)
        aggressive_npc.update(maze, (player.x, player.y))
        aggressive_npc.draw(screen)

        # Draw the player
        player.draw(screen)
        player.draw_hud(screen)
        
    if not inventory_active and not dialogue_active:
        current_npc = player.get_nearby_npc(npcs)

        # If the player is near an NPC, show "Press Enter to talk"
        if current_npc and not dialogue_active and not item_message_active:
            text_surface = font.render("Press Enter to talk", True, WHITE)
            screen.blit(text_surface, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 50))
        
        player_at_item = player.is_item_at_player_position(maze)

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            # Close the item message dialogue box when pressing Enter or Esc
            if (event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE) and item_message_active:
                item_message = None
                item_message_active = False

            # Only allow item use after the item message box has been closed
            elif inventory_active and not item_message_active:
                # Inventory navigation and item usage code...
                pass

            # Handle movement only when no item message is active, inventory is closed, and not in dialogue
            elif not dialogue_active and not inventory_active and not item_message_active:
                player.move(event, maze)
                # After moving, update item and NPC status
                player_at_item = player.is_item_at_player_position(maze)
                if not dialogue_active:
                    current_npc = player.get_nearby_npc(npcs)

            # Start conversation with NPC (only if inventory is closed)
            if not inventory_active and not item_message_active and event.key == pygame.K_RETURN:
                if player_at_item:
                    # Player is standing on item
                    item_message = player.pick_up_item(maze)
                    item_message_active = True
                    player_at_item = False
                elif current_npc and not dialogue_active:
                    # Activate chat
                    dialogue_active = True
                    npc_message = handle_npc_response(current_npc, '')  # NPC says "hello"
                    user_input = ""
                    input_active = True
                elif dialogue_active and input_active:
                    # NPC responds with player's message or silence
                    npc_message = handle_npc_response(current_npc, user_input)
                    user_input = ""

            # Handle typing input for NPC dialogue
            if input_active and event.key != pygame.K_RETURN:
                if event.key == pygame.K_BACKSPACE:
                    user_input = user_input[:-1]
                else:
                    user_input += event.unicode

            # Escape key to exit conversation
            if event.key == pygame.K_ESCAPE and dialogue_active:
                dialogue_active = False
                input_active = False
                npc_message = ""
                user_input = ""
                current_npc = None  # Reset current_npc when dialogue ends

            # Open/close inventory
            if event.key == pygame.K_i and not dialogue_active:
                inventory_active = not inventory_active
            elif event.key == pygame.K_ESCAPE and inventory_active:
                inventory_active = False

    # Draw the dialogue box with item message if it exists
    if item_message_active:
        draw_dialogue_box(screen, font, item_message = item_message)
    elif dialogue_active:
        draw_dialogue_box(screen, font, current_npc = current_npc, npc_message = npc_message, user_message=user_input)
    elif player_at_item:
        # Show prompt to pick up item
        item_id = maze.grid[player.y][player.x]
        item = ENTITY_IDS[item_id]
        prompt = f"Press 'Enter' to pick up {item}"
        draw_dialogue_box(screen, font, item_message=prompt)
    
    # Update the screen
    pygame.display.flip()

# Quit the game
pygame.quit()
