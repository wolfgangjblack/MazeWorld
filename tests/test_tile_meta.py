"""Tests for the Phase 2 TileMeta system — density-based tile placement.

Each test validates a contract that downstream phases depend on.
"""

import math
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import EVENT_DENSITY, ITEM_DENSITY, NPC_DENSITY, TIME_GATE_FRACTION
from src.models.maze import Maze


@pytest.fixture
def seeded_maze():
    """Generate a deterministic maze with tile meta built.

    Returns (maze, player_start, pool_size) where pool_size is the number
    of open cells available for placement (before build_tile_meta runs).
    """
    random.seed(42)
    m = Maze(environment="castle", environment_name="Ironspire")
    m.generate()
    open_spaces = m.find_open_spaces()
    player_start = open_spaces[0]
    pool_size = len(open_spaces) - 1  # player_start is excluded from pool
    m.build_tile_meta(player_start)
    return m, player_start, pool_size


class TestTileCounts:
    def test_tile_counts_match_density_config(self, seeded_maze):
        """Event/NPC/item tile counts should be ceil(pool * density),
        where pool = open cells minus player start, with events inflated
        by TIME_GATE_FRACTION."""
        maze, _, pool_size = seeded_maze

        events = maze.get_tiles_by_type("event")
        npcs = maze.get_tiles_by_type("npc")
        items = maze.get_tiles_by_type("item")

        expected_events = math.ceil(pool_size * EVENT_DENSITY * (1.0 + TIME_GATE_FRACTION))
        expected_npcs = math.ceil(pool_size * NPC_DENSITY)
        expected_items = math.ceil(pool_size * ITEM_DENSITY)

        assert abs(len(events) - expected_events) <= 1, f"Events: got {len(events)}, expected ~{expected_events}"
        assert abs(len(npcs) - expected_npcs) <= 1, f"NPCs: got {len(npcs)}, expected ~{expected_npcs}"
        assert abs(len(items) - expected_items) <= 1, f"Items: got {len(items)}, expected ~{expected_items}"


class TestTileIntegrity:
    def test_no_tile_position_collisions(self, seeded_maze):
        """No two non-start tiles should share the same position."""
        maze, _, _ = seeded_maze
        positions = [t.position for t in maze.tile_meta if t.tile_type != "start"]
        assert len(positions) == len(set(positions)), "Duplicate tile positions found"

    def test_all_tiles_on_open_cells(self, seeded_maze):
        """Every placed tile must be on a cell that was originally open or
        is marked as an event tile (events overwrite open cells)."""
        maze, player_start, _ = seeded_maze
        for tile in maze.tile_meta:
            x, y = tile.position
            cell = maze.grid[y][x]
            assert cell != maze.wall_tile_id, f"Tile at {tile.position} ({tile.tile_type}) placed on a wall"


class TestQuestTargets:
    def test_quest_npcs_target_valid_tiles(self, seeded_maze):
        """NPCs with event-referencing quests must point to an existing
        event tile of the correct type."""
        maze, _, _ = seeded_maze
        event_map = {}
        for t in maze.get_tiles_by_type("event"):
            event_map[t.position] = t.event_type

        quest_to_event_type = {
            "combat_event": "combat",
            "solve_puzzle": "puzzle",
            "solve_event": "event",
        }

        for npc in maze.get_tiles_by_type("npc"):
            if npc.quest_type in quest_to_event_type:
                if npc.quest_target_tile is None:
                    continue
                assert npc.quest_target_tile in event_map, (
                    f"NPC at {npc.position} targets tile {npc.quest_target_tile} which is not an event tile"
                )
                expected_type = quest_to_event_type[npc.quest_type]
                actual_type = event_map[npc.quest_target_tile]
                assert actual_type == expected_type, (
                    f"NPC quest_type={npc.quest_type} targets {npc.quest_target_tile} "
                    f"which is '{actual_type}', expected '{expected_type}'"
                )


class TestNPCExchanges:
    def test_npc_max_exchanges_in_range(self, seeded_maze):
        """Every NPC must have max_exchanges between 3 and 10."""
        maze, _, _ = seeded_maze
        for npc in maze.get_tiles_by_type("npc"):
            assert 3 <= npc.npc_max_exchanges <= 10, f"NPC at {npc.position} has max_exchanges={npc.npc_max_exchanges}"


class TestDeterminism:
    def test_seeded_layout_is_deterministic(self):
        """Same seed must produce identical tile layouts."""
        layouts = []
        for _ in range(2):
            random.seed(99)
            m = Maze(environment="forest", environment_name="Thornwood")
            m.generate()
            start = m.find_open_spaces()[0]
            m.build_tile_meta(start)
            snapshot = [(t.position, t.tile_type, t.event_type, t.npc_role, t.item_category) for t in m.tile_meta]
            layouts.append(snapshot)

        assert layouts[0] == layouts[1], "Seeded layouts differ between runs"
