"""Quick story screen — overarching story summary + current room intro."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK
from src.utils.text_utils import draw_wrapped_text

TITLE_COLOR = (220, 180, 60)
TEXT_COLOR = (200, 200, 200)
SECTION_COLOR = (180, 160, 80)
HINT_COLOR = (120, 120, 120)

SCROLL_STEP = 20


class StoryView:
    """Overlay showing the overarching story synopsis and current room context."""

    def __init__(self, screen, font, story=None, room_story_beat="",
                 room_name=""):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)
        self.scroll_offset = 0

        self.title = story.title if story else "The Story So Far"
        self.synopsis = story.synopsis if story else "No story data available."
        self.faction_name = (
            story.faction.name if story and story.faction else ""
        )
        self.faction_desc = (
            story.faction.description if story and story.faction else ""
        )
        self.climax = story.climax if story else ""
        self.room_story_beat = room_story_beat
        self.room_name = room_name

    def draw(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(210)
        self.screen.blit(overlay, (0, 0))

        y = 30 - self.scroll_offset

        # Title
        title_surf = self.title_font.render(self.title, True, TITLE_COLOR)
        self.screen.blit(title_surf, ((SCREEN_WIDTH - title_surf.get_width()) // 2, y))
        y += 50

        # Synopsis
        self._draw_section("Synopsis", y)
        y += 24
        y = draw_wrapped_text(self.screen, self.synopsis, 60, y,
                              SCREEN_WIDTH - 120, self.small_font, TEXT_COLOR)
        y += 16

        # Faction
        if self.faction_name:
            self._draw_section(f"Faction: {self.faction_name}", y)
            y += 24
            if self.faction_desc:
                y = draw_wrapped_text(self.screen, self.faction_desc, 60, y,
                                      SCREEN_WIDTH - 120, self.small_font, TEXT_COLOR)
            y += 16

        # What lies ahead
        if self.climax:
            self._draw_section("What Lies Ahead", y)
            y += 24
            y = draw_wrapped_text(self.screen, self.climax, 60, y,
                                  SCREEN_WIDTH - 120, self.small_font, TEXT_COLOR)
            y += 16

        # Current room
        if self.room_story_beat:
            label = f"Current Area: {self.room_name}" if self.room_name else "Current Area"
            self._draw_section(label, y)
            y += 24
            draw_wrapped_text(self.screen, self.room_story_beat, 60, y,
                              SCREEN_WIDTH - 120, self.small_font, TEXT_COLOR)

        # Footer (fixed at bottom, unaffected by scroll)
        hint = self.small_font.render(
            "Up/Down: Scroll  |  Esc/Enter: Return", True, HINT_COLOR)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 30))

    def _draw_section(self, text: str, y: int):
        surf = self.small_font.render(text, True, SECTION_COLOR)
        self.screen.blit(surf, (40, y))

    def handle_input(self, event) -> str | None:
        """Returns 'back' on Esc or Enter. Up/Down scrolls."""
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            return "back"
        if event.key == pygame.K_UP:
            self.scroll_offset = max(0, self.scroll_offset - SCROLL_STEP)
        elif event.key == pygame.K_DOWN:
            self.scroll_offset += SCROLL_STEP
        return None
