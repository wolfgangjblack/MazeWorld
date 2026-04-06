"""Tutorial screen — controls reference card accessible from the start menu."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK
from src.views.pause_view import CONTROLS_TEXT

TITLE_COLOR = (220, 180, 60)
TEXT_COLOR = (200, 200, 200)
HINT_COLOR = (120, 120, 120)
SECTION_COLOR = (180, 160, 80)


class TutorialView:
    """Full-screen controls reference card with keybindings and basic mechanics."""

    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 24)

    def draw(self):
        self.screen.fill(BLACK)

        # Title
        title = self.title_font.render("Controls & Mechanics", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 40))

        # Controls reference (from pause_view)
        y = 110
        for line in CONTROLS_TEXT:
            if not line:
                y += 10
                continue
            # Section headers (lines ending with ':')
            if line.endswith(":"):
                color = SECTION_COLOR
            else:
                color = TEXT_COLOR
            surf = self.small_font.render(line, True, color)
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - 160, y))
            y += 24

        # Additional mechanics section
        y += 16
        self._draw_section("Gameplay Tips:", y)
        y += 28
        tips = [
            "Explore each room to find items, NPCs, and quests.",
            "Keep hunger and thirst above 0 or you'll lose HP.",
            "Talk to NPCs for quests, lore, and trading.",
            "Clear encounters to unlock the gate to the next room.",
            "Use M to open the full menu with stats and spells.",
            "Press B during gameplay to review the story so far.",
        ]
        for tip in tips:
            surf = self.small_font.render(tip, True, TEXT_COLOR)
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - 160, y))
            y += 24

        # Footer
        hint = self.small_font.render("Press Esc or Enter to return", True, HINT_COLOR)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 40))

    def _draw_section(self, text: str, y: int):
        surf = self.small_font.render(text, True, SECTION_COLOR)
        self.screen.blit(surf, (SCREEN_WIDTH // 2 - 160, y))

    def handle_input(self, event) -> str | None:
        """Returns 'back' on Esc or Enter."""
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            return "back"
        return None
