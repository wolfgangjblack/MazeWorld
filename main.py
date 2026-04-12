"""MazeWorld — single entry point.

Usage:
    python main.py             # Full pipeline: generate -> package (future)
    python main.py --dev       # Generate world -> launch game directly
    python main.py --dev --skip-gen  # Skip generation, launch from existing data/
"""

import argparse
import logging
import os
import sys
import time

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WORLD_SEED, NUM_ROOMS,
)
from src.registry import registry
from src.models.maze import Maze
from src.models.dialogue_box import DialogueBox
from src.models.player import PlayerCharacter
from src.models.npc import StaticNPC, RandomNPC, AggressiveNPC, MerchantNPC
from src.controllers.game_controller import GameController
from src.controllers.screen_controller import ScreenController, ScreenState
from src.views.start_view import StartView
from src.views.config_view import ConfigView
from src.views.class_select_view import ClassSelectView
from src.views.room_intro_view import RoomIntroView
from src.views.level_up_view import LevelUpView
from src.views.victory_view import VictoryView
from src.views.player_menu_view import PlayerMenuView
from src.views.load_game_view import LoadGameView
from src.views.pause_view import PauseView
from src.views.gameover_view import GameOverView
from src.views.menu_view import MenuView
from src.views.tutorial_view import TutorialView
from src.views.story_view import StoryView
from src.views.credits_view import CreditsView
from src.systems import save_manager
from src.systems.fog_of_war import FogOfWar
from src.models.time import DayNightCycle

logger = logging.getLogger(__name__)

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


def setup_game(screen, font, player_name="Adventurer", selected_class=None,
               room_index=0, player=None, sfx=None):
    """Load game data and create all game objects. Returns GameController.

    If ``player`` is provided (room transition), reuse it instead of creating new.
    """
    has_pregen = registry.has_manifest() and registry.manifest_matches_seed(WORLD_SEED)
    total_rooms = registry.manifest.get("num_rooms", 1) if registry.manifest else NUM_ROOMS

    # Load room-specific data if available
    room_dir = registry.get_room_dir(room_index)
    room_maze_path = os.path.join(room_dir, "maze.json")
    if has_pregen and os.path.exists(room_maze_path):
        registry.load_room(room_index)
        maze, maze_data = Maze.load_from_json(room_maze_path)
        player_start = maze_data.get("player_start", [1, 1])
        npc_positions = maze_data.get("npc_positions", {})
    elif has_pregen and os.path.exists("data/maze/maze.json"):
        # Legacy fallback (single-room world)
        maze, maze_data = Maze.load_from_json("data/maze/maze.json")
        player_start = maze_data.get("player_start", [1, 1])
        npc_positions = maze_data.get("npc_positions", {})
    else:
        maze = Maze()
        maze.generate()
        maze.place_event_tiles()
        player_start = None
        npc_positions = {}

    dialogue_box = DialogueBox(screen, font)

    # --- Create or reuse player ---
    if player is None:
        if player_start:
            player = PlayerCharacter(x=player_start[0], y=player_start[1], name=player_name)
        else:
            player = PlayerCharacter(x=0, y=0, name=player_name)
        if selected_class:
            player.apply_class(selected_class)
        player.initialize_inventory()
        if not selected_class and registry.manifest and registry.manifest.get("player_portrait"):
            player.profile_image = registry.manifest["player_portrait"]
    else:
        # Room transition — place player at start of new room
        if player_start:
            player.x, player.y = player_start[0], player_start[1]
        else:
            player.x, player.y = 1, 1

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

    if not has_pregen:
        for char in [player] + npcs:
            char.x, char.y = maze.place_character()

    for npc in npcs:
        if isinstance(npc, RandomNPC) and not has_pregen:
            npc.home_x, npc.home_y = npc.x, npc.y
        npc.prepare(maze_environment=maze.environment)

    events = registry.event_registry
    quests = registry.quest_registry

    return GameController(screen, font, maze, player, npcs, dialogue_box, events, quests,
                          current_room=room_index, total_rooms=total_rooms, sfx=sfx)


