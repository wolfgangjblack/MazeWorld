"""Class selection screen — pick from 4 generated classes, name character."""

import os
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE


TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
STAT_COLOR = (140, 200, 140)
SPELL_COLOR = (140, 160, 220)
ABILITY_COLOR = (220, 160, 140)
JESTER_HIDDEN_COLOR = (100, 100, 100)
PANEL_BG = (30, 30, 50)
PANEL_BORDER = (80, 80, 120)
CONFIRM_COLOR = (100, 255, 100)

STAT_NAMES = ["STR", "DEX", "CON", "INT", "WIS", "CHA", "LUCK"]

# Screen sub-states
STATE_SELECT = "select"
STATE_DETAIL = "detail"
STATE_NAME = "name"
STATE_CONFIRM = "confirm"


class ClassSelectView:
    """Renders class selection UI and manages selection flow."""

    def __init__(self, screen, font, class_options):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)
        self.class_options = class_options  # list[PlayerClass]
        self.selected_index = 0
        self.state = STATE_SELECT
        self.player_name = ""
        self.portraits = {}
        self._load_portraits()

    def _load_portraits(self):
        """Load portrait images for each class."""
        for i, pc in enumerate(self.class_options):
            if pc.portrait_path and os.path.exists(pc.portrait_path):
                try:
                    img = pygame.image.load(pc.portrait_path)
                    self.portraits[i] = pygame.transform.scale(img, (128, 128))
                except Exception:
                    self.portraits[i] = None
            else:
                self.portraits[i] = None

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

    def _draw_selection_grid(self):
        """Draw the 4 class cards in a 2x2 grid."""
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
            selected = (i == self.selected_index)
            self._draw_class_card(x, y, card_w, card_h, pc, i, selected)

        hint = self.small_font.render(
            "Arrow keys to select  |  Enter to view details  |  Esc to go back",
            True, UNSELECTED_COLOR
        )
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 30))

    def _draw_class_card(self, x, y, w, h, pc, index, selected):
        """Draw a single class card."""
        border_color = SELECTED_COLOR if selected else PANEL_BORDER
        pygame.draw.rect(self.screen, PANEL_BG, (x, y, w, h))
        pygame.draw.rect(self.screen, border_color, (x, y, w, h), 2)

        is_jester = pc.archetype == "jester"
        pad = 10

        # Portrait area
        portrait_rect = pygame.Rect(x + pad, y + pad, 128, 128)
        if is_jester and self.state == STATE_SELECT:
            # Black silhouette with "???"
            pygame.draw.rect(self.screen, (20, 20, 20), portrait_rect)
            q_text = self.title_font.render("???", True, JESTER_HIDDEN_COLOR)
            self.screen.blit(q_text, (
                portrait_rect.x + (128 - q_text.get_width()) // 2,
                portrait_rect.y + (128 - q_text.get_height()) // 2
            ))
        elif self.portraits.get(index):
            self.screen.blit(self.portraits[index], portrait_rect.topleft)
        else:
            pygame.draw.rect(self.screen, (40, 40, 60), portrait_rect)
            placeholder = self.small_font.render("No Portrait", True, UNSELECTED_COLOR)
            self.screen.blit(placeholder, (
                portrait_rect.x + (128 - placeholder.get_width()) // 2,
                portrait_rect.y + 55
            ))

        # Text area (right of portrait)
        text_x = x + pad + 128 + pad
        text_y = y + pad

        if is_jester and self.state == STATE_SELECT:
            name_text = self.font.render("???", True, JESTER_HIDDEN_COLOR)
            self.screen.blit(name_text, (text_x, text_y))
            flavor = self.small_font.render("A mystery awaits...", True, JESTER_HIDDEN_COLOR)
            self.screen.blit(flavor, (text_x, text_y + 30))
        else:
            # Name
            name_color = SELECTED_COLOR if selected else WHITE
            name_text = self.font.render(pc.name, True, name_color)
            self.screen.blit(name_text, (text_x, text_y))

            # Archetype
            arch_text = self.small_font.render(f"({pc.archetype.title()})", True, UNSELECTED_COLOR)
            self.screen.blit(arch_text, (text_x, text_y + 28))

            # Weapon
            wpn_text = self.small_font.render(f"Weapon: {pc.starting_weapon}", True, ABILITY_COLOR)
            self.screen.blit(wpn_text, (text_x, text_y + 50))

        # Stats bar (below portrait)
        stats_y = y + pad + 128 + 8
        if not (is_jester and self.state == STATE_SELECT):
            self._draw_stat_bars_mini(x + pad, stats_y, w - 2 * pad, pc)
        else:
            hidden = self.small_font.render("Stats hidden until selected", True, JESTER_HIDDEN_COLOR)
            self.screen.blit(hidden, (x + pad, stats_y))

    def _draw_stat_bars_mini(self, x, y, total_w, pc):
        """Draw compact stat bars for card view."""
        bar_h = 10
        gap = 2
        for i, stat in enumerate(STAT_NAMES):
            val = getattr(pc.stats, stat)
            label = self.small_font.render(f"{stat[:3]}", True, STAT_COLOR)
            self.screen.blit(label, (x, y + i * (bar_h + gap)))

            bar_x = x + 40
            bar_w = total_w - 50
            # Background
            pygame.draw.rect(self.screen, (40, 40, 60), (bar_x, y + i * (bar_h + gap), bar_w, bar_h))
            # Fill (scale 6-18 to 0-100%)
            fill_pct = max(0, min(1, (val - 6) / 12))
            fill_w = int(bar_w * fill_pct)
            bar_color = SELECTED_COLOR if val >= 14 else STAT_COLOR if val >= 11 else (160, 80, 80)
            pygame.draw.rect(self.screen, bar_color, (bar_x, y + i * (bar_h + gap), fill_w, bar_h))
            # Value
            val_text = self.small_font.render(str(val), True, WHITE)
            self.screen.blit(val_text, (bar_x + bar_w + 4, y + i * (bar_h + gap) - 2))

    def _draw_detail_view(self):
        """Draw detailed view of the selected class."""
        pc = self.class_options[self.selected_index]
        pad = 20

        title = self.title_font.render(pc.name, True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 15))

        arch = self.font.render(f"{pc.archetype.title()} — {pc.environment}", True, UNSELECTED_COLOR)
        self.screen.blit(arch, ((SCREEN_WIDTH - arch.get_width()) // 2, 55))

        # Portrait (left column)
        portrait_x, portrait_y = pad, 90
        if self.portraits.get(self.selected_index):
            portrait = pygame.transform.scale(self.portraits[self.selected_index], (180, 180))
            self.screen.blit(portrait, (portrait_x, portrait_y))
        else:
            pygame.draw.rect(self.screen, (40, 40, 60), (portrait_x, portrait_y, 180, 180))

        # Flavor text
        flavor_y = portrait_y + 190
        self._draw_wrapped_text(pc.flavor_text, pad, flavor_y, 180, self.small_font, UNSELECTED_COLOR)

        # Weapon
        weapon_y = flavor_y + 50
        wpn = self.font.render(f"Weapon: {pc.starting_weapon}", True, ABILITY_COLOR)
        self.screen.blit(wpn, (pad, weapon_y))

        # Stats (middle column)
        stats_x = pad + 200 + pad
        stats_y = 90
        stats_title = self.font.render("Stats", True, STAT_COLOR)
        self.screen.blit(stats_title, (stats_x, stats_y))
        stats_y += 30
        for stat in STAT_NAMES:
            val = getattr(pc.stats, stat)
            mod = pc.stats.modifier(stat)
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            line = self.small_font.render(f"{stat}: {val} ({mod_str})", True, STAT_COLOR)
            self.screen.blit(line, (stats_x, stats_y))
            stats_y += 22
        total = self.small_font.render(f"Total: {pc.stats.total()}/72", True, UNSELECTED_COLOR)
        self.screen.blit(total, (stats_x, stats_y + 5))

        # Abilities & Spells (right column)
        right_x = stats_x + 160
        right_y = 90

        if pc.abilities:
            ab_title = self.font.render("Abilities", True, ABILITY_COLOR)
            self.screen.blit(ab_title, (right_x, right_y))
            right_y += 28
            for ab in pc.abilities[:6]:
                line = self.small_font.render(f"- {ab.name}", True, ABILITY_COLOR)
                self.screen.blit(line, (right_x, right_y))
                right_y += 20

        right_y += 10
        if pc.spells:
            sp_title = self.font.render("Spells", True, SPELL_COLOR)
            self.screen.blit(sp_title, (right_x, right_y))
            right_y += 28
            for sp in pc.spells[:6]:
                type_tag = f"[{sp.spell_type}]"
                line = self.small_font.render(f"- {sp.name} {type_tag}", True, SPELL_COLOR)
                self.screen.blit(line, (right_x, right_y))
                right_y += 20

        # Hints
        hint = self.small_font.render(
            "Enter to select this class  |  Esc to go back",
            True, UNSELECTED_COLOR
        )
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 30))

    def _draw_name_input(self):
        """Draw the character naming screen."""
        title = self.title_font.render("Name Your Character", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, SCREEN_HEIGHT // 3 - 60))

        pc = self.class_options[self.selected_index]
        cls_text = self.font.render(f"Class: {pc.name} ({pc.archetype.title()})", True, UNSELECTED_COLOR)
        self.screen.blit(cls_text, ((SCREEN_WIDTH - cls_text.get_width()) // 2, SCREEN_HEIGHT // 3))

        # Name input box
        box_w = 400
        box_h = 50
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = SCREEN_HEIGHT // 2 - box_h // 2
        pygame.draw.rect(self.screen, PANEL_BG, (box_x, box_y, box_w, box_h))
        pygame.draw.rect(self.screen, SELECTED_COLOR, (box_x, box_y, box_w, box_h), 2)

        name_surface = self.font.render(self.player_name + "_", True, WHITE)
        self.screen.blit(name_surface, (box_x + 10, box_y + 12))

        hint = self.small_font.render(
            "Type your name and press Enter  |  Esc to go back",
            True, UNSELECTED_COLOR
        )
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 30))

    def _draw_confirm(self):
        """Draw confirmation: 'Will you be [Name] the [Class]?'"""
        pc = self.class_options[self.selected_index]

        question = self.title_font.render(
            f"Will you be {self.player_name} the {pc.name}?",
            True, TITLE_COLOR
        )
        self.screen.blit(question, ((SCREEN_WIDTH - question.get_width()) // 2, SCREEN_HEIGHT // 3))

        yes_text = self.font.render("[Y] Yes, begin my journey", True, CONFIRM_COLOR)
        no_text = self.font.render("[N] No, let me reconsider", True, UNSELECTED_COLOR)
        self.screen.blit(yes_text, ((SCREEN_WIDTH - yes_text.get_width()) // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(no_text, ((SCREEN_WIDTH - no_text.get_width()) // 2, SCREEN_HEIGHT // 2 + 40))

    def _draw_wrapped_text(self, text, x, y, max_w, font, color):
        """Draw text wrapped to max_w pixels."""
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

    def handle_input(self, event) -> dict | None:
        """Process keydown event. Returns action dict or None.

        Possible return values:
        - {"action": "selected", "class_index": int, "player_name": str}
        - {"action": "back"}
        - None (no action)
        """
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
            self.state = STATE_DETAIL
        elif event.key == pygame.K_ESCAPE:
            return {"action": "back"}
        return None

    def _handle_detail_input(self, event):
        if event.key == pygame.K_RETURN:
            self.state = STATE_NAME
        elif event.key == pygame.K_ESCAPE:
            self.state = STATE_SELECT
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
        if event.key == pygame.K_y:
            return {
                "action": "selected",
                "class_index": self.selected_index,
                "player_name": self.player_name.strip(),
            }
        elif event.key in (pygame.K_n, pygame.K_ESCAPE):
            self.state = STATE_SELECT
            self.player_name = ""
        return None
