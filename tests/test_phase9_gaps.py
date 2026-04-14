"""Tests for Phase 9 gaps: Tutorial, Story, GameOver portrait, Combat record."""

import sys
import os
import pytest
import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.player import PlayerCharacter, PlayerClass, Stats
from src.controllers.screen_controller import ScreenController, ScreenState
from src.views.tutorial_view import TutorialView
from src.views.story_view import StoryView
from src.views.gameover_view import GameOverView
from src.views.menu_view import MenuView
from src.models.story import OverarchingStory, Faction
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


def _make_player_with_class():
    pc = PlayerClass(
        name="Knight", archetype="warrior",
        stats=Stats(STR=16, DEX=12, CON=14, INT=8, WIS=8, CHA=10, LUCK=10),
    )
    p = PlayerCharacter(x=0, y=0, name="TestHero")
    p.player_class = pc
    return p


# ---------------------------------------------------------------------------
# GAP 1: Tutorial View
# ---------------------------------------------------------------------------

class TestTutorialView:
    def test_screen_state_exists(self):
        assert hasattr(ScreenState, "TUTORIAL")
        assert ScreenState.TUTORIAL.value == "tutorial"

    def test_draw_no_crash(self, screen, font):
        view = TutorialView(screen, font)
        view.draw()

    def test_esc_returns_back(self, screen, font):
        view = TutorialView(screen, font)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        assert view.handle_input(event) == "back"

    def test_enter_returns_back(self, screen, font):
        view = TutorialView(screen, font)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        assert view.handle_input(event) == "back"

    def test_other_keys_return_none(self, screen, font):
        view = TutorialView(screen, font)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        assert view.handle_input(event) is None

    def test_tutorial_pushed_from_start(self):
        sc = ScreenController(ScreenState.START)
        sc.push(ScreenState.TUTORIAL)
        assert sc.state == ScreenState.TUTORIAL
        sc.pop()
        assert sc.state == ScreenState.START


# ---------------------------------------------------------------------------
# GAP 2: Story View
# ---------------------------------------------------------------------------

class TestStoryView:
    def test_screen_state_exists(self):
        assert hasattr(ScreenState, "STORY")
        assert ScreenState.STORY.value == "story"

    def test_draw_no_crash_no_story(self, screen, font):
        view = StoryView(screen, font, story=None)
        view.draw()

    def test_draw_with_story(self, screen, font):
        story = OverarchingStory(
            title="The Dark Rift",
            synopsis="Evil grows in the land.",
            faction=Faction(name="Shadow Cult", description="They worship darkness."),
            climax="A showdown at the rift.",
        )
        view = StoryView(screen, font, story=story, room_story_beat="A cold wind blows.",
                         room_name="The Crypt")
        view.draw()

    def test_esc_returns_back(self, screen, font):
        view = StoryView(screen, font, story=None)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        assert view.handle_input(event) == "back"

    def test_enter_returns_back(self, screen, font):
        view = StoryView(screen, font, story=None)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        assert view.handle_input(event) == "back"

    def test_other_keys_return_none(self, screen, font):
        view = StoryView(screen, font, story=None)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        assert view.handle_input(event) is None


# ---------------------------------------------------------------------------
# GAP 3: GameOver Portrait
# ---------------------------------------------------------------------------

class TestGameOverPortrait:
    def test_gameover_accepts_portrait_path(self, screen, font):
        player = _make_player_with_class()
        player.completed_quests = []
        player.failed_quests = []
        view = GameOverView(screen, font, player, portrait_path=None)
        assert view.bg_image is None

    def test_gameover_missing_portrait_fallback(self, screen, font):
        player = _make_player_with_class()
        player.completed_quests = []
        player.failed_quests = []
        view = GameOverView(screen, font, player, portrait_path="/nonexistent/path.png")
        assert view.bg_image is None

    def test_gameover_draw_no_crash_without_portrait(self, screen, font):
        player = _make_player_with_class()
        player.completed_quests = []
        player.failed_quests = []
        view = GameOverView(screen, font, player, portrait_path=None)
        view.draw()

    def test_gameover_draw_no_crash_with_portrait(self, screen, font, tmp_path):
        # Create a small test image
        img = pygame.Surface((100, 100))
        img.fill((128, 0, 0))
        img_path = str(tmp_path / "test_portrait.png")
        pygame.image.save(img, img_path)

        player = _make_player_with_class()
        player.completed_quests = []
        player.failed_quests = []
        view = GameOverView(screen, font, player, portrait_path=img_path)
        assert view.bg_image is not None
        view.draw()


