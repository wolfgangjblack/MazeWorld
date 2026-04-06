"""MazeWorld — single entry point.

Usage:
    python main.py             # Full pipeline: generate -> package (future)
    python main.py --dev       # Generate world -> launch game directly
    python main.py --dev --skip-gen  # Skip generation, launch from existing data/
"""

import argparse
import logging
import os
import time

logger = logging.getLogger(__name__)

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NUM_FOOD, NUM_DRINKS, NUM_TOOLS,
    NUM_WEAPONS, NUM_SPELL_SCROLLS, WORLD_SEED,
)
from src.registry import registry
from src.models.maze import Maze
from src.models.dialogue_box import DialogueBox
from src.models.player import PlayerCharacter
from src.models.npc import StaticNPC, RandomNPC, AggressiveNPC, MerchantNPC
from src.controllers.game_controller import GameController
from src.controllers.screen_controller import ScreenController, ScreenState
from src.views.start_view import StartView
from src.views.class_select_view import ClassSelectView
from src.views.room_intro_view import RoomIntroView
from src.views.player_menu_view import PlayerMenuView
from src.views.load_game_view import LoadGameView
from src.systems import save_manager

NPC_CLASS_MAP = {
    "StaticNPC": StaticNPC,
    "RandomNPC": RandomNPC,
    "AggressiveNPC": AggressiveNPC,
    "MerchantNPC": MerchantNPC,
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
    """Load game data and create all game objects. Returns GameController."""
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
        maze.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS, NUM_WEAPONS, NUM_SPELL_SCROLLS)
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


