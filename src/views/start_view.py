"""Start screen — New Game, Load Game, Config, Quit."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK


MENU_ITEMS = ["Start New Game", "Load Game", "Config", "Quit"]

# Colors
TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
DISABLED_COLOR = (80, 80, 80)


class StartView:
    """Renders the start menu and handles selection state."""

    def __init__(self, screen, font, has_saves=False):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 64)
        self.selected_index = 0
        self.has_saves = has_saves

    def draw(self):
        self.screen.fill(BLACK)

        # Title
        title_surface = self.title_font.render("MazeWorld", True, TITLE_COLOR)
        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, SCREEN_HEIGHT // 4))

        # Menu items
        line_height = self.font.get_linesize()
        start_y = SCREEN_HEIGHT // 2
        for i, item in enumerate(MENU_ITEMS):
            disabled = self._is_disabled(i)
            if disabled:
                color = DISABLED_COLOR
            elif i == self.selected_index:
                color = SELECTED_COLOR
            else:
                color = UNSELECTED_COLOR
            prefix = "> " if i == self.selected_index else "  "
            text_surface = self.font.render(f"{prefix}{item}", True, color)
            text_x = (SCREEN_WIDTH - text_surface.get_width()) // 2
            self.screen.blit(text_surface, (text_x, start_y + i * (line_height + 10)))

        # Footer hint
        selected_item = MENU_ITEMS[self.selected_index]
        if self._is_disabled(self.selected_index):
            if selected_item == "Load Game":
                hint_text = "(no save files found)"
            else:
                hint_text = "(coming soon)"
        else:
            hint_text = {
                "Start New Game": "Press Enter to begin",
                "Load Game": "Continue a saved game",
                "Config": "View and edit settings",
                "Quit": "Exit the game",
            }.get(selected_item, "")

        if hint_text:
            hint = self.font.render(hint_text, True, (120, 120, 120))
            hint_x = (SCREEN_WIDTH - hint.get_width()) // 2
            self.screen.blit(hint, (hint_x, start_y + len(MENU_ITEMS) * (line_height + 10) + 20))

    def _is_disabled(self, index: int) -> bool:
        item = MENU_ITEMS[index]
        if item == "Load Game" and not self.has_saves:
            return True
        return False

    def handle_input(self, event) -> str | None:
        """Process a keydown event. Returns an action string or None.

        Actions: "new_game", "load_game", "config", "quit", or None.
        """
        if event.key == pygame.K_UP:
            self.selected_index = (self.selected_index - 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.selected_index = (self.selected_index + 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_RETURN:
            if self._is_disabled(self.selected_index):
                return None
            selected = MENU_ITEMS[self.selected_index]
            if selected == "Start New Game":
                return "new_game"
            elif selected == "Load Game":
                return "load_game"
            elif selected == "Config":
                return "config"
            elif selected == "Quit":
                return "quit"
        return None
