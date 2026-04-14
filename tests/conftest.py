import os
import random

import pytest

from config import DATA_DIR
from src.registry import registry
from src.models.maze import Maze
from src.models.player import PlayerCharacter

HAS_GENERATED_DATA = os.path.exists(os.path.join(DATA_DIR, "items", "items.json"))
requires_data = pytest.mark.skipif(
    not HAS_GENERATED_DATA,
    reason="Requires generated world data (run pipeline first)",
)


@pytest.fixture(scope="session", autouse=True)
def load_registry():
    registry.load()
    return registry


@pytest.fixture
def reg(load_registry):
    return load_registry


@pytest.fixture
def maze():
    m = Maze()
    m.generate()
    m.place_event_tiles()
    player_start = m.find_open_spaces()[0]
    m.build_tile_meta(player_start)
    avail_ids = registry.item_ids()
    if avail_ids:
        for tile in m.get_tiles_by_type("item"):
            x, y = tile.position
            m.grid[y][x] = random.choice(avail_ids)
    return m


@pytest.fixture
def player():
    p = PlayerCharacter(x=0, y=0)
    p.initialize_inventory()
    return p
