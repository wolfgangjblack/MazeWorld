"""Tests for config.resolve_data_path portability.

The pipeline records absolute portrait/music/SFX paths from the generation
machine. When the packaged game runs on a different machine (or Windows)
those paths don't exist, so resolve_data_path must re-anchor them onto the
local data/ folder. These tests pin that behavior down.
"""

import os

import pytest

import config


@pytest.fixture
def bundle_data_dir(tmp_path, monkeypatch):
    """Pretend the bundle lives at tmp_path/ with a real data/ beside config."""
    data_dir = tmp_path / "data"
    (data_dir / "portraits" / "npcs").mkdir(parents=True)
    portrait = data_dir / "portraits" / "npcs" / "npc_1000.png"
    portrait.write_bytes(b"\x89PNG\r\n")
    monkeypatch.setattr(config, "_BASE_DIR", str(tmp_path))
    return tmp_path, portrait


def test_relative_path_anchored_to_base_dir(bundle_data_dir):
    base, _ = bundle_data_dir
    resolved = config.resolve_data_path("data/portraits/npcs/npc_1000.png")
    assert resolved == os.path.join(str(base), "data/portraits/npcs/npc_1000.png")


def test_existing_absolute_path_passes_through(bundle_data_dir):
    _, portrait = bundle_data_dir
    resolved = config.resolve_data_path(str(portrait))
    assert resolved == str(portrait)


def test_missing_absolute_path_reanchored_onto_bundle(bundle_data_dir):
    base, portrait = bundle_data_dir
    foreign = "/Users/someone_else/MazeWorld/data/portraits/npcs/npc_1000.png"
    resolved = config.resolve_data_path(foreign)
    assert resolved == str(portrait)


def test_missing_path_with_no_bundle_copy_returns_original(bundle_data_dir):
    foreign = "/Users/nobody/MazeWorld/data/portraits/npcs/missing.png"
    resolved = config.resolve_data_path(foreign)
    assert resolved == foreign


def test_none_and_empty_passthrough():
    assert config.resolve_data_path(None) is None
    assert config.resolve_data_path("") == ""
