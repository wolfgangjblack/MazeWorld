import random
import pytest
from src.models.npc import StaticNPC, RandomNPC, AggressiveNPC, MerchantNPC
from src.models.maze import Maze


def test_random_npc_construction():
    npc = RandomNPC(x=3, y=3, id=1001, home_x=3, home_y=3)
    assert npc.home_x == 3
    assert npc.home_y == 3


def test_aggressive_npc_construction():
    npc = AggressiveNPC(x=7, y=7, id=1002)
    assert npc.dist == 5
    assert npc.color == (255, 0, 0)


def test_prepare_sets_identity():
    npc = StaticNPC(x=0, y=0, id=1000)
    assert npc.identity is None
    npc.prepare(maze_environment="forest")
    assert npc.identity is not None
    assert isinstance(npc.identity, str)
    assert npc.name in npc.identity


def test_add_turn():
    npc = StaticNPC(x=0, y=0, id=1000)
    assert len(npc.interaction_history) == 0
    npc.add_turn("user", "Hello there")
    assert len(npc.interaction_history) == 1
    assert npc.interaction_history[0] == {"role": "user", "content": "Hello there"}


def test_add_turn_multiple():
    npc = StaticNPC(x=0, y=0, id=1000)
    npc.add_turn("user", "Hello")
    npc.add_turn("npc", "Greetings!")
    npc.add_turn("user", "How are you?")
    assert len(npc.interaction_history) == 3
    assert npc.interaction_history[1]["role"] == "npc"


def test_get_recent_history_under_limit():
    npc = StaticNPC(x=0, y=0, id=1000)
    npc.add_turn("user", "Hello")
    npc.add_turn("npc", "Hi")
    history = npc.get_recent_history(max_turns=6)
    assert len(history) == 2


def test_get_recent_history_over_limit():
    npc = StaticNPC(x=0, y=0, id=1000)
    for i in range(10):
        npc.add_turn("user", f"msg {i}")
    history = npc.get_recent_history(max_turns=4)
    assert len(history) == 4
    assert history[0]["content"] == "msg 6"
    assert history[-1]["content"] == "msg 9"


def test_history_persists_across_sessions():
    """NPC history is not cleared -- it accumulates across conversations."""
    npc = StaticNPC(x=0, y=0, id=1000)
    npc.add_turn("user", "First visit greeting")
    npc.add_turn("npc", "Hello traveler!")
    assert len(npc.interaction_history) == 2

    npc.add_turn("user", "I'm back!")
    npc.add_turn("npc", "Welcome back!")
    assert len(npc.interaction_history) == 4
    assert npc.interaction_history[0]["content"] == "First visit greeting"


