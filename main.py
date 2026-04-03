import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, NUM_FOOD, NUM_DRINKS, NUM_TOOLS

from src.registry import registry
from src.models.maze import Maze
from src.models.dialogue_box import DialogueBox
from src.models.player_character import PlayerCharacter
from src.models.npc import StaticNPC, RandomNPC, AggressiveNPC
from src.controllers.game_controller import GameController

NPC_CLASS_MAP = {
    "StaticNPC": StaticNPC,
    "RandomNPC": RandomNPC,
    "AggressiveNPC": AggressiveNPC,
}

registry.load()

pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
font = pygame.font.Font(None, 32)

dialogue_box = DialogueBox(screen, font)

maze = Maze()
maze.generate()
maze.place_event_tiles()
maze.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS)

player = PlayerCharacter(x=0, y=0)
player.initialize_inventory()

npcs = []
for template in registry.npc_templates:
    cls = NPC_CLASS_MAP[template["type"]]
    npc_id = template["id"]
    kwargs = {"x": 0, "y": 0, "id": npc_id}
    if cls is RandomNPC:
        kwargs["home_x"] = 0
        kwargs["home_y"] = 0
    npc = cls(**kwargs)
    npcs.append(npc)

for char in [player] + npcs:
    char.x, char.y = maze.place_character()

for npc in npcs:
    if isinstance(npc, RandomNPC):
        npc.home_x, npc.home_y = npc.x, npc.y
    npc.prepare()

game_controller = GameController(screen, font, maze, player, npcs, dialogue_box)
game_controller.run()