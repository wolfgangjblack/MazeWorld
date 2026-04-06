"""Room intro screen — full-screen environment portrait + story text overlay."""

import os
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK


TITLE_COLOR = (220, 180, 60)
TEXT_COLOR = (200, 200, 200)
PANEL_BG = (0, 0, 0, 180)  # semi-transparent


class RoomIntroView:
    """Renders room entry intro: environment art + dialogue box with story text."""

    def __init__(self, screen, font, env_name: str, env_type: str,
                 story_text: str, portrait_path: str | None = None):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 24)
        self.env_name = env_name
        self.env_type = env_type
        self.story_text = story_text
        self.bg_image = None
        self.done = False

        if portrait_path and os.path.exists(portrait_path):
            try:
                img = pygame.image.load(portrait_path)
                self.bg_image = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception:
                pass

    def draw(self):
        # Background: environment portrait or dark fill
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
            # Darken overlay for readability
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(BLACK)

        # Title: environment name
        title = self.title_font.render(self.env_name, True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, SCREEN_HEIGHT // 4))

        subtitle = self.font.render(f"A {self.env_type} awaits...", True, TEXT_COLOR)
        self.screen.blit(subtitle, ((SCREEN_WIDTH - subtitle.get_width()) // 2, SCREEN_HEIGHT // 4 + 60))

        # Dialogue box overlay at bottom
        box_h = 200
        box_y = SCREEN_HEIGHT - box_h - 20
        box_x = 40
        box_w = SCREEN_WIDTH - 80

        # Semi-transparent panel
        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill((20, 20, 40, 200))
        self.screen.blit(panel, (box_x, box_y))
        pygame.draw.rect(self.screen, (80, 80, 120), (box_x, box_y, box_w, box_h), 2)

        # Story text wrapped
        self._draw_wrapped_text(
            self.story_text, box_x + 15, box_y + 15,
            box_w - 30, self.font, TEXT_COLOR
        )

        # Continue hint
        hint = self.small_font.render("Press Enter to continue...", True, (150, 150, 150))
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 15))

    def handle_input(self, event) -> bool:
        """Returns True when the player wants to proceed."""
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return True
        return False

    def _draw_wrapped_text(self, text, x, y, max_w, font, color):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if font.size(test)[0] <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        for i, line in enumerate(lines):
            surface = font.render(line, True, color)
            self.screen.blit(surface, (x, y + i * font.get_linesize()))