def test_random_npc_movement():
    random.seed(42)
    maze = Maze()
    maze.generate()

    open_spaces = maze.find_open_spaces()
    sx, sy = open_spaces[len(open_spaces) // 2]

    npc = RandomNPC(x=sx, y=sy, id=1001, home_x=sx, home_y=sy, movement_range=2)
    npc.last_move_time = 0

    npc.update_position(maze, current_time=6000)

    dist_from_home = abs(npc.x - sx) + abs(npc.y - sy)
    assert dist_from_home <= npc.movement_range * 2


def test_aggressive_npc_line_of_sight():
    maze = Maze()
    maze.generate()

    open_spaces = maze.find_open_spaces()
    nx, ny = open_spaces[len(open_spaces) // 2]

    npc = AggressiveNPC(x=nx, y=ny, id=1002)

    assert not npc.in_line_of_sight(maze, (nx + 100, ny + 100))
    assert npc.in_line_of_sight(maze, (nx, ny))


def test_can_move():
    npc = StaticNPC(x=0, y=0, id=1000)
    npc.last_move_time = 0
    assert npc.can_move(5000)
    assert not npc.can_move(5001)
    assert npc.can_move(10000)


def test_is_appropriate():
    npc = StaticNPC(x=0, y=0, id=1000)
    assert npc.is_appropriate("Hello, how are you?")
    assert not npc.is_appropriate("This is chibi content")
    assert npc.is_appropriate("I'm a blacksmith in the forest")


def test_get_fallback_response():
    npc = StaticNPC(x=0, y=0, id=1000)
    response = npc.get_fallback_response()
    assert isinstance(response, str)
    assert len(response) > 0


def test_interaction_history_isolation():
    npc_a = StaticNPC(x=0, y=0, id=1000)
    npc_b = StaticNPC(x=1, y=1, id=1001)

    npc_a.add_turn("user", "Hello A")
    assert len(npc_a.interaction_history) == 1
    assert len(npc_b.interaction_history) == 0


def test_aggressive_npc_chases_player():
    random.seed(42)
    maze = Maze()
    maze.generate()
    open_spaces = maze.find_open_spaces()
    open_set = set(open_spaces)

    for sx, sy in open_spaces:
        for dx in range(2, 6):
            tx = sx + dx
            if (tx, sy) in open_set:
                if all(not maze.is_wall(sx + i, sy) for i in range(1, dx)):
                    npc = AggressiveNPC(x=sx, y=sy, id=1002)
                    npc.last_move_time = 0

                    npc.update_position(maze, (tx, sy), current_time=6000)
                    new_dist = abs(npc.x - tx) + abs(npc.y - sy)
                    assert new_dist < dx, "NPC should have moved closer to player"
                    return

    pytest.fail("Could not find line-of-sight pair in generated maze")


def test_aggressive_npc_random_when_no_los():
    random.seed(42)
    maze = Maze()
    maze.generate()
    open_spaces = maze.find_open_spaces()
    nx, ny = open_spaces[len(open_spaces) // 2]

    npc = AggressiveNPC(x=nx, y=ny, id=1002)
    npc.last_move_time = 0

    far_pos = (nx + 100, ny + 100)

    moved = False
    for t in range(6000, 60000, 6000):
        old_x, old_y = npc.x, npc.y
        npc.update_position(maze, far_pos, current_time=t)
        if (npc.x, npc.y) != (old_x, old_y):
            moved = True
            break

    assert moved, "NPC should eventually move randomly when player is not in line of sight"


@pytest.mark.parametrize("cls,extra_kwargs", [
    (StaticNPC, {}),
    (RandomNPC, {"home_x": 0, "home_y": 0}),
    (AggressiveNPC, {}),
    (MerchantNPC, {}),
])
def test_npc_inherits_maze_environment(cls, extra_kwargs):
    """All NPC types must inherit environment from the maze via prepare()."""
    maze_env = "cave"
    npc = cls(x=0, y=0, id=1500, **extra_kwargs)
    npc.prepare(maze_environment=maze_env)
    assert npc.environment == maze_env


@pytest.mark.parametrize("cls,extra_kwargs", [
    (StaticNPC, {}),
    (RandomNPC, {"home_x": 0, "home_y": 0}),
    (AggressiveNPC, {}),
    (MerchantNPC, {}),
])
def test_npc_environment_overrides_default(cls, extra_kwargs):
    """Even if NPC already has an environment, prepare() with maze_environment overrides it."""
    npc = cls(x=0, y=0, id=1501, environment="forest", **extra_kwargs)
    npc.prepare(maze_environment="dungeon")
    assert npc.environment == "dungeon"


@pytest.mark.parametrize("cls,extra_kwargs", [
    (StaticNPC, {}),
    (RandomNPC, {"home_x": 0, "home_y": 0}),
    (AggressiveNPC, {}),
    (MerchantNPC, {}),
])
def test_npc_job_hobby_match_maze_environment(cls, extra_kwargs):
    """Job and hobby must come from the maze's environment, not a random one."""
    from src.data.world_data import JOBS, HOBBIES
    maze_env = "cave"
    npc = cls(x=0, y=0, id=1502, **extra_kwargs)
    npc.prepare(maze_environment=maze_env)
    assert npc.job in JOBS[maze_env] or npc.job == "merchant"
    assert npc.hobby in HOBBIES[maze_env]


def test_random_npc_stays_in_range():
    random.seed(42)
    maze = Maze()
    maze.generate()
    open_spaces = maze.find_open_spaces()
    sx, sy = open_spaces[len(open_spaces) // 2]

    npc = RandomNPC(x=sx, y=sy, id=1001, home_x=sx, home_y=sy, movement_range=2)
    npc.last_move_time = 0

    for t in range(5000, 100000, 5000):
        npc.update_position(maze, current_time=t)
        assert abs(npc.x - sx) <= npc.movement_range
        assert abs(npc.y - sy) <= npc.movement_range
