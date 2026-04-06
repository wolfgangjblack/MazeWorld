"""Pause screen — overlay on gameplay with Resume, Save, Controls, Quit."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
DISABLED_COLOR = (80, 80, 80)
TEXT_COLOR = (200, 200, 200)

MENU_ITEMS = ["Resume", "Save Game", "Controls", "Quit to Start"]

CONTROLS_TEXT = [
    "Arrow Keys  -  Move",
    "Enter       -  Interact / Pick up",
    "Esc         -  Pause / Back",
    "Tab         -  Player Menu",
    "I           -  Inventory",
    "Q           -  Quest Log",
    "S           -  Shop (near merchant)",
    "T           -  Talk to follower",
    "F1          -  Toggle debug view",
    "",
    "Combat:",
    "A           -  Attack",
    "F           -  Flee",
    "I           -  Use item",
    "Up/Down     -  Select target",
]


class PauseView:
    """Pause overlay with Resume, Save, Controls, and Quit options."""

    def __init__(self, screen, font, can_save=True):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 22)
        self.selected_index = 0
        self.can_save = can_save
        self.showing_controls = False
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

        if self.showing_controls:
            self._draw_controls()
            return

        # Title
        title = self.title_font.render("PAUSED", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, SCREEN_HEIGHT // 4))

        # Menu items
        line_height = self.font.get_linesize()
        start_y = SCREEN_HEIGHT // 2 - 40

        for i, item in enumerate(MENU_ITEMS):
            disabled = (item == "Save Game" and not self.can_save)
            if disabled:
                color = DISABLED_COLOR
            elif i == self.selected_index:
                color = SELECTED_COLOR
            else:
                color = UNSELECTED_COLOR

            prefix = "> " if i == self.selected_index else "  "
            label = item
            if disabled:
                label += " (unavailable)"
            surf = self.font.render(f"{prefix}{label}", True, color)
            self.screen.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2,
                                    start_y + i * (line_height + 10)))

        # Status message
        if self.status_message:
            color = (200, 100, 100) if self.status_is_error else (100, 200, 100)
            msg = self.font.render(self.status_message, True, color)
            self.screen.blit(msg, ((SCREEN_WIDTH - msg.get_width()) // 2,
                                   start_y + len(MENU_ITEMS) * (line_height + 10) + 20))

    def _draw_controls(self):
        title = self.title_font.render("CONTROLS", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 60))

        y = 120
        for line in CONTROLS_TEXT:
            if not line:
                y += 10
                continue
            surf = self.small_font.render(line, True, TEXT_COLOR)
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - 150, y))
            y += 24

        hint = self.small_font.render("Press Esc to go back", True, (120, 120, 120))
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 40))

    def handle_input(self, event) -> str | None:
        """Returns 'resume', 'save', 'controls', 'quit_to_start', or None."""
        if self.showing_controls:
            if event.key == pygame.K_ESCAPE:
                self.showing_controls = False
            return None

        if event.key == pygame.K_ESCAPE:
            return "resume"

        if event.key == pygame.K_UP:
            self.selected_index = (self.selected_index - 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.selected_index = (self.selected_index + 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_RETURN:
            selected = MENU_ITEMS[self.selected_index]
            if selected == "Resume":
                return "resume"
            if selected == "Save Game":
                if not self.can_save:
                    return None
                return "save"
            if selected == "Controls":
                self.showing_controls = True
                return None
            if selected == "Quit to Start":
                return "quit_to_start"
        return None
