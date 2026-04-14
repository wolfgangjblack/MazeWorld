import math
import random

from config import ITEM_DENSITY, MAZE_HEIGHT, MAZE_WIDTH
from src.models.maze import Maze


def test_item_tiles_match_density():
    random.seed(42)
    m = Maze()
    m.generate()
    open_spaces = m.find_open_spaces()
    player_start = open_spaces[0]
    pool_size = len(open_spaces) - 1
    m.build_tile_meta(player_start)

    item_tiles = m.get_tiles_by_type("item")
    expected = math.ceil(pool_size * ITEM_DENSITY)
    assert abs(len(item_tiles) - expected) <= 1, f"Items: got {len(item_tiles)}, expected ~{expected}"


def test_place_character():
    m = Maze()
    m.generate()
    x, y = m.place_character()
    assert 0 <= x < MAZE_WIDTH
    assert 0 <= y < MAZE_HEIGHT
    assert not m.is_wall(x, y)


def test_place_event_tiles_count():
    m = Maze()
    m.generate()
    open_count = len(m.find_open_spaces())
    m.place_event_tiles()

    event_count = sum(1 for row in m.grid for cell in row if cell == m.event_tile_id)
    expected = math.ceil(open_count * m.event_percent)
    assert event_count == expected


def test_get_random_open_space():
    m = Maze()
    m.generate()
    x, y = m.get_random_open_space()
    assert not m.is_wall(x, y)
