"""Game over screen — displays death message, brief stats, and options."""

import os
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

TITLE_COLOR = (200, 50, 50)
TEXT_COLOR = (180, 180, 180)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)

MENU_ITEMS = ["Load Game", "Quit to Start"]


class GameOverView:
    """Game Over screen with brief stats summary and load/quit options."""

    def __init__(self, screen, font, player, has_saves=False, portrait_path=None):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 64)
        self.small_font = pygame.font.Font(None, 24)
        self.player = player
        self.has_saves = has_saves
        self.selected_index = 0
        self.bg_image = None

        if portrait_path and os.path.exists(portrait_path):
            try:
                img = pygame.image.load(portrait_path)
                self.bg_image = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception:
                pass

    def draw(self):
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(BLACK)

        # Title
        title = self.title_font.render("GAME OVER", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 100))

        # Death message
        name = self.player.name
        cls_name = self.player.player_class.name if self.player.player_class else "Adventurer"
        msg = self.font.render(f"{name} the {cls_name} has fallen.", True, TEXT_COLOR)
        self.screen.blit(msg, ((SCREEN_WIDTH - msg.get_width()) // 2, 180))

        # Brief stats
        stats = [
            f"Level: {self.player.level}",
            f"Quests Completed: {len(self.player.completed_quests)}",
            f"Quests Failed: {len(self.player.failed_quests)}",
        ]
        y = 240
        for line in stats:
            surf = self.small_font.render(line, True, TEXT_COLOR)
            self.screen.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2, y))
            y += 28

        # Menu options
        y = SCREEN_HEIGHT // 2 + 60
        for i, item in enumerate(MENU_ITEMS):
            disabled = (item == "Load Game" and not self.has_saves)
            if disabled:
                color = (80, 80, 80)
            elif i == self.selected_index:
                color = SELECTED_COLOR
            else:
                color = UNSELECTED_COLOR
            prefix = "> " if i == self.selected_index else "  "
            surf = self.font.render(f"{prefix}{item}", True, color)
            self.screen.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2, y))
            y += 40

    def handle_input(self, event) -> str | None:
        """Returns 'load' or 'quit_to_start', or None."""
        if event.key == pygame.K_UP:
            self.selected_index = (self.selected_index - 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.selected_index = (self.selected_index + 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_RETURN:
            selected = MENU_ITEMS[self.selected_index]
            if selected == "Load Game" and not self.has_saves:
                return None
            if selected == "Load Game":
                return "load"
            if selected == "Quit to Start":
                return "quit_to_start"
        return None
