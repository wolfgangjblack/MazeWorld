"""MazeWorld — single entry point.

Usage:
    python main.py             # Full pipeline: generate -> package (future)
    python main.py --dev       # Generate world -> launch game directly
    python main.py --dev --skip-gen  # Skip generation, launch from existing data/
"""

import argparse
import os

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NUM_FOOD, NUM_DRINKS, NUM_TOOLS, WORLD_SEED,
)
from src.registry import registry
from src.models.maze import Maze
from src.models.dialogue_box import DialogueBox
from src.models.player import PlayerCharacter
from src.models.npc import StaticNPC, RandomNPC, AggressiveNPC
from src.controllers.game_controller import GameController
from src.controllers.screen_controller import ScreenController, ScreenState
from src.views.start_view import StartView
from src.views.class_select_view import ClassSelectView
from src.views.room_intro_view import RoomIntroView

NPC_CLASS_MAP = {
    "StaticNPC": StaticNPC,
    "RandomNPC": RandomNPC,
    "AggressiveNPC": AggressiveNPC,
}


def parse_args():
    parser = argparse.ArgumentParser(description="MazeWorld V1")
    parser.add_argument("--dev", action="store_true",
                        help="Dev mode: generate world and launch game directly")
    parser.add_argument("--skip-gen", action="store_true",
                        help="Skip world generation (use with --dev)")
    return parser.parse_args()


def run_generation():
    """Run the world generation pipeline."""
    from src.generate.pipeline import generate_world
    generate_world()
    registry.reload()


def setup_game(screen, font, player_name="Adventurer", selected_class=None):
    """Load game data and create all game objects. Returns (game_controller,)."""
    has_pregen = registry.has_manifest() and registry.manifest_matches_seed(WORLD_SEED)

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
        player = PlayerCharacter(x=player_start[0], y=player_start[1], name=player_name)
    else:
        player = PlayerCharacter(x=0, y=0, name=player_name)

    # Apply selected class
    if selected_class:
        player.apply_class(selected_class)

    player.initialize_inventory()

    if not selected_class and registry.manifest and registry.manifest.get("player_portrait"):
        player.profile_image = registry.manifest["player_portrait"]

    # --- Create NPCs ---
    npcs = []
    if has_pregen:
        for npc_data in registry.get_active_npcs():
            cls = NPC_CLASS_MAP.get(npc_data.get("type", "StaticNPC"), StaticNPC)
            kwargs = dict(npc_data)
            npc_id_str = str(kwargs.get("id", 0))
            pos = npc_positions.get(npc_id_str, [kwargs.get("x", 0), kwargs.get("y", 0)])
            kwargs["x"] = pos[0]
            kwargs["y"] = pos[1]
            if cls is RandomNPC:
                kwargs.setdefault("home_x", pos[0])
                kwargs.setdefault("home_y", pos[1])
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
        npc.prepare(maze_environment=maze.environment)

    # --- Load events and quests ---
    events = registry.event_registry
    quests = registry.quest_registry

    return GameController(screen, font, maze, player, npcs, dialogue_box, events, quests)


def main():
    args = parse_args()

    registry.load()

    # --- Generation phase ---
    if args.dev and not args.skip_gen:
        has_pregen = registry.has_manifest() and registry.manifest_matches_seed(WORLD_SEED)
        if not has_pregen:
            print(f"World data missing or stale (seed={WORLD_SEED}). Generating...")
            run_generation()
    elif not args.dev:
        # Default mode: ensure world exists, then generate if needed
        has_pregen = registry.has_manifest() and registry.manifest_matches_seed(WORLD_SEED)
        if not has_pregen:
            print(f"World data missing or stale (seed={WORLD_SEED}).")
            print("Run `python main.py --dev` to generate, or press Enter to generate now.")
            try:
                input()
                run_generation()
            except (EOFError, KeyboardInterrupt):
                print("Skipping generation, using fallback runtime mode.")

    # --- Initialize Pygame ---
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("MazeWorld")
    font = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()

    # --- Screen state machine ---
    screen_ctrl = ScreenController(ScreenState.START)
    start_view = StartView(screen, font)
    class_select_view = None
    room_intro_view = None
    selected_class = None
    player_name = "Adventurer"

    def _handle_start() -> str | None:
        nonlocal class_select_view
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = start_view.handle_input(event)
                if action == "new_game":
                    class_options = registry.get_class_options()
                    if class_options:
                        class_select_view = ClassSelectView(screen, font, class_options)
                        screen_ctrl.replace(ScreenState.CLASS_SELECT)
                    else:
                        screen_ctrl.replace(ScreenState.GAMEPLAY)
                    return None
                if action == "quit":
                    return "quit"
        start_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_class_select() -> str | None:
        nonlocal player_name, selected_class, room_intro_view
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                result = class_select_view.handle_input(event)
                if result:
                    if result["action"] == "selected":
                        class_idx = result["class_index"]
                        player_name = result["player_name"]
                        selected_class = registry.get_class_options()[class_idx]
                        env_name = ""
                        env_type = ""
                        if registry.manifest:
                            env_name = registry.manifest.get("environment_name", "Unknown Land")
                            env_type = registry.manifest.get("environment", "unknown")
                        story_text = (
                            f"{player_name} the {selected_class.name} "
                            f"steps into {env_name}, a {env_type} shrouded in mystery. "
                            "The air hums with untold stories, and the path ahead "
                            "promises both peril and wonder."
                        )
                        env_portrait = registry.manifest.get("environment_portrait") if registry.manifest else None
                        room_intro_view = RoomIntroView(
                            screen, font, env_name, env_type, story_text,
                            portrait_path=env_portrait,
                        )
                        screen_ctrl.replace(ScreenState.ROOM_INTRO)
                    elif result["action"] == "back":
                        screen_ctrl.replace(ScreenState.START)
                    return None
        if class_select_view:
            class_select_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_room_intro() -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if room_intro_view and room_intro_view.handle_input(event):
                    screen_ctrl.replace(ScreenState.GAMEPLAY)
                    return None
        if room_intro_view:
            room_intro_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_gameplay() -> str | None:
        game_controller = setup_game(screen, font, player_name, selected_class)
        game_controller.run()
        return "quit"

    screen_handlers: dict[ScreenState, callable] = {
        ScreenState.START: _handle_start,
        ScreenState.CLASS_SELECT: _handle_class_select,
        ScreenState.ROOM_INTRO: _handle_room_intro,
        ScreenState.GAMEPLAY: _handle_gameplay,
    }

    running = True
    while running:
        handler = screen_handlers.get(screen_ctrl.state)
        if handler is None:
            break
        result = handler()
        if result == "quit":
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
