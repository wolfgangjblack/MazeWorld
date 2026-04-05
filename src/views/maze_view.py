import pygame
from config import GRID_SIZE, WHITE, BLACK
from src.models.items import Food, Drink, Tool
from src.utils.display_utils import game_to_screen
from src.registry import registry


EVENT_COLOR = (128, 0, 128)    # Purple for event tiles
ESCORT_HIGHLIGHT = (0, 180, 0, 100)  # Semi-transparent green for escort zones


class MazeView:
    def draw_maze(self, screen, maze, escort_zones=None):

        for y, row in enumerate(maze.grid):
            for x, cell in enumerate(row):
                screen_x, screen_y = game_to_screen(x, y)
                rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)
                if cell == maze.wall_tile_id:
                    pygame.draw.rect(screen, WHITE, rect)
                elif cell == maze.event_tile_id:
                    pygame.draw.rect(screen, BLACK, rect)
                    event_rect = pygame.Rect(
                        screen_x + GRID_SIZE // 4,
                        screen_y + GRID_SIZE // 4,
                        GRID_SIZE // 2,
                        GRID_SIZE // 2,
                    )
                    pygame.draw.rect(screen, EVENT_COLOR, event_rect)
                elif cell == 0:
                    pygame.draw.rect(screen, BLACK, rect)
                elif registry.is_item(cell):
                    pygame.draw.rect(screen, BLACK, rect)
                    item = registry.get_item(cell)
                    if isinstance(item, Food):
                        color = (255, 215, 0)
                    elif isinstance(item, Drink):
                        color = (30, 144, 255)
                    elif isinstance(item, Tool):
                        color = (255, 0, 255)
                    else:
                        color = (200, 200, 200)

                    item_rect = pygame.Rect(
                        screen_x + GRID_SIZE // 4,
                        screen_y + GRID_SIZE // 4,
                        GRID_SIZE // 2,
                        GRID_SIZE // 2,
                    )
                    pygame.draw.rect(screen, color, item_rect)

        if escort_zones:
            for (tx, ty) in escort_zones:
                for ox in range(-2, 3):
                    for oy in range(-2, 3):
                        hx, hy = tx + ox, ty + oy
                        sx, sy = game_to_screen(hx, hy)
                        highlight = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
                        highlight.fill((0, 180, 0, 60))
                        screen.blit(highlight, (sx, sy))
