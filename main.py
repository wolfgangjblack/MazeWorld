import pygame
import random
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, NUM_FOOD, NUM_DRINKS, NUM_TOOLS 

#Classes
from src.models.player_character import PlayerCharacter
from src.models.npc import StaticNPC, RandomNPC, AggressiveNPC

#Utilities
from src.utils.maze_utils import Maze
from src.utils.dialogue_utils import DialogueBox
from src.utils.item_utils import ENTITY_IDS

#Views
from src.views.player_view import PlayerView
from src.views.npc_view import NPCView

#Controls
from src.controllers.game_controller import GameController

# Initialize pygame
pygame.init()
pygame.font.init()    

# Create the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
font = pygame.font.Font(None, 32)

#Create Dialogue Box Instance
dialogue_box = DialogueBox(screen, font)

# Initialize and generate the maze
maze = Maze()
maze.generate()
maze.place_event_tiles()
maze.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS)

# Find open spaces for player and NPC placemen
# # Helper function to get a random open space
def get_random_open_space():
    space = random.choice(open_spaces)
    open_spaces.remove(space)  # Remove the chosen space to prevent reuse
    return space

open_spaces = maze.find_open_spaces()

# Initialize player at a random open space
player_pos = list(get_random_open_space())  # Use list to modify position later

# Create the player character
player = PlayerCharacter(x=player_pos[0], y=player_pos[1])
player.initialize_inventory()

# Initialize NPCs at random open spaces
static_npc = StaticNPC(x=0, y=0)
static_npc.prepare()
static_npc.x, static_npc.y = get_random_open_space()

random_npc = RandomNPC(x=0, y=0, home_x=0, home_y=0)
random_npc.x, random_npc.y = get_random_open_space()
random_npc.home_x, random_npc.home_y = random_npc.x, random_npc.y
random_npc.prepare()

aggressive_npc = AggressiveNPC(x=0, y=0)
aggressive_npc.x, aggressive_npc.y = get_random_open_space()
aggressive_npc.prepare()
npcs = [static_npc, random_npc, aggressive_npc]

game_controller = GameController(screen, font, maze, player, npcs, dialogue_box)
game_controller.run()