# ---------------------------------------------------------------------------
# GAP 4: Combat Record + Title
# ---------------------------------------------------------------------------

class TestCombatRecord:
    def test_default_combat_record(self):
        p = PlayerCharacter(x=0, y=0)
        assert p.combat_record == {
            "monsters_killed": 0,
            "damage_dealt": 0,
            "damage_taken": 0,
            "combats_won": 0,
            "combats_fled": 0,
        }

    def test_default_title_empty(self):
        p = PlayerCharacter(x=0, y=0)
        assert p.title == ""

    def test_combat_record_mutable(self):
        p = PlayerCharacter(x=0, y=0)
        p.combat_record["monsters_killed"] += 5
        p.combat_record["damage_dealt"] += 120
        p.combat_record["damage_taken"] += 40
        p.combat_record["combats_won"] += 3
        p.combat_record["combats_fled"] += 1
        assert p.combat_record["monsters_killed"] == 5
        assert p.combat_record["combats_won"] == 3

    def test_combat_record_independent_per_player(self):
        p1 = PlayerCharacter(x=0, y=0)
        p2 = PlayerCharacter(x=1, y=1)
        p1.combat_record["monsters_killed"] = 10
        assert p2.combat_record["monsters_killed"] == 0

    def test_title_set(self):
        p = PlayerCharacter(x=0, y=0, title="Dragon Slayer")
        assert p.title == "Dragon Slayer"

    def test_stats_tab_shows_combat_record(self, screen, font):
        player = _make_player_with_class()
        player.active_quests = []
        player.completed_quests = [4000]
        player.failed_quests = []
        player.combat_record["monsters_killed"] = 7
        player.combat_record["combats_won"] = 3
        player.combat_record["combats_fled"] = 1
        player.combat_record["damage_dealt"] = 200
        player.combat_record["damage_taken"] = 50
        player.title = "Champion"

        view = MenuView(screen, font, player)
        view.active_tab = 1
        view.draw()  # Should not crash

    def test_stats_tab_no_title(self, screen, font):
        player = _make_player_with_class()
        player.active_quests = []
        player.completed_quests = []
        player.failed_quests = []
        player.title = ""

        view = MenuView(screen, font, player)
        view.active_tab = 1
        view.draw()  # Should not crash


# ---------------------------------------------------------------------------
# Combat Record Serialization
# ---------------------------------------------------------------------------

class TestCombatRecordSerialization:
    def test_serialize_combat_record(self):
        from src.systems.save_manager import serialize_player
        p = _make_player_with_class()
        p.initialize_inventory()
        p.combat_record["monsters_killed"] = 5
        p.combat_record["damage_dealt"] = 100
        p.title = "Veteran"

        data = serialize_player(p)
        assert data["combat_record"]["monsters_killed"] == 5
        assert data["combat_record"]["damage_dealt"] == 100
        assert data["title"] == "Veteran"

    def test_deserialize_combat_record(self):
        from src.systems.save_manager import serialize_player, deserialize_player
        p = _make_player_with_class()
        p.initialize_inventory()
        p.combat_record["combats_won"] = 3
        p.combat_record["combats_fled"] = 1
        p.title = "Hero"

        data = serialize_player(p)
        restored = deserialize_player(data)
        assert restored.combat_record["combats_won"] == 3
        assert restored.combat_record["combats_fled"] == 1
        assert restored.title == "Hero"

    def test_deserialize_missing_combat_record(self):
        from src.systems.save_manager import deserialize_player
        data = {"x": 0, "y": 0, "name": "Test"}
        restored = deserialize_player(data)
        assert restored.combat_record["monsters_killed"] == 0
        assert restored.title == ""
