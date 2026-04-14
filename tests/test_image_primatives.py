import os
import pytest
from unittest.mock import patch, MagicMock
from src.generate import image_client as img_mod
from src.generate.backends.image_api import ApiImageBackend


# -- ApiImageBackend --------------------------------------------------------

class TestApiImageBackend:
    def setup_method(self):
        self.backend = ApiImageBackend()

    def test_generate_image_raises_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="FAL_KEY"):
                self.backend.generate_image("a portrait")

    @patch("fal_client.subscribe")
    def test_generate_image_returns_url(self, mock_subscribe):
        mock_subscribe.return_value = {"images": [{"url": "https://example.com/img.png"}]}
        with patch.dict(os.environ, {"FAL_KEY": "test-key"}):
            url = self.backend.generate_image("a portrait")
        assert url == "https://example.com/img.png"
        mock_subscribe.assert_called_once()


# -- Portrait helpers via registry ------------------------------------------

def test_generate_npc_portraits_delegates(tmp_path):
    """When IMAGE_BACKEND is 'local', falls back to sequential path via get_image_backend."""
    mock_backend = MagicMock()
    mock_backend.generate_and_save.return_value = True

    npc_db = {
        "1000": {"description": "a warrior"},
        "1001": {"description": "an elf"},
    }

    # Patch both get_image_backend AND IMAGE_BACKEND so the parallel path
    # falls through to the sequential backend.
    with patch("src.generate.image_client.get_image_backend", return_value=mock_backend), \
         patch("src.generate.image_client.os.environ.get", return_value=None), \
         patch("config.IMAGE_BACKEND", "local"):
        img_mod.generate_npc_portraits(npc_db, save_dir=str(tmp_path))

    assert mock_backend.generate_and_save.call_count == 2
    assert npc_db["1000"]["profile_image"].endswith("npc_1000.png")
    assert npc_db["1001"]["profile_image"].endswith("npc_1001.png")


def test_generate_npc_portraits_handles_failure(tmp_path):
    """When backend returns False, profile_image should be None."""
    mock_backend = MagicMock()
    mock_backend.generate_and_save.return_value = False

    npc_db = {"1001": {"description": "an elf"}}

    with patch("src.generate.image_client.get_image_backend", return_value=mock_backend), \
         patch("config.IMAGE_BACKEND", "local"):
        img_mod.generate_npc_portraits(npc_db, save_dir=str(tmp_path))

    assert npc_db["1001"]["profile_image"] is None
