import pytest
from src.models.player import PlayerCharacter
from src.models.items import Food, Drink, ItemStats
from src.models.npc import StaticNPC


def test_starter_inventory_cloned(player, reg):
    player.inventory["bread"].quantity = 99
    assert reg.starter_inventory["bread"].quantity == 1


def test_is_item_at_player_position(maze, reg):
    player = PlayerCharacter(x=0, y=0)
    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if reg.is_item(cell):
                player.x, player.y = x, y
                assert player.is_item_at_player_position(maze)
                return
    pytest.fail("Precondition not met: maze must contain at least one item")


def test_is_item_at_empty_position(maze):
    player = PlayerCharacter(x=0, y=0)
    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if cell == 0:
                player.x, player.y = x, y
                assert not player.is_item_at_player_position(maze)
                return


def test_pick_up_item(maze, reg):
    player = PlayerCharacter(x=0, y=0)
    player.initialize_inventory()

    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if reg.is_item(cell):
                player.x, player.y = x, y
                item_name = reg.get_item_name(cell)
                msg = player.pick_up_item(maze)
                assert "Picked up" in msg
                assert maze.grid[y][x] == 0
                assert item_name in player.inventory
                return

    pytest.fail("Precondition not met: maze must contain at least one item")


def test_pick_up_empty(maze):
    player = PlayerCharacter(x=0, y=0)
    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if cell == 0:
                player.x, player.y = x, y
                msg = player.pick_up_item(maze)
                assert msg == ""
                return


def test_move_blocked_by_wall(maze):
    player = PlayerCharacter(x=0, y=0)
    open_spaces = maze.find_open_spaces()
    px, py = open_spaces[0]
    player.x, player.y = px, py

    assert maze.is_wall(0, 0)
    player_on_edge = PlayerCharacter(x=0, y=0)
    player_on_edge.move(dx=-1, dy=0, maze=maze)
    assert player_on_edge.x == 0 and player_on_edge.y == 0


def test_move_decrements_stats(maze):
    player = PlayerCharacter(x=0, y=0)
    open_spaces = maze.find_open_spaces()
    px, py = open_spaces[0]
    player.x, player.y = px, py

    initial_hunger = player.hunger
    initial_thirst = player.thirst

    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if cell == 0 and (x, y) != (px, py):
                dx = x - px
                dy = y - py
                if abs(dx) + abs(dy) == 1:
                    player.move(dx=dx, dy=dy, maze=maze)
                    assert player.hunger < initial_hunger
                    assert player.thirst < initial_thirst
                    return

    pytest.fail("Precondition not met: maze must contain adjacent open spaces")


def _make_food(name="apple", nutrition=20, health=5, qty=1):
    return Food(
        category="food", name=name, desc="test",
        quantity=qty, item_stats=ItemStats(nutrition_value=nutrition, health_value=health),
    )


def _make_drink(name="juice", hydration=20, health=5, qty=1):
    return Drink(
        category="drink", name=name, desc="test",
        quantity=qty, item_stats=ItemStats(hydration_value=hydration, health_value=health),
    )


def test_use_item_applies_effect():
    player = PlayerCharacter(x=0, y=0)
    food = _make_food(nutrition=20, health=5)
    player.inventory = {"apple": food}
    player.selected_item_index = 0
    player.hunger = 50
    player.health = 80

    msg = player.use_item()
    assert "ate" in msg.lower()
    assert player.hunger == 70
    assert player.health == 85


def test_use_item_removes_on_zero():
    player = PlayerCharacter(x=0, y=0)
    player.inventory = {"apple": _make_food(qty=1)}
    player.selected_item_index = 0

    player.use_item()
    assert "apple" not in player.inventory


def test_use_item_empty_inventory():
    player = PlayerCharacter(x=0, y=0)
    player.inventory = {}
    msg = player.use_item()
    assert msg == "No item to use."


def test_give_item():
    player = PlayerCharacter(x=0, y=0)
    player.inventory = {"apple": _make_food(qty=2)}
    player.selected_item_index = 0

    msg = player.give_item()
    assert "gave" in msg.lower()
    assert player.inventory["apple"].quantity == 1


def test_give_item_empty_inventory():
    player = PlayerCharacter(x=0, y=0)
    player.inventory = {}
    msg = player.give_item()
    assert msg == "No item to give."


def test_remove_from_inventory_decrements():
    player = PlayerCharacter(x=0, y=0)
    player.inventory = {"apple": _make_food(qty=3)}

    player.remove_from_inventory("apple")
    assert player.inventory["apple"].quantity == 2


def test_remove_from_inventory_deletes_at_zero():
    player = PlayerCharacter(x=0, y=0)
    player.inventory = {"apple": _make_food(qty=1)}

    player.remove_from_inventory("apple")
    assert "apple" not in player.inventory


def test_get_inventory_format():
    player = PlayerCharacter(x=0, y=0)
    player.inventory = {
        "apple": _make_food(qty=3),
        "juice": _make_drink(qty=2),
    }

    inv = player.get_inventory()
    assert isinstance(inv, list)
    assert ("apple", 3) in inv
    assert ("juice", 2) in inv


def test_move_while_starving_costs_health():
    """Moving when hunger reaches 0 costs 1 HP."""
    from unittest.mock import MagicMock
    maze = MagicMock()
    maze.is_wall.return_value = False
    player = PlayerCharacter(x=0, y=0)
    player.hunger = 1  # drops to 0 after move
    player.thirst = 50
    initial_health = player.health
    player.move(dx=1, dy=0, maze=maze)
    assert player.hunger == 0
    assert player.health == initial_health - 1


def test_move_while_low_hunger_slows_player():
    """Moving when hunger drops below 20 reduces speed to 80%."""
    from unittest.mock import MagicMock
    maze = MagicMock()
    maze.is_wall.return_value = False
    player = PlayerCharacter(x=0, y=0)
    player.hunger = 16  # drops to 15 after move
    player.thirst = 50
    initial_speed = player.speed
    player.move(dx=1, dy=0, maze=maze)
    assert player.hunger == 15
    assert player.speed == initial_speed * 0.8


def test_move_while_dehydrated_costs_health():
    """Moving when thirst reaches 0 costs 1 HP."""
    from unittest.mock import MagicMock
    maze = MagicMock()
    maze.is_wall.return_value = False
    player = PlayerCharacter(x=0, y=0)
    player.hunger = 50
    player.thirst = 1  # drops to 0 after move
    initial_health = player.health
    player.move(dx=1, dy=0, maze=maze)
    assert player.thirst == 0
    assert player.health == initial_health - 1


def test_get_nearby_npc_adjacent():
    player = PlayerCharacter(x=5, y=5)
    npc = StaticNPC(x=5, y=6, id=100)

    result = player.get_nearby_npc([npc])
    assert result is npc


def test_get_nearby_npc_none():
    player = PlayerCharacter(x=5, y=5)
    npc = StaticNPC(x=50, y=50, id=100)

    result = player.get_nearby_npc([npc])
    assert result is None


def test_is_on_event_tile(maze):
    player = PlayerCharacter(x=0, y=0)
    for y, row in enumerate(maze.grid):
        for x, cell in enumerate(row):
            if cell == maze.event_tile_id:
                player.x, player.y = x, y
                assert player.is_on_event_tile(maze)
                return
    pytest.fail("Precondition not met: maze must contain event tiles")
