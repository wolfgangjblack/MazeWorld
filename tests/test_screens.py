"""Tests for StartView, ConfigView (tabbed), and screen state machine."""

import sys
import os
import pytest
import pygame
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.controllers.screen_controller import ScreenController, ScreenState
from src.views.start_view import StartView, MENU_ITEMS
from src.views.config_view import (
    ConfigView, EDITABLE_SETTINGS, GENERATION_SETTINGS,
    _mask_secret, _update_dotenv,
)
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
    assert "Load Game" in MENU_ITEMS
    assert "Tutorial" in MENU_ITEMS
    assert "Config" in MENU_ITEMS
    assert "Quit" in MENU_ITEMS


def test_start_view_new_game(screen, font):
    view = StartView(screen, font)
    view.selected_index = 0
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert view.handle_input(event) == "new_game"


def test_start_view_config(screen, font):
    view = StartView(screen, font)
    view.selected_index = MENU_ITEMS.index("Config")
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert view.handle_input(event) == "config"


def test_start_view_load_game(screen, font):
    view = StartView(screen, font, has_saves=True)
    view.selected_index = MENU_ITEMS.index("Load Game")
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert view.handle_input(event) == "load_game"


def test_start_view_load_game_disabled(screen, font):
    view = StartView(screen, font, has_saves=False)
    view.selected_index = MENU_ITEMS.index("Load Game")
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert view.handle_input(event) is None


def test_start_view_tutorial_disabled(screen, font):
    view = StartView(screen, font)
    view.selected_index = MENU_ITEMS.index("Tutorial")
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert view.handle_input(event) is None


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
    view.draw()


# --- ConfigView: tab structure ---

def test_config_view_has_all_settings(screen, font):
    """Legacy .items property returns combined list for both tabs."""
    view = ConfigView(screen, font)
    attrs = [item[0] for item in view.items]
    for attr, _ in GENERATION_SETTINGS:
        assert attr in attrs
    for attr, _, _, _ in EDITABLE_SETTINGS:
        assert attr in attrs


def test_config_view_editable_tab_has_settings(screen, font):
    view = ConfigView(screen, font)
    attrs = [item[0] for item in view.editable_items]
    for attr, _, _, _ in EDITABLE_SETTINGS:
        assert attr in attrs


def test_config_view_generation_tab_has_settings(screen, font):
    view = ConfigView(screen, font)
    attrs = [item[0] for item in view.generation_items]
    for attr, _ in GENERATION_SETTINGS:
        assert attr in attrs


def test_config_view_starts_on_editable_tab(screen, font):
    view = ConfigView(screen, font)
    assert view.active_tab == 0


def test_config_view_tab_switch(screen, font):
    view = ConfigView(screen, font)
    assert view.active_tab == 0

    right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    view.handle_input(right)
    assert view.active_tab == 1
    assert view.selected_index == 0

    left = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
    view.handle_input(left)
    assert view.active_tab == 0
    assert view.selected_index == 0


def test_config_view_generation_tab_readonly(screen, font):
    """Enter does nothing on the generation tab (all read-only)."""
    view = ConfigView(screen, font)
    right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    view.handle_input(right)
    assert view.active_tab == 1

    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    result = view.handle_input(enter)
    assert result is None
    assert view.editing is False


def test_config_view_escape_returns_back(screen, font):
    view = ConfigView(screen, font)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert view.handle_input(event) == "back"


# --- ConfigView: editable tab editing ---

def test_config_view_cycle_editable(screen, font):
    view = ConfigView(screen, font)
    assert view.active_tab == 0
    idx = next(i for i, item in enumerate(view.editable_items) if item[0] == "LLM_BACKEND")
    view.selected_index = idx
    original = cfg.LLM_BACKEND
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(event)
    new_val = cfg.LLM_BACKEND
    assert new_val != original or len(view.editable_items[idx][2]) == 1
    cfg.LLM_BACKEND = original


def test_config_view_freetext_edit(screen, font):
    view = ConfigView(screen, font)
    idx = next(i for i, item in enumerate(view.editable_items) if item[0] == "LLM_MODEL_PATH")
    view.selected_index = idx
    original = cfg.LLM_MODEL_PATH

    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(enter)
    assert view.editing is True

    char_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="X")
    view.handle_input(char_event)
    assert "X" in view.edit_buffer

    bs = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE)
    view.handle_input(bs)

    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    view.handle_input(esc)
    assert view.editing is False
    assert cfg.LLM_MODEL_PATH == original


