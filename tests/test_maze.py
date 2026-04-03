from src.models.maze import Maze
from src.models.items import Food, Drink, Tool
from src.registry import registry
from config import MAZE_WIDTH, MAZE_HEIGHT, NUM_FOOD, NUM_DRINKS, NUM_TOOLS


def test_maze_generation():
    m = Maze()
    m.generate()
    assert len(m.grid) == MAZE_HEIGHT
    assert all(len(row) == MAZE_WIDTH for row in m.grid)


def test_maze_has_open_spaces():
    m = Maze()
    m.generate()
    open_spaces = m.find_open_spaces()
    assert len(open_spaces) > 0


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


def test_is_wall_boundary():
    m = Maze()
    m.generate()
    assert m.is_wall(-1, 0)
    assert m.is_wall(0, -1)
    assert m.is_wall(MAZE_WIDTH, 0)
    assert m.is_wall(0, MAZE_HEIGHT)


def test_is_wall_carved_cell():
    m = Maze()
    m.generate()
    open_spaces = m.find_open_spaces()
    assert len(open_spaces) > 0
    x, y = open_spaces[0]
    assert not m.is_wall(x, y)


def test_place_character():
    m = Maze()
    m.generate()
    x, y = m.place_character()
    assert 0 <= x < MAZE_WIDTH
    assert 0 <= y < MAZE_HEIGHT
    assert not m.is_wall(x, y)
