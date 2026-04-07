"""Placement utilities for NPCs, items, and encounters on the maze grid.

Rules:
- Not on walls
- Encounter tiles are invisible (player doesn't see them until triggered)
- Density is configurable
- Day and night event variants placed on the same tile
- NPCs get placed in zones with open spaces
"""

import random
from typing import Optional


def find_open_cells(grid: list[list[int]], wall_id: int = 1,
                    occupied: set[tuple[int, int]] | None = None) -> list[tuple[int, int]]:
    """Return all open (non-wall) cells not already occupied."""
    occupied = occupied or set()
    cells = []
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell != wall_id and (x, y) not in occupied:
                cells.append((x, y))
    return cells


def place_encounters(
    grid: list[list[int]],
    event_list: list[dict],
    wall_id: int = 1,
    event_tile_id: int = -1,
    occupied: set[tuple[int, int]] | None = None,
    density: float = 0.1,
    time_gate_ratio: float = 0.2,
) -> list[dict]:
    """Place encounter events on the grid and assign time gates.

    Returns a list of ``{"x": int, "y": int, "event_id": str}`` mappings.

    About 20% of events get a ``time_gate`` ("day" or "night").
    """
    occupied = set(occupied) if occupied else set()
    open_cells = find_open_cells(grid, wall_id, occupied)

    if not open_cells:
        return []

    # Determine how many tiles to place
    target_count = max(1, int(len(open_cells) * density))
    target_count = min(target_count, len(event_list), len(open_cells))

    random.shuffle(open_cells)
    positions = open_cells[:target_count]

    event_position_map = []
    for i, (x, y) in enumerate(positions):
        if i >= len(event_list):
            break
        grid[y][x] = event_tile_id
        event_list[i]["x"] = x
        event_list[i]["y"] = y

        # Assign time gate (~20%)
        if random.random() < time_gate_ratio:
            event_list[i]["time_gate"] = random.choice(["day", "night"])

        event_position_map.append({
            "x": x, "y": y, "event_id": event_list[i]["id"],
        })
        occupied.add((x, y))

    return event_position_map


def place_npcs(
    grid: list[list[int]],
    npc_pool: list[dict],
    zones: list[tuple[int, int]],
    zone_size: int = 10,
    wall_id: int = 1,
    occupied: set[tuple[int, int]] | None = None,
) -> list[dict]:
    """Place selected NPCs in their assigned zones on open cells.

    Returns updated NPC pool with x, y positions set on active NPCs.
    NPCs that can't be placed (no open space in zone) are deselected.
    """
    occupied = set(occupied) if occupied else set()
    open_cells_set = set(find_open_cells(grid, wall_id, occupied))

    for npc in npc_pool:
        if not npc.get("selected"):
            continue

        zone = npc.get("zone", [0, 0])
        zone_x, zone_y = zone[0], zone[1]

        # Find open cells within this NPC's zone
        zone_open = [
            (x, y) for (x, y) in open_cells_set
            if zone_x <= x < zone_x + zone_size and zone_y <= y < zone_y + zone_size
        ]

        if zone_open:
            pos = random.choice(zone_open)
            npc["x"] = pos[0]
            npc["y"] = pos[1]
            open_cells_set.discard(pos)
            occupied.add(pos)
        else:
            npc["selected"] = False

    return npc_pool


def place_items(
    grid: list[list[int]],
    item_ids: list[int],
    wall_id: int = 1,
    occupied: set[tuple[int, int]] | None = None,
) -> list[dict]:
    """Place items randomly on open cells.

    Returns a list of ``{"x": int, "y": int, "item_id": int}`` placements.
    """
    occupied = set(occupied) if occupied else set()
    open_cells = find_open_cells(grid, wall_id, occupied)

    if not open_cells:
        return []

    random.shuffle(open_cells)
    placements = []

    for i, item_id in enumerate(item_ids):
        if i >= len(open_cells):
            break
        x, y = open_cells[i]
        grid[y][x] = item_id
        placements.append({"x": x, "y": y, "item_id": item_id})
        occupied.add((x, y))

    return placements


def place_day_night_variants(
    event_list: list[dict],
    time_gate_ratio: float = 0.2,
) -> list[dict]:
    """Assign time_gate values to events. ~20% get 'day' or 'night'.

    Returns the modified event list.
    """
    for event in event_list:
        if event.get("time_gate") is not None:
            continue  # Already assigned
        if random.random() < time_gate_ratio:
            event["time_gate"] = random.choice(["day", "night"])
    return event_list


def compute_zones(width: int, height: int, zone_size: int) -> list[tuple[int, int]]:
    """Return a list of (zone_x, zone_y) top-left corners for a zone grid."""
    zones = []
    for zy in range(0, height, zone_size):
        for zx in range(0, width, zone_size):
            zones.append((zx, zy))
    return zones


def get_player_start(
    grid: list[list[int]],
    wall_id: int = 1,
    occupied: set[tuple[int, int]] | None = None,
) -> Optional[tuple[int, int]]:
    """Find a random open cell for the player to start in."""
    open_cells = find_open_cells(grid, wall_id, occupied)
    if not open_cells:
        return None
    return random.choice(open_cells)
