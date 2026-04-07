"""Shared text-wrapping utility for pygame views."""

import pygame


def draw_wrapped_text(screen: pygame.Surface, text: str, x: int, y: int,
                      max_w: int, font: pygame.font.Font,
                      color: tuple[int, ...]) -> int:
    """Word-wrap *text* at *max_w* pixels and blit to *screen*. Returns final y."""
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
    for line in lines:
        surf = font.render(line, True, color)
        screen.blit(surf, (x, y))
        y += font.get_linesize()
    return y
