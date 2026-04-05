import os
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, NUM_FOOD, NUM_DRINKS, NUM_TOOLS, WORLD_SEED

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

# --- Check manifest: if stale or missing, prompt to regenerate ---
has_pregen = registry.has_manifest() and registry.manifest_matches_seed(WORLD_SEED)

if not has_pregen:
    print(f"World data missing or stale (seed={WORLD_SEED}).")
    print("Run `python world_gen.py` to generate, or press Enter to generate now.")
    try:
        input()
        from world_gen import generate_world
        generate_world()
        registry.reload()
        has_pregen = registry.has_manifest()
    except (EOFError, KeyboardInterrupt):
        print("Skipping generation, using fallback runtime mode.")

# --- Initialize Pygame ---
pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
font = pygame.font.Font(None, 32)

dialogue_box = DialogueBox(screen, font)

# --- Load or generate maze ---
if has_pregen and os.path.exists("data/maze/maze.json"):
    maze, maze_data = Maze.load_from_json("data/maze/maze.json")
    player_start = maze_data.get("player_start", [1, 1])
    npc_positions = maze_data.get("npc_positions", {})
else:
    maze = Maze()
    maze.generate()
    maze.place_event_tiles()
    maze.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS)
    player_start = None
    npc_positions = {}

# --- Create player ---
if player_start:
    player = PlayerCharacter(x=player_start[0], y=player_start[1])
else:
    player = PlayerCharacter(x=0, y=0)
player.initialize_inventory()

if registry.manifest and registry.manifest.get("player_portrait"):
    player.profile_image = registry.manifest["player_portrait"]

# --- Create NPCs ---
npcs = []
if has_pregen:
    for npc_data in registry.get_active_npcs():
        cls = NPC_CLASS_MAP.get(npc_data.get("type", "StaticNPC"), StaticNPC)
        kwargs = dict(npc_data)
        # Ensure required positional fields
        npc_id_str = str(kwargs.get("id", 0))
        pos = npc_positions.get(npc_id_str, [kwargs.get("x", 0), kwargs.get("y", 0)])
        kwargs["x"] = pos[0]
        kwargs["y"] = pos[1]
        if cls is RandomNPC:
            kwargs.setdefault("home_x", pos[0])
            kwargs.setdefault("home_y", pos[1])
        # Remove fields that aren't on the model to avoid validation errors
        kwargs.pop("selected", None)
        npc = cls(**kwargs)
        npcs.append(npc)
else:
    for template in registry.npc_templates:
        cls = NPC_CLASS_MAP[template["type"]]
        npc_id = template["id"]
        kwargs = {"x": 0, "y": 0, "id": npc_id, "environment": maze.environment}
        if cls is RandomNPC:
            kwargs["home_x"] = 0
            kwargs["home_y"] = 0
        npc = cls(**kwargs)
        npcs.append(npc)

# Fallback: place characters if no pre-gen positions
if not has_pregen:
    for char in [player] + npcs:
        char.x, char.y = maze.place_character()

for npc in npcs:
    if isinstance(npc, RandomNPC) and not has_pregen:
        npc.home_x, npc.home_y = npc.x, npc.y
    npc.prepare()

# --- Load events and quests ---
events = registry.event_registry
quests = registry.quest_registry

game_controller = GameController(screen, font, maze, player, npcs, dialogue_box, events, quests)
game_controller.run()
