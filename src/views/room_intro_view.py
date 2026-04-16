"""Room intro screen — full-screen environment portrait + story text overlay."""

import os

import pygame

from config import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH, resolve_data_path

TITLE_COLOR = (220, 180, 60)
TEXT_COLOR = (200, 200, 200)
SCROLL_ARROW_COLOR = (150, 150, 180)


def _wrap_lines(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    """Word-wrap *text* at *max_w* pixels. Returns list of line strings."""
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

    def __init__(self, screen, font, env_name: str, env_type: str, story_text: str, portrait_path: str | None = None):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 24)
        self.env_name = env_name
        self.env_type = env_type
        self.bg_image = None
        self.scroll_offset = 0

        self._box_h = 200
        self._box_x = 40
        self._box_w = SCREEN_WIDTH - 80
        self._text_max_w = self._box_w - 30
        self._lines = _wrap_lines(story_text, font, self._text_max_w)
        self._line_h = font.get_linesize()
        self._max_visible = max(1, (self._box_h - 30) // self._line_h)

        resolved_portrait = resolve_data_path(portrait_path)
        if resolved_portrait and os.path.exists(resolved_portrait):
            try:
                img = pygame.image.load(resolved_portrait)
                self.bg_image = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception:
                pass

    def draw(self):
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(BLACK)

        title = self.title_font.render(self.env_name, True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, SCREEN_HEIGHT // 4))

        subtitle = self.font.render(f"A {self.env_type} awaits...", True, TEXT_COLOR)
        self.screen.blit(subtitle, ((SCREEN_WIDTH - subtitle.get_width()) // 2, SCREEN_HEIGHT // 4 + 60))

        box_y = SCREEN_HEIGHT - self._box_h - 20

        panel = pygame.Surface((self._box_w, self._box_h), pygame.SRCALPHA)
        panel.fill((20, 20, 40, 200))
        self.screen.blit(panel, (self._box_x, box_y))
        pygame.draw.rect(self.screen, (80, 80, 120), (self._box_x, box_y, self._box_w, self._box_h), 2)

        text_x = self._box_x + 15
        text_y = box_y + 15
        clip_rect = pygame.Rect(self._box_x, box_y, self._box_w, self._box_h)
        self.screen.set_clip(clip_rect)

        visible = self._lines[self.scroll_offset : self.scroll_offset + self._max_visible]
        for line in visible:
            surf = self.font.render(line, True, TEXT_COLOR)
            self.screen.blit(surf, (text_x, text_y))
            text_y += self._line_h

        self.screen.set_clip(None)

        if self.scroll_offset > 0:
            arrow = self.small_font.render("^", True, SCROLL_ARROW_COLOR)
            self.screen.blit(arrow, (self._box_x + self._box_w - 20, box_y + 4))
        if self.scroll_offset + self._max_visible < len(self._lines):
            arrow = self.small_font.render("v", True, SCROLL_ARROW_COLOR)
            self.screen.blit(arrow, (self._box_x + self._box_w - 20, box_y + self._box_h - 18))

        hint_parts = []
        if len(self._lines) > self._max_visible:
            hint_parts.append("Up/Down to scroll")
        hint_parts.append("Enter to continue...")
        hint = self.small_font.render("  |  ".join(hint_parts), True, (150, 150, 150))
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 15))

    def handle_input(self, event) -> bool:
        """Returns True when the player wants to proceed."""
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return True
        max_scroll = max(0, len(self._lines) - self._max_visible)
        if event.key == pygame.K_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif event.key == pygame.K_DOWN:
            self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
        return False