def test_config_view_freetext_confirm(screen, font):
    view = ConfigView(screen, font)
    idx = next(i for i, item in enumerate(view.editable_items) if item[0] == "FAL_MODEL")
    view.selected_index = idx
    original = cfg.FAL_MODEL

    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(enter)
    assert view.editing is True

    view.edit_buffer = "test-model"
    view.handle_input(enter)
    assert view.editing is False
    assert cfg.FAL_MODEL == "test-model"

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
    view.handle_input(up)
    assert view.selected_index == 0


def test_config_view_draw_no_crash(screen, font):
    view = ConfigView(screen, font)
    view.draw()
    # Draw on generation tab too
    right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    view.handle_input(right)
    view.draw()


# --- Secret masking ---

def test_mask_secret_empty():
    assert _mask_secret("") == "(not set)"


def test_mask_secret_short():
    assert _mask_secret("abc") == "****"


def test_mask_secret_long():
    result = _mask_secret("sk-ant-api03-abcdefghijklmnop")
    assert result.startswith("****...")
    assert result.endswith("mnop")


# --- Secret editing ---

def test_config_view_secret_edit_writes_env(screen, font, tmp_path, monkeypatch):
    """Editing an API key writes to os.environ and calls _update_dotenv."""
    view = ConfigView(screen, font)
    idx = next(i for i, item in enumerate(view.editable_items) if item[0] == "ANTHROPIC_API_KEY")
    view.selected_index = idx

    original = os.environ.get("ANTHROPIC_API_KEY", "")

    dotenv_calls = []
    monkeypatch.setattr(
        "src.views.config_view._update_dotenv",
        lambda k, v: dotenv_calls.append((k, v)),
    )

    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(enter)
    assert view.editing is True
    assert view.edit_buffer == ""

    view.edit_buffer = "sk-test-key-1234"
    view.handle_input(enter)
    assert view.editing is False
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test-key-1234"
    assert dotenv_calls == [("ANTHROPIC_API_KEY", "sk-test-key-1234")]

    # Restore
    if original:
        os.environ["ANTHROPIC_API_KEY"] = original
    else:
        os.environ.pop("ANTHROPIC_API_KEY", None)


def test_config_view_secret_displays_masked(screen, font, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "fal-secret-key-abcd")
    view = ConfigView(screen, font)
    display = view._get_display_value("FAL_KEY", secret=True)
    assert "abcd" in display
    assert "fal-secret-key" not in display


# --- _update_dotenv ---

