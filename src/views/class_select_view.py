"""Class selection screen — pick from 4 generated classes, name character."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE
from src.views.portrait_utils import load_portrait
from src.views.status_layout import (
    draw_status_layout, estimate_status_height, truncate_to_fit,
)


TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
STAT_COLOR = (140, 200, 140)
SPELL_COLOR = (140, 160, 220)

ARCHETYPE_DISPLAY = {"jester": "Wild Card"}
ABILITY_COLOR = (220, 160, 140)
JESTER_HIDDEN_COLOR = (100, 100, 100)
PANEL_BG = (30, 30, 50)
PANEL_BORDER = (80, 80, 120)
CONFIRM_COLOR = (100, 255, 100)
HINT_COLOR = (120, 120, 120)
COST_COLOR = (180, 120, 80)
DIM_COLOR = (150, 150, 150)

STAT_NAMES = ["STR", "DEX", "CON", "INT", "WIS", "CHA", "LUCK"]

STATE_SELECT = "select"
STATE_DETAIL = "detail"
STATE_NAME = "name"
STATE_CONFIRM = "confirm"

DETAIL_SCROLL_STEP = 24
FOOTER_HEIGHT = 40


class ClassSelectView:
    """Renders class selection UI and manages selection flow."""

    def __init__(self, screen, font, class_options):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)
        self.tiny_font = pygame.font.Font(None, 20)
        self.class_options = class_options
        self.selected_index = 0
        self.state = STATE_SELECT
        self.player_name = ""
        self.detail_scroll = 0
        self.portraits = {}
        self._load_portraits()

    def _load_portraits(self):
        for i, pc in enumerate(self.class_options):
            self.portraits[i] = load_portrait(pc.portrait_path, (128, 128))

    # ------------------------------------------------------------------
    # Draw dispatch
    # ------------------------------------------------------------------

    def draw(self):
        self.screen.fill(BLACK)

        if self.state == STATE_SELECT:
            self._draw_selection_grid()
        elif self.state == STATE_DETAIL:
            self._draw_detail_view()
        elif self.state == STATE_NAME:
            self._draw_name_input()
        elif self.state == STATE_CONFIRM:
            self._draw_confirm()

    # ------------------------------------------------------------------
    # Card grid (2x2)
    # ------------------------------------------------------------------

    def _draw_selection_grid(self):
        title = self.title_font.render("Choose Your Class", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 20))

        card_w, card_h = 340, 260
        gap = 20
        start_x = (SCREEN_WIDTH - 2 * card_w - gap) // 2
        start_y = 80

        for i, pc in enumerate(self.class_options):
            col = i % 2
            row = i // 2
            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap)
            self._draw_class_card(x, y, card_w, card_h, pc, i, i == self.selected_index)

        hint = self.small_font.render(
            "Arrow keys to select  |  Enter to view details  |  Esc to go back",
            True, UNSELECTED_COLOR,
        )
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 30))

    def _draw_class_card(self, x, y, w, h, pc, index, selected):
        border_color = SELECTED_COLOR if selected else PANEL_BORDER
        pygame.draw.rect(self.screen, PANEL_BG, (x, y, w, h))
        pygame.draw.rect(self.screen, border_color, (x, y, w, h), 2)

        is_jester = pc.archetype == "jester"
        pad = 10
        portrait_size = 100
        text_right_edge = x + w - pad

        # Portrait
        portrait_rect = pygame.Rect(x + pad, y + pad, portrait_size, portrait_size)
        if is_jester and self.state == STATE_SELECT:
            pygame.draw.rect(self.screen, (20, 20, 20), portrait_rect)
            q_text = self.font.render("???", True, JESTER_HIDDEN_COLOR)
            self.screen.blit(q_text, (
                portrait_rect.x + (portrait_size - q_text.get_width()) // 2,
                portrait_rect.y + (portrait_size - q_text.get_height()) // 2,
            ))
        elif self.portraits.get(index):
            scaled = pygame.transform.scale(self.portraits[index], (portrait_size, portrait_size))
            self.screen.blit(scaled, portrait_rect.topleft)
        else:
            pygame.draw.rect(self.screen, (40, 40, 60), portrait_rect)

        # Text area (right of portrait)
        text_x = x + pad + portrait_size + pad
        text_y = y + pad
        text_max_w = text_right_edge - text_x

        if is_jester and self.state == STATE_SELECT:
            self.screen.blit(self.font.render("???", True, JESTER_HIDDEN_COLOR), (text_x, text_y))
            self.screen.blit(self.small_font.render("A mystery awaits...", True, JESTER_HIDDEN_COLOR),
                             (text_x, text_y + 28))
        else:
            name_color = SELECTED_COLOR if selected else WHITE
            name_surf = self.font.render(pc.name, True, name_color)
            self.screen.blit(name_surf, (text_x, text_y))

            arch_text = self.small_font.render(f"({ARCHETYPE_DISPLAY.get(pc.archetype, pc.archetype.title())})", True, UNSELECTED_COLOR)
            self.screen.blit(arch_text, (text_x, text_y + 26))

            wpn_text = self.tiny_font.render(f"Weapon: {pc.starting_weapon}", True, ABILITY_COLOR)
            self.screen.blit(wpn_text, (text_x, text_y + 46))

            # Truncated flavor text (pixel-accurate)
            flavor = pc.flavor_text
            if flavor:
                line1 = truncate_to_fit(flavor, self.tiny_font, text_max_w)
                surf = self.tiny_font.render(line1, True, DIM_COLOR)
                self.screen.blit(surf, (text_x, text_y + 64))
                if len(line1) < len(flavor) and not line1.endswith("..."):
                    rest = flavor[len(line1):]
                    line2 = truncate_to_fit(rest, self.tiny_font, text_max_w)
                    surf2 = self.tiny_font.render(line2, True, DIM_COLOR)
                    self.screen.blit(surf2, (text_x, text_y + 80))

        # Stats (below portrait, full card width)
        stats_y = y + pad + portrait_size + 8
        card_bottom = y + h - pad
        if not (is_jester and self.state == STATE_SELECT):
            self._draw_stat_bars_mini(x + pad, stats_y, w - 2 * pad, pc, card_bottom)
        else:
            hidden = self.tiny_font.render("Stats hidden until selected", True, JESTER_HIDDEN_COLOR)
            self.screen.blit(hidden, (x + pad, stats_y))

    def _draw_stat_bars_mini(self, x, y, total_w, pc, y_limit):
        bar_h = 8
        gap = 2
        for i, stat in enumerate(STAT_NAMES):
            row_y = y + i * (bar_h + gap)
            if row_y + bar_h > y_limit:
                break
            val = getattr(pc.stats, stat)
            label = self.tiny_font.render(stat[:3], True, STAT_COLOR)
            self.screen.blit(label, (x, row_y))

            bar_x = x + 35
            bar_w = total_w - 60
            pygame.draw.rect(self.screen, (40, 40, 60), (bar_x, row_y, bar_w, bar_h))
            fill_pct = max(0, min(1, (val - 6) / 12))
            fill_w = int(bar_w * fill_pct)
            bar_color = SELECTED_COLOR if val >= 14 else STAT_COLOR if val >= 11 else (160, 80, 80)
            pygame.draw.rect(self.screen, bar_color, (bar_x, row_y, fill_w, bar_h))
            val_text = self.tiny_font.render(str(val), True, WHITE)
            self.screen.blit(val_text, (bar_x + bar_w + 4, row_y - 1))

    # ------------------------------------------------------------------
    # Detail view — wireframe layout (portrait+stats top, desc mid, spells bottom)
    # ------------------------------------------------------------------

    def _draw_detail_view(self):
        pc = self.class_options[self.selected_index]
        pad = 20

        # Title bar (fixed)
        title = self.title_font.render(pc.name, True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 10))
        arch = self.small_font.render(
            f"{ARCHETYPE_DISPLAY.get(pc.archetype, pc.archetype.title())} \u2014 {pc.environment}", True, UNSELECTED_COLOR
        )
        self.screen.blit(arch, ((SCREEN_WIDTH - arch.get_width()) // 2, 48))

        header_h = 72
        viewport_top = header_h
        viewport_bottom = SCREEN_HEIGHT - FOOTER_HEIGHT
        viewport_h = viewport_bottom - viewport_top

        # Weapon info string
        from src.models.weapon import STARTER_WEAPONS
        starter = STARTER_WEAPONS.get(pc.archetype)
        weapon_info = ""
        if starter:
            weapon_info = f"{starter.weapon_type.title()}  |  1d{starter.damage_dice}  |  {starter.stat}"

        content_h = estimate_status_height(
            pc.stats, pc.flavor_text, pc.starting_weapon,
            pc.abilities, pc.spells,
        )
        max_scroll = max(0, content_h - viewport_h)
        self.detail_scroll = max(0, min(self.detail_scroll, max_scroll))

        clip_rect = pygame.Rect(0, viewport_top, SCREEN_WIDTH, viewport_h)
        self.screen.set_clip(clip_rect)

        base_y = viewport_top - self.detail_scroll
        portrait = self.portraits.get(self.selected_index)

        draw_status_layout(
            self.screen, self.font, self.small_font, self.tiny_font,
            portrait, pc.stats, pc.flavor_text,
            pc.starting_weapon, weapon_info,
            pc.abilities, pc.spells,
            base_y, pad,
        )

        self.screen.set_clip(None)

        if self.detail_scroll > 0:
            arrow = self.tiny_font.render("\u25b2 Scroll up", True, HINT_COLOR)
            self.screen.blit(arrow, ((SCREEN_WIDTH - arrow.get_width()) // 2, viewport_top + 2))
        if self.detail_scroll < max_scroll:
            arrow = self.tiny_font.render("\u25bc Scroll down", True, HINT_COLOR)
            self.screen.blit(arrow, ((SCREEN_WIDTH - arrow.get_width()) // 2, viewport_bottom - 16))

        hint = self.small_font.render(
            "Enter to select this class  |  Esc to go back  |  Up/Down to scroll",
            True, UNSELECTED_COLOR,
        )
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 30))

    # ------------------------------------------------------------------
    # Name input
    # ------------------------------------------------------------------

    def _draw_name_input(self):
        title = self.title_font.render("Name Your Character", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, SCREEN_HEIGHT // 3 - 60))

        pc = self.class_options[self.selected_index]
        cls_text = self.font.render(
            f"Class: {pc.name} ({ARCHETYPE_DISPLAY.get(pc.archetype, pc.archetype.title())})", True, UNSELECTED_COLOR
        )
        self.screen.blit(cls_text, ((SCREEN_WIDTH - cls_text.get_width()) // 2, SCREEN_HEIGHT // 3))

        box_w, box_h = 400, 50
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = SCREEN_HEIGHT // 2 - box_h // 2
        pygame.draw.rect(self.screen, PANEL_BG, (box_x, box_y, box_w, box_h))
        pygame.draw.rect(self.screen, SELECTED_COLOR, (box_x, box_y, box_w, box_h), 2)

        name_surface = self.font.render(self.player_name + "_", True, WHITE)
        self.screen.blit(name_surface, (box_x + 10, box_y + 12))

        hint = self.small_font.render(
            "Type your name and press Enter  |  Esc to go back",
            True, UNSELECTED_COLOR,
        )
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 30))

    # ------------------------------------------------------------------
    # Confirm (Enter / Esc)
    # ------------------------------------------------------------------

    def _draw_confirm(self):
        pc = self.class_options[self.selected_index]

        question = self.title_font.render(
            f"Will you be {self.player_name} the {pc.name}?",
            True, TITLE_COLOR,
        )
        self.screen.blit(question, ((SCREEN_WIDTH - question.get_width()) // 2, SCREEN_HEIGHT // 3))

        yes_text = self.font.render("[Enter] Begin my journey", True, CONFIRM_COLOR)
        no_text = self.font.render("[Esc] Let me reconsider", True, UNSELECTED_COLOR)
        self.screen.blit(yes_text, ((SCREEN_WIDTH - yes_text.get_width()) // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(no_text, ((SCREEN_WIDTH - no_text.get_width()) // 2, SCREEN_HEIGHT // 2 + 40))

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def handle_input(self, event) -> dict | None:
        """Process keydown event. Returns action dict or None."""
        if self.state == STATE_SELECT:
            return self._handle_select_input(event)
        elif self.state == STATE_DETAIL:
            return self._handle_detail_input(event)
        elif self.state == STATE_NAME:
            return self._handle_name_input(event)
        elif self.state == STATE_CONFIRM:
            return self._handle_confirm_input(event)
        return None

    def _handle_select_input(self, event):
        if event.key == pygame.K_LEFT:
            if self.selected_index % 2 == 1:
                self.selected_index -= 1
        elif event.key == pygame.K_RIGHT:
            if self.selected_index % 2 == 0 and self.selected_index + 1 < len(self.class_options):
                self.selected_index += 1
        elif event.key == pygame.K_UP:
            if self.selected_index >= 2:
                self.selected_index -= 2
        elif event.key == pygame.K_DOWN:
            if self.selected_index + 2 < len(self.class_options):
                self.selected_index += 2
        elif event.key == pygame.K_RETURN:
            self.detail_scroll = 0
            self.state = STATE_DETAIL
        elif event.key == pygame.K_ESCAPE:
            return {"action": "back"}
        return None

    def _handle_detail_input(self, event):
        if event.key == pygame.K_RETURN:
            self.state = STATE_NAME
        elif event.key == pygame.K_ESCAPE:
            self.state = STATE_SELECT
        elif event.key == pygame.K_UP:
            self.detail_scroll = max(0, self.detail_scroll - DETAIL_SCROLL_STEP)
        elif event.key == pygame.K_DOWN:
            self.detail_scroll += DETAIL_SCROLL_STEP
        return None

    def _handle_name_input(self, event):
        if event.key == pygame.K_RETURN:
            if self.player_name.strip():
                self.state = STATE_CONFIRM
        elif event.key == pygame.K_ESCAPE:
            self.state = STATE_DETAIL
        elif event.key == pygame.K_BACKSPACE:
            self.player_name = self.player_name[:-1]
        elif event.unicode and event.unicode.isprintable() and len(self.player_name) < 20:
            self.player_name += event.unicode
        return None

    def _handle_confirm_input(self, event):
        if event.key == pygame.K_RETURN:
            return {
                "action": "selected",
                "class_index": self.selected_index,
                "player_name": self.player_name.strip(),
            }
        elif event.key == pygame.K_ESCAPE:
            self.state = STATE_SELECT
            self.player_name = ""
        return None
