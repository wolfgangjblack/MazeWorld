import random
from src.models.npc import NPC, StaticNPC, RandomNPC, AggressiveNPC
from src.models.maze import Maze


def test_npc_construction_from_template():
    npc = StaticNPC(x=5, y=5, id=100)
    assert npc.x == 5
    assert npc.y == 5
    assert npc.id == 100
    assert npc.name is not None
    assert npc.personality is not None
    assert npc.environment is not None
    assert npc.job is not None
    assert npc.hobby is not None


def test_random_npc_construction():
    npc = RandomNPC(x=3, y=3, id=101, home_x=3, home_y=3)
    assert npc.home_x == 3
    assert npc.home_y == 3


def test_aggressive_npc_construction():
    npc = AggressiveNPC(x=7, y=7, id=102)
    assert npc.dist == 5
    assert npc.color == (255, 0, 0)


def test_prepare_sets_interaction_history():
    npc = StaticNPC(x=0, y=0, id=100)
    assert len(npc.interaction_history) == 0
    npc.prepare()
    assert len(npc.interaction_history) == 1
    assert "'sys':" in npc.interaction_history[0]


def test_construct_chat_history_first_greeting():
    npc = StaticNPC(x=0, y=0, id=100)
    npc.prepare()
    history = npc.construct_chat_history("")
    assert len(history) == 4
    assert "walks up and greets" in history[1]
    assert "first time" in history[2].lower()
    assert "response:" in history[3]


def test_construct_chat_history_subsequent():
    npc = StaticNPC(x=0, y=0, id=100)
    npc.prepare()
    npc.construct_chat_history("")
    npc.interaction_history[-1] = f"{npc.name}: Hello there!"

    history = npc.construct_chat_history("How are you?")
    found_player_msg = any("How are you?" in h for h in history)
    assert found_player_msg


def test_random_npc_movement():
    random.seed(42)
    maze = Maze()
    maze.generate()

    open_spaces = maze.find_open_spaces()
    sx, sy = open_spaces[len(open_spaces) // 2]

    npc = RandomNPC(x=sx, y=sy, id=101, home_x=sx, home_y=sy, movement_range=2)
    npc.last_move_time = 0

    npc.update_position(maze, current_time=6000)

    dist_from_home = abs(npc.x - sx) + abs(npc.y - sy)
    assert dist_from_home <= npc.movement_range * 2


def test_aggressive_npc_line_of_sight():
    maze = Maze()
    maze.generate()

    open_spaces = maze.find_open_spaces()
    nx, ny = open_spaces[len(open_spaces) // 2]

    npc = AggressiveNPC(x=nx, y=ny, id=102)

    assert not npc.in_line_of_sight(maze, (nx + 100, ny + 100))
    assert npc.in_line_of_sight(maze, (nx, ny))


def test_can_move():
    npc = StaticNPC(x=0, y=0, id=100)
    npc.last_move_time = 0
    assert npc.can_move(5000)
    assert not npc.can_move(5001)
    assert npc.can_move(10000)


def test_is_appropriate():
    npc = StaticNPC(x=0, y=0, id=100)
    assert npc.is_appropriate("Hello, how are you?")
    assert not npc.is_appropriate("This is chibi content")
    assert npc.is_appropriate("I'm a blacksmith in the forest")


def test_get_fallback_response():
    npc = StaticNPC(x=0, y=0, id=100)
    response = npc.get_fallback_response()
    assert isinstance(response, str)
    assert len(response) > 0
