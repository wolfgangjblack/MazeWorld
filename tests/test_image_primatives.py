import os
import pytest
from unittest.mock import patch, MagicMock
from src.generate import image_client as img_mod


@pytest.fixture(autouse=True)
def reset_pipe():
    img_mod._pipe = None
    img_mod._pipe_type = None
    yield
    img_mod._pipe = None
    img_mod._pipe_type = None


def test_generate_image_api_raises_without_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="FAL_KEY"):
            img_mod._generate_image_api("a portrait")


@patch("fal_client.subscribe")
def test_generate_image_api_returns_url(mock_subscribe):
    mock_subscribe.return_value = {"images": [{"url": "https://example.com/img.png"}]}
    with patch.dict(os.environ, {"FAL_KEY": "test-key"}):
        url = img_mod._generate_image_api("a portrait")
    assert url == "https://example.com/img.png"
    mock_subscribe.assert_called_once()


@patch.object(img_mod, "IMAGE_BACKEND", "api")
@patch.object(img_mod, "_generate_image_api", return_value="https://example.com/img.png")
@patch("urllib.request.urlretrieve")
def test_generate_npc_portraits_api_saves(mock_retrieve, mock_api, tmp_path):
    npc_db = {
        "100": {"description": "a warrior"},
        "101": {"description": "an elf"},
    }
    img_mod.generate_npc_portraits(npc_db, save_dir=str(tmp_path))

    assert mock_api.call_count == 2
    assert mock_retrieve.call_count == 2
    assert npc_db["100"]["profile_image"].endswith("npc_100.png")
    assert npc_db["101"]["profile_image"].endswith("npc_101.png")


@patch.object(img_mod, "IMAGE_BACKEND", "local")
@patch.object(img_mod, "_generate_image_local")
def test_generate_npc_portraits_local_saves(mock_local, tmp_path):
    mock_image = MagicMock()
    mock_local.return_value = mock_image

    npc_db = {"101": {"description": "an elf"}}
    img_mod.generate_npc_portraits(npc_db, save_dir=str(tmp_path))

    mock_local.assert_called_once_with("an elf")
    mock_image.save.assert_called_once()
    assert npc_db["101"]["profile_image"].endswith("npc_101.png")
