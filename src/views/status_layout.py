"""Shared character status layout used by class detail and in-game status views.

Layout (per wireframe):
  Top row:    Portrait (left, 200px)  |  Stats block (right)
  Middle:     Description + Weapon info (full width)
  Bottom:     Abilities + Spells list (full width, scrollable)
"""

import pygame

from config import SCREEN_WIDTH
from src.utils.text_utils import draw_wrapped_text

TITLE_COLOR = (220, 180, 60)
STAT_COLOR = (140, 200, 140)
SPELL_COLOR = (140, 160, 220)
ABILITY_COLOR = (220, 160, 140)
COST_COLOR = (180, 120, 80)
DIM_COLOR = (150, 150, 150)
WHITE = (255, 255, 255)
UNSELECTED_COLOR = (180, 180, 180)
SECTION_BG = (25, 25, 40)
SECTION_BORDER = (60, 60, 80)

STAT_NAMES = ["STR", "DEX", "CON", "INT", "WIS", "CHA", "LUCK"]


def truncate_to_fit(text: str, font: pygame.font.Font, max_w: int) -> str:
    """Truncate text with '...' so it fits within max_w pixels."""
    if font.size(text)[0] <= max_w:
        return text
    while len(text) > 0 and font.size(text + "...")[0] > max_w:
        text = text[:-1]
    return text + "..."


def draw_status_layout(screen, font, small_font, tiny_font,
                       portrait_surface, stats, flavor_text,
                       weapon_name, weapon_info, abilities, spells,
                       base_y, pad=20):
    """Draw the wireframe layout and return total content height.

    Parameters
    ----------
    portrait_surface : pygame.Surface or None
    stats : object with .STR, .DEX, etc and .modifier(), .total()
    flavor_text : str
    weapon_name : str
    weapon_info : str  (e.g. "Heavy | 1d8 | STR")
    abilities : list of objects with .name, .description, .stat, .stamina_cost
    spells : list of objects with .name, .description, .spell_type, .element,
             .damage_dice, .stamina_cost, .targets, .stat
    base_y : int — top of the content area (scrolled)
    pad : int — horizontal padding
    """
    full_w = SCREEN_WIDTH - 2 * pad
    y = base_y

    # ── TOP ROW: Portrait + Stats ──
    portrait_size = 180
    top_row_h = portrait_size + 10

    # Portrait
    if portrait_surface:
        scaled = pygame.transform.scale(portrait_surface, (portrait_size, portrait_size))
        screen.blit(scaled, (pad, y))
    else:
        pygame.draw.rect(screen, (40, 40, 60), (pad, y, portrait_size, portrait_size))

    # Stats (right of portrait)
    stats_x = pad + portrait_size + pad
    sy = y
    stats_title = font.render("Stats", True, STAT_COLOR)
    screen.blit(stats_title, (stats_x, sy))
    sy += 26
    for stat in STAT_NAMES:
        val = getattr(stats, stat, 10)
        mod = stats.modifier(stat) if hasattr(stats, 'modifier') else (val - 10) // 2
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        line = small_font.render(f"{stat}: {val} ({mod_str})", True, STAT_COLOR)
        screen.blit(line, (stats_x, sy))
        sy += 20
    total_val = stats.total() if hasattr(stats, 'total') else sum(getattr(stats, s, 10) for s in STAT_NAMES)
    total = small_font.render(f"Total: {total_val}/95", True, UNSELECTED_COLOR)
    screen.blit(total, (stats_x, sy))

    y += top_row_h

    # ── MIDDLE: Description + Weapon ──
    sep_y = y
    pygame.draw.line(screen, SECTION_BORDER, (pad, sep_y), (pad + full_w, sep_y))
    y += 8

    if flavor_text:
        y = draw_wrapped_text(screen, flavor_text, pad, y, full_w, small_font, UNSELECTED_COLOR)
        y += 6

    if weapon_name:
        wpn = font.render(f"Weapon: {weapon_name}", True, ABILITY_COLOR)
        screen.blit(wpn, (pad, y))
        y += 24
        if weapon_info:
            info = small_font.render(weapon_info, True, COST_COLOR)
            screen.blit(info, (pad + 12, y))
            y += 20

    y += 6
    pygame.draw.line(screen, SECTION_BORDER, (pad, y), (pad + full_w, y))
    y += 8

    # ── BOTTOM: Abilities + Spells ──
    if abilities:
        ab_title = font.render("Abilities", True, ABILITY_COLOR)
        screen.blit(ab_title, (pad, y))
        y += 24
        for ab in abilities:
            name_surf = small_font.render(f"\u2022 {ab.name}", True, ABILITY_COLOR)
            screen.blit(name_surf, (pad + 8, y))
            meta_parts = [f"Stat: {ab.stat}"]
            if ab.stamina_cost:
                meta_parts.append(f"Cost: {ab.stamina_cost}")
            meta = tiny_font.render("  |  ".join(meta_parts), True, COST_COLOR)
            screen.blit(meta, (pad + full_w - meta.get_width(), y + 2))
            y += 20
            y = draw_wrapped_text(screen, ab.description, pad + 20, y,
                                  full_w - 20, tiny_font, DIM_COLOR)
            y += 6
        y += 4

    if spells:
        sp_title = font.render("Spells", True, SPELL_COLOR)
        screen.blit(sp_title, (pad, y))
        y += 24
        for sp in spells:
            name_surf = small_font.render(f"\u2022 {sp.name}", True, SPELL_COLOR)
            screen.blit(name_surf, (pad + 8, y))
            meta_parts = [sp.spell_type.replace("_", " ").title()]
            if sp.element:
                meta_parts.append(sp.element.title())
            meta_parts.append(f"Stat: {sp.stat}")
            if sp.damage_dice and sp.spell_type.startswith("damage"):
                meta_parts.append(f"d{sp.damage_dice}")
            if sp.stamina_cost:
                meta_parts.append(f"Cost: {sp.stamina_cost}")
            if sp.targets:
                meta_parts.append(f"Targets: {sp.targets}")
            meta = tiny_font.render("  |  ".join(meta_parts), True, COST_COLOR)
            screen.blit(meta, (pad + full_w - meta.get_width(), y + 2))
            y += 20
            y = draw_wrapped_text(screen, sp.description, pad + 20, y,
                                  full_w - 20, tiny_font, DIM_COLOR)
            y += 6

    return y - base_y


def estimate_status_height(stats, flavor_text, weapon_name,
                           abilities, spells, full_w=760):
    """Estimate total content height for scroll calculation."""
    h = 190  # portrait row
    if flavor_text:
        chars_per_line = max(1, full_w // 7)
        lines = max(1, (len(flavor_text) + chars_per_line - 1) // chars_per_line)
        h += lines * 18 + 6
    if weapon_name:
        h += 44 + 14
    h += 22  # separators
    if abilities:
        h += 24
        for ab in abilities:
            h += 20 + 6
            desc_lines = max(1, len(ab.description) // (full_w // 7) + 1)
            h += desc_lines * 16
        h += 4
    if spells:
        h += 24
        for sp in spells:
            h += 20 + 6
            desc_lines = max(1, len(sp.description) // (full_w // 7) + 1)
            h += desc_lines * 16
    return h