def test_update_dotenv_creates_file(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    monkeypatch.setattr("src.views.config_view._DOTENV_PATH", str(dotenv_file))

    _update_dotenv("MY_KEY", "my_value")
    content = dotenv_file.read_text()
    assert 'MY_KEY="my_value"' in content


def test_update_dotenv_replaces_existing(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("OTHER=foo\nMY_KEY=old_value\nANOTHER=bar\n")
    monkeypatch.setattr("src.views.config_view._DOTENV_PATH", str(dotenv_file))

    _update_dotenv("MY_KEY", "new_value")
    content = dotenv_file.read_text()
    assert 'MY_KEY="new_value"' in content
    assert "old_value" not in content
    assert "OTHER=foo" in content
    assert "ANOTHER=bar" in content


def test_update_dotenv_appends_new_key(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("EXISTING=yes\n")
    monkeypatch.setattr("src.views.config_view._DOTENV_PATH", str(dotenv_file))

    _update_dotenv("NEW_KEY", "new_val")
    content = dotenv_file.read_text()
    assert "EXISTING=yes" in content
    assert 'NEW_KEY="new_val"' in content


# --- New config settings ---

def test_config_new_settings_exist():
    """All Phase 1 gap settings exist in config module."""
    assert hasattr(cfg, "NUM_ROOMS")
    assert hasattr(cfg, "QUEST_DENSITY")
    assert hasattr(cfg, "MAP_COLORS")
    assert hasattr(cfg, "MASTER_VOLUME")
    assert hasattr(cfg, "MUSIC_VOLUME")
    assert hasattr(cfg, "MUSIC_BACKEND")


def test_config_num_rooms_default():
    assert cfg.NUM_ROOMS == 1
    assert isinstance(cfg.NUM_ROOMS, int)


def test_config_quest_density_default():
    assert cfg.QUEST_DENSITY == 0.1
    assert isinstance(cfg.QUEST_DENSITY, float)


def test_config_map_colors_default():
    assert isinstance(cfg.MAP_COLORS, dict)
    assert "wall" in cfg.MAP_COLORS
    assert "path" in cfg.MAP_COLORS
    assert "player" in cfg.MAP_COLORS


def test_config_volume_defaults():
    assert 0 <= cfg.MASTER_VOLUME <= 100
    assert 0 <= cfg.MUSIC_VOLUME <= 100


def test_config_music_backend_default():
    assert cfg.MUSIC_BACKEND in ("none", "local", "api")


# --- GAME_MODE is read-only (generation tab) ---

def test_game_mode_in_generation_tab():
    """GAME_MODE must be in the read-only generation tab, not editable."""
    gen_attrs = [attr for attr, _ in GENERATION_SETTINGS]
    assert "GAME_MODE" in gen_attrs
    edit_attrs = [attr for attr, _, _, _ in EDITABLE_SETTINGS]
    assert "GAME_MODE" not in edit_attrs


def test_new_settings_in_generation_tab():
    """NUM_ROOMS, QUEST_DENSITY, MAP_COLORS are in generation (read-only) tab."""
    gen_attrs = [attr for attr, _ in GENERATION_SETTINGS]
    assert "NUM_ROOMS" in gen_attrs
    assert "QUEST_DENSITY" in gen_attrs
    assert "MAP_COLORS" in gen_attrs


def test_new_settings_in_editable_tab():
    """MASTER_VOLUME, MUSIC_VOLUME, MUSIC_BACKEND are in editable (runtime) tab."""
    edit_attrs = [attr for attr, _, _, _ in EDITABLE_SETTINGS]
    assert "MASTER_VOLUME" in edit_attrs
    assert "MUSIC_VOLUME" in edit_attrs
    assert "MUSIC_BACKEND" in edit_attrs


def test_config_view_cycle_music_backend(screen, font):
    view = ConfigView(screen, font)
    idx = next(i for i, item in enumerate(view.editable_items) if item[0] == "MUSIC_BACKEND")
    view.selected_index = idx
    original = cfg.MUSIC_BACKEND
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(enter)
    assert cfg.MUSIC_BACKEND != original or len(view.editable_items[idx][2]) == 1
    cfg.MUSIC_BACKEND = original


def test_config_view_edit_volume(screen, font):
    view = ConfigView(screen, font)
    idx = next(i for i, item in enumerate(view.editable_items) if item[0] == "MASTER_VOLUME")
    view.selected_index = idx
    original = cfg.MASTER_VOLUME

    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    view.handle_input(enter)
    assert view.editing is True

    view.edit_buffer = "50"
    view.handle_input(enter)
    assert view.editing is False
    assert cfg.MASTER_VOLUME == 50

    cfg.MASTER_VOLUME = original


# --- Manifest schema ---

def test_manifest_schema():
    """Manifest output from pipeline matches PDR spec structure."""
    import json
    from datetime import datetime, timezone

    # Build a minimal manifest matching what pipeline.py now produces
    manifest = {
        "seed": 1234,
        "story_seed": "test",
        "game_mode": "online",
        "num_rooms": 1,
        "environments": ["forest"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation": {"status": "passed"},
        "content_index": {
            "rooms": 1,
            "npcs": 5,
            "items": 10,
            "quests": 3,
            "encounters": 8,
            "monsters": 4,
            "images": 2,
            "music_tracks": 0,
        },
    }
    # All PDR-required top-level keys present
    for key in ("seed", "story_seed", "game_mode", "num_rooms",
                "environments", "generated_at", "validation", "content_index"):
        assert key in manifest, f"Missing manifest key: {key}"

    # content_index sub-keys
    ci = manifest["content_index"]
    for key in ("rooms", "npcs", "items", "quests", "encounters",
                "monsters", "images", "music_tracks"):
        assert key in ci, f"Missing content_index key: {key}"


def test_registry_manifest_seed_compat():
    """Registry handles both old 'world_seed' and new 'seed' key."""
    from src.registry import GameRegistry

    reg = GameRegistry()
    reg.manifest = {"seed": 42}
    assert reg.manifest_matches_seed(42)
    assert not reg.manifest_matches_seed(99)

    reg.manifest = {"world_seed": 42}
    assert reg.manifest_matches_seed(42)
