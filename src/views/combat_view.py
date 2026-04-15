"""Combat view — renders the turn-based combat UI in Pygame.

Layout (top to bottom):
  1. Player HP/Stamina bars at top, turn-order panel top-right
  2. Monster area centered with portraits and HP bars
  3. Action grid (3x2) just above log
  4. Scrollable combat log at bottom
"""

import pygame

from config import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.controllers.combat_controller import CombatController
from src.models.combat import CombatState
from src.models.weapon import resolve_weapon_stat, step_down_weapon_dice, weapon_stat_bonus
from src.views.portrait_utils import load_portrait

RED = (220, 50, 50)
GREEN = (50, 200, 50)
BLUE = (65, 105, 225)
ORANGE = (255, 165, 0)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (180, 180, 180)
YELLOW = (255, 220, 50)
MED_GRAY = (70, 70, 70)


def _weapon_type_tag(weapon) -> str:
    """Build a short tag like '[slashing]' or '[slashing + fire]' for UI display."""
    if weapon is None:
        return ""
    parts = []
    dt = getattr(weapon, "damage_type", "physical")
    if dt and dt != "physical":
        parts.append(dt)
    me = getattr(weapon, "magic_element", None)
    if me:
        parts.append(me)
    return f"[{' + '.join(parts)}]" if parts else ""


_ELEMENT_COLORS = {
    "fire": RED,
    "water": BLUE,
    "forest": GREEN,
    "light": YELLOW,
    "dark": (100, 50, 150),
}

