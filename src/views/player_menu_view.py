"""Player menu screen — Save and Load options during gameplay.

Opened with Tab key during normal gameplay (not during combat/events).
"""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

MENU_ITEMS = ["Save Game", "Load Game", "Back"]

TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
DISABLED_COLOR = (80, 80, 80)
STATUS_COLOR = (100, 200, 100)
ERROR_COLOR = (200, 100, 100)


class PlayerMenuView:
    """Minimal player menu with Save / Load / Back."""

    def __init__(self, screen, font, can_save=True, has_saves=False):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.selected_index = 0
        self.can_save = can_save
        self.has_saves = has_saves
        self.status_message = ""
        self.status_is_error = False

    def set_status(self, message: str, is_error: bool = False):
        self.status_message = message
        self.status_is_error = is_error

    def draw(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))

        # Title
        title_surface = self.title_font.render("Menu", True, TITLE_COLOR)
        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, SCREEN_HEIGHT // 4))

        # Menu items
        line_height = self.font.get_linesize()
        start_y = SCREEN_HEIGHT // 2 - 30

        for i, item in enumerate(MENU_ITEMS):
            disabled = self._is_disabled(i)
            if disabled:
                color = DISABLED_COLOR
            elif i == self.selected_index:
                color = SELECTED_COLOR
            else:
                color = UNSELECTED_COLOR

            prefix = "> " if i == self.selected_index else "  "
            label = item
            if disabled:
                if item == "Save Game":
                    label += " (in combat)"
                elif item == "Load Game":
                    label += " (no saves)"
            text_surface = self.font.render(f"{prefix}{label}", True, color)
            text_x = (SCREEN_WIDTH - text_surface.get_width()) // 2
            self.screen.blit(
                text_surface,
                (text_x, start_y + i * (line_height + 10)),
            )

        # Status message
        if self.status_message:
            msg_color = ERROR_COLOR if self.status_is_error else STATUS_COLOR
            msg_surface = self.font.render(self.status_message, True, msg_color)
            msg_x = (SCREEN_WIDTH - msg_surface.get_width()) // 2
            self.screen.blit(
                msg_surface,
                (msg_x, start_y + len(MENU_ITEMS) * (line_height + 10) + 20),
            )

        # Hint
        hint_text = "Tab/Esc: Close"
        hint_surface = self.font.render(hint_text, True, (100, 100, 100))
        self.screen.blit(hint_surface, (10, SCREEN_HEIGHT - 30))

    def _is_disabled(self, index: int) -> bool:
        item = MENU_ITEMS[index]
        if item == "Save Game" and not self.can_save:
            return True
        if item == "Load Game" and not self.has_saves:
            return True
        return False

    def handle_input(self, event) -> str | None:
        """Process keydown. Returns: 'save', 'load', 'back', or None."""
        if event.key in (pygame.K_TAB, pygame.K_ESCAPE):
            return "back"

        if event.key == pygame.K_UP:
            self.selected_index = (self.selected_index - 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.selected_index = (self.selected_index + 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_RETURN:
            if self._is_disabled(self.selected_index):
                return None
            selected = MENU_ITEMS[self.selected_index]
            if selected == "Save Game":
                return "save"
            elif selected == "Load Game":
                return "load"
            elif selected == "Back":
                return "back"
        return None
