import pygame
import random
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK
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
    player_rect = pygame.Rect(player_pos[0] * 40, player_pos[1] * 40, 40, 40)
    pygame.draw.rect(screen, (0, 0, 255), player_rect)

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            new_pos = player_pos[:]
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

    # Update the screen
    pygame.display.flip()

# Quit the game
pygame.quit()
