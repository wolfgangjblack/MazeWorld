"""Tests for the Fog of War system."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.systems.fog_of_war import FogOfWar, DEFAULT_VISIBILITY_RADIUS
from config import FOG_NIGHT_PENALTY as NIGHT_VISIBILITY_PENALTY
from src.models.player import PlayerCharacter, PlayerClass, Stats


def _make_simple_maze(width=10, height=10):
    """Create a simple open maze (no walls except border)."""

    class SimpleMaze:
        wall_tile_id = 1
        event_tile_id = -1

        def __init__(self, w, h):
            self.grid = [[0 for _ in range(w)] for _ in range(h)]
            # Walls on border
            for y in range(h):
                self.grid[y][0] = 1
                self.grid[y][w - 1] = 1
            for x in range(w):
                self.grid[0][x] = 1
                self.grid[h - 1][x] = 1

        def is_wall(self, x, y):
            if not (0 <= x < len(self.grid[0]) and 0 <= y < len(self.grid)):
                return True
            return self.grid[y][x] == 1

    return SimpleMaze(width, height)


def _make_wall_maze(width=10, height=10):
    """Create a maze with a vertical wall blocking LOS."""
    maze = _make_simple_maze(width, height)
    # Vertical wall at x=5, from y=1 to y=8
    for y in range(1, height - 1):
        maze.grid[y][5] = 1
    return maze


def _make_player(x=5, y=5, wis=10):
    """Create a player with specific WIS stat."""
    p = PlayerCharacter(x=x, y=y)
    p.player_class = PlayerClass(
        name="Test",
        archetype="healer",
        stats=Stats(WIS=wis, STR=10, DEX=10, CON=10, INT=10, CHA=10, LUCK=10),
    )
    return p


class TestFogOfWarBasics:
    def test_all_tiles_start_hidden(self):
        fog = FogOfWar(width=10, height=10)
        for y in range(10):
            for x in range(10):
                assert not fog.is_revealed(x, y)

    def test_update_reveals_player_tile(self):
        fog = FogOfWar(width=10, height=10)
        maze = _make_simple_maze()
        fog.update(5, 5, maze, radius=3)
        assert fog.is_revealed(5, 5)

    def test_update_reveals_within_radius(self):
        fog = FogOfWar(width=10, height=10)
        maze = _make_simple_maze()
        fog.update(5, 5, maze, radius=3)
        # Tiles within radius should be revealed
        assert fog.is_revealed(5, 4)
        assert fog.is_revealed(5, 6)
        assert fog.is_revealed(4, 5)
        assert fog.is_revealed(6, 5)

    def test_tiles_outside_radius_stay_hidden(self):
        fog = FogOfWar(width=20, height=20)
        maze = _make_simple_maze(20, 20)
        fog.update(5, 5, maze, radius=2)
        # Tile far away should not be revealed
        assert not fog.is_revealed(15, 15)

    def test_revealed_tiles_stay_permanent(self):
        fog = FogOfWar(width=10, height=10)
        maze = _make_simple_maze()
        fog.update(3, 3, maze, radius=2)
        assert fog.is_revealed(3, 3)
        # Move away — tile should still be revealed
        fog.update(7, 7, maze, radius=2)
        assert fog.is_revealed(3, 3)


class TestLineOfSight:
    def test_walls_block_los(self):
        """Tiles behind a wall should not be revealed."""
        fog = FogOfWar(width=10, height=10)
        maze = _make_wall_maze()
        # Player at x=3, wall at x=5
        fog.update(3, 5, maze, radius=5)
        # Tile at x=3 (same side as player) should be revealed
        assert fog.is_revealed(4, 5)
        # Wall itself should be visible
        assert fog.is_revealed(5, 5)
        # Tile behind the wall should NOT be revealed
        assert not fog.is_revealed(6, 5)
        assert not fog.is_revealed(7, 5)

    def test_adjacent_to_wall_still_visible(self):
        """Tiles next to walls but with clear LOS should be visible."""
        fog = FogOfWar(width=10, height=10)
        maze = _make_simple_maze()
        fog.update(5, 5, maze, radius=3)
        # Border walls are visible
        assert fog.is_revealed(5, 5)


class TestWISModifier:
    def test_wis_increases_radius(self):
        """Higher WIS should increase visibility radius."""
        from config import FOG_DAY_BONUS
        # WIS 10 = modifier 0, no bonus (day period adds FOG_DAY_BONUS)
        player_low = _make_player(wis=10)
        fog_low = FogOfWar(width=20, height=20)
        radius_low = fog_low.get_visibility_radius(player_low, time_period="day")
        assert radius_low == DEFAULT_VISIBILITY_RADIUS + FOG_DAY_BONUS

        # WIS 16 = modifier +3, bonus = 3 // 2 = 1
        player_mid = _make_player(wis=16)
        radius_mid = fog_low.get_visibility_radius(player_mid, time_period="day")
        assert radius_mid == DEFAULT_VISIBILITY_RADIUS + FOG_DAY_BONUS + 1

        # WIS 18 = modifier +4, bonus = 4 // 2 = 2
        player_high = _make_player(wis=18)
        radius_high = fog_low.get_visibility_radius(player_high, time_period="day")
        assert radius_high == DEFAULT_VISIBILITY_RADIUS + FOG_DAY_BONUS + 2

    def test_negative_wis_no_negative_bonus(self):
        """Negative WIS modifier should not reduce radius below base."""
        from config import FOG_DAY_BONUS
        player = _make_player(wis=6)  # modifier = -2
        fog = FogOfWar()
        radius = fog.get_visibility_radius(player, time_period="day")
        # max(0, -2 // 2) = 0, so radius = DEFAULT + FOG_DAY_BONUS
        assert radius == DEFAULT_VISIBILITY_RADIUS + FOG_DAY_BONUS


class TestNightVisibility:
    def test_night_reduces_radius(self):
        fog = FogOfWar()
        player = _make_player(wis=10)
        day = fog.get_visibility_radius(player, time_period="day")
        night = fog.get_visibility_radius(player, time_period="night")
        from config import FOG_DAY_BONUS
        assert night == DEFAULT_VISIBILITY_RADIUS - NIGHT_VISIBILITY_PENALTY
        assert day == DEFAULT_VISIBILITY_RADIUS + FOG_DAY_BONUS

    def test_torch_restores_radius_at_night(self):
        fog = FogOfWar()
        player = _make_player(wis=10)
        night_torch = fog.get_visibility_radius(player, time_period="night", has_torch=True)
        assert night_torch == DEFAULT_VISIBILITY_RADIUS

    def test_radius_never_below_one(self):
        fog = FogOfWar()
        player = _make_player(wis=6)
        radius = fog.get_visibility_radius(player, is_night=True)
        assert radius >= 1


class TestFogVisibility:
    def test_currently_visible(self):
        fog = FogOfWar(width=10, height=10)
        assert fog.is_currently_visible(5, 5, 5, 5, 3)
        assert fog.is_currently_visible(6, 5, 5, 5, 3)
        assert not fog.is_currently_visible(9, 9, 5, 5, 3)

    def test_dim_edge(self):
        fog = FogOfWar(width=10, height=10)
        # At radius 3 with dim edge 1: tiles at distance 2-3 should be dim
        # Tile at exact radius boundary
        assert fog.is_dim(8, 5, 5, 5, 3)  # distance 3, in dim zone
        assert not fog.is_dim(5, 5, 5, 5, 3)  # distance 0, not dim


class TestSerialization:
    def test_round_trip(self):
        fog = FogOfWar(width=5, height=5)
        fog.revealed[2][2] = True
        fog.revealed[3][3] = True

        data = fog.serialize()
        restored = FogOfWar.deserialize(data)

        assert restored.width == 5
        assert restored.height == 5
        assert restored.is_revealed(2, 2)
        assert restored.is_revealed(3, 3)
        assert not restored.is_revealed(0, 0)
