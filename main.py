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
    DATA_DIR,
    NUM_ROOMS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WORLD_SEED,
)
from src.controllers.game_controller import GameController
from src.controllers.screen_controller import ScreenController, ScreenState
from src.models.dialogue_box import DialogueBox
from src.models.maze import Maze
from src.models.npc import AggressiveNPC, MerchantNPC, RandomNPC, StaticNPC
from src.models.player import PlayerCharacter
from src.models.time import DayNightCycle
from src.registry import registry
from src.systems import save_manager
from src.systems.fog_of_war import FogOfWar
from src.systems.music_director import MusicDirector
from src.utils.dataloader_utils import load_json_data
from src.views.class_select_view import ClassSelectView
from src.views.config_view import ConfigView
from src.views.credits_view import CreditsView
from src.views.gameover_view import GameOverView
from src.views.level_up_view import LevelUpView
from src.views.load_game_view import LoadGameView
from src.views.menu_view import MenuView
from src.views.pause_view import PauseView
from src.views.player_menu_view import PlayerMenuView
from src.views.room_intro_view import RoomIntroView
from src.views.start_view import StartView
from src.views.story_view import StoryView
from src.views.tutorial_view import TutorialView
from src.views.victory_view import VictoryView

logger = logging.getLogger(__name__)

NPC_CLASS_MAP = {
    "StaticNPC": StaticNPC,
    "RandomNPC": RandomNPC,
    "AggressiveNPC": AggressiveNPC,
    "MerchantNPC": MerchantNPC,
}


def parse_args():
    parser = argparse.ArgumentParser(description="MazeWorld V1")
    parser.add_argument("--dev", action="store_true", help="Dev mode: generate world and launch game directly")
    parser.add_argument("--skip-gen", action="store_true", help="Skip world generation (use with --dev)")
    parser.add_argument(
        "--exe",
        action="store_true",
        help="After (optional) generation, build the frozen macOS .app via PyInstaller and exit",
    )
    return parser.parse_args()


def run_generation():
    from src.generate.pipeline import generate_world

    generate_world()
    registry.reload()


def _start_game_loop():
    """Initialize pygame, build the session, and run until exit.

    Shared by main() and run_game_only(). Assumes registry.load() has
    already run and data is present on disk.
    """
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("MazeWorld")
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        pygame.display.set_icon(pygame.image.load(icon_path))
    font = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()

    from src.systems.music_controller import MusicController

    music = MusicController(registry.manifest.get("music", {}) if registry.manifest else {})
    music.play_start_screen()

    from src.systems.sfx_controller import SFXController

    sfx = SFXController(registry.manifest.get("sfx", {}) if registry.manifest else {})

    screen_ctrl = ScreenController(ScreenState.START)
    _start_portrait = registry.manifest.get("start_portrait") if registry.manifest else None
    start_view = StartView(screen, font, has_saves=save_manager.has_saves(), portrait_path=_start_portrait)
    config_view = ConfigView(screen, font)

    narrative = {}
    narrative_path = os.path.join(DATA_DIR, "narrative.json")
    if os.path.exists(narrative_path):
        try:
            import json as _json

            with open(narrative_path) as _nf:
                narrative = _json.load(_nf)
        except Exception:
            logger.warning("Failed to load narrative.json", exc_info=True)

    session = SessionManager(screen, font, clock, screen_ctrl, music, sfx, start_view, config_view, narrative)
    session.run()
    pygame.quit()


def run_game_only():
    """Frozen entry point: skip argparse and world generation entirely.

    Called by launcher.py when the game is running as a PyInstaller bundle.
    Raises RuntimeError if bundled data is missing -- launcher.py catches
    this and writes it to crash.log (we cannot print to a console-less app
    and pygame is not yet initialized to show a dialog).
    """
    registry.load()
    if not registry.has_manifest():
        raise RuntimeError("Game data not found. Ensure the 'data/' folder is present inside the app bundle.")
    _start_game_loop()


