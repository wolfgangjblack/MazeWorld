import pygame
import random
from config import GRID_SIZE, MAZE_HEIGHT, MAZE_WIDTH, WHITE, BLACK, MAZE_SEED

# Set seed for deterministic mazes
if MAZE_SEED != -1:
    random.seed(MAZE_SEED)

# Directions for maze carving (up, down, left, right)
DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]


class Maze:
    def __init__(self):
        """Initialize the maze object with a grid."""
        self.grid = self.initialize_maze()

    def initialize_maze(self):
        """Initialize a grid where all cells are walls (1)."""
        return [[1 for _ in range(MAZE_WIDTH)] for _ in range(MAZE_HEIGHT)]

    def carve_passages_from(self, x, y):
        """Recursive backtracking algorithm to carve maze paths."""
        directions = DIRECTIONS[:]
        random.shuffle(directions)

        for direction in directions:
            nx, ny = x + direction[0] * 2, y + direction[1] * 2  # Jump 2 cells

            if 0 <= nx < MAZE_HEIGHT and 0 <= ny < MAZE_WIDTH and self.grid[nx][ny] == 1:
                # Carve passage between current cell and the next cell
                self.grid[nx][ny] = 0
                self.grid[x + direction[0]][y + direction[1]] = 0

                # Recursively generate next passage
                self.carve_passages_from(nx, ny)

    def generate(self):
        """Generate the maze starting from the top-left corner."""
        self.grid = self.initialize_maze()  # Reset the grid
        self.carve_passages_from(1, 1)

    def draw(self, screen):
        """Draw the maze on the screen."""
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                if cell == 1:
                    pygame.draw.rect(screen, WHITE, rect)
                else:
                    pygame.draw.rect(screen, BLACK, rect)
                    
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
