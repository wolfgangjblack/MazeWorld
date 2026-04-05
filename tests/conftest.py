import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.registry import registry
from src.models.maze import Maze
from src.models.player import PlayerCharacter
from config import NUM_FOOD, NUM_DRINKS, NUM_TOOLS


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
    m.place_items(NUM_FOOD, NUM_DRINKS, NUM_TOOLS)
    return m


@pytest.fixture
def player():
    p = PlayerCharacter(x=0, y=0)
    p.initialize_inventory()
    return p
