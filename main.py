import pygame
import random
from config import SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE, BLACK, WHITE
from utils.npc_utils import StaticNPC, RandomNPC, AggressiveNPC
from utils.maze_utils import Maze

# Initialize pygame
pygame.init()

# Create the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# Initialize and generate the maze
maze = Maze()
maze.generate()

# Find open spaces for player and NPC placement
open_spaces = maze.find_open_spaces()

# Helper function to get a random open space
def get_random_open_space():
    space = random.choice(open_spaces)
    open_spaces.remove(space)  # Remove the chosen space to prevent reuse
    return space

# Initialize player at a random open space
player_pos = list(get_random_open_space())  # Use list to modify position later

# Initialize NPCs at random open spaces
static_npc = StaticNPC(x=0, y=0, image_path='path_to_image')
static_npc.x, static_npc.y = get_random_open_space()

random_npc = RandomNPC(x=0, y=0, home_x=0, home_y=0, image_path='path_to_image')
random_npc.x, random_npc.y = get_random_open_space()
random_npc.home_x, random_npc.home_y = random_npc.x, random_npc.y

aggressive_npc = AggressiveNPC(x=0, y=0, image_path='path_to_image')
aggressive_npc.x, aggressive_npc.y = get_random_open_space()


#dialogue state
dialogue_active = False
current_npc = None
input_active = False
user_input = ""

# Font for text rendering
font = pygame.font.Font(None, 32)

def draw_dialogue_box(npc_message, user_message):
    """Draw the dialogue box at the bottom of the screen."""
    dialogue_box_rect = pygame.Rect(0, SCREEN_HEIGHT - 100, SCREEN_WIDTH, 100)
    pygame.draw.rect(screen, (236,236,236), dialogue_box_rect)

    # NPC message
    npc_text_surface = font.render(f"NPC: {npc_message}", True, BLACK)
    screen.blit(npc_text_surface, (10, SCREEN_HEIGHT - 90))

    # User message
    user_text_surface = font.render(f"You: {user_message}", True, BLACK)
    screen.blit(user_text_surface, (10, SCREEN_HEIGHT - 60))

def player_near_npc(player_pos, npc):
    """Check if the player is within 1 square of the NPC."""
    return abs(player_pos[0] - npc.x) <= 1 and abs(player_pos[1] - npc.y) <= 1

# Game loop
running = True
while running:
    screen.fill(BLACK)

    # Draw the maze
    maze.draw(screen)

    # Update and draw NPCs
    static_npc.draw(screen)
    random_npc.update(maze)
    random_npc.draw(screen)
    aggressive_npc.update(maze, player_pos)
    aggressive_npc.draw(screen)

    # Draw the player
    player_rect = pygame.Rect(player_pos[0] * GRID_SIZE, player_pos[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE)
    pygame.draw.rect(screen, (0, 0, 255), player_rect)

    # Check if the player is near any NPC
    if player_near_npc(player_pos, static_npc):
        current_npc = static_npc
    elif player_near_npc(player_pos, random_npc):
        current_npc = random_npc
    elif player_near_npc(player_pos, aggressive_npc):
        current_npc = aggressive_npc
    else:
        current_npc = None

    # If the player is near an NPC, show "Press enter to talk"
    if current_npc and not dialogue_active:
        text_surface = font.render("Press Enter to talk", True, WHITE)
        screen.blit(text_surface, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 50))

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            new_pos = player_pos[:]

            if event.key == pygame.K_RETURN:
                if current_npc and not dialogue_active:
                    # Activate chat
                    dialogue_active = True
                    npc_message = current_npc.npc_chat()  # NPC says "hello"
                    user_input = ""  # Clear user input
                    input_active = True
                elif dialogue_active and input_active:
                    # NPC response after player types
                    npc_message = "Oh no, I'm not sure how to respond"
                    input_active = False  # End the conversation

            # Handle typing input
            if input_active and event.key != pygame.K_RETURN:
                if event.key == pygame.K_BACKSPACE:
                    user_input = user_input[:-1]  # Remove last character
                else:
                    user_input += event.unicode  # Add typed character

            # Escape key to exit conversation
            if event.key == pygame.K_ESCAPE and dialogue_active:
                dialogue_active = False  # Exit dialogue mode
                input_active = False  # Stop collecting input
                npc_message = ""  # Clear NPC message
                user_input = ""  # Clear user input

            # Movement keys (only allow movement if not in dialogue)
            if not dialogue_active:
                if event.key == pygame.K_LEFT:
                    new_pos[0] -= 1
                elif event.key == pygame.K_RIGHT:
                    new_pos[0] += 1
                elif event.key == pygame.K_UP:
                    new_pos[1] -= 1
                elif event.key == pygame.K_DOWN:
                    new_pos[1] += 1

            # Check if the new position is a wall (internal or boundary)
            if not maze.is_wall(new_pos[0], new_pos[1]):
                player_pos = new_pos  # Move the player only if it's not a wall
                
    # Draw the dialogue box if it's active
    if dialogue_active:
        draw_dialogue_box(npc_message, user_input)
        
    # Update the screen
    pygame.display.flip()

# Quit the game
pygame.quit()
