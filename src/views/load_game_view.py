"""Load game screen — shows save file list for selection.

Used both from the start screen and from the player menu.
"""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
HEADER_COLOR = (150, 150, 200)
ERROR_COLOR = (200, 100, 100)


def _format_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS."""
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


class LoadGameView:
    """Renders the save file list and handles selection."""

    def __init__(self, screen, font, saves: list[dict]):
        """
        saves: list of dicts from save_manager.list_saves(), each with:
            filepath, character_name, character_class, room_level,
            time_played_seconds, last_save_date, seed
        """
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)
        self.saves = saves
        self.selected_index = 0
        self.error_message = ""
        self.scroll_offset = 0
        self.max_visible = 6

    def draw(self):
        self.screen.fill(BLACK)

        # Title
        title_surface = self.title_font.render("Load Game", True, TITLE_COLOR)
        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, 30))

        if not self.saves:
            no_saves = self.font.render(
                "No save files found.", True, (120, 120, 120),
            )
            x = (SCREEN_WIDTH - no_saves.get_width()) // 2
            self.screen.blit(no_saves, (x, SCREEN_HEIGHT // 2))
            hint = self.font.render(
                "Esc: Back", True, (100, 100, 100),
            )
            self.screen.blit(hint, (10, SCREEN_HEIGHT - 30))
            return

        # Column header
        header = "  Name              Class           Level   Time      Saved"
        header_surface = self.small_font.render(header, True, HEADER_COLOR)
        self.screen.blit(header_surface, (40, 80))

        # Draw separator
        pygame.draw.line(
            self.screen, HEADER_COLOR, (40, 100), (SCREEN_WIDTH - 40, 100),
        )

        # Save entries
        line_height = 50
        start_y = 110
        visible_saves = self.saves[
            self.scroll_offset:self.scroll_offset + self.max_visible
        ]

        for i, save in enumerate(visible_saves):
            actual_idx = i + self.scroll_offset
            selected = actual_idx == self.selected_index
            color = SELECTED_COLOR if selected else UNSELECTED_COLOR
            prefix = "> " if selected else "  "

            name = save["character_name"][:16].ljust(16)
            cls = save["character_class"][:14].ljust(14)
            level = f"Rm {save['room_level']}".ljust(8)
            time_str = _format_time(save["time_played_seconds"]).ljust(10)
            date = save["last_save_date"]

            line = f"{prefix}{name}  {cls}  {level}{time_str}{date}"
            text_surface = self.font.render(line, True, color)
            self.screen.blit(text_surface, (30, start_y + i * line_height))

            # Seed info on second line if selected
            if selected:
                seed_text = f"   Seed: {save['seed']}"
                seed_surface = self.small_font.render(
                    seed_text, True, (100, 100, 100),
                )
                self.screen.blit(
                    seed_surface,
                    (50, start_y + i * line_height + 25),
                )

        # Scroll indicators
        if self.scroll_offset > 0:
            arrow = self.font.render("^ more saves above", True, (100, 100, 100))
            self.screen.blit(arrow, (SCREEN_WIDTH // 2 - 80, start_y - 20))
        if self.scroll_offset + self.max_visible < len(self.saves):
            arrow = self.font.render(
                "v more saves below", True, (100, 100, 100),
            )
            self.screen.blit(
                arrow,
                (SCREEN_WIDTH // 2 - 80,
                 start_y + self.max_visible * line_height + 5),
            )

        # Error message
        if self.error_message:
            err = self.font.render(self.error_message, True, ERROR_COLOR)
            err_x = (SCREEN_WIDTH - err.get_width()) // 2
            self.screen.blit(err, (err_x, SCREEN_HEIGHT - 70))

        # Hints
        hint_text = "Enter: Load  |  Esc: Back"
        hint = self.font.render(hint_text, True, (100, 100, 100))
        self.screen.blit(hint, (10, SCREEN_HEIGHT - 30))

    def handle_input(self, event) -> dict | None:
        """Process keydown. Returns:
        - {"action": "load", "filepath": str, "save": dict} on selection
        - {"action": "back"} on escape
        - None otherwise
        """
        if event.key == pygame.K_ESCAPE:
            return {"action": "back"}

        if not self.saves:
            return None

        if event.key == pygame.K_UP:
            self.selected_index = max(0, self.selected_index - 1)
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
        elif event.key == pygame.K_DOWN:
            self.selected_index = min(
                len(self.saves) - 1, self.selected_index + 1,
            )
            if self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = (
                    self.selected_index - self.max_visible + 1
                )
        elif event.key == pygame.K_RETURN:
            save = self.saves[self.selected_index]
            return {
                "action": "load",
                "filepath": save["filepath"],
                "save": save,
            }
        return None
