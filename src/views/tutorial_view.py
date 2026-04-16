"""Tutorial screen — controls reference card accessible from the start menu."""

import pygame

from config import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH
from src.views.pause_view import CONTROLS_TEXT

TITLE_COLOR = (220, 180, 60)
TEXT_COLOR = (200, 200, 200)
HINT_COLOR = (120, 120, 120)
SECTION_COLOR = (180, 160, 80)

TITLE_HEIGHT = 80
FOOTER_HEIGHT = 50
SCROLL_STEP = 24


class TutorialView:
    """Full-screen controls reference card with keybindings and basic mechanics."""

    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 24)
        self.scroll_offset = 0
        self._content_height = 0

    def _build_lines(self):
        """Return list of (text, color, extra_gap_before) tuples."""
        lines = []
        for line in CONTROLS_TEXT:
            if not line:
                lines.append(("", TEXT_COLOR, 10))
                continue
            color = SECTION_COLOR if line.endswith(":") else TEXT_COLOR
            lines.append((line, color, 0))

        lines.append(("", TEXT_COLOR, 16))
        lines.append(("Gameplay Tips:", SECTION_COLOR, 0))
        lines.append(("", TEXT_COLOR, 4))
        tips = [
            "Explore each room to find items, NPCs, and quests.",
            "Keep stamina above 0 or you'll lose HP.",
            "Talk to NPCs for quests, lore, and trading.",
            "Clear encounters to unlock the gate to the next room.",
            "Use M to open the full menu with stats and spells.",
            "Press B during gameplay to review the story so far.",
        ]
        for tip in tips:
            lines.append((tip, TEXT_COLOR, 0))
        return lines

    def draw(self):
        self.screen.fill(BLACK)

        # Title (fixed, not scrolled)
        title = self.title_font.render("Controls & Mechanics", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 20))

        viewport_top = TITLE_HEIGHT
        viewport_bottom = SCREEN_HEIGHT - FOOTER_HEIGHT
        viewport_h = viewport_bottom - viewport_top

        lines = self._build_lines()

        # Compute total content height
        total_h = 0
        for text, _, gap in lines:
            total_h += gap
            if text:
                total_h += 24
        self._content_height = total_h

        max_scroll = max(0, total_h - viewport_h)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        clip_rect = pygame.Rect(0, viewport_top, SCREEN_WIDTH, viewport_h)
        self.screen.set_clip(clip_rect)

        content_x = SCREEN_WIDTH // 2 - 160
        y = viewport_top - self.scroll_offset
        for text, color, gap in lines:
            y += gap
            if text:
                if viewport_top - 24 <= y <= viewport_bottom:
                    surf = self.small_font.render(text, True, color)
                    self.screen.blit(surf, (content_x, y))
                y += 24

        self.screen.set_clip(None)

        # Scroll indicators
        if self.scroll_offset > 0:
            arrow = self.small_font.render("▲ Scroll up", True, HINT_COLOR)
            self.screen.blit(arrow, ((SCREEN_WIDTH - arrow.get_width()) // 2, viewport_top))
        if self.scroll_offset < max_scroll:
            arrow = self.small_font.render("▼ Scroll down", True, HINT_COLOR)
            self.screen.blit(arrow, ((SCREEN_WIDTH - arrow.get_width()) // 2, viewport_bottom - 20))

        # Footer (fixed)
        hint = self.small_font.render("Press Esc or Enter to return  |  Up/Down to scroll", True, HINT_COLOR)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 35))

    def handle_input(self, event) -> str | None:
        """Returns 'back' on Esc or Enter. Up/Down scrolls."""
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            return "back"
        if event.key == pygame.K_UP:
            self.scroll_offset = max(0, self.scroll_offset - SCROLL_STEP)
        elif event.key == pygame.K_DOWN:
            self.scroll_offset += SCROLL_STEP
        return None