def setup_game_from_save(screen, font, save_state):
    """Restore a full game from a SaveState. Returns GameController."""
    from src.models.follower import Follower

    dialogue_box = DialogueBox(screen, font)

    # --- Restore maze ---
    maze = Maze()
    maze.grid = [list(row) for row in save_state.maze_grid]
    maze.environment = save_state.maze_environment
    maze.environment_name = save_state.maze_environment_name

    # --- Restore player ---
    player = save_manager.deserialize_player(save_state.player_data)

    # --- Restore followers ---
    player.followers = [Follower(**fd) for fd in save_state.follower_data]

    # --- Restore NPCs (merge saved mutable state onto base templates) ---
    npcs = []
    saved_npc_map = {s["id"]: s for s in save_state.npc_states}

    has_pregen = registry.has_manifest() and registry.manifest_matches_seed(save_state.seed)
    if has_pregen:
        for npc_data in registry.get_active_npcs():
            cls = NPC_CLASS_MAP.get(npc_data.get("type", "StaticNPC"), StaticNPC)
            kwargs = dict(npc_data)
            kwargs.pop("selected", None)
            npc_id = kwargs.get("id", 0)

            # Apply saved state
            saved = saved_npc_map.get(npc_id, {})
            kwargs["x"] = saved.get("x", kwargs.get("x", 0))
            kwargs["y"] = saved.get("y", kwargs.get("y", 0))
            if cls is RandomNPC:
                kwargs.setdefault("home_x", saved.get("home_x", kwargs["x"]))
                kwargs.setdefault("home_y", saved.get("home_y", kwargs["y"]))

            npc = cls(**kwargs)
            npc.interaction_history = saved.get("interaction_history", [])
            npc.has_met_player = saved.get("has_met_player", False)

            # Restore merchant shop inventory
            if hasattr(npc, 'shop_inventory') and "shop_inventory" in saved:
                npc.shop_inventory = saved["shop_inventory"]

            npc.prepare(maze_environment=maze.environment)
            npcs.append(npc)

    # --- Restore events and quests (only if registry matches save seed) ---
    events = {}
    quests = {}
    if has_pregen:
        events = registry.event_registry
        for eid, saved_evt in save_state.event_states.items():
            if eid in events:
                events[eid].resolved = saved_evt.get("resolved", False)
                if hasattr(events[eid], 'monsters') and "monster_states" in saved_evt:
                    for i, ms in enumerate(saved_evt["monster_states"]):
                        if i < len(events[eid].monsters):
                            events[eid].monsters[i].hp = ms.get("hp", events[eid].monsters[i].hp)
                            events[eid].monsters[i].status_effects = ms.get("status_effects", {})
                    events[eid].combat_started = saved_evt.get("combat_started", False)
                    events[eid].player_fled = saved_evt.get("player_fled", False)

        quests = registry.quest_registry
        for qid, saved_q in save_state.quest_states.items():
            if qid in quests:
                quests[qid].status = saved_q.get("status", "not_started")
                if hasattr(quests[qid], 'current_step') and "current_step" in saved_q:
                    quests[qid].current_step = saved_q["current_step"]
    else:
        logger.warning(
            "Registry does not match save seed %d; events and quests will be empty.",
            save_state.seed,
        )

    # --- Build controller ---
    gc = GameController(screen, font, maze, player, npcs, dialogue_box, events, quests)

    # Restore event position map from save
    gc.event_position_map = {}
    for key, eid in save_state.event_position_map.items():
        parts = key.split(",")
        if len(parts) == 2:
            gc.event_position_map[(int(parts[0]), int(parts[1]))] = eid

    return gc


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
    _cached_has_saves = save_manager.has_saves()
    start_view = StartView(screen, font, has_saves=_cached_has_saves)
    class_select_view = None
    room_intro_view = None
    load_game_view = None
    player_menu_view = None
    game_controller = None
    selected_class = None
    player_name = "Adventurer"
    gameplay_start_time = 0.0
    accumulated_play_time = 0.0
    # Track where load was opened from: "start" or "gameplay"
    load_source = "start"

    def _handle_start() -> str | None:
        nonlocal class_select_view, load_game_view, load_source
        start_view.has_saves = _cached_has_saves
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
                if action == "load_game":
                    saves = save_manager.list_saves()
                    load_game_view = LoadGameView(screen, font, saves)
                    load_source = "start"
                    screen_ctrl.replace(ScreenState.LOAD_GAME)
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
        nonlocal game_controller, gameplay_start_time, player_menu_view
        nonlocal load_game_view, load_source

        if game_controller is None:
            game_controller = setup_game(screen, font, player_name, selected_class)
            gameplay_start_time = time.time()

        result = game_controller.run()

        if result == "open_menu":
            can_save = not game_controller.has_active_overlay
            player_menu_view = PlayerMenuView(
                screen, font,
                can_save=can_save,
                has_saves=_cached_has_saves,
            )
            screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        # Game loop ended (window closed)
        return "quit"

    def _handle_player_menu() -> str | None:
        nonlocal game_controller, player_menu_view
        nonlocal load_game_view, load_source, gameplay_start_time
        nonlocal accumulated_play_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = player_menu_view.handle_input(event)
                if action == "back":
                    screen_ctrl.pop()
                    return None
                if action == "save":
                    nonlocal _cached_has_saves
                    elapsed = time.time() - gameplay_start_time
                    total_time = accumulated_play_time + elapsed
                    try:
                        filepath = save_manager.save_game(
                            game_controller, WORLD_SEED, total_time,
                        )
                        _cached_has_saves = True
                        player_menu_view.set_status("Game saved!")
                    except Exception as e:
                        player_menu_view.set_status(f"Save failed: {e}", is_error=True)
                    return None
                if action == "load":
                    saves = save_manager.list_saves()
                    load_game_view = LoadGameView(screen, font, saves)
                    load_source = "gameplay"
                    screen_ctrl.push(ScreenState.LOAD_GAME)
                    return None

        # Draw the game underneath, then the menu overlay
        if game_controller:
            current_time = pygame.time.get_ticks()
            game_controller.draw(current_time)
        player_menu_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_load_game() -> str | None:
        nonlocal game_controller, gameplay_start_time, accumulated_play_time
        nonlocal load_game_view

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                result = load_game_view.handle_input(event)
                if result is None:
                    pass
                elif result["action"] == "back":
                    if load_source == "start":
                        screen_ctrl.replace(ScreenState.START)
                    else:
                        # Pop back to player menu
                        screen_ctrl.pop()
                    return None
                elif result["action"] == "load":
                    filepath = result["filepath"]
                    save_state = save_manager.load_game(filepath)
                    if save_state is None:
                        load_game_view.error_message = "Failed to load save file (corrupt or invalid)."
                        return None

                    # Restore game from save
                    try:
                        game_controller = setup_game_from_save(
                            screen, font, save_state,
                        )
                        accumulated_play_time = save_state.time_played_seconds
                        gameplay_start_time = time.time()
                        screen_ctrl.reset_to(ScreenState.GAMEPLAY)
                    except Exception as e:
                        load_game_view.error_message = f"Load failed: {e}"
                        return None
                    return None

        load_game_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    screen_handlers: dict[ScreenState, callable] = {
        ScreenState.START: _handle_start,
        ScreenState.CLASS_SELECT: _handle_class_select,
        ScreenState.ROOM_INTRO: _handle_room_intro,
        ScreenState.GAMEPLAY: _handle_gameplay,
        ScreenState.PLAYER_MENU: _handle_player_menu,
        ScreenState.LOAD_GAME: _handle_load_game,
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
