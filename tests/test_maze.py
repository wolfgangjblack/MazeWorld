import math
from src.models.maze import Maze
from src.models.items import Food, Drink, Tool

from config import MAZE_WIDTH, MAZE_HEIGHT, NUM_FOOD, NUM_DRINKS, NUM_TOOLS


def test_place_items(maze, reg):
    placed = {}
    for row in maze.grid:
        for cell in row:
            if reg.is_item(cell):
                item = reg.get_item(cell)
                cls = type(item)
                placed[cls] = placed.get(cls, 0) + 1

    assert placed.get(Food, 0) == NUM_FOOD
    assert placed.get(Drink, 0) == NUM_DRINKS
    assert placed.get(Tool, 0) == NUM_TOOLS


def test_place_items_uses_registry(maze, reg):
    for row in maze.grid:
        for cell in row:
            if cell not in (0, 1, maze.event_tile_id):
                assert reg.is_item(cell), f"Cell value {cell} not in registry"


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

    event_count = sum(
        1 for row in m.grid for cell in row if cell == m.event_tile_id
    )
    expected = math.ceil(open_count * m.event_percent)
    assert event_count == expected


def test_get_random_open_space():
    m = Maze()
    m.generate()
    x, y = m.get_random_open_space()
    assert not m.is_wall(x, y)