def setup_game(
    screen, font, player_name="Adventurer", selected_class=None, room_index=0, player=None, day_night=None, sfx=None
):
    """Load game data and create all game objects. Returns GameController.

    Global entity databases are loaded once by registry.load(). Room-specific
    entities are filtered by the position maps in maze.json.
    """
    has_pregen = registry.has_manifest() and registry.manifest_matches_seed(WORLD_SEED)
    total_rooms = registry.manifest.get("num_rooms", 1) if registry.manifest else NUM_ROOMS

    room_dir = registry.get_room_dir(room_index)
    room_maze_path = os.path.join(room_dir, "maze.json")
    maze_data = {}
    if has_pregen and os.path.exists(room_maze_path):
        registry.load_room(room_index)
        maze, maze_data = Maze.load_from_json(room_maze_path)
        player_start = maze_data.get("player_start", [1, 1])
        npc_positions = maze_data.get("npc_positions", {})
    else:
        maze = Maze()
        maze.generate()
        maze.place_event_tiles()
        player_start = None
        npc_positions = {}

    dialogue_box = DialogueBox(screen, font)

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
        if player_start:
            player.x, player.y = player_start[0], player_start[1]
        else:
            player.x, player.y = 1, 1

    # Filter entities to this room using maze.json position maps
    room_npc_ids = {int(k) for k in npc_positions.keys()} if npc_positions else set()
    room_event_ids = {ep["event_id"] for ep in maze_data.get("event_positions", [])}
    room_quest_ids = set(maze_data.get("quest_ids", []))

    npcs = []
    if has_pregen:
        for npc_data in registry.get_npcs_by_ids(room_npc_ids):
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

    events = registry.get_events_by_ids(room_event_ids) if room_event_ids else registry.event_registry
    quests = registry.get_quests_by_ids(room_quest_ids) if room_quest_ids else registry.quest_registry

    return GameController(
        screen,
        font,
        maze,
        player,
        npcs,
        dialogue_box,
        events,
        quests,
        current_room=room_index,
        total_rooms=total_rooms,
        day_night=day_night,
        sfx=sfx,
    )


