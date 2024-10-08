import pygame
import random
from config import GRID_SIZE, MAZE_HEIGHT, MAZE_WIDTH, WHITE, BLACK, MAZE_SEED, MIN_HALLWAY_SIZE, MAX_HALLWAY_SIZE
from utils.display_utils import game_to_screen
from utils.item_utils import ENTITY_IDS, Food, Drink, Tool, item_registry

# Set seed for deterministic mazes
if MAZE_SEED != -1:
    random.seed(MAZE_SEED)

# Directions for maze carving (up, down, left, right)
DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # (dx, dy)

class Maze:
    def __init__(self):
        """Initialize the maze object with a grid."""
        self.grid = self.initialize_maze()

    def initialize_maze(self):
        """Initialize a grid where all cells are walls (1)."""
        return [[1 for _ in range(MAZE_WIDTH)] for _ in range(MAZE_HEIGHT)]

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
            if 0 <= nx < MAZE_WIDTH and 0 <= ny < MAZE_HEIGHT and self.grid[ny][nx] == 1:
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

    def draw(self, screen):
        """Draw the maze on the screen."""
        WALL_SCALE = 0.5  # Adjust this value between 0 and 1 to change wall size
        WALL_SIZE = GRID_SIZE * WALL_SCALE
        WALL_OFFSET = (GRID_SIZE - WALL_SIZE) / 2
        
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                screen_x, screen_y = game_to_screen(x, y)
                rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)
                if cell == 1:
                    # Draw walls
                    pygame.draw.rect(screen, WHITE, rect)
                elif cell == 0:
                    # Draw floor
                    pygame.draw.rect(screen, BLACK, rect)
                elif cell in item_registry:
                    # Draw food item
                    item = item_registry[cell]
                    if isinstance(item, Food):
                        color = (255, 215, 0)  # Gold color for food
                    elif isinstance(item, Drink):
                        color = (30, 144, 255) # Blue color for drinks
                    elif isinstance(item, Tool):
                        color = (255, 0, 255) # magenta color for tools
                        
                        
                    item_rect = pygame.Rect(
                        screen_x + GRID_SIZE // 4,
                        screen_y + GRID_SIZE // 4,
                        GRID_SIZE // 2,
                        GRID_SIZE // 2
                    )
                    pygame.draw.rect(screen, color, item_rect)  # Gold color for food
                    
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
        
    def place_items(self, num_food: int = 1, num_drink: int = 1, num_tools: int = 1):
        open_spaces = self.find_open_spaces()  # Find open spaces in the maze
        random.shuffle(open_spaces)  # Shuffle the spaces to randomize placement

        item_ids = list(ENTITY_IDS.keys())  # Get the list of item IDs
        
        def generate_items_by_class(cls, num_gens):
            """Place items in the maze based on their class."""
            i = 0
            while i < num_gens:
                if open_spaces:
                    x, y = open_spaces.pop()  # Get a random open space
                    item_id = random.choice(item_ids)  # Choose a random item ID
                    
                    # Check if the item class matches (Food, Drink, or Tool)
                    if isinstance(item_registry[item_id], cls):
                        self.grid[y][x] = item_id  # Place the item in the grid (using the ID)
                        i += 1  # Increment the counter when an item is successfully placed
        
        # Generate items based on the class
        generate_items_by_class(Food, num_food)
        generate_items_by_class(Drink, num_drink)
        generate_items_by_class(Tool, num_tools)
