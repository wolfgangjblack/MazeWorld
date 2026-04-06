"""Tests for debug toggle, GameController, GameView, and MazeView."""
import sys
import os
import pytest
import pygame
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import GRID_SIZE, HUD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT
from src.views.maze_view import MazeView, DEBUG_EVENT_COLOR


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def screen():
    return pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))


@pytest.fixture
def font():
    return pygame.font.SysFont(None, 24)


@pytest.fixture
def mock_dialogue_box():
    db = MagicMock()
    db.event_active = False
    db.dialogue_active = False
    db.generating = False
    db.input_active = False
    db.current_event = None
    db.awaiting_roll = False
    return db


def _make_mini_maze():
    """Build a tiny maze with one open cell and one event tile."""
    maze = MagicMock()
    maze.wall_tile_id = 1
    maze.event_tile_id = -1
    # 3x3 grid: walls on edges, open center, event tile at (1,2)
    maze.grid = [
        [1, 1, 1],
        [1, 0, 1],
        [1, -1, 1],
    ]
    return maze


# ---------------------------------------------------------------------------
# MazeView tests
# ---------------------------------------------------------------------------

class TestMazeViewEventVisibility:
    def test_event_tile_invisible_by_default(self, screen):
        maze = _make_mini_maze()
        view = MazeView()

        with patch("src.views.maze_view.registry") as mock_reg:
            mock_reg.is_item.return_value = False
            view.draw_maze(screen, maze, debug_reveal=False)

        # Event tile at grid (1, 2): center pixel of the inner rect
        cx = 1 * GRID_SIZE + GRID_SIZE // 2
        cy = 2 * GRID_SIZE + HUD_HEIGHT + GRID_SIZE // 2
        color = screen.get_at((cx, cy))
        assert (color.r, color.g, color.b) == (0, 0, 0), (
            f"Event tile should be black when debug_reveal=False, got {color}"
        )

    def test_event_tile_visible_with_debug_reveal(self, screen):
        maze = _make_mini_maze()
        view = MazeView()

        with patch("src.views.maze_view.registry") as mock_reg:
            mock_reg.is_item.return_value = False
            view.draw_maze(screen, maze, debug_reveal=True)

        cx = 1 * GRID_SIZE + GRID_SIZE // 2
        cy = 2 * GRID_SIZE + HUD_HEIGHT + GRID_SIZE // 2
        color = screen.get_at((cx, cy))
        assert (color.r, color.g, color.b) == DEBUG_EVENT_COLOR, (
            f"Event tile should be purple when debug_reveal=True, got {color}"
        )


# ---------------------------------------------------------------------------
# GameController tests
# ---------------------------------------------------------------------------

class TestGameControllerDebugToggle:
    def _make_controller(self, mock_dialogue_box):
        from src.controllers.game_controller import GameController

        screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        player = MagicMock()
        player.x = 1
        player.y = 1
        player.inventory = {}
        player.get_stat_mod = MagicMock(return_value=0)
        player.player_class = None
        player.is_on_event_tile = MagicMock(return_value=False)
        player.is_item_at_player_position = MagicMock(return_value=False)
        player.get_nearby_npc = MagicMock(return_value=None)
        player.followers = []
        maze = _make_mini_maze()
        maze.is_wall = MagicMock(side_effect=lambda x, y: (
            not (0 <= x < 3 and 0 <= y < 3) or maze.grid[y][x] == 1
        ))

        with patch("src.controllers.game_controller.GameView"):
            ctrl = GameController(
                screen=screen,
                font=font,
                maze=maze,
                player=player,
                npcs=[],
                dialogue_box=mock_dialogue_box,
            )
        return ctrl

    def test_debug_reveal_defaults_false(self, mock_dialogue_box):
        ctrl = self._make_controller(mock_dialogue_box)
        assert ctrl.debug_reveal is False

    def test_f1_toggles_debug_reveal(self, mock_dialogue_box):
        ctrl = self._make_controller(mock_dialogue_box)
        f1_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, unicode="", mod=0)

        ctrl.handle_keydown(f1_event)
        assert ctrl.debug_reveal is True

        ctrl.handle_keydown(f1_event)
        assert ctrl.debug_reveal is False

    def test_debug_reveal_passed_to_draw(self, mock_dialogue_box):
        ctrl = self._make_controller(mock_dialogue_box)
        ctrl.debug_reveal = True
        ctrl.draw(0)

        ctrl.game_view.draw_game.assert_called_once()
        call_kwargs = ctrl.game_view.draw_game.call_args
        assert call_kwargs.kwargs.get("debug_reveal") is True


# ---------------------------------------------------------------------------
# GameView DEBUG label tests
# ---------------------------------------------------------------------------

class TestGameViewDebugLabel:
    def _make_game_view(self, screen, font, mock_dialogue_box):
        from src.views.gameplay_view import GameView
        return GameView(screen, font, mock_dialogue_box)

    @staticmethod
    def _make_player_mock():
        player = MagicMock()
        player.x = 1
        player.y = 1
        player.color = (0, 0, 255)
        player.hunger = 100
        player.thirst = 100
        player.health = 100
        player.max_hunger = 100
        player.max_thirst = 100
        player.max_health = 100
        player.inventory = {}
        player.active_quests = []
        player.money = 0
        player.equipped_weapon = None
        player.selected_item_index = 0
        return player

    def test_debug_label_not_rendered_by_default(self, screen, font, mock_dialogue_box):
        gv = self._make_game_view(screen, font, mock_dialogue_box)
        player = self._make_player_mock()
        maze = _make_mini_maze()

        pre_color = screen.get_at((SCREEN_WIDTH - 20, 10))

        with patch("src.views.gameplay_view.registry"):
            gv.draw_game(
                maze=maze, player=player, npcs=[], inventory_active=False,
                item_message_active=False, current_npc=None,
                player_at_item=False, debug_reveal=False,
            )

        post_color = screen.get_at((SCREEN_WIDTH - 20, 10))
        assert post_color.r < 200 or post_color == pre_color

    def test_debug_label_rendered_when_active(self, screen, font, mock_dialogue_box):
        gv = self._make_game_view(screen, font, mock_dialogue_box)
        player = self._make_player_mock()
        maze = _make_mini_maze()

        with patch("src.views.gameplay_view.registry"):
            gv.draw_game(
                maze=maze, player=player, npcs=[], inventory_active=False,
                item_message_active=False, current_npc=None,
                player_at_item=False, debug_reveal=True,
            )

        expected = font.render("DEBUG", True, (255, 0, 0))
        label_x = SCREEN_WIDTH - expected.get_width() - 10
        label_y = 10
        # Scan the label bounding box for any red pixel (anti-aliased text
        # won't necessarily have a solid red pixel at any single point).
        found_red = False
        for py in range(label_y, label_y + expected.get_height()):
            for px in range(label_x, label_x + expected.get_width()):
                c = screen.get_at((px, py))
                if c.r > 150 and c.g < 50 and c.b < 50:
                    found_red = True
                    break
            if found_red:
                break
        assert found_red, "Expected red DEBUG label pixels in top-right area"
