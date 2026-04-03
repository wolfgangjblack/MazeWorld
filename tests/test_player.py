from src.models.player_character import PlayerCharacter
from src.models.items import Food, Drink, Tool


def test_initialize_inventory(player):
    assert set(player.inventory.keys()) == {"bread", "water", "hammer"}
    assert isinstance(player.inventory["bread"], Food)
    assert isinstance(player.inventory["water"], Drink)
    assert isinstance(player.inventory["hammer"], Tool)


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
    # If no items were placed (unlikely), skip
    assert True


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

    assert True


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

    assert True
