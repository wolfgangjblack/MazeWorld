"""Credits screen — accessible from the start menu."""

import pygame

from config import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH

TITLE_COLOR = (220, 180, 60)
TEXT_COLOR = (200, 200, 200)
HINT_COLOR = (120, 120, 120)
ROLE_COLOR = (180, 160, 80)
NAME_COLOR = (255, 255, 255)

TITLE_HEIGHT = 80
FOOTER_HEIGHT = 50
SCROLL_STEP = 24


def build_credits_lines() -> list[tuple[str, str]]:
    """Build credits as (text, style) tuples. Style: 'role', 'name', 'blank', 'heading'.

    Reads config to determine which models/providers were used, so the credits
    reflect the actual generation setup.
    """
    from config import (
        ANTHROPIC_MODEL,
        FAL_MODEL,
        GAME_MODE,
        IMAGE_BACKEND,
        LLM_BACKEND,
        LLM_MODEL_PATH,
        LOCAL_IMAGE_MODEL_MPS,
        MUSIC_BACKEND,
    )

    lines: list[tuple[str, str]] = []

    lines.append(("MazeWorld", "heading"))
    lines.append(("", "blank"))

    lines.append(("Game Creator", "role"))
    lines.append(("Wolfgang Black", "name"))
    lines.append(("", "blank"))

    lines.append(("Writer", "role"))
    lines.append(("Wolfgang Black", "name"))
    lines.append(("", "blank"))

    lines.append(("Director", "role"))
    lines.append(("Wolfgang Black", "name"))
    lines.append(("", "blank"))

    lines.append(("Producer", "role"))
    lines.append(("Wolfgang Black", "name"))
    lines.append(("", "blank"))
    lines.append(("", "blank"))

    lines.append(("— Technology —", "heading"))
    lines.append(("", "blank"))

    lines.append(("Game Engine", "role"))
    lines.append(("Pygame", "name"))
    lines.append(("", "blank"))

    lines.append(("Story & Content Generation", "role"))
    if LLM_BACKEND == "api":
        lines.append((f"Anthropic Claude ({ANTHROPIC_MODEL})", "name"))
    else:
        model_name = LLM_MODEL_PATH.split("/")[-1] if "/" in LLM_MODEL_PATH else LLM_MODEL_PATH
        lines.append((f"HuggingFace Transformers ({model_name})", "name"))
    lines.append(("", "blank"))

    lines.append(("Portrait & Image Generation", "role"))
    if IMAGE_BACKEND == "api":
        lines.append((f"fal.ai ({FAL_MODEL})", "name"))
    else:
        lines.append((f"Stable Diffusion ({LOCAL_IMAGE_MODEL_MPS})", "name"))
    lines.append(("", "blank"))

    if MUSIC_BACKEND == "api":
        lines.append(("Music Generation", "role"))
        lines.append(("Google Lyria 3", "name"))
        lines.append(("", "blank"))

        lines.append(("Sound Effects", "role"))
        lines.append(("ElevenLabs", "name"))
        lines.append(("", "blank"))

    lines.append(("", "blank"))
    lines.append(("— Runtime —", "heading"))
    lines.append(("", "blank"))

    mode_labels = {
        "online": "Online (Live AI)",
        "offline_local": "Offline (Local Models)",
        "offline_static": "Offline (Pre-generated)",
    }
    lines.append(("Game Mode", "role"))
    lines.append((mode_labels.get(GAME_MODE, GAME_MODE), "name"))
    lines.append(("", "blank"))

    if GAME_MODE == "online":
        lines.append(("Runtime Dialogue", "role"))
        lines.append(("Anthropic Claude", "name"))
        lines.append(("", "blank"))
    elif GAME_MODE == "offline_local":
        lines.append(("Runtime Dialogue", "role"))
        model_name = LLM_MODEL_PATH.split("/")[-1] if "/" in LLM_MODEL_PATH else LLM_MODEL_PATH
        lines.append((f"HuggingFace ({model_name})", "name"))
        lines.append(("", "blank"))

    lines.append(("", "blank"))
    lines.append(("Thank you for playing!", "heading"))
    lines.append(("", "blank"))

    return lines


class CreditsView:
    """Full-screen scrollable credits display."""

    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 56)
        self.heading_font = pygame.font.Font(None, 44)
        self.role_font = pygame.font.Font(None, 28)
        self.name_font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.scroll_offset = 0
        self.lines = build_credits_lines()

    def _line_height(self, style: str) -> int:
        if style == "heading":
            return 44
        if style == "role":
            return 28
        if style == "name":
            return 36
        return 16

    def _get_total_height(self) -> int:
        total = 0
        for _, style in self.lines:
            total += self._line_height(style) + 4
        return total

    def draw(self):
        self.screen.fill(BLACK)

        viewport_top = 20
        viewport_bottom = SCREEN_HEIGHT - FOOTER_HEIGHT
        viewport_h = viewport_bottom - viewport_top

        total_h = self._get_total_height()
        max_scroll = max(0, total_h - viewport_h)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        clip_rect = pygame.Rect(0, viewport_top, SCREEN_WIDTH, viewport_h)
        self.screen.set_clip(clip_rect)

        y = viewport_top - self.scroll_offset + 20

        for text, style in self.lines:
            h = self._line_height(style)

            if viewport_top - h <= y <= viewport_bottom:
                if style == "heading":
                    color = TITLE_COLOR
                    fnt = self.heading_font
                elif style == "role":
                    color = ROLE_COLOR
                    fnt = self.role_font
                elif style == "name":
                    color = NAME_COLOR
                    fnt = self.name_font
                else:
                    color = TEXT_COLOR
                    fnt = self.small_font

                if text:
                    surf = fnt.render(text, True, color)
                    self.screen.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2, y))

            y += h + 4

        self.screen.set_clip(None)

        if self.scroll_offset > 0:
            arrow = self.small_font.render("▲", True, HINT_COLOR)
            self.screen.blit(arrow, ((SCREEN_WIDTH - arrow.get_width()) // 2, viewport_top))
        if self.scroll_offset < max_scroll:
            arrow = self.small_font.render("▼", True, HINT_COLOR)
            self.screen.blit(arrow, ((SCREEN_WIDTH - arrow.get_width()) // 2, viewport_bottom - 20))

        hint = self.small_font.render("Press Esc or Enter to return  |  Up/Down to scroll", True, HINT_COLOR)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 35))

    def handle_input(self, event) -> str | None:
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            return "back"
        if event.key == pygame.K_UP:
            self.scroll_offset = max(0, self.scroll_offset - SCROLL_STEP)
        elif event.key == pygame.K_DOWN:
            self.scroll_offset += SCROLL_STEP
        return None