def setup_game_from_save(screen, font, save_state, sfx=None):
    """Restore a full game from a SaveState. Returns GameController."""
    from src.models.follower import Follower

    dialogue_box = DialogueBox(screen, font)

    room_index = save_state.current_room
    total_rooms = save_state.total_rooms

    maze = Maze()
    maze.grid = [list(row) for row in save_state.maze_grid]
    maze.environment = save_state.maze_environment
    maze.environment_name = save_state.maze_environment_name

    if save_state.maze_door_position:
        maze.door_position = tuple(save_state.maze_door_position)
    maze.door_revealed = save_state.maze_door_revealed
    maze.gate_encounter_id = save_state.maze_gate_encounter_id

    player = save_manager.deserialize_player(save_state.player_data)
    player.followers = [Follower(**fd) for fd in save_state.follower_data]

    has_pregen = registry.has_manifest() and registry.manifest_matches_seed(save_state.seed)
    if has_pregen:
        registry.load_room(room_index)

    # Load room's maze.json for position maps to filter entities
    room_dir = registry.get_room_dir(room_index)
    room_maze_path = os.path.join(room_dir, "maze.json")
    maze_data = {}
    if os.path.exists(room_maze_path):
        maze_data = load_json_data(room_maze_path)

    room_npc_ids = {int(k) for k in maze_data.get("npc_positions", {}).keys()}
    room_event_ids = {ep["event_id"] for ep in maze_data.get("event_positions", [])}
    room_quest_ids = set(maze_data.get("quest_ids", []))

    npcs = []
    saved_npc_map = {s["id"]: s for s in save_state.npc_states}

    if has_pregen:
        npc_source = registry.get_npcs_by_ids(room_npc_ids) if room_npc_ids else registry.get_active_npcs()
        for npc_data in npc_source:
            cls = NPC_CLASS_MAP.get(npc_data.get("type", "StaticNPC"), StaticNPC)
            kwargs = dict(npc_data)
            kwargs.pop("selected", None)
            npc_id = kwargs.get("id", 0)

            saved = saved_npc_map.get(npc_id, {})
            kwargs["x"] = saved.get("x", kwargs.get("x", 0))
            kwargs["y"] = saved.get("y", kwargs.get("y", 0))
            if cls is RandomNPC:
                kwargs.setdefault("home_x", saved.get("home_x", kwargs["x"]))
                kwargs.setdefault("home_y", saved.get("home_y", kwargs["y"]))

            npc = cls(**kwargs)
            npc.interaction_history = saved.get("interaction_history", [])
            npc.has_met_player = saved.get("has_met_player", False)

            if hasattr(npc, "shop_inventory") and "shop_inventory" in saved:
                npc.shop_inventory = saved["shop_inventory"]

            # Restore dialogue state
            npc.dialogue_exhausted = saved.get("dialogue_exhausted", False)
            npc.finished_dialogue = saved.get("finished_dialogue", npc.finished_dialogue)
            npc.exhausted_dialogue = saved.get("exhausted_dialogue", npc.exhausted_dialogue)
            npc.current_dc = saved.get("current_dc", 10)
            active_tree = saved.get("_active_tree")
            if active_tree == "complete" and getattr(npc, "dialogue_tree_complete", None):
                npc.dialogue_tree = npc.dialogue_tree_complete
            elif active_tree == "failed" and getattr(npc, "dialogue_tree_failed", None):
                npc.dialogue_tree = npc.dialogue_tree_failed
            dialogue_current = saved.get("_dialogue_current")
            if dialogue_current and npc.dialogue_tree:
                npc.dialogue_tree["_current"] = dialogue_current

            if isinstance(npc, AggressiveNPC):
                npc.combat_defeated = saved.get("combat_defeated", False)
                color = saved.get("color")
                if color:
                    npc.color = tuple(color)

            npc.prepare(maze_environment=maze.environment)
            npcs.append(npc)

    events = {}
    quests = {}
    if has_pregen:
        events = registry.get_events_by_ids(room_event_ids) if room_event_ids else registry.event_registry
        for raw_eid, saved_evt in save_state.event_states.items():
            eid = int(raw_eid) if isinstance(raw_eid, str) else raw_eid
            if eid in events:
                events[eid].resolved = saved_evt.get("resolved", False)
                if hasattr(events[eid], "monsters") and "monster_states" in saved_evt:
                    for i, ms in enumerate(saved_evt["monster_states"]):
                        if i < len(events[eid].monsters):
                            events[eid].monsters[i].hp = ms.get("hp", events[eid].monsters[i].hp)
                            events[eid].monsters[i].status_effects = ms.get("status_effects", {})

        quests = registry.get_quests_by_ids(room_quest_ids) if room_quest_ids else registry.quest_registry
        for raw_qid, saved_q in save_state.quest_states.items():
            qid = int(raw_qid) if isinstance(raw_qid, str) else raw_qid
            if qid in quests:
                quests[qid].status = saved_q.get("status", "not_started")
                if hasattr(quests[qid], "current_step") and "current_step" in saved_q:
                    quests[qid].current_step = saved_q["current_step"]
    else:
        logger.warning(
            "Registry does not match save seed %d; events and quests will be empty.",
            save_state.seed,
        )

    fog = None
    if save_state.fog_data:
        fog = FogOfWar.deserialize(save_state.fog_data)
    day_night = None
    if save_state.day_night_data:
        day_night = DayNightCycle.deserialize(save_state.day_night_data)

    gc = GameController(
        screen,
        font,
        maze,
        player,
        npcs,
        dialogue_box,
        events,
        quests,
        fog=fog,
        day_night=day_night,
        current_room=room_index,
        total_rooms=total_rooms,
        sfx=sfx,
    )

    gc.event_position_map = {}
    for key, eid in save_state.event_position_map.items():
        parts = key.split(",")
        if len(parts) == 2:
            gc.event_position_map[(int(parts[0]), int(parts[1]))] = int(eid) if isinstance(eid, str) else eid
    gc.rebuild_event_maps()

    gc.gate_cleared = save_state.gate_cleared
    gc.stats = dict(save_state.gc_stats)

    return gc


