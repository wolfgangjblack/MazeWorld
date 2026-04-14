import json
import math
import random
from dataclasses import dataclass, field
from src.registry import registry
from src.data.world_data import ENVIRONMENT_TYPES
from config import (
    MAZE_HEIGHT, MAZE_WIDTH, WORLD_SEED, MIN_HALLWAY_SIZE, MAX_HALLWAY_SIZE,
    EVENT_PERCENT, EVENT_DENSITY, ITEM_DENSITY, NPC_DENSITY,
    COMBAT_CHANCE, PUZZLE_CHANCE, EVENT_CHANCE, TIME_GATE_FRACTION,
)

# Set seed for deterministic mazes
if WORLD_SEED != -1:
    random.seed(WORLD_SEED)

# Directions for maze carving (up, down, left, right)
DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # (dx, dy)

DOOR_TILE_ID = -2  # Special tile value for exit doors

WALL_COLORS = {
    "forest": (34, 80, 34),
    "cave": (90, 75, 60),
    "dungeon": (50, 50, 60),
    "castle": (140, 135, 130),
    "house": (120, 90, 60),
    "city": (160, 155, 150),
    "village": (110, 95, 65),
    "mountain": (95, 85, 75),
    "swamp": (55, 75, 45),
    "ruins": (100, 95, 85),
    "desert": (180, 165, 120),
}

NPC_QUEST_TYPE_WEIGHTS = {
    "fetch": 0.30,
    "combat": 0.25,
    "solve": 0.30,
    "escort": 0.15,
}


REQUIREMENT_TYPES = ["tool", "ability", "spell", "item"]


@dataclass
class TileMeta:
    """Metadata for a single tile on the maze, assigned during Phase 2 layout."""
    position: tuple[int, int]
    tile_type: str  # "event" | "npc" | "item" | "door" | "start" | "path" | "wall"
    # Event-specific
    event_type: str | None = None
    is_multi_combat: bool = False
    multi_combat_count: int = 1
    is_story_related: bool = False
    time_gate: str | None = None
    # Requirement slots (Phase 2 rolls type, enrichment pass fills ref)
    requires_type: str | None = None   # "tool" | "ability" | "spell" | "item"
    requires_ref: str | None = None    # filled by enrichment: actual DB name
    # Combat assignment (filled by enrichment pass from monster DB)
    assigned_monsters: list | None = None
    assigned_monster_count: int = 1
    is_gate: bool = False
    is_climax_boss: bool = False
    # NPC-specific
    npc_role: str | None = None
    npc_max_exchanges: int = 5
    quest_type: str | None = None
    quest_target_tile: tuple[int, int] | None = None
    quest_target_monsters: list | None = None  # filled by enrichment
    is_story_npc: bool = False
    # Item-specific
    item_category: str | None = None


