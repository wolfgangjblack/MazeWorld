import pygame

from config import GRID_SIZE
from src.utils.display_utils import game_to_screen

QUEST_BORDER_COLORS = {
    "escort": (255, 0, 255),
    "solve": (0, 255, 255),
    "fetch": (255, 255, 0),
    "combat": (255, 0, 0),
}


class NPCView:
    def draw_npc(self, screen, npc, quest_type: str | None = None):
        """Draw the NPC at the specified position.

        When *quest_type* is provided, draw a colored debug border
        around the NPC square indicating the quest type.
        """
        screen_x, screen_y = game_to_screen(npc.x, npc.y)
        rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, npc.color, rect)
        if quest_type:
            border_color = QUEST_BORDER_COLORS.get(quest_type)
            if border_color:
                pygame.draw.rect(screen, border_color, rect, 2)
