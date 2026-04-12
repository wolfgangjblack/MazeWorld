"""Room intro screen — full-screen environment portrait + story text overlay."""

import os
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK


TITLE_COLOR = (220, 180, 60)
TEXT_COLOR = (200, 200, 200)
HINT_COLOR = (150, 150, 150)
SCROLL_STEP = 24


def _wrap_text(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    """Word-wrap text into lines that fit within max_w pixels."""
    words = text.split()
    lines: list[str] = []
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
    return lines


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
        self.scroll_offset = 0

        if portrait_path and os.path.exists(portrait_path):
            try:
                img = pygame.image.load(portrait_path)
                self.bg_image = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception:
                pass

        # Pre-compute wrapped lines
        self._box_x = 40
        self._box_w = SCREEN_WIDTH - 80
        self._text_pad = 15
        text_area_w = self._box_w - 2 * self._text_pad
        self._lines = _wrap_text(story_text, font, text_area_w)
        self._line_h = font.get_linesize()

    def draw(self):
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(BLACK)

        # Title
        title = self.title_font.render(self.env_name, True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, SCREEN_HEIGHT // 4))

        subtitle = self.font.render(f"A {self.env_type} awaits...", True, TEXT_COLOR)
        self.screen.blit(subtitle, ((SCREEN_WIDTH - subtitle.get_width()) // 2, SCREEN_HEIGHT // 4 + 60))

        # Dialogue box
        box_h = 200
        box_y = SCREEN_HEIGHT - box_h - 30
        box_x = self._box_x
        box_w = self._box_w

        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill((20, 20, 40, 200))
        self.screen.blit(panel, (box_x, box_y))
        pygame.draw.rect(self.screen, (80, 80, 120), (box_x, box_y, box_w, box_h), 2)

        # Scrollable text inside box
        text_x = box_x + self._text_pad
        text_area_h = box_h - 2 * self._text_pad
        total_text_h = len(self._lines) * self._line_h
        max_scroll = max(0, total_text_h - text_area_h)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        clip_rect = pygame.Rect(box_x + 2, box_y + self._text_pad,
                                box_w - 4, text_area_h)
        self.screen.set_clip(clip_rect)

        y = box_y + self._text_pad - self.scroll_offset
        for line_text in self._lines:
            if y + self._line_h > box_y and y < box_y + box_h:
                surf = self.font.render(line_text, True, TEXT_COLOR)
                self.screen.blit(surf, (text_x, y))
            y += self._line_h

        self.screen.set_clip(None)

        # Scroll indicators inside box
        if self.scroll_offset > 0:
            arrow = self.small_font.render("\u25b2", True, HINT_COLOR)
            self.screen.blit(arrow, (box_x + box_w - 20, box_y + 4))
        if self.scroll_offset < max_scroll:
            arrow = self.small_font.render("\u25bc", True, HINT_COLOR)
            self.screen.blit(arrow, (box_x + box_w - 20, box_y + box_h - 18))

        # Footer hint
        hint_parts = ["Press Enter to continue..."]
        if max_scroll > 0:
            hint_parts.append("Up/Down to scroll")
        hint = self.small_font.render("  |  ".join(hint_parts), True, HINT_COLOR)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 20))

    def handle_input(self, event) -> bool:
        """Returns True when the player wants to proceed."""
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return True
        if event.key == pygame.K_UP:
            self.scroll_offset = max(0, self.scroll_offset - SCROLL_STEP)
        elif event.key == pygame.K_DOWN:
            self.scroll_offset += SCROLL_STEP
        return False
