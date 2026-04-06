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
    mock_backend = MagicMock()
    mock_backend.generate_and_save.return_value = True

    npc_db = {
        "100": {"description": "a warrior"},
        "101": {"description": "an elf"},
    }

    with patch("src.generate.image_client.get_image_backend", return_value=mock_backend):
        img_mod.generate_npc_portraits(npc_db, save_dir=str(tmp_path))

    assert mock_backend.generate_and_save.call_count == 2
    assert npc_db["100"]["profile_image"].endswith("npc_100.png")
    assert npc_db["101"]["profile_image"].endswith("npc_101.png")


def test_generate_npc_portraits_handles_failure(tmp_path):
    mock_backend = MagicMock()
    mock_backend.generate_and_save.return_value = False

    npc_db = {"101": {"description": "an elf"}}

    with patch("src.generate.image_client.get_image_backend", return_value=mock_backend):
        img_mod.generate_npc_portraits(npc_db, save_dir=str(tmp_path))

    assert npc_db["101"]["profile_image"] is None