def setup_game_from_save(screen, font, save_state, sfx=None):
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

    # --- Restore fog of war and day/night cycle ---
    fog = None
    if save_state.fog_data:
        fog = FogOfWar.deserialize(save_state.fog_data)
    day_night = None
    if save_state.day_night_data:
        day_night = DayNightCycle.deserialize(save_state.day_night_data)

    gc = GameController(screen, font, maze, player, npcs, dialogue_box, events, quests,
                        fog=fog, day_night=day_night, sfx=sfx)

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

    # --- Music ---
    from src.systems.music_controller import MusicController
    music = MusicController(registry.manifest.get("music", {}) if registry.manifest else {})
    music.play_start_screen()

    # --- SFX ---
    from src.systems.sfx_controller import SFXController
    sfx = SFXController(registry.manifest.get("sfx", {}) if registry.manifest else {})

    # --- Screen state machine ---
    screen_ctrl = ScreenController(ScreenState.START)
    _cached_has_saves = save_manager.has_saves()
    _start_portrait = registry.manifest.get("start_portrait") if registry.manifest else None
    start_view = StartView(screen, font, has_saves=_cached_has_saves,
                           portrait_path=_start_portrait)
    config_view = ConfigView(screen, font)
    class_select_view = None
    room_intro_view = None
    load_game_view = None
    player_menu_view = None
    game_controller = None
    selected_class = None
    player_name = "Adventurer"

    # Load summary agent narrative data (if available)
    narrative = {}
    narrative_path = os.path.join("data", "narrative.json")
    if os.path.exists(narrative_path):
        try:
            import json as _json
            with open(narrative_path) as _nf:
                narrative = _json.load(_nf)
        except Exception:
            pass
    gameplay_start_time = 0.0
    accumulated_play_time = 0.0
    # Track where load was opened from: "start" or "gameplay"
    load_source = "start"
    pause_view = None
    gameover_view = None
    victory_view = None
    menu_view = None
    tutorial_view = None
    story_view = None
    credits_view = None

    def _handle_start() -> str | None:
        nonlocal class_select_view, load_game_view, load_source, tutorial_view, credits_view
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
                if action == "tutorial":
                    tutorial_view = TutorialView(screen, font)
                    screen_ctrl.push(ScreenState.TUTORIAL)
                    return None
                if action == "config":
                    screen_ctrl.replace(ScreenState.CONFIG)
                    return None
                if action == "credits":
                    credits_view = CreditsView(screen, font)
                    screen_ctrl.push(ScreenState.CREDITS)
                    return None
                if action == "quit":
                    return "quit"
        start_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_config() -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = config_view.handle_input(event)
                if action == "back":
                    screen_ctrl.replace(ScreenState.START)
                    return None
        config_view.draw()
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
                        story_text = narrative.get("room_intro_room_0", "")
                        if not story_text:
                            story_text = (
                                f"{player_name} the {selected_class.name} "
                                f"steps into {env_name}, a {env_type} shrouded in mystery. "
                                "The air hums with untold stories, and the path ahead "
                                "promises both peril and wonder."
                            )
                        env_portrait = None
                        if registry.manifest:
                            rooms = registry.manifest.get("rooms", [])
                            if rooms:
                                env_portrait = rooms[0].get("environment_portrait")
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
        nonlocal game_controller
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if room_intro_view and room_intro_view.handle_input(event):
                    if current_room_index > 0 and game_controller is not None:
                        # Room transition: create new controller for new room
                        player = game_controller.player
                        game_controller = setup_game(
                            screen, font, room_index=current_room_index,
                            player=player, sfx=sfx)
                    if game_controller is not None:
                        music.play_maze(game_controller.maze.environment)
                        sfx.play_ambience(game_controller.maze.environment)
                    screen_ctrl.replace(ScreenState.GAMEPLAY)
                    return None
        if room_intro_view:
            room_intro_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    current_room_index = 0
    level_up_view = None
    victory_view = None
    # Accumulated stats across rooms
    game_stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
    # Music state tracking for smooth transitions
    _was_in_combat = False
    _was_in_event = False

    def _handle_gameplay() -> str | None:
        nonlocal game_controller, gameplay_start_time, player_menu_view
        nonlocal load_game_view, load_source, current_room_index
        nonlocal pause_view, gameover_view, menu_view
        nonlocal room_intro_view, level_up_view, game_stats, victory_view, story_view
        nonlocal _was_in_combat, _was_in_event

        if game_controller is None:
            game_controller = setup_game(screen, font, player_name, selected_class,
                                         room_index=current_room_index, sfx=sfx)
            gameplay_start_time = time.time()
            music.play_maze(game_controller.maze.environment)
            sfx.play_ambience(game_controller.maze.environment)

        # --- Music: detect combat/event enter/exit ---
        in_combat = game_controller.combat_controller is not None
        in_event = game_controller.dialogue_box.event_active

        if in_combat and not _was_in_combat:
            music.play_combat()
        elif in_event and not _was_in_event and not in_combat:
            music.play_puzzle_event()
        elif not in_combat and not in_event and (_was_in_combat or _was_in_event):
            music.restore_maze()

        _was_in_combat = in_combat
        _was_in_event = in_event

        result = game_controller.run()

        if result == "open_menu":
            can_save = not game_controller.has_active_overlay
            player_menu_view = PlayerMenuView(
                screen, font,
                can_save=can_save,
                has_saves=_cached_has_saves,
                quest_log=game_controller.get_quest_log(),
                follower_info=game_controller.get_follower_info(),
            )
            screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        if result == "open_pause":
            game_controller.day_night.pause()
            can_save = not game_controller.has_active_overlay
            pause_view = PauseView(screen, font, can_save=can_save,
                                    has_saves=_cached_has_saves)
            screen_ctrl.push(ScreenState.PAUSE)
            return None

        if result == "open_full_menu":
            game_controller.day_night.pause()
            menu_view = MenuView(screen, font, game_controller.player)
            screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        if result == "open_status":
            game_controller.day_night.pause()
            menu_view = MenuView(screen, font, game_controller.player, initial_tab="stats")
            screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        if result == "open_spells":
            game_controller.day_night.pause()
            menu_view = MenuView(screen, font, game_controller.player, initial_tab="spells")
            screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        if result == "open_story":
            story = registry.get_story()
            room_beat = ""
            room_name = ""
            if story:
                beat = next(
                    (b for b in story.beats
                     if b.room_id == f"room_{current_room_index}"), None)
                if beat:
                    room_beat = beat.summary
            if game_controller:
                room_name = game_controller.maze.environment_name or ""
            story_view = StoryView(
                screen, font, story=story,
                room_story_beat=room_beat, room_name=room_name,
            )
            screen_ctrl.push(ScreenState.STORY)
            return None

        if result == "game_over":
            music.play_game_over()
            go_portrait = None
            if registry.manifest:
                go_portrait = registry.manifest.get("gameover_portrait")
            if not go_portrait:
                go_portrait = game_controller.player.profile_image
            gameover_view = GameOverView(
                screen, font, game_controller.player,
                has_saves=_cached_has_saves,
                portrait_path=go_portrait,
                story_paragraph=narrative.get("game_over", ""),
            )
            screen_ctrl.push(ScreenState.GAME_OVER)
            return None

        if result == "room_transition":
            # Accumulate stats from current room
            for k in game_stats:
                game_stats[k] += game_controller.stats.get(k, 0)

            current_room_index += 1
            total_rooms = game_controller.total_rooms

            if current_room_index >= total_rooms:
                # Final room cleared — victory!
                game_stats["rooms_cleared"] += 1
                music.play_victory()
                player = game_controller.player
                vic_portrait = registry.manifest.get("victory_portrait") if registry.manifest else None
                victory_view = VictoryView(
                    screen, font, player, game_stats, total_rooms,
                    story_paragraph=narrative.get("victory", ""),
                    portrait_path=vic_portrait)
                screen_ctrl.replace(ScreenState.VICTORY)
                return None

            # Level up before entering next room
            player = game_controller.player
            level_up_view = LevelUpView(screen, font, player)
            screen_ctrl.replace(ScreenState.LEVEL_UP)
            return None

        if result == "victory":
            for k in game_stats:
                game_stats[k] += game_controller.stats.get(k, 0)
            music.play_victory()
            player = game_controller.player
            total_rooms = game_controller.total_rooms
            vic_portrait = registry.manifest.get("victory_portrait") if registry.manifest else None
            victory_view = VictoryView(
                screen, font, player, game_stats, total_rooms,
                story_paragraph=narrative.get("victory", ""),
                portrait_path=vic_portrait)
            screen_ctrl.replace(ScreenState.VICTORY)
            return None

        return "quit"

    def _handle_player_menu() -> str | None:
        nonlocal game_controller, player_menu_view, menu_view
        nonlocal load_game_view, load_source, gameplay_start_time
        nonlocal accumulated_play_time

        # Full tabbed menu mode
        if menu_view is not None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    action = menu_view.handle_input(event)
                    if action == "close":
                        menu_view = None
                        if game_controller:
                            game_controller.day_night.resume()
                        screen_ctrl.pop()
                        return None
            menu_view.draw()
            pygame.display.flip()
            clock.tick(60)
            return None

        # Save/load menu mode
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = player_menu_view.handle_input(event)
                if action == "back":
                    if game_controller:
                        game_controller.day_night.resume()
                    screen_ctrl.pop()
                    return None
                if action == "save":
                    nonlocal _cached_has_saves
                    elapsed = time.time() - gameplay_start_time
                    total_time = accumulated_play_time + elapsed
                    try:
                        save_manager.save_game(
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
                if action and action.startswith("talk_follower_"):
                    try:
                        idx = int(action.split("_")[-1])
                        msg = game_controller.follower_manager.talk_to_follower(idx)
                        player_menu_view.set_status(msg)
                    except (ValueError, IndexError):
                        pass
                    return None

        # Draw the game underneath, then the menu overlay
        if game_controller:
            current_time = pygame.time.get_ticks()
            game_controller.draw(current_time)
        player_menu_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_pause() -> str | None:
        nonlocal pause_view, game_controller, gameplay_start_time
        nonlocal accumulated_play_time, _cached_has_saves
        nonlocal menu_view, player_menu_view, story_view
        nonlocal load_game_view, load_source

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = pause_view.handle_input(event)
                if action == "resume":
                    game_controller.day_night.resume()
                    screen_ctrl.pop()
                    return None
                if action == "inventory":
                    screen_ctrl.pop()
                    game_controller.inventory_active = True
                    return None
                if action == "rest":
                    screen_ctrl.pop()
                    game_controller.rest_menu_active = True
                    game_controller.dialogue_box.set_item_message(
                        "Rest: 1=3hr  2=6hr  3=12hr  Esc=Cancel")
                    game_controller.item_message_active = True
                    return None
                if action == "status":
                    menu_view = MenuView(screen, font, game_controller.player, initial_tab="stats")
                    screen_ctrl.pop()
                    screen_ctrl.push(ScreenState.PLAYER_MENU)
                    return None
                if action == "spells":
                    menu_view = MenuView(screen, font, game_controller.player, initial_tab="spells")
                    screen_ctrl.pop()
                    screen_ctrl.push(ScreenState.PLAYER_MENU)
                    return None
                if action == "quest_log":
                    screen_ctrl.pop()
                    game_controller.quest_log_active = True
                    return None
                if action == "story":
                    story = registry.get_story()
                    room_beat = ""
                    room_name = ""
                    if story:
                        beat = next(
                            (b for b in story.beats
                             if b.room_id == f"room_{current_room_index}"), None)
                        if beat:
                            room_beat = beat.summary
                    if game_controller:
                        room_name = game_controller.maze.environment_name or ""
                    story_view = StoryView(
                        screen, font, story=story,
                        room_story_beat=room_beat, room_name=room_name,
                    )
                    screen_ctrl.pop()
                    screen_ctrl.push(ScreenState.STORY)
                    return None
                if action == "save":
                    elapsed = time.time() - gameplay_start_time
                    total_time = accumulated_play_time + elapsed
                    try:
                        save_manager.save_game(
                            game_controller, WORLD_SEED, total_time,
                        )
                        _cached_has_saves = True
                        pause_view.has_saves = True
                        pause_view.set_status("Game saved!")
                    except Exception as e:
                        pause_view.set_status(f"Save failed: {e}", is_error=True)
                    return None
                if action == "load":
                    saves = save_manager.list_saves()
                    load_game_view = LoadGameView(screen, font, saves)
                    load_source = "gameplay"
                    screen_ctrl.pop()
                    screen_ctrl.push(ScreenState.LOAD_GAME)
                    return None
                if action == "quit_to_start":
                    game_controller = None
                    music.play_start_screen()
                    sfx.stop_ambience()
                    screen_ctrl.reset_to(ScreenState.START)
                    return None
                if action == "exit_game":
                    pygame.quit()
                    sys.exit()

        # Draw the game underneath, then the pause overlay
        if game_controller:
            current_time = pygame.time.get_ticks()
            game_controller.draw(current_time)
        pause_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_game_over() -> str | None:
        nonlocal gameover_view, game_controller
        nonlocal load_game_view, load_source

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = gameover_view.handle_input(event)
                if action == "load":
                    saves = save_manager.list_saves()
                    load_game_view = LoadGameView(screen, font, saves)
                    load_source = "start"
                    screen_ctrl.replace(ScreenState.LOAD_GAME)
                    return None
                if action == "quit_to_start":
                    game_controller = None
                    music.play_start_screen()
                    sfx.stop_ambience()
                    screen_ctrl.reset_to(ScreenState.START)
                    return None

        gameover_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_victory() -> str | None:
        nonlocal victory_view, game_controller

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = victory_view.handle_input(event)
                if action == "new_game":
                    game_controller = None
                    music.play_start_screen()
                    sfx.stop_ambience()
                    screen_ctrl.reset_to(ScreenState.START)
                    return None
                if action == "quit":
                    return "quit"

        victory_view.draw()
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
                            screen, font, save_state, sfx=sfx,
                        )
                        accumulated_play_time = save_state.time_played_seconds
                        gameplay_start_time = time.time()
                        music.play_maze(game_controller.maze.environment)
                        sfx.play_ambience(game_controller.maze.environment)
                        screen_ctrl.reset_to(ScreenState.GAMEPLAY)
                    except Exception as e:
                        load_game_view.error_message = f"Load failed: {e}"
                        return None
                    return None

        load_game_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_level_up() -> str | None:
        nonlocal level_up_view, room_intro_view, game_controller
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                result = level_up_view.handle_input(event)
                if result:
                    if result["action"] == "chosen":
                        player = game_controller.player
                        # Jester: randomly assign from other class pools
                        if (player.player_class
                                and player.player_class.archetype == "jester"):
                            _apply_jester_level_up(player, result["type"], result["choice"])
                        else:
                            player.apply_level_up(result["type"], result["choice"])
                    elif result["action"] == "skip":
                        if game_controller:
                            game_controller.player.level += 1

                    # Show room intro for the new room
                    _setup_room_intro_for_transition()
                    screen_ctrl.replace(ScreenState.ROOM_INTRO)
                    return None
        if level_up_view:
            level_up_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _apply_jester_level_up(player, choice_type, choice):
        """Jester level-up: apply the choice but it was randomly picked from other pools."""
        # The choice comes from the jester's own pool which was populated from
        # other class pools during generation. Just apply it normally.
        player.apply_level_up(choice_type, choice)

    def _setup_room_intro_for_transition():
        nonlocal room_intro_view, game_controller
        # Load new room data to get environment info
        room_dir = registry.get_room_dir(current_room_index)
        maze_path = os.path.join(room_dir, "maze.json")
        env_name = "Unknown Land"
        env_type = "unknown"
        env_portrait = None
        if os.path.exists(maze_path):
            import json
            with open(maze_path) as f:
                mdata = json.load(f)
            env_name = mdata.get("environment_name", env_name)
            env_type = mdata.get("environment", env_type)
        # Get story beat for this room (prefer summary agent narrative)
        room_key = f"room_intro_room_{current_room_index}"
        story_text = narrative.get(room_key, "")
        if not story_text:
            story = registry.get_story()
            if story:
                beat = next((b for b in story.beats
                             if b.room_id == f"room_{current_room_index}"), None)
                if beat:
                    story_text = beat.summary
        if not story_text:
            story_text = f"You enter a new {env_type}, deeper into the dungeon."

        # Check for room portrait
        if registry.manifest:
            rooms = registry.manifest.get("rooms", [])
            for rm in rooms:
                if rm.get("room_id") == f"room_{current_room_index}":
                    env_portrait = rm.get("environment_portrait")
                    break

        room_intro_view = RoomIntroView(
            screen, font, env_name, env_type, story_text,
            portrait_path=env_portrait,
        )

    def _handle_room_intro_transition() -> str | None:
        """Handle room intro during room transitions (reuses room_intro_view)."""
        nonlocal game_controller
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if room_intro_view and room_intro_view.handle_input(event):
                    # Create new game controller for the new room
                    player = game_controller.player
                    game_controller = setup_game(
                        screen, font, room_index=current_room_index,
                        player=player, sfx=sfx)
                    # Transfer stats
                    game_controller.stats = dict(game_stats)
                    screen_ctrl.replace(ScreenState.GAMEPLAY)
                    return None
        if room_intro_view:
            room_intro_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_victory() -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if victory_view:
                    result = victory_view.handle_input(event)
                    if result == "quit":
                        return "quit"
                    if result == "menu":
                        music.play_start_screen()
                        sfx.stop_ambience()
                        screen_ctrl.reset_to(ScreenState.START)
                        return None
        if victory_view:
            victory_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_tutorial() -> str | None:
        nonlocal tutorial_view
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = tutorial_view.handle_input(event)
                if action == "back":
                    screen_ctrl.pop()
                    return None
        tutorial_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_story() -> str | None:
        nonlocal story_view
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = story_view.handle_input(event)
                if action == "back":
                    screen_ctrl.pop()
                    return None
        if game_controller:
            current_time = pygame.time.get_ticks()
            game_controller.draw(current_time)
        story_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    def _handle_credits() -> str | None:
        nonlocal credits_view
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = credits_view.handle_input(event)
                if action == "back":
                    screen_ctrl.pop()
                    return None
        credits_view.draw()
        pygame.display.flip()
        clock.tick(60)
        return None

    screen_handlers: dict[ScreenState, callable] = {
        ScreenState.START: _handle_start,
        ScreenState.TUTORIAL: _handle_tutorial,
        ScreenState.CONFIG: _handle_config,
        ScreenState.CLASS_SELECT: _handle_class_select,
        ScreenState.ROOM_INTRO: _handle_room_intro,
        ScreenState.GAMEPLAY: _handle_gameplay,
        ScreenState.PLAYER_MENU: _handle_player_menu,
        ScreenState.LOAD_GAME: _handle_load_game,
        ScreenState.PAUSE: _handle_pause,
        ScreenState.GAME_OVER: _handle_game_over,
        ScreenState.LEVEL_UP: _handle_level_up,
        ScreenState.VICTORY: _handle_victory,
        ScreenState.STORY: _handle_story,
        ScreenState.CREDITS: _handle_credits,
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
