"""Tests for StartView, ConfigView, and screen state machine CONFIG transitions."""

import sys
import os
import pytest
import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.controllers.screen_controller import ScreenController, ScreenState
from src.views.start_view import StartView, MENU_ITEMS
from src.views.config_view import ConfigView, READONLY_SETTINGS, EDITABLE_SETTINGS
import config as cfg


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def screen():
    return pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))


@pytest.fixture
def font():
    return pygame.font.SysFont(None, 24)


# --- ScreenState CONFIG ---

def test_config_state_exists():
    assert hasattr(ScreenState, "CONFIG")
    assert ScreenState.CONFIG.value == "config"


def test_start_to_config_transition():
    sc = ScreenController(ScreenState.START)
    sc.replace(ScreenState.CONFIG)
    assert sc.state == ScreenState.CONFIG
    assert sc.depth == 1


def test_config_back_to_start():
    sc = ScreenController(ScreenState.CONFIG)
    sc.replace(ScreenState.START)
    assert sc.state == ScreenState.START


# --- StartView ---

def test_start_view_menu_items():
    assert "Start New Game" in MENU_ITEMS
    assert "Config" in MENU_ITEMS
    assert "Quit" in MENU_ITEMS


def test_start_view_new_game(screen, font):
    view = StartView(screen, font)
    # Select "Start New Game" (index 0)
    view.selected_index = 0
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert view.handle_input(event) == "new_game"


def test_start_view_config(screen, font):
    view = StartView(screen, font)
    view.selected_index = MENU_ITEMS.index("Config")
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert view.handle_input(event) == "config"


def test_start_view_quit(screen, font):
    view = StartView(screen, font)
    view.selected_index = MENU_ITEMS.index("Quit")
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert view.handle_input(event) == "quit"


def test_start_view_navigation(screen, font):
    view = StartView(screen, font)
    assert view.selected_index == 0
    down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)
    view.handle_input(down)
    assert view.selected_index == 1
    up = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
    view.handle_input(up)
    assert view.selected_index == 0


def test_start_view_wraps(screen, font):
    view = StartView(screen, font)
    up = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
    view.handle_input(up)
    assert view.selected_index == len(MENU_ITEMS) - 1


def test_start_view_draw_no_crash(screen, font):
    view = StartView(screen, font)
    view.draw()  # Should not raise


# --- ConfigView ---

def test_config_view_has_all_settings(screen, font):
    view = ConfigView(screen, font)
    attrs = [item[0] for item in view.items]
    for attr, _ in READONLY_SETTINGS:
        assert attr in attrs
    for attr, _, _ in EDITABLE_SETTINGS:
        assert attr in attrs


def test_config_view_escape_returns_back(screen, font):
    view = ConfigView(screen, font)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert view.handle_input(event) == "back"


def test_config_view_readonly_no_edit(screen, font):
    view = ConfigView(screen, font)
    # First item is readonly
    view.selected_index = 0
    assert view.items[0][2] is True  # readonly flag
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    result = view.handle_input(event)
    assert result is None
    assert view.editing is False


def test_config_view_cycle_editable(screen, font):
    view = ConfigView(screen, font)
    # Find GAME_MODE (has choices)
    idx = next(i for i, item in enumerate(view.items) if item[0] == "GAME_MODE")
    view.selected_index = idx
    original = cfg.GAME_MODE
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(event)
    # Value should have cycled
    new_val = cfg.GAME_MODE
    assert new_val != original or len(view.items[idx][3]) == 1
    # Restore
    cfg.GAME_MODE = original


def test_config_view_freetext_edit(screen, font):
    view = ConfigView(screen, font)
    # Find LLM_MODEL_PATH (no choices, freetext)
    idx = next(i for i, item in enumerate(view.items) if item[0] == "LLM_MODEL_PATH")
    view.selected_index = idx
    original = cfg.LLM_MODEL_PATH

    # Press enter to start editing
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(enter)
    assert view.editing is True

    # Type a character
    char_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="X")
    view.handle_input(char_event)
    assert "X" in view.edit_buffer

    # Backspace
    bs = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE)
    view.handle_input(bs)

    # Cancel with escape
    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    view.handle_input(esc)
    assert view.editing is False
    assert cfg.LLM_MODEL_PATH == original  # unchanged


def test_config_view_freetext_confirm(screen, font):
    view = ConfigView(screen, font)
    idx = next(i for i, item in enumerate(view.items) if item[0] == "FAL_MODEL")
    view.selected_index = idx
    original = cfg.FAL_MODEL

    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(enter)
    assert view.editing is True

    # Clear buffer and type new value
    view.edit_buffer = "test-model"
    view.handle_input(enter)
    assert view.editing is False
    assert cfg.FAL_MODEL == "test-model"

    # Restore
    cfg.FAL_MODEL = original


def test_config_view_navigation(screen, font):
    view = ConfigView(screen, font)
    assert view.selected_index == 0
    down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)
    view.handle_input(down)
    assert view.selected_index == 1
    up = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
    view.handle_input(up)
    assert view.selected_index == 0
    # Can't go below 0
    view.handle_input(up)
    assert view.selected_index == 0


def test_config_view_draw_no_crash(screen, font):
    view = ConfigView(screen, font)
    view.draw()  # Should not raise
    view.selected_index = len(view.items) - 1
    view.draw()
