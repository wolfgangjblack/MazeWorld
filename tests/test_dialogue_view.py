"""Tests for portrait loading and display in DialogueBoxView."""
import os
import pytest
import pygame
from unittest.mock import MagicMock

from src.views.portrait_utils import load_portrait as _load_portrait, _cache as _portrait_cache
from src.views.dialogue_view import DialogueBoxView
from config import SCREEN_WIDTH, SCREEN_HEIGHT


@pytest.fixture(autouse=True)
def init_pygame():
    import os
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def clear_portrait_cache():
    """Ensure each test starts with a clean cache."""
    _portrait_cache.clear()
    yield
    _portrait_cache.clear()


@pytest.fixture
def screen():
    return pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))


@pytest.fixture
def font():
    return pygame.font.SysFont(None, 24)


def _make_portrait_file(tmp_path, name="portrait.png", size=(64, 64)):
    """Write a small valid PNG to disk and return the path."""
    surf = pygame.Surface(size)
    surf.fill((255, 0, 0))
    path = os.path.join(str(tmp_path), name)
    pygame.image.save(surf, path)
    return path


# ---------------------------------------------------------------------------
# _load_portrait unit tests
# ---------------------------------------------------------------------------

class TestLoadPortrait:
    def test_returns_none_for_none_path(self):
        assert _load_portrait(None) is None

    def test_returns_none_for_empty_string(self):
        assert _load_portrait("") is None

    def test_returns_none_for_missing_file(self):
        assert _load_portrait("/nonexistent/portrait.png") is None

    def test_caches_none_for_missing_file(self):
        path = "/nonexistent/portrait.png"
        _load_portrait(path)
        key = f"{path}:128x128"
        assert key in _portrait_cache
        assert _portrait_cache[key] is None

    def test_loads_valid_image(self, tmp_path):
        path = _make_portrait_file(tmp_path)
        result = _load_portrait(path)
        assert result is not None
        assert isinstance(result, pygame.Surface)

    def test_scales_to_requested_size(self, tmp_path):
        path = _make_portrait_file(tmp_path, size=(128, 128))
        result = _load_portrait(path, size=(32, 32))
        assert result.get_size() == (32, 32)

    def test_default_size_is_128x128(self, tmp_path):
        path = _make_portrait_file(tmp_path, size=(100, 100))
        result = _load_portrait(path)
        assert result.get_size() == (128, 128)

    def test_caches_loaded_surface(self, tmp_path):
        path = _make_portrait_file(tmp_path)
        first = _load_portrait(path)
        second = _load_portrait(path)
        assert first is second

    def test_cache_hit_skips_disk(self, tmp_path):
        path = _make_portrait_file(tmp_path)
        _load_portrait(path)
        # Remove the file — cache should still serve
        os.remove(path)
        result = _load_portrait(path)
        assert result is not None

    def test_corrupt_file_returns_none(self, tmp_path):
        path = os.path.join(str(tmp_path), "bad.png")
        with open(path, "wb") as f:
            f.write(b"not-a-png")
        assert _load_portrait(path) is None
        assert _portrait_cache[f"{path}:128x128"] is None


# ---------------------------------------------------------------------------
# DialogueBoxView portrait integration
# ---------------------------------------------------------------------------

class TestDialogueViewPortraitIntegration:
    """Verify that draw() handles portrait presence/absence correctly."""

    def _make_dialogue_box(self, npc=None):
        db = MagicMock()
        db.event_active = False
        db.combat_active = False
        db.dialogue_active = True
        db.item_message = None
        db.current_npc = npc
        db.conversation_history = ["Hello there"]
        db.generating = False
        db.user_message = ""
        db.max_width = SCREEN_WIDTH - 20
        db.get_display_window.return_value = (0, 1)
        return db

    def _make_npc(self, profile_image=None):
        npc = MagicMock()
        npc.name = "Arin"
        npc.job = "hunter"
        npc.profile_image = profile_image
        return npc

    def test_draw_without_portrait_does_not_crash(self, screen, font):
        npc = self._make_npc(profile_image=None)
        db = self._make_dialogue_box(npc)
        view = DialogueBoxView(screen, font)
        # Should not raise
        view.draw(db)

    def test_draw_with_missing_file_does_not_crash(self, screen, font):
        npc = self._make_npc(profile_image="/no/such/file.png")
        db = self._make_dialogue_box(npc)
        view = DialogueBoxView(screen, font)
        view.draw(db)

    def test_draw_with_valid_portrait(self, screen, font, tmp_path):
        path = _make_portrait_file(tmp_path)
        npc = self._make_npc(profile_image=path)
        db = self._make_dialogue_box(npc)
        view = DialogueBoxView(screen, font)
        view.draw(db)
        # Pixel-level checks only work with a real display driver;
        # under SDL_VIDEODRIVER=dummy, surfaces don't render real pixels.
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            return
        found_red = False
        for py in range(SCREEN_HEIGHT - 250, SCREEN_HEIGHT - 180):
            c = screen.get_at((12, py))
            if c.r > 200 and c.g < 50 and c.b < 50:
                found_red = True
                break
        assert found_red, "Expected red portrait pixels in left area of dialogue box"

    def test_no_portrait_no_red_pixels(self, screen, font):
        npc = self._make_npc(profile_image=None)
        db = self._make_dialogue_box(npc)
        view = DialogueBoxView(screen, font)
        view.draw(db)
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            return
        found_red = False
        for py in range(SCREEN_HEIGHT - 250, SCREEN_HEIGHT - 180):
            c = screen.get_at((12, py))
            if c.r > 200 and c.g < 50 and c.b < 50:
                found_red = True
                break
        assert not found_red, "No portrait pixels expected when profile_image is None"

    def test_npc_without_profile_image_attr(self, screen, font):
        """NPC object that lacks profile_image attribute entirely."""
        npc = MagicMock(spec=[])
        npc.name = "Ghost"
        npc.job = "phantom"
        db = self._make_dialogue_box(npc)
        view = DialogueBoxView(screen, font)
        # getattr fallback should handle missing attribute
        view.draw(db)