class SessionManager:
    """Owns all screen-level state and the screen handler dispatch loop.

    Replaces the 15 nested closures and 20+ nonlocal variables that
    previously lived inside main().
    """

    def __init__(self, screen, font, clock, screen_ctrl, music, sfx, start_view, config_view, narrative):
        self.screen = screen
        self.font = font
        self.clock = clock
        self.screen_ctrl = screen_ctrl
        self.music = music
        self.sfx = sfx
        self.start_view = start_view
        self.config_view = config_view
        self.narrative = narrative
        self.music_director = MusicDirector(music)

        self.game_controller = None
        self.selected_class = None
        self.player_name = "Adventurer"
        self.current_room_index = 0
        self.game_stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
        self.gameplay_start_time = 0.0
        self.accumulated_play_time = 0.0
        self.load_source = "start"
        self._cached_has_saves = save_manager.has_saves()

        self.class_select_view = None
        self.room_intro_view = None
        self.load_game_view = None
        self.player_menu_view = None
        self.pause_view = None
        self.gameover_view = None
        self.victory_view = None
        self.menu_view = None
        self.tutorial_view = None
        self.story_view = None
        self.credits_view = None
        self.level_up_view = None

    def run(self):
        handlers = {
            ScreenState.START: self._handle_start,
            ScreenState.TUTORIAL: self._handle_tutorial,
            ScreenState.CONFIG: self._handle_config,
            ScreenState.CLASS_SELECT: self._handle_class_select,
            ScreenState.ROOM_INTRO: self._handle_room_intro,
            ScreenState.GAMEPLAY: self._handle_gameplay,
            ScreenState.PLAYER_MENU: self._handle_player_menu,
            ScreenState.LOAD_GAME: self._handle_load_game,
            ScreenState.PAUSE: self._handle_pause,
            ScreenState.GAME_OVER: self._handle_game_over,
            ScreenState.LEVEL_UP: self._handle_level_up,
            ScreenState.VICTORY: self._handle_victory,
            ScreenState.STORY: self._handle_story,
            ScreenState.CREDITS: self._handle_credits,
        }
        running = True
        while running:
            handler = handlers.get(self.screen_ctrl.state)
            if handler is None:
                break
            if handler() == "quit":
                running = False

    # ------------------------------------------------------------------
    # Screen handlers
    # ------------------------------------------------------------------

    def _handle_start(self) -> str | None:
        self.start_view.has_saves = self._cached_has_saves
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = self.start_view.handle_input(event)
                if action == "new_game":
                    class_options = registry.get_class_options()
                    if class_options:
                        self.class_select_view = ClassSelectView(self.screen, self.font, class_options)
                        self.screen_ctrl.replace(ScreenState.CLASS_SELECT)
                    else:
                        self.screen_ctrl.replace(ScreenState.GAMEPLAY)
                    return None
                if action == "load_game":
                    saves = save_manager.list_saves()
                    self.load_game_view = LoadGameView(self.screen, self.font, saves)
                    self.load_source = "start"
                    self.screen_ctrl.replace(ScreenState.LOAD_GAME)
                    return None
                if action == "tutorial":
                    self.tutorial_view = TutorialView(self.screen, self.font)
                    self.screen_ctrl.push(ScreenState.TUTORIAL)
                    return None
                if action == "config":
                    self.screen_ctrl.replace(ScreenState.CONFIG)
                    return None
                if action == "credits":
                    self.credits_view = CreditsView(self.screen, self.font)
                    self.screen_ctrl.push(ScreenState.CREDITS)
                    return None
                if action == "quit":
                    return "quit"
        self.start_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_config(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = self.config_view.handle_input(event)
                if action == "back":
                    self.screen_ctrl.replace(ScreenState.START)
                    return None
        self.config_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_class_select(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                result = self.class_select_view.handle_input(event)
                if result:
                    if result["action"] == "selected":
                        class_idx = result["class_index"]
                        self.player_name = result["player_name"]
                        self.selected_class = registry.get_class_options()[class_idx]
                        env_name = ""
                        env_type = ""
                        if registry.manifest:
                            env_name = registry.manifest.get("environment_name", "Unknown Land")
                            env_type = registry.manifest.get("environment", "unknown")
                        story_text = self.narrative.get("room_intro_room_0", "")
                        if not story_text:
                            story_text = (
                                f"{self.player_name} the {self.selected_class.name} "
                                f"steps into {env_name}, a {env_type} shrouded in mystery. "
                                "The air hums with untold stories, and the path ahead "
                                "promises both peril and wonder."
                            )
                        env_portrait = None
                        if registry.manifest:
                            rooms = registry.manifest.get("rooms", [])
                            if rooms:
                                env_portrait = rooms[0].get("environment_portrait")
                        self.room_intro_view = RoomIntroView(
                            self.screen,
                            self.font,
                            env_name,
                            env_type,
                            story_text,
                            portrait_path=env_portrait,
                        )
                        self.screen_ctrl.replace(ScreenState.ROOM_INTRO)
                    elif result["action"] == "back":
                        self.screen_ctrl.replace(ScreenState.START)
                    return None
        if self.class_select_view:
            self.class_select_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_room_intro(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if self.room_intro_view and self.room_intro_view.handle_input(event):
                    if self.current_room_index > 0 and self.game_controller is not None:
                        player = self.game_controller.player
                        day_night = self.game_controller.day_night
                        self.game_controller = setup_game(
                            self.screen,
                            self.font,
                            room_index=self.current_room_index,
                            player=player,
                            day_night=day_night,
                            sfx=self.sfx,
                        )
                    if self.game_controller is not None:
                        self.music.play_maze(self.game_controller.maze.environment)
                        self.sfx.play_ambience(self.game_controller.maze.environment)
                    self.screen_ctrl.replace(ScreenState.GAMEPLAY)
                    return None
        if self.room_intro_view:
            self.room_intro_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_gameplay(self) -> str | None:
        if self.game_controller is None:
            self.game_controller = setup_game(
                self.screen,
                self.font,
                self.player_name,
                self.selected_class,
                room_index=self.current_room_index,
                sfx=self.sfx,
            )
            self.gameplay_start_time = time.time()
            self.music.play_maze(self.game_controller.maze.environment)
            self.sfx.play_ambience(self.game_controller.maze.environment)

        self.music_director.update(self.game_controller)

        result = self.game_controller.run()

        if result == "open_menu":
            can_save = not self.game_controller.has_active_overlay
            self.player_menu_view = PlayerMenuView(
                self.screen,
                self.font,
                can_save=can_save,
                has_saves=self._cached_has_saves,
                quest_log=self.game_controller.get_quest_log(),
                follower_info=self.game_controller.get_follower_info(),
                saves=save_manager.list_saves(),
            )
            self.screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        if result == "open_pause":
            self.game_controller.day_night.pause()
            can_save = not self.game_controller.has_active_overlay
            self.pause_view = PauseView(self.screen, self.font, can_save=can_save, has_saves=self._cached_has_saves)
            self.screen_ctrl.push(ScreenState.PAUSE)
            return None

        if result == "open_full_menu":
            self.game_controller.day_night.pause()
            self.menu_view = MenuView(self.screen, self.font, self.game_controller.player)
            self.screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        if result == "open_status":
            self.game_controller.day_night.pause()
            self.menu_view = MenuView(self.screen, self.font, self.game_controller.player, initial_tab="stats")
            self.screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        if result == "open_spells":
            self.game_controller.day_night.pause()
            self.menu_view = MenuView(self.screen, self.font, self.game_controller.player, initial_tab="spells")
            self.screen_ctrl.push(ScreenState.PLAYER_MENU)
            return None

        if result == "open_story":
            story = registry.get_story()
            room_beat = ""
            room_name = ""
            if story:
                beat = next((b for b in story.beats if b.room_id == f"room_{self.current_room_index}"), None)
                if beat:
                    room_beat = beat.summary
            if self.game_controller:
                room_name = self.game_controller.maze.environment_name or ""
            self.story_view = StoryView(
                self.screen,
                self.font,
                story=story,
                room_story_beat=room_beat,
                room_name=room_name,
            )
            self.screen_ctrl.push(ScreenState.STORY)
            return None

        if result == "game_over":
            self.music.play_game_over()
            go_portrait = None
            if registry.manifest:
                go_portrait = registry.manifest.get("gameover_portrait")
            if not go_portrait:
                go_portrait = self.game_controller.player.profile_image
            self.gameover_view = GameOverView(
                self.screen,
                self.font,
                self.game_controller.player,
                has_saves=self._cached_has_saves,
                portrait_path=go_portrait,
                story_paragraph=self.narrative.get("game_over", ""),
            )
            self.screen_ctrl.push(ScreenState.GAME_OVER)
            return None

        if result == "room_transition":
            for k in self.game_stats:
                self.game_stats[k] += self.game_controller.stats.get(k, 0)

            self.current_room_index += 1
            total_rooms = self.game_controller.total_rooms

            if self.current_room_index >= total_rooms:
                self.game_stats["rooms_cleared"] += 1
                self.music.play_victory()
                player = self.game_controller.player
                vic_portrait = registry.manifest.get("victory_portrait") if registry.manifest else None
                self.victory_view = VictoryView(
                    self.screen,
                    self.font,
                    player,
                    self.game_stats,
                    total_rooms,
                    story_paragraph=self.narrative.get("victory", ""),
                    portrait_path=vic_portrait,
                )
                self.screen_ctrl.replace(ScreenState.VICTORY)
                return None

            player = self.game_controller.player
            self.level_up_view = LevelUpView(self.screen, self.font, player)
            self.screen_ctrl.replace(ScreenState.LEVEL_UP)
            return None

        if result == "victory":
            for k in self.game_stats:
                self.game_stats[k] += self.game_controller.stats.get(k, 0)
            self.music.play_victory()
            player = self.game_controller.player
            total_rooms = self.game_controller.total_rooms
            vic_portrait = registry.manifest.get("victory_portrait") if registry.manifest else None
            self.victory_view = VictoryView(
                self.screen,
                self.font,
                player,
                self.game_stats,
                total_rooms,
                story_paragraph=self.narrative.get("victory", ""),
                portrait_path=vic_portrait,
            )
            self.screen_ctrl.replace(ScreenState.VICTORY)
            return None

        if result == "load":
            saves = save_manager.list_saves()
            self.load_game_view = LoadGameView(self.screen, self.font, saves)
            self.load_source = "start"
            self.screen_ctrl.push(ScreenState.LOAD_GAME)
            return None

        return "quit"

    def _handle_save_load_action(self, action: dict, panel) -> str | None:
        act = action["action"]

        if act == "save_new":
            elapsed = time.time() - self.gameplay_start_time
            total_time = self.accumulated_play_time + elapsed
            try:
                save_manager.save_game(self.game_controller, WORLD_SEED, total_time)
                self._cached_has_saves = True
                panel.refresh_saves(save_manager.list_saves())
                panel.set_status("Game saved!")
            except Exception as e:
                panel.set_status(f"Save failed: {e}", is_error=True)

        elif act == "save_overwrite":
            elapsed = time.time() - self.gameplay_start_time
            total_time = self.accumulated_play_time + elapsed
            try:
                save_manager.save_game_to_path(
                    self.game_controller,
                    WORLD_SEED,
                    total_time,
                    action["filepath"],
                )
                self._cached_has_saves = True
                panel.refresh_saves(save_manager.list_saves())
                panel.set_status("Save overwritten!")
            except Exception as e:
                panel.set_status(f"Save failed: {e}", is_error=True)

        elif act == "load":
            filepath = action["filepath"]
            save_state = save_manager.load_game(filepath)
            if save_state is None:
                panel.set_status("Failed to load (corrupt or invalid).", is_error=True)
                return None
            try:
                self.game_controller = setup_game_from_save(self.screen, self.font, save_state, sfx=self.sfx)
                self.current_room_index = save_state.current_room
                self.accumulated_play_time = save_state.time_played_seconds
                self.gameplay_start_time = time.time()
                self.music.play_maze(self.game_controller.maze.environment)
                self.sfx.play_ambience(self.game_controller.maze.environment)
                return "loaded"
            except Exception as e:
                panel.set_status(f"Load failed: {e}", is_error=True)

        elif act == "delete":
            save_manager.delete_save(action["filepath"])
            saves = save_manager.list_saves()
            self._cached_has_saves = bool(saves)
            panel.refresh_saves(saves)
            panel.set_status("Save deleted.")

        return None

    def _handle_player_menu(self) -> str | None:
        if self.menu_view is not None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    action = self.menu_view.handle_input(event)
                    if action == "close":
                        self.menu_view = None
                        if self.game_controller:
                            self.game_controller.day_night.resume()
                        self.screen_ctrl.pop()
                        return None
            self.menu_view.draw()
            pygame.display.flip()
            self.clock.tick(60)
            return None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = self.player_menu_view.handle_input(event)
                if action == "back":
                    if self.game_controller:
                        self.game_controller.day_night.resume()
                    self.screen_ctrl.pop()
                    return None
                if isinstance(action, dict):
                    result = self._handle_save_load_action(
                        action,
                        self.player_menu_view.save_load_panel,
                    )
                    if result == "loaded":
                        self.screen_ctrl.reset_to(ScreenState.GAMEPLAY)
                    return None
                if isinstance(action, str) and action.startswith("talk_follower_"):
                    try:
                        idx = int(action.split("_")[-1])
                        msg = self.game_controller.follower_manager.talk_to_follower(idx)
                        self.player_menu_view.set_status(msg)
                    except (ValueError, IndexError):
                        pass
                    return None

        if self.game_controller:
            current_time = pygame.time.get_ticks()
            self.game_controller.draw(current_time)
        self.player_menu_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_pause(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = self.pause_view.handle_input(event)
                if action == "resume":
                    self.game_controller.day_night.resume()
                    self.screen_ctrl.pop()
                    return None
                if action == "inventory":
                    self.screen_ctrl.pop()
                    self.game_controller.inventory_active = True
                    return None
                if action == "rest":
                    self.screen_ctrl.pop()
                    self.game_controller.rest_menu_active = True
                    self.game_controller.dialogue_box.set_item_message("Rest: 1=3hr  2=6hr  3=12hr  Esc=Cancel")
                    self.game_controller.item_message_active = True
                    return None
                if action == "status":
                    self.menu_view = MenuView(self.screen, self.font, self.game_controller.player, initial_tab="stats")
                    self.screen_ctrl.pop()
                    self.screen_ctrl.push(ScreenState.PLAYER_MENU)
                    return None
                if action == "spells":
                    self.menu_view = MenuView(self.screen, self.font, self.game_controller.player, initial_tab="spells")
                    self.screen_ctrl.pop()
                    self.screen_ctrl.push(ScreenState.PLAYER_MENU)
                    return None
                if action == "quest_log":
                    self.screen_ctrl.pop()
                    self.game_controller.quest_log_active = True
                    return None
                if action == "story":
                    story = registry.get_story()
                    room_beat = ""
                    room_name = ""
                    if story:
                        beat = next((b for b in story.beats if b.room_id == f"room_{self.current_room_index}"), None)
                        if beat:
                            room_beat = beat.summary
                    if self.game_controller:
                        room_name = self.game_controller.maze.environment_name or ""
                    self.story_view = StoryView(
                        self.screen,
                        self.font,
                        story=story,
                        room_story_beat=room_beat,
                        room_name=room_name,
                    )
                    self.screen_ctrl.pop()
                    self.screen_ctrl.push(ScreenState.STORY)
                    return None
                if action == "open_save_load":
                    saves = save_manager.list_saves()
                    self.pause_view.open_save_load(saves)
                    return None
                if isinstance(action, dict):
                    panel = self.pause_view.save_load_panel
                    result = self._handle_save_load_action(action, panel)
                    if result == "loaded":
                        self.screen_ctrl.reset_to(ScreenState.GAMEPLAY)
                    return None
                if action == "quit_to_start":
                    self.game_controller = None
                    self.current_room_index = 0
                    self.game_stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
                    self.music.play_start_screen()
                    self.sfx.stop_ambience()
                    self.screen_ctrl.reset_to(ScreenState.START)
                    return None
                if action == "exit_game":
                    pygame.quit()
                    sys.exit()

        if self.game_controller:
            current_time = pygame.time.get_ticks()
            self.game_controller.draw(current_time)
        self.pause_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_game_over(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = self.gameover_view.handle_input(event)
                if action == "load":
                    saves = save_manager.list_saves()
                    self.load_game_view = LoadGameView(self.screen, self.font, saves)
                    self.load_source = "start"
                    self.screen_ctrl.replace(ScreenState.LOAD_GAME)
                    return None
                if action == "quit_to_start":
                    self.game_controller = None
                    self.current_room_index = 0
                    self.game_stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
                    self.music.play_start_screen()
                    self.sfx.stop_ambience()
                    self.screen_ctrl.reset_to(ScreenState.START)
                    return None

        self.gameover_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_victory(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if self.victory_view:
                    action = self.victory_view.handle_input(event)
                    if action == "menu":
                        self.game_controller = None
                        self.current_room_index = 0
                        self.game_stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
                        self.music.play_start_screen()
                        self.sfx.stop_ambience()
                        self.screen_ctrl.reset_to(ScreenState.START)
                        return None
                    if action == "quit":
                        return "quit"

        if self.victory_view:
            self.victory_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_load_game(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                result = self.load_game_view.handle_input(event)
                if result is None:
                    pass
                elif result["action"] == "back":
                    if self.load_source == "start":
                        self.screen_ctrl.replace(ScreenState.START)
                    else:
                        self.screen_ctrl.pop()
                    return None
                elif result["action"] == "load":
                    filepath = result["filepath"]
                    save_state = save_manager.load_game(filepath)
                    if save_state is None:
                        self.load_game_view.error_message = "Failed to load save file (corrupt or invalid)."
                        return None

                    try:
                        self.game_controller = setup_game_from_save(
                            self.screen,
                            self.font,
                            save_state,
                            sfx=self.sfx,
                        )
                        self.current_room_index = save_state.current_room
                        self.accumulated_play_time = save_state.time_played_seconds
                        self.gameplay_start_time = time.time()
                        self.music.play_maze(self.game_controller.maze.environment)
                        self.sfx.play_ambience(self.game_controller.maze.environment)
                        self.screen_ctrl.reset_to(ScreenState.GAMEPLAY)
                    except Exception as e:
                        self.load_game_view.error_message = f"Load failed: {e}"
                        return None
                    return None

        self.load_game_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_level_up(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                result = self.level_up_view.handle_input(event)
                if result:
                    if result["action"] == "chosen":
                        player = self.game_controller.player
                        room_level = self.current_room_index + 1
                        player.apply_level_up(result["type"], result["choice"], room_level=room_level)
                    elif result["action"] == "skip":
                        if self.game_controller:
                            self.game_controller.player.level += 1

                    self._setup_room_intro_for_transition()
                    self.screen_ctrl.replace(ScreenState.ROOM_INTRO)
                    return None
        if self.level_up_view:
            self.level_up_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _setup_room_intro_for_transition(self):
        room_dir = registry.get_room_dir(self.current_room_index)
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
        room_key = f"room_intro_room_{self.current_room_index}"
        story_text = self.narrative.get(room_key, "")
        if not story_text:
            story = registry.get_story()
            if story:
                beat = next((b for b in story.beats if b.room_id == f"room_{self.current_room_index}"), None)
                if beat:
                    story_text = beat.summary
        if not story_text:
            story_text = f"You enter a new {env_type}, deeper into the dungeon."

        if registry.manifest:
            rooms = registry.manifest.get("rooms", [])
            for rm in rooms:
                if rm.get("room_id") == f"room_{self.current_room_index}":
                    env_portrait = rm.get("environment_portrait")
                    break

        self.room_intro_view = RoomIntroView(
            self.screen,
            self.font,
            env_name,
            env_type,
            story_text,
            portrait_path=env_portrait,
        )

    def _handle_tutorial(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = self.tutorial_view.handle_input(event)
                if action == "back":
                    self.screen_ctrl.pop()
                    return None
        self.tutorial_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_story(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = self.story_view.handle_input(event)
                if action == "back":
                    self.screen_ctrl.pop()
                    return None
        if self.game_controller:
            current_time = pygame.time.get_ticks()
            self.game_controller.draw(current_time)
        self.story_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None

    def _handle_credits(self) -> str | None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                action = self.credits_view.handle_input(event)
                if action == "back":
                    self.screen_ctrl.pop()
                    return None
        self.credits_view.draw()
        pygame.display.flip()
        self.clock.tick(60)
        return None


def main():
    args = parse_args()

    registry.load()

    if args.dev and not args.skip_gen:
        has_pregen = registry.has_manifest() and registry.manifest_matches_seed(WORLD_SEED)
        if not has_pregen:
            print(f"World data missing or stale (seed={WORLD_SEED}). Generating...")
            run_generation()
    elif not args.dev:
        has_pregen = registry.has_manifest() and registry.manifest_matches_seed(WORLD_SEED)
        if not has_pregen:
            print(f"World data missing or stale (seed={WORLD_SEED}).")
            print("Run `python main.py --dev` to generate, or press Enter to generate now.")
            try:
                input()
                run_generation()
            except (EOFError, KeyboardInterrupt):
                print("Skipping generation, using fallback runtime mode.")

    if args.exe:
        import subprocess

        # Prefer .venv-build (framework Python required for macOS .app bundles).
        # PyInstaller can't produce a .app bundle from a non-framework Python,
        # so a separate build venv is created with only runtime deps + PyInstaller.
        build_python = os.path.join(os.path.dirname(__file__), ".venv-build", "bin", "python")
        python_exe = build_python if os.path.exists(build_python) else sys.executable
        print(f"Building macOS .app via PyInstaller (using {python_exe})...")
        result = subprocess.run(
            [python_exe, "-m", "PyInstaller", "mazeworld.spec", "--clean", "--noconfirm"],
            check=False,
        )
        sys.exit(result.returncode)

    _start_game_loop()


if __name__ == "__main__":
    main()
