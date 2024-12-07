import pygame
from config import GRID_SIZE
from src.utils.display_utils import game_to_screen

class NPCView:
    def draw_npc(self, screen, npc):
        """Draw the NPC at the specified position."""
        screen_x, screen_y = game_to_screen(npc.x, npc.y)
        rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, npc.color, rect)