class Maze:
    def __init__(self, environment: str | None = None,
                 environment_name: str = ""):
        """Initialize the maze object with a grid.

        Parameters
        ----------
        environment : str or None
            The environment type (e.g. "forest", "castle"). If None, picks
            randomly from ENVIRONMENT_TYPES for backward compatibility.
        environment_name : str
            A thematic name for this environment (e.g. "Ironspire").
        """
        self.event_percent = EVENT_PERCENT
        self.event_tile_id = -1
        self.door_tile_id = DOOR_TILE_ID
        self.wall_tile_id = 1
        self.environment = environment if environment else random.choice(ENVIRONMENT_TYPES)
        self.environment_name: str = environment_name
        self.wall_color = WALL_COLORS.get(self.environment, WALL_COLORS["dungeon"])
        self.grid = self.initialize_maze()
        self.door_position: tuple[int, int] | None = None
        self.door_revealed: bool = False
        self.gate_encounter_id: int | None = None
        self.tile_meta: list[TileMeta] = []

    def initialize_maze(self):
        """Initialize a grid where all cells are walls (1)."""
        return [[self.wall_tile_id for _ in range(MAZE_WIDTH)] for _ in range(MAZE_HEIGHT)]

    def carve_passages_from(self, x, y):
        """Recursive backtracking algorithm to carve maze paths with hallway size control."""
        directions = DIRECTIONS[:]
        random.shuffle(directions)

        for direction in directions:
            # Randomly choose a hallway size but keep it between the min and max limits
            if random.random() < 0.4:
                hallway_width = random.choices(
                population=range(MIN_HALLWAY_SIZE, MAX_HALLWAY_SIZE + 1),
                weights=[MAX_HALLWAY_SIZE + 1 - w for w in range(MIN_HALLWAY_SIZE, MAX_HALLWAY_SIZE + 1)],
                k=1
            )[0]
            else:
                hallway_width = MIN_HALLWAY_SIZE

            dx, dy = direction
            nx, ny = x + dx * 2, y + dy * 2  # Jump 2 cells to leave walls
            if 0 <= nx < MAZE_WIDTH and 0 <= ny < MAZE_HEIGHT and self.grid[ny][nx] == self.wall_tile_id:
                # Carve passage based on the hallway size
                self.carve_hallway(x, y, direction, hallway_width)

                # Recursively generate next passage
                self.carve_passages_from(nx, ny)

    def carve_hallway(self, x, y, direction, width):
        """Carve a hallway of variable width based on the direction and width."""
        dx, dy = direction
        steps = 2  # Number of steps to reach the next cell
        half_width = width // 2  # Since width is odd, half_width is an integer

        for i in range(steps + 1):  # From the current cell to the next
            mx = x + dx * i
            my = y + dy * i
            for w in range(-half_width, half_width + 1):
                if dy != 0:
                    # Moving vertically; vary x to create width
                    wx = mx + w
                    wy = my
                else:
                    # Moving horizontally; vary y to create width
                    wx = mx
                    wy = my + w

                if 0 <= wx < MAZE_WIDTH and 0 <= wy < MAZE_HEIGHT:
                    self.grid[wy][wx] = 0  # Carve out the hallway

    def generate(self):
        """Generate the maze starting from the top-left corner."""
        self.grid = self.initialize_maze()  # Reset the grid
        self.carve_passages_from(1, 1)
                    
    def is_wall(self, x, y):
        """Check if the given position (x, y) is a wall or out of bounds."""
        # Check if the coordinates are out of bounds (boundary check)
        if not (0 <= x < MAZE_WIDTH and 0 <= y < MAZE_HEIGHT):
            return True  # Treat out-of-bounds as a wall

        # Check if the cell is a wall inside the maze
        return self.grid[y][x] == 1

    def find_open_spaces(self):
        """Return a list of coordinates (x, y) that are open spaces in the maze."""
        open_spaces = []
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == 0:  # 0 means open space
                    open_spaces.append((x, y))
        return open_spaces
    
    def get_random_open_space(self):
        """Get a random open space from the maze - use to place entities."""
        open_spaces = self.find_open_spaces()
        return random.choice(open_spaces)
    
    def place_character(self):
        """Place a character in the maze."""
        open_spaces = self.find_open_spaces()
        space = random.choice(open_spaces)
        return space[0], space[1]
    
    def place_event_tiles(self, random_var: float = 0.05):
        """Place event tiles in the maze."""
        open_spaces = self.find_open_spaces()
        
        #Randomly vary event percent - later
        if WORLD_SEED == -1:
            event_percent = random.uniform(self.event_percent -random_var, self.event_percent + random_var)

        else:
            event_percent = self.event_percent
        
        num_events = math.ceil(len(open_spaces) * event_percent)
        for _ in range(num_events):
            x, y = random.choice(open_spaces)
            self.grid[y][x] = self.event_tile_id
            open_spaces.remove((x, y))
        
    def place_door(self, player_start: tuple[int, int]) -> tuple[int, int] | None:
        """Place an exit door far from the player start. Returns door position."""
        open_spaces = self.find_open_spaces()
        if not open_spaces:
            return None
        # Pick the farthest open space from player start
        px, py = player_start
        open_spaces.sort(key=lambda p: abs(p[0] - px) + abs(p[1] - py), reverse=True)
        # Pick from the farthest 10% to add some variance
        top_n = max(1, len(open_spaces) // 10)
        dx, dy = random.choice(open_spaces[:top_n])
        self.door_position = (dx, dy)
        # Door starts hidden (remains a wall tile); reveal_door() places the tile
        return self.door_position

    def reveal_door(self):
        """Make the door visible on the map as a gold door tile."""
        if self.door_position and not self.door_revealed:
            dx, dy = self.door_position
            self.grid[dy][dx] = self.door_tile_id
            self.door_revealed = True

    def count_open_cells(self) -> int:
        """Count all open/path cells (value == 0) in the grid."""
        return sum(1 for row in self.grid for cell in row if cell == 0)

    def build_tile_meta(self, player_start: tuple[int, int]) -> list[TileMeta]:
        """Build density-based tile metadata for all special tiles.

        Assigns event, NPC, and item tiles based on density configs applied
        to the number of open cells. Returns the list and also stores it
        on self.tile_meta.
        """
        open_cells = self.find_open_spaces()
        if player_start in open_cells:
            open_cells.remove(player_start)
        random.shuffle(open_cells)
        num_open = len(open_cells)

        meta: list[TileMeta] = []
        used: set[tuple[int, int]] = set()

        # -- Events: EVENT_DENSITY * 1.25 (to account for time-gated extras) --
        num_events = math.ceil(num_open * EVENT_DENSITY * (1.0 + TIME_GATE_FRACTION))
        event_positions = []
        for pos in open_cells:
            if len(event_positions) >= num_events:
                break
            if pos not in used:
                event_positions.append(pos)
                used.add(pos)

        num_time_gated = math.ceil(len(event_positions) * TIME_GATE_FRACTION)
        time_gated_indices = set(random.sample(
            range(len(event_positions)),
            min(num_time_gated, len(event_positions)),
        ))

        for idx, pos in enumerate(event_positions):
            roll = random.random()
            if roll < COMBAT_CHANCE:
                etype = "combat"
            elif roll < COMBAT_CHANCE + PUZZLE_CHANCE:
                etype = "puzzle"
            else:
                etype = "event"

            is_multi = False
            multi_count = 1
            if etype == "combat" and random.random() < 0.10:
                is_multi = True
                multi_count = random.randint(2, 4)

            tg = None
            if idx in time_gated_indices:
                tg = random.choice(["day", "night"])

            req_type = None
            if etype in ("puzzle", "event") and random.random() < 0.10:
                req_type = random.choice(REQUIREMENT_TYPES)

            meta.append(TileMeta(
                position=pos,
                tile_type="event",
                event_type=etype,
                is_multi_combat=is_multi,
                multi_combat_count=multi_count,
                is_story_related=(random.random() < 0.10),
                time_gate=tg,
                requires_type=req_type,
                assigned_monster_count=multi_count if etype == "combat" else 1,
            ))
            self.grid[pos[1]][pos[0]] = self.event_tile_id

        # -- NPCs: NPC_DENSITY of open cells, ceil --
        remaining = [p for p in open_cells if p not in used]
        num_npcs = math.ceil(num_open * NPC_DENSITY)
        npc_positions = remaining[:num_npcs]
        for pos in npc_positions:
            used.add(pos)

        quest_types = list(NPC_QUEST_TYPE_WEIGHTS.keys())
        quest_weights = list(NPC_QUEST_TYPE_WEIGHTS.values())
        assigned_solve_tiles: set[tuple] = set()

        for pos in npc_positions:
            role_roll = random.random()
            if role_roll < 0.40:
                role = "quest"
                qt = random.choices(quest_types, weights=quest_weights, k=1)[0]
            elif role_roll < 0.50:
                role = "merchant"
                qt = None
            else:
                role = "regular"
                qt = None

            max_ex = random.randint(3, 10)

            target_tile = None
            if qt == "solve":
                event_tiles = [m for m in meta if m.tile_type == "event"
                               and m.position not in assigned_solve_tiles]
                if event_tiles:
                    chosen = random.choice(event_tiles)
                    target_tile = chosen.position
                    assigned_solve_tiles.add(target_tile)
            elif qt == "escort":
                far_tiles = [p for p in open_cells if p not in used
                             and abs(p[0] - pos[0]) + abs(p[1] - pos[1]) > 10]
                if far_tiles:
                    target_tile = random.choice(far_tiles[:max(1, len(far_tiles) // 3)])

            meta.append(TileMeta(
                position=pos,
                tile_type="npc",
                npc_role=role,
                npc_max_exchanges=max_ex,
                quest_type=qt,
                quest_target_tile=target_tile,
            ))

        # Mark 2-5 random quest NPCs as story NPCs
        quest_npc_tiles = [t for t in meta if t.tile_type == "npc" and t.quest_type]
        num_story = min(len(quest_npc_tiles), random.randint(2, 5))
        for t in random.sample(quest_npc_tiles, num_story) if quest_npc_tiles else []:
            t.is_story_npc = True

        # -- Items: ITEM_DENSITY of open cells --
        remaining = [p for p in open_cells if p not in used]
        num_items = math.ceil(num_open * ITEM_DENSITY)
        item_positions = remaining[:num_items]
        for pos in item_positions:
            used.add(pos)

        categories = ["food", "drink", "tool", "weapon"]
        cat_weights = [0.30, 0.30, 0.25, 0.15]
        for pos in item_positions:
            cat = random.choices(categories, weights=cat_weights, k=1)[0]
            meta.append(TileMeta(
                position=pos,
                tile_type="item",
                item_category=cat,
            ))

        # -- Player start --
        meta.append(TileMeta(position=player_start, tile_type="start"))

        self.tile_meta = meta
        return meta

    def get_tiles_by_type(self, tile_type: str) -> list[TileMeta]:
        """Return all TileMeta entries matching a given tile_type."""
        return [t for t in self.tile_meta if t.tile_type == tile_type]

    def get_event_tiles(self, event_type: str | None = None) -> list[TileMeta]:
        """Return event tiles, optionally filtered by event_type."""
        tiles = self.get_tiles_by_type("event")
        if event_type:
            tiles = [t for t in tiles if t.event_type == event_type]
        return tiles

    def save_to_json(self, path: str, extra: dict | None = None):
        """Persist the maze grid and metadata to a JSON file."""
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "grid": self.grid,
            "environment": self.environment,
            "environment_name": self.environment_name,
        }
        if self.door_position:
            data["door_position"] = list(self.door_position)
            data["door_revealed"] = self.door_revealed
        if self.gate_encounter_id:
            data["gate_encounter_id"] = self.gate_encounter_id
        if extra:
            data.update(extra)
        with open(path, "w") as f:
            json.dump(data, f)

    @classmethod
    def load_from_json(cls, path: str) -> tuple["Maze", dict]:
        """Reconstruct a Maze from a previously saved JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        maze = cls.__new__(cls)
        maze.event_percent = EVENT_PERCENT
        maze.event_tile_id = -1
        maze.door_tile_id = DOOR_TILE_ID
        maze.wall_tile_id = 1
        maze.tile_meta = []
        maze.environment = data["environment"]
        maze.environment_name = data.get("environment_name", "")
        maze.grid = data["grid"]
        door_pos = data.get("door_position")
        maze.door_position = tuple(door_pos) if door_pos else None
        maze.door_revealed = data.get("door_revealed", False)
        maze.gate_encounter_id = data.get("gate_encounter_id")
        return maze, data