LOG_HEIGHT = 60
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

    def draw(
        self,
        combat: CombatController,
        selected_action: int = 0,
        selected_target: int = 0,
        selecting_target: bool = False,
        selecting_spell: bool = False,
        selected_spell: int = 0,
        selecting_item: bool = False,
        selected_item: int = 0,
        game_over_selection: int = 0,
        is_gate_fight: bool = False,
        highlight_all_targets: bool = False,
        loot_summary: list[str] | None = None,
        pending_action: str = "",
        pending_spell_index: int = -1,
        showing_result: bool = False,
        result_text: str = "",
        browsing_log: bool = False,
        log_browse_scroll: int = 0,
    ):
        self.screen.fill(DARK_GRAY)
        self._draw_player_stats(combat.player)
        self._draw_turn_order(combat)
        self._draw_monsters(
            combat,
            selecting_target=selecting_target,
            selected_target=selected_target,
            highlight_all=highlight_all_targets,
        )
        self._draw_action_menu(
            combat,
            selected_action,
            selected_target,
            selecting_target,
            selecting_spell,
            selected_spell,
            selecting_item,
            selected_item,
            is_gate_fight=is_gate_fight,
            highlight_all=highlight_all_targets,
            pending_action=pending_action,
            pending_spell_index=pending_spell_index,
            showing_result=showing_result,
            result_text=result_text,
            browsing_log=browsing_log,
            log_browse_scroll=log_browse_scroll,
        )
        self._draw_combat_log(combat, focused=browsing_log)
        self._draw_state_banner(combat, game_over_selection, loot_summary=loot_summary, showing_result=showing_result)

    # ------------------------------------------------------------------
    # Player stats — top of screen
    # ------------------------------------------------------------------

    def _draw_player_stats(self, player):
        y = 10
        bar_w = 200
        bar_h = 16

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

    def _draw_monsters(
        self,
        combat: CombatController,
        selecting_target: bool = False,
        selected_target: int = 0,
        highlight_all: bool = False,
    ):
        alive = [m for m in combat.monsters if m.is_alive]
        if not alive:
            return

        monster_area_top = PLAYER_STATS_HEIGHT + 20
        monster_area_bottom = SCREEN_HEIGHT - LOG_HEIGHT - MENU_HEIGHT - 20
        area_h = monster_area_bottom - monster_area_top
        portrait_size = min(150, max(64, area_h - 50))
        slot_height = portrait_size + 40
        area_center_y = monster_area_top + area_h // 2

        area_w = SCREEN_WIDTH - 40
        slot_width = min(180, area_w // max(len(alive), 1))
        total_w = slot_width * len(alive)
        start_x = (SCREEN_WIDTH - total_w) // 2

        for i, monster in enumerate(alive):
            x = start_x + i * slot_width + (slot_width - portrait_size) // 2
            slot_y = area_center_y - slot_height // 2
            is_highlighted = selecting_target and (highlight_all or i == selected_target)

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
                name = monster.display_name
                lines = self._wrap_name_for_portrait(name, portrait_size)
                total_text_h = len(lines) * 16
                text_start_y = portrait_y + (portrait_size - total_text_h) // 2
                for li, line in enumerate(lines):
                    ts = self.small_font.render(line, True, WHITE)
                    tx = x + (portrait_size - ts.get_width()) // 2
                    self.screen.blit(ts, (tx, text_start_y + li * 16))

            # Dim non-selected portraits when targeting
            if selecting_target and not is_highlighted:
                dim = pygame.Surface((portrait_size, portrait_size))
                dim.set_alpha(140)
                dim.fill(BLACK)
                self.screen.blit(dim, (x, portrait_y))

            # Border: white highlight when targeted, default thin border otherwise
            if is_highlighted:
                pygame.draw.rect(self.screen, WHITE, (x - 2, portrait_y - 2, portrait_size + 4, portrait_size + 4), 3)
            else:
                pygame.draw.rect(self.screen, WHITE, (x, portrait_y, portrait_size, portrait_size), 1)

            # Name
            name = monster.display_name
            if len(name) > 18:
                name = name[:16] + ".."
            name_surf = self.small_font.render(name, True, WHITE)
            name_x = x + (portrait_size - name_surf.get_width()) // 2
            self.screen.blit(name_surf, (name_x, portrait_y + portrait_size + 4))

    def _wrap_name_for_portrait(self, name: str, max_width: int) -> list[str]:
        """Break a name into lines that fit within max_width pixels."""
        words = name.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if self.small_font.size(test)[0] <= max_width - 8:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [name[:10]]

    # ------------------------------------------------------------------
    # Action grid — just above combat log
    # ------------------------------------------------------------------

    @staticmethod
    def get_action_grid(combat: CombatController, is_gate_fight: bool = False) -> list[list[str | None]]:
        pc = combat.player.player_class
        archetype = pc.archetype if pc else "warrior"

        row0 = ["Attack", "Item", "Weapons"]

        if archetype == "warrior":
            cast_label = "Multi-Attack"
        else:
            cast_label = "Cast Spell"

        flee_label = None if is_gate_fight else "Flee"

        if archetype == "jester":
            row1 = [cast_label, "Gamble", flee_label]
        else:
            row1 = [cast_label, flee_label, None]

        return [row0, row1]

    def _draw_action_menu(
        self,
        combat: CombatController,
        selected: int,
        selected_target: int,
        selecting_target: bool,
        selecting_spell: bool = False,
        selected_spell: int = 0,
        selecting_item: bool = False,
        selected_item: int = 0,
        is_gate_fight: bool = False,
        highlight_all: bool = False,
        pending_action: str = "",
        pending_spell_index: int = -1,
        showing_result: bool = False,
        result_text: str = "",
        browsing_log: bool = False,
        log_browse_scroll: int = 0,
    ):
        menu_y = SCREEN_HEIGHT - LOG_HEIGHT - MENU_HEIGHT - 10

        if showing_result:
            self._draw_action_result(result_text, menu_y)
            return

        if not combat.is_player_turn() or combat.state != CombatState.ONGOING:
            hint = self.font.render(
                "Enemy turn..." if combat.state == CombatState.ONGOING else "",
                True,
                LIGHT_GRAY,
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
            self._draw_target_selector(
                combat,
                menu_y,
                selected_target,
                highlight_all=highlight_all,
                pending_action=pending_action,
                pending_spell_index=pending_spell_index,
            )
            return

        grid = self.get_action_grid(combat, is_gate_fight=is_gate_fight)
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
                is_sel = r == sel_row and c == sel_col
                color = YELLOW if is_sel else LIGHT_GRAY
                prefix = "> " if is_sel else "  "
                text = self.font.render(f"{prefix}{label}", True, color)
                self.screen.blit(text, (cx, cy))

        tab_hint = self.small_font.render("Tab: scroll log", True, MED_GRAY)
        self.screen.blit(tab_hint, (SCREEN_WIDTH - tab_hint.get_width() - 25, menu_y + panel_h - 14))

    def _draw_target_selector(
        self,
        combat: CombatController,
        y: int,
        selected_target: int,
        highlight_all: bool = False,
        pending_action: str = "",
        pending_spell_index: int = -1,
    ):
        panel_h = self.GRID_ROWS * 36 + 16
        pygame.draw.rect(self.screen, (30, 30, 40), (15, y, SCREEN_WIDTH - 30, panel_h))
        pygame.draw.rect(self.screen, MED_GRAY, (15, y, SCREEN_WIDTH - 30, panel_h), 1)

        player = combat.player
        alive = [m for m in combat.monsters if m.is_alive]

        dmg_tag = _weapon_type_tag(player.weapon)

        if highlight_all and pending_action == "Multi-Attack":
            dice = step_down_weapon_dice(player.weapon)
            stat = resolve_weapon_stat(player.weapon)
            bonus = weapon_stat_bonus(player, player.weapon, stat)
            sign = "+" if bonus >= 0 else ""
            action_text = f"Hit all enemies {dice} {sign}{bonus} {dmg_tag}"
            cost_text = "6 stam"
            controls = "Enter to confirm  |  Esc to cancel"
        elif highlight_all and pending_action == "Cast Spell":
            spell = player.spells[pending_spell_index] if 0 <= pending_spell_index < len(player.spells) else None
            if spell:
                cost = f"{spell.stamina_cost} stam" if spell.stamina_cost else "free"
                action_text = f"Cast {spell.name} on all"
                cost_text = cost
            else:
                action_text = "Cast spell on all"
                cost_text = ""
            controls = "Enter to confirm  |  Esc to cancel"
        elif pending_action == "Cast Spell":
            spell = player.spells[pending_spell_index] if 0 <= pending_spell_index < len(player.spells) else None
            target_name = alive[selected_target].display_name if alive else "?"
            if spell:
                cost = f"{spell.stamina_cost} stam" if spell.stamina_cost else "free"
                if spell.spell_type == "heal":
                    action_text = f"Heal with {spell.name}"
                elif spell.spell_type in ("buff_stat", "buff_sustain"):
                    action_text = f"Buff with {spell.name}"
                else:
                    action_text = f"Cast {spell.name} at {target_name}"
                cost_text = cost
            else:
                action_text = f"Cast at {target_name}"
                cost_text = ""
            controls = "Left/Right  |  Enter  |  Esc"
        else:
            target_name = alive[selected_target].display_name if alive else "?"
            dice = f"1d{player.weapon.damage_dice}" if player.weapon else "1d4"
            stat = resolve_weapon_stat(player.weapon)
            bonus = weapon_stat_bonus(player, player.weapon, stat)
            sign = "+" if bonus >= 0 else ""
            action_text = f"Attack {target_name} for {dice} {sign}{bonus} {dmg_tag}"
            cost_text = ""
            controls = "Left/Right  |  Enter  |  Esc"

        action_surf = self.font.render(action_text, True, WHITE)
        self.screen.blit(action_surf, (20, y + 8))

        if cost_text:
            cost_surf = self.small_font.render(cost_text, True, YELLOW)
            self.screen.blit(cost_surf, (SCREEN_WIDTH - cost_surf.get_width() - 25, y + 10))

        ctrl_surf = self.small_font.render(controls, True, LIGHT_GRAY)
        self.screen.blit(ctrl_surf, (20, y + panel_h - 20))

    def _draw_spell_selector(self, combat: CombatController, y: int, selected_spell: int):
        panel_h = self.GRID_ROWS * 36 + 16
        pygame.draw.rect(self.screen, (30, 30, 40), (15, y, SCREEN_WIDTH - 30, panel_h))
        pygame.draw.rect(self.screen, MED_GRAY, (15, y, SCREEN_WIDTH - 30, panel_h), 1)

        label = self.font.render("Select spell:  (Esc to cancel)", True, WHITE)
        self.screen.blit(label, (20, y + 4))

        spells = combat.player.spells
        items: list[str] = []
        for s in spells:
            cost = f"{s.stamina_cost} stam" if s.stamina_cost else "free"
            items.append(f"{s.name} [{s.element}] ({cost})")

        item_y = y + 26
        avail_h = panel_h - 26
        max_visible = max(1, avail_h // 24)
        scroll_offset = max(0, min(selected_spell - max_visible + 1, len(items) - max_visible))

        clip = pygame.Rect(15, item_y, SCREEN_WIDTH - 30, avail_h)
        self.screen.set_clip(clip)
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(items))):
            is_sel = i == selected_spell
            color = YELLOW if is_sel else LIGHT_GRAY
            prefix = "> " if is_sel else "  "
            text = self.font.render(f"{prefix}{items[i]}", True, color)
            self.screen.blit(text, (30, item_y + (i - scroll_offset) * 24))
        self.screen.set_clip(None)

        if scroll_offset > 0:
            arrow = self.small_font.render("^", True, LIGHT_GRAY)
            self.screen.blit(arrow, (SCREEN_WIDTH - 40, y + 4))
        if scroll_offset + max_visible < len(items):
            arrow = self.small_font.render("v", True, LIGHT_GRAY)
            self.screen.blit(arrow, (SCREEN_WIDTH - 40, y + panel_h - 16))

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
        from src.models.items import Drink, Food

        panel_h = self.GRID_ROWS * 36 + 16
        pygame.draw.rect(self.screen, (30, 30, 40), (15, y, SCREEN_WIDTH - 30, panel_h))
        pygame.draw.rect(self.screen, MED_GRAY, (15, y, SCREEN_WIDTH - 30, panel_h), 1)

        label = self.font.render("Select item:  (Esc to cancel)", True, WHITE)
        self.screen.blit(label, (20, y + 4))

        consumables = [
            (name, item) for name, item in combat.player.inventory.items() if isinstance(item, (Food, Drink))
        ]

        item_y = y + 26
        avail_h = panel_h - 26
        max_visible = max(1, avail_h // 24)
        scroll_offset = max(0, min(selected_item - max_visible + 1, len(consumables) - max_visible))

        clip = pygame.Rect(15, item_y, SCREEN_WIDTH - 30, avail_h)
        self.screen.set_clip(clip)
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(consumables))):
            is_sel = i == selected_item
            color = YELLOW if is_sel else LIGHT_GRAY
            prefix = "> " if is_sel else "  "
            name, item = consumables[i]
            text = self.font.render(f"{prefix}{name}  — {item.desc}", True, color)
            self.screen.blit(text, (30, item_y + (i - scroll_offset) * 24))
        self.screen.set_clip(None)

        if scroll_offset > 0:
            arrow = self.small_font.render("^", True, LIGHT_GRAY)
            self.screen.blit(arrow, (SCREEN_WIDTH - 40, y + 4))
        if scroll_offset + max_visible < len(consumables):
            arrow = self.small_font.render("v", True, LIGHT_GRAY)
            self.screen.blit(arrow, (SCREEN_WIDTH - 40, y + panel_h - 16))

    # ------------------------------------------------------------------
    # Action result display — shown after player acts, before enemy turns
    # ------------------------------------------------------------------

    def _draw_action_result(self, result_text: str, y: int):
        panel_h = self.GRID_ROWS * 36 + 16
        pygame.draw.rect(self.screen, (30, 30, 40), (15, y, SCREEN_WIDTH - 30, panel_h))
        pygame.draw.rect(self.screen, MED_GRAY, (15, y, SCREEN_WIDTH - 30, panel_h), 1)

        max_w = SCREEN_WIDTH - 70
        words = result_text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if self.font.size(test)[0] <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        is_miss = "miss" in result_text.lower()
        is_fail = "not enough" in result_text.lower() or "failed" in result_text.lower()
        if is_miss or is_fail:
            text_color = RED
        elif "heal" in result_text.lower() or "buff" in result_text.lower() or "energy" in result_text.lower():
            text_color = GREEN
        else:
            text_color = WHITE

        line_h = self.font.get_linesize()
        max_lines = max(1, (panel_h - 24) // line_h)
        for i, line in enumerate(lines[:max_lines]):
            surf = self.font.render(line, True, text_color)
            self.screen.blit(surf, (25, y + 6 + i * line_h))

        ctrl = self.small_font.render("Enter to continue  |  Tab: Combat Log", True, LIGHT_GRAY)
        self.screen.blit(ctrl, (20, y + panel_h - 18))

    # ------------------------------------------------------------------
    # Log browser — full combat log in menu panel, scrollable
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Combat log — scrollable, bottom strip
    # ------------------------------------------------------------------

    def _draw_combat_log(self, combat: CombatController, focused: bool = False):
        log_y = SCREEN_HEIGHT - LOG_HEIGHT
        pygame.draw.rect(self.screen, BLACK, (10, log_y, SCREEN_WIDTH - 20, LOG_HEIGHT - 5))
        if focused:
            pygame.draw.rect(self.screen, YELLOW, (10, log_y, SCREEN_WIDTH - 20, LOG_HEIGHT - 5), 1)
        label_text = "Combat Log  (Up/Down scroll, Tab/Esc close)" if focused else "Combat Log"
        label = self.small_font.render(label_text, True, YELLOW)
        self.screen.blit(label, (15, log_y + 3))

        max_lines = (LOG_HEIGHT - 25) // 16
        total = len(combat.log)
        self.log_scroll = max(0, min(self.log_scroll, max(0, total - max_lines)))
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

    def _draw_state_banner(
        self,
        combat: CombatController,
        game_over_selection: int = 0,
        loot_summary: list[str] | None = None,
        showing_result: bool = False,
    ):
        if combat.state == CombatState.ONGOING or showing_result:
            return

        banners = {
            CombatState.VICTORY: ("VICTORY!", GREEN),
            CombatState.DEFEAT: ("DEFEAT", RED),
            CombatState.FLED: ("ESCAPED!", YELLOW),
        }
        text, color = banners.get(combat.state, ("", WHITE))
        big_font = pygame.font.SysFont(None, 64)
        surf = big_font.render(text, True, color)

        loot_lines: list[str] = []
        if combat.state == CombatState.VICTORY and loot_summary:
            loot_lines = loot_summary

        banner_h = surf.get_height() + 20
        if loot_lines:
            banner_h += 10 + len(loot_lines) * 22
        banner_h += 30  # room for "Press Enter"

        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - banner_h // 4))

        backdrop_w = max(rect.width + 60, 400)
        backdrop = pygame.Surface((backdrop_w, banner_h))
        backdrop.set_alpha(200)
        backdrop.fill(BLACK)
        self.screen.blit(backdrop, (SCREEN_WIDTH // 2 - backdrop_w // 2, rect.y - 10))
        self.screen.blit(surf, rect)

        if combat.state == CombatState.DEFEAT:
            self._draw_game_over_menu(rect.bottom + 15, game_over_selection)
        else:
            next_y = rect.bottom + 8
            if loot_lines:
                for line in loot_lines:
                    loot_surf = self.font.render(f"  {line}", True, YELLOW)
                    self.screen.blit(loot_surf, (SCREEN_WIDTH // 2 - loot_surf.get_width() // 2, next_y))
                    next_y += 22
                next_y += 4
            hint = self.font.render("Press Enter to continue", True, LIGHT_GRAY)
            self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, next_y))

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
