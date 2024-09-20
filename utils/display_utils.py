import random
from config import GRID_SIZE, HUD_HEIGHT

def game_to_screen(x, y):
    """Convert game grid coordinates to screen pixel coordinates."""
    screen_x = x * GRID_SIZE
    screen_y = y * GRID_SIZE + HUD_HEIGHT  # Apply HUD_HEIGHT offset
    return screen_x, screen_y

