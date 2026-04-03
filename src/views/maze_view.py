import pygame
from config import GRID_SIZE, WHITE, BLACK
from src.models.items import Food, Drink, Tool
from src.utils.display_utils import game_to_screen
from src.registry import registry

class MazeView:
    def draw_maze(self, screen, maze):

        for y, row in enumerate(maze.grid):
            for x, cell in enumerate(row):
                screen_x, screen_y = game_to_screen(x, y)
                rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)
                if cell == maze.wall_tile_id:
                    # Draw walls
                    pygame.draw.rect(screen, WHITE, rect)
                elif cell == 0:
                    # Draw floor
                    pygame.draw.rect(screen, BLACK, rect)
                elif registry.is_item(cell):
                    item = registry.get_item(cell)
                    if isinstance(item, Food):
                        color = (255, 215, 0)  # Gold for food
                    elif isinstance(item, Drink):
                        color = (30, 144, 255) # Blue for drinks
                    elif isinstance(item, Tool):
                        color = (255, 0, 255) # Magenta for tools

                    item_rect = pygame.Rect(
                        screen_x + GRID_SIZE // 4,
                        screen_y + GRID_SIZE // 4,
                        GRID_SIZE // 2,
                        GRID_SIZE // 2
                    )
                    pygame.draw.rect(screen, color, item_rect)