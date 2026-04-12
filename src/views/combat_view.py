"""Combat view — renders the turn-based combat UI in Pygame.

Layout (top to bottom):
  1. Player HP/Stamina bars at top, turn-order panel top-right
  2. Monster area centered with portraits and HP bars
  3. Action grid (3x2) just above log
  4. Scrollable combat log at bottom
"""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE
from src.controllers.combat_controller import CombatController
from src.models.combat import CombatState
from src.views.portrait_utils import load_portrait

RED = (220, 50, 50)
GREEN = (50, 200, 50)
BLUE = (65, 105, 225)
ORANGE = (255, 165, 0)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (180, 180, 180)
YELLOW = (255, 220, 50)
MED_GRAY = (70, 70, 70)

_ELEMENT_COLORS = {
    "fire": RED,
    "water": BLUE,
    "forest": GREEN,
    "light": YELLOW,
    "dark": (100, 50, 150),
}

LOG_HEIGHT = 100
MENU_HEIGHT = 80
PLAYER_STATS_HEIGHT = 50


class CombatView:
    """Renders combat state to a Pygame surface."""

    GRID_COLS = 3
    GRID_ROWS = 2

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.SysFont(None, 20)
        self.log_font = pygame.font.SysFont(None, 18)
        self.log_scroll = 0

    def draw(self, combat: CombatController, selected_action: int = 0,
             selected_target: int = 0, selecting_target: bool = False,
             selecting_spell: bool = False, selected_spell: int = 0,
             selecting_item: bool = False, selected_item: int = 0,
             game_over_selection: int = 0):
        self.screen.fill(DARK_GRAY)
        self._draw_player_stats(combat.player)
        self._draw_turn_order(combat)
        self._draw_monsters(combat)
        self._draw_action_menu(combat, selected_action, selected_target,
                               selecting_target, selecting_spell, selected_spell,
                               selecting_item, selected_item)
        self._draw_combat_log(combat)
        self._draw_state_banner(combat, game_over_selection)

    # ------------------------------------------------------------------
    # Player stats — top of screen
    # ------------------------------------------------------------------

    def _draw_player_stats(self, player):
        y = 10
        bar_w = 200
        bar_h = 16

        panel_w = SCREEN_WIDTH - 220
        pygame.draw.rect(self.screen, MED_GRAY, (10, y - 4, panel_w, PLAYER_STATS_HEIGHT), 1)

        stats = [
            ("HP", player.health, player.max_health, RED),
            ("Stamina", player.stamina, player.max_stamina, GREEN),
        ]

        for i, (label, current, maximum, color) in enumerate(stats):
            x = 20 + i * (bar_w + 80)
            lbl = self.small_font.render(label, True, WHITE)
            self.screen.blit(lbl, (x, y + 2))
            ratio = min(1.0, max(0, current / maximum)) if maximum > 0 else 0
            bar_y = y + 20
            pygame.draw.rect(self.screen, (50, 50, 50), (x, bar_y, bar_w, bar_h))
            pygame.draw.rect(self.screen, color, (x, bar_y, int(bar_w * ratio), bar_h))
            pygame.draw.rect(self.screen, WHITE, (x, bar_y, bar_w, bar_h), 1)
            val = self.small_font.render(f"{int(current)}/{maximum}", True, WHITE)
            self.screen.blit(val, (x + bar_w + 5, bar_y))

    # ------------------------------------------------------------------
    # Turn order — top-right
    # ------------------------------------------------------------------

    def _draw_turn_order(self, combat: CombatController):
        panel_x = SCREEN_WIDTH - 210
        panel_y = 6
        panel_w = 195
        line_h = 20

        alive_count = sum(1 for c in combat.combatants if c.is_alive)
        panel_h = 24 + alive_count * line_h + 8
        pygame.draw.rect(self.screen, MED_GRAY, (panel_x, panel_y, panel_w, panel_h), 1)

        label = self.font.render("Turn Order", True, YELLOW)
        self.screen.blit(label, (panel_x + 8, panel_y + 4))

        y = panel_y + 26
        for c in combat.combatants:
            if not c.is_alive:
                continue
            is_current = c is combat.current_combatant()
            color = YELLOW if is_current else LIGHT_GRAY
            prefix = "> " if is_current else "  "
            name = c.name
            if len(name) > 16:
                name = name[:14] + ".."
            text = self.small_font.render(f"{prefix}{name} ({c.initiative})", True, color)
            self.screen.blit(text, (panel_x + 6, y))
            y += line_h

    # ------------------------------------------------------------------
    # Monster area — centered
    # ------------------------------------------------------------------

    def _draw_monsters(self, combat: CombatController):
        alive = [m for m in combat.monsters if m.is_alive]
        if not alive:
            return

        monster_area_top = PLAYER_STATS_HEIGHT + 20
        monster_area_bottom = SCREEN_HEIGHT - LOG_HEIGHT - MENU_HEIGHT - 20
        area_h = monster_area_bottom - monster_area_top
        portrait_size = min(80, max(48, area_h - 50))
        slot_height = portrait_size + 40
        area_center_y = monster_area_top + area_h // 2

        area_w = SCREEN_WIDTH - 40
        slot_width = min(180, area_w // max(len(alive), 1))
        total_w = slot_width * len(alive)
        start_x = (SCREEN_WIDTH - total_w) // 2

        for i, monster in enumerate(alive):
            x = start_x + i * slot_width + (slot_width - portrait_size) // 2
            slot_y = area_center_y - slot_height // 2

            # HP bar
            bar_w = portrait_size + 20
            bar_h = 10
            hp_ratio = min(1.0, max(0, monster.hp / monster.max_hp)) if monster.max_hp > 0 else 0
            bar_x = x - 10
            pygame.draw.rect(self.screen, (80, 0, 0), (bar_x, slot_y, bar_w, bar_h))
            pygame.draw.rect(self.screen, RED, (bar_x, slot_y, int(bar_w * hp_ratio), bar_h))
            pygame.draw.rect(self.screen, WHITE, (bar_x, slot_y, bar_w, bar_h), 1)

            hp_text = self.small_font.render(f"{monster.hp}/{monster.max_hp}", True, WHITE)
            self.screen.blit(hp_text, (bar_x, slot_y + bar_h + 2))

            # Portrait
            portrait_y = slot_y + bar_h + 18
            portrait_surf = load_portrait(
                getattr(monster, "profile_image", None),
                (portrait_size, portrait_size),
            )
            if portrait_surf:
                self.screen.blit(portrait_surf, (x, portrait_y))
            else:
                color = _ELEMENT_COLORS.get(monster.elemental_affinity, LIGHT_GRAY)
                pygame.draw.rect(self.screen, color, (x, portrait_y, portrait_size, portrait_size))
            pygame.draw.rect(self.screen, WHITE, (x, portrait_y, portrait_size, portrait_size), 1)

            # Name
            name = monster.display_name
            if len(name) > 18:
                name = name[:16] + ".."
            name_surf = self.small_font.render(name, True, WHITE)
            name_x = x + (portrait_size - name_surf.get_width()) // 2
            self.screen.blit(name_surf, (name_x, portrait_y + portrait_size + 4))

    # ------------------------------------------------------------------
    # Action grid — just above combat log
    # ------------------------------------------------------------------

    @staticmethod
    def get_action_grid(combat: CombatController) -> list[list[str | None]]:
        pc = combat.player.player_class
        archetype = pc.archetype if pc else "warrior"

        row0 = ["Attack", "Item", "Weapons"]

        if archetype == "warrior":
            cast_label = "Multi-Attack"
        else:
            cast_label = "Cast Spell"

        if archetype == "jester":
            row1 = [cast_label, "Gamble", "Flee"]
        else:
            row1 = [cast_label, "Flee", None]

        return [row0, row1]

    def _draw_action_menu(self, combat: CombatController, selected: int,
                          selected_target: int, selecting_target: bool,
                          selecting_spell: bool = False, selected_spell: int = 0,
                          selecting_item: bool = False, selected_item: int = 0):
        menu_y = SCREEN_HEIGHT - LOG_HEIGHT - MENU_HEIGHT - 5
        if not combat.is_player_turn() or combat.state != CombatState.ONGOING:
            hint = self.font.render(
                "Enemy turn..." if combat.state == CombatState.ONGOING else "",
                True, LIGHT_GRAY,
            )
            self.screen.blit(hint, (20, menu_y + 10))
            return

        if selecting_spell:
            self._draw_spell_selector(combat, menu_y, selected_spell)
            return

        if selecting_item:
            self._draw_item_selector(combat, menu_y, selected_item)
            return

        if selecting_target:
            self._draw_target_selector(combat, menu_y, selected_target)
            return

        grid = self.get_action_grid(combat)
        col_w = (SCREEN_WIDTH - 60) // self.GRID_COLS
        row_h = 36

        panel_h = self.GRID_ROWS * row_h + 16
        pygame.draw.rect(self.screen, (30, 30, 40), (15, menu_y, SCREEN_WIDTH - 30, panel_h))
        pygame.draw.rect(self.screen, MED_GRAY, (15, menu_y, SCREEN_WIDTH - 30, panel_h), 1)

        sel_row = selected // self.GRID_COLS
        sel_col = selected % self.GRID_COLS

        for r, row in enumerate(grid):
            for c, label in enumerate(row):
                if label is None:
                    continue
                cx = 30 + c * col_w
                cy = menu_y + 8 + r * row_h
                is_sel = (r == sel_row and c == sel_col)
                color = YELLOW if is_sel else LIGHT_GRAY
                prefix = "> " if is_sel else "  "
                text = self.font.render(f"{prefix}{label}", True, color)
                self.screen.blit(text, (cx, cy))

    def _draw_target_selector(self, combat: CombatController, y: int, selected_target: int):
        label = self.font.render("Select target:", True, WHITE)
        self.screen.blit(label, (20, y))
        alive = [m for m in combat.monsters if m.is_alive]
        for i, m in enumerate(alive):
            color = YELLOW if i == selected_target else LIGHT_GRAY
            prefix = "> " if i == selected_target else "  "
            text = self.font.render(f"{prefix}{m.display_name} (HP: {m.hp}/{m.max_hp})", True, color)
            self.screen.blit(text, (30, y + 28 + i * 24))

    def _draw_spell_selector(self, combat: CombatController, y: int, selected_spell: int):
        label = self.font.render("Select spell:  (Esc to cancel)", True, WHITE)
        self.screen.blit(label, (20, y))
        spells = combat.player.spells

        pairs = self._pair_spells(spells)
        row_y = y + 28
        flat_idx = 0

        for single, multi in pairs:
            if single:
                is_sel = flat_idx == selected_spell
                color = YELLOW if is_sel else LIGHT_GRAY
                prefix = "> " if is_sel else "  "
                cost = f"{single.stamina_cost} stam" if single.stamina_cost else "free"
                text = self.font.render(
                    f"{prefix}{single.name} [{single.element}] ({cost})",
                    True, color,
                )
                self.screen.blit(text, (30, row_y))
                flat_idx += 1
            if multi:
                is_sel = flat_idx == selected_spell
                color = YELLOW if is_sel else LIGHT_GRAY
                prefix = "> " if is_sel else "  "
                cost = f"{multi.stamina_cost} stam" if multi.stamina_cost else "free"
                text = self.font.render(
                    f"{prefix}{multi.name} [{multi.element}] ({cost})",
                    True, color,
                )
                self.screen.blit(text, (SCREEN_WIDTH // 2 + 10, row_y))
                flat_idx += 1
            row_y += 24

    @staticmethod
    def _pair_spells(spells) -> list[tuple]:
        damage_singles: dict[str, object] = {}
        damage_multis: dict[str, object] = {}
        others = []
        for s in spells:
            if s.spell_type == "damage_single":
                damage_singles[s.element] = s
            elif s.spell_type == "damage_multi":
                damage_multis[s.element] = s
            else:
                others.append(s)
        pairs = []
        seen_elements = set()
        for elem in list(damage_singles) + list(damage_multis):
            if elem in seen_elements:
                continue
            seen_elements.add(elem)
            pairs.append((damage_singles.get(elem), damage_multis.get(elem)))
        for s in others:
            pairs.append((s, None))
        return pairs

    def _draw_item_selector(self, combat: CombatController, y: int, selected_item: int):
        from src.models.items import Food, Drink
        label = self.font.render("Select item:  (Esc to cancel)", True, WHITE)
        self.screen.blit(label, (20, y))
        consumables = [
            (name, item) for name, item in combat.player.inventory.items()
            if isinstance(item, (Food, Drink))
        ]
        for i, (name, item) in enumerate(consumables):
            color = YELLOW if i == selected_item else LIGHT_GRAY
            prefix = "> " if i == selected_item else "  "
            text = self.font.render(f"{prefix}{name}  — {item.desc}", True, color)
            self.screen.blit(text, (30, y + 28 + i * 24))

    # ------------------------------------------------------------------
    # Combat log — scrollable, bottom strip
    # ------------------------------------------------------------------

    def _draw_combat_log(self, combat: CombatController):
        log_y = SCREEN_HEIGHT - LOG_HEIGHT
        pygame.draw.rect(self.screen, BLACK, (10, log_y, SCREEN_WIDTH - 20, LOG_HEIGHT - 5))
        pygame.draw.rect(self.screen, LIGHT_GRAY, (10, log_y, SCREEN_WIDTH - 20, LOG_HEIGHT - 5), 1)

        label = self.small_font.render("Combat Log", True, YELLOW)
        self.screen.blit(label, (15, log_y + 3))

        max_lines = (LOG_HEIGHT - 25) // 16
        total = len(combat.log)
        self.log_scroll = max(0, min(self.log_scroll, total - max_lines))
        start = max(0, total - max_lines - self.log_scroll)
        end = start + max_lines
        visible = combat.log[start:end]

        for i, msg in enumerate(visible):
            display = msg[:100] + "..." if len(msg) > 100 else msg
            text = self.log_font.render(display, True, LIGHT_GRAY)
            self.screen.blit(text, (15, log_y + 20 + i * 16))

    def scroll_log(self, direction: int):
        self.log_scroll = max(0, self.log_scroll + direction)

    # ------------------------------------------------------------------
    # State banner
    # ------------------------------------------------------------------

    def _draw_state_banner(self, combat: CombatController, game_over_selection: int = 0):
        if combat.state == CombatState.ONGOING:
            return

        banners = {
            CombatState.VICTORY: ("VICTORY!", GREEN),
            CombatState.DEFEAT: ("DEFEAT", RED),
            CombatState.FLED: ("ESCAPED!", YELLOW),
        }
        text, color = banners.get(combat.state, ("", WHITE))
        surf = pygame.font.SysFont(None, 64).render(text, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

        backdrop = pygame.Surface((rect.width + 40, rect.height + 20))
        backdrop.set_alpha(200)
        backdrop.fill(BLACK)
        self.screen.blit(backdrop, (rect.x - 20, rect.y - 10))
        self.screen.blit(surf, rect)

        if combat.state == CombatState.DEFEAT:
            self._draw_game_over_menu(rect.bottom + 15, game_over_selection)
        else:
            hint = self.font.render("Press Enter to continue", True, LIGHT_GRAY)
            self.screen.blit(hint, (SCREEN_WIDTH // 2 - 100, rect.bottom + 20))

    GAME_OVER_OPTIONS = ["Load Save", "Quit to Menu"]

    def _draw_game_over_menu(self, y: int, selected: int = 0):
        label = self.font.render("Game Over", True, RED)
        self.screen.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, y))

        for i, option in enumerate(self.GAME_OVER_OPTIONS):
            color = YELLOW if i == selected else LIGHT_GRAY
            prefix = "> " if i == selected else "  "
            text = self.font.render(f"{prefix}{option}", True, color)
            self.screen.blit(
                text,
                (SCREEN_WIDTH // 2 - text.get_width() // 2, y + 28 + i * 26),
            )
