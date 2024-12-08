import math 
import random
from src.models.items import Food, Drink, Tool
from src.utils.dataloader_utils import load_json_data, create_item_from_data
from config import MAZE_HEIGHT, MAZE_WIDTH, MAZE_SEED, MIN_HALLWAY_SIZE, MAX_HALLWAY_SIZE, EVENT_PERCENT

# Set seed for deterministic mazes
if MAZE_SEED != -1:
    random.seed(MAZE_SEED)

# Directions for maze carving (up, down, left, right)
DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # (dx, dy)

items_data = load_json_data('data/items/items.json')

item_registry = {}
for item_id_str, item_info in items_data.items():
    item_id = int(item_id_str)
    item_obj = create_item_from_data(item_id, item_info)
    item_registry[item_id] = item_obj

ENTITY_IDS = load_json_data('data/items/entities.json')

ENTITY_IDS = {int(k): v for k, v in ENTITY_IDS.items()}
item_registry = {int(k): v for k, v in item_registry.items()}

class Maze:
    def __init__(self):
        """Initialize the maze object with a grid."""
        self.event_percent = EVENT_PERCENT
        self.event_tile_id = -1
        self.wall_tile_id = 1
        self.environment = random.choice(["forest", "cave", "dungeon", "castle", "house", "city"])
        self.grid = self.initialize_maze()

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
        if MAZE_SEED == -1:
            event_percent = random.uniform(self.event_percent -random_var, self.event_percent + random_var)

        else:
            event_percent = self.event_percent
        
        num_events = math.ceil(len(open_spaces) * event_percent)
        for _ in range(num_events):
            x, y = random.choice(open_spaces)
            self.grid[y][x] = self.event_tile_id
            open_spaces.remove((x, y))
        
    def place_items(self, num_food: int = 1, num_drink: int = 1, num_tools: int = 1):
        open_spaces = self.find_open_spaces()
        random.shuffle(open_spaces)
        
        item_ids = list(item_registry.keys())

        def generate_items_by_class(cls, num_gens):
            i = 0
            attempts = 0
            max_attempts = 1000
            while i < num_gens and attempts < max_attempts:
                attempts += 1
                if not open_spaces:
                    break
                x, y = open_spaces.pop()
                item_id = random.choice(item_ids)
                item = item_registry[item_id]

                if isinstance(item, cls):
                    self.grid[y][x] = item_id
                    i += 1
                # If not the right class, we just continue trying
            # If after max_attempts or out of open spaces we haven't placed enough, we stop.

        generate_items_by_class(Food, num_food)
        generate_items_by_class(Drink, num_drink)
        generate_items_by_class(Tool, num_tools)
