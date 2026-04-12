"""Tabbed player menu view — Inventory, Stats, Spells/Abilities tabs."""

import os
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from src.views.status_layout import draw_status_layout, estimate_status_height

TITLE_COLOR = (220, 180, 60)
TAB_ACTIVE_COLOR = (255, 255, 100)
TAB_INACTIVE_COLOR = (120, 120, 120)
TEXT_COLOR = (200, 200, 200)
HIGHLIGHT_COLOR = (255, 255, 150)
SELECTED_COLOR = (255, 80, 80)
HEADER_COLOR = (180, 160, 80)
EQUIPPED_COLOR = (100, 255, 100)
STAT_LABEL_COLOR = (160, 160, 180)
STAT_VALUE_COLOR = (220, 220, 255)

TABS = ["Stats", "Spells"]

# Item category display order
CATEGORY_ORDER = ["weapon", "food", "drink", "tool", "scroll", "escort"]
CATEGORY_LABELS = {
    "weapon": "Weapons",
    "food": "Food",
    "drink": "Drinks",
    "tool": "Tools",
    "scroll": "Scrolls",
    "escort": "Escort",
}


class MenuView:
    """Full-screen tabbed player menu with Inventory, Stats, and Spells tabs."""

    def __init__(self, screen, font, player, initial_tab=None):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 40)
        self.player = player
        _tab_map = {"stats": 0, "spells": 1}
        self.active_tab = _tab_map.get(initial_tab, 0) if initial_tab else 0
        self.selected_index = 0
        self.scroll_offset = 0
        self.action_message = ""
        self.action_message_timer = 0

    def draw(self):
        self.screen.fill((20, 20, 30))

        # Tab bar
        self._draw_tabs()

        if self.active_tab == 0:
            self._draw_stats()
        elif self.active_tab == 1:
            self._draw_spells()

        # Controls hint (always at bottom)
        hint = "Tab: Switch Tab  |  Esc: Close"
        hint_surf = self.small_font.render(hint, True, (100, 100, 100))
        self.screen.blit(hint_surf, (10, SCREEN_HEIGHT - 22))

        # Action message (above controls hint)
        if self.action_message and self.action_message_timer > 0:
            msg = self.font.render(self.action_message, True, (100, 255, 100))
            self.screen.blit(msg, ((SCREEN_WIDTH - msg.get_width()) // 2, SCREEN_HEIGHT - 46))
            self.action_message_timer -= 1

    def _draw_tabs(self):
        tab_width = SCREEN_WIDTH // len(TABS)
        for i, tab_name in enumerate(TABS):
            x = i * tab_width
            active = i == self.active_tab
            bg_color = (50, 50, 70) if active else (30, 30, 40)
            pygame.draw.rect(self.screen, bg_color, (x, 0, tab_width, 36))
            pygame.draw.line(self.screen, (80, 80, 100), (x, 0), (x, 36))

            color = TAB_ACTIVE_COLOR if active else TAB_INACTIVE_COLOR
            label = self.font.render(tab_name, True, color)
            self.screen.blit(label, (x + (tab_width - label.get_width()) // 2, 6))

        pygame.draw.line(self.screen, (80, 80, 100), (0, 36), (SCREEN_WIDTH, 36))

    # --- Inventory Tab ---

    def _draw_inventory(self):
        y = 50
        # Gold
        gold = self.font.render(f"Gold: {self.player.money}", True, (220, 190, 60))
        self.screen.blit(gold, (SCREEN_WIDTH - gold.get_width() - 20, y))

        items = list(self.player.inventory.values())
        if not items:
            empty = self.font.render("Your inventory is empty.", True, TEXT_COLOR)
            self.screen.blit(empty, (40, y + 40))
            return

        # Group items by category
        grouped: dict[str, list] = {}
        for item in items:
            cat = item.category.lower()
            grouped.setdefault(cat, []).append(item)

        flat_items = []  # For selection indexing
        for cat in CATEGORY_ORDER:
            if cat in grouped:
                flat_items.append(("header", cat))
                for item in grouped[cat]:
                    flat_items.append(("item", item))
        # Any remaining categories
        for cat, cat_items in grouped.items():
            if cat not in CATEGORY_ORDER:
                flat_items.append(("header", cat))
                for item in cat_items:
                    flat_items.append(("item", item))

        # Count only items (not headers) for selection
        item_indices = [i for i, (kind, _) in enumerate(flat_items) if kind == "item"]
        if item_indices and self.selected_index >= len(item_indices):
            self.selected_index = len(item_indices) - 1

        y = 50
        item_counter = 0
        for kind, entry in flat_items:
            if y > SCREEN_HEIGHT - 80:
                more = self.small_font.render("... (scroll down)", True, (120, 120, 120))
                self.screen.blit(more, (40, y))
                break

            if kind == "header":
                y += 8
                label = CATEGORY_LABELS.get(entry, entry.title())
                header = self.font.render(f"-- {label} --", True, HEADER_COLOR)
                self.screen.blit(header, (40, y))
                y += 28
            else:
                item = entry
                is_selected = item_counter == self.selected_index
                is_equipped = self.player.equipped_weapon == item.name

                prefix = "> " if is_selected else "  "
                equip_tag = "[E] " if is_equipped else ""
                color = SELECTED_COLOR if is_selected else (EQUIPPED_COLOR if is_equipped else TEXT_COLOR)

                name_text = f"{prefix}{equip_tag}{item.quantity}x {item.name}"
                name_surf = self.small_font.render(name_text, True, color)
                self.screen.blit(name_surf, (40, y))

                # Brief effect
                effect_parts = []
                stats = item.item_stats
                if stats.stamina_value:
                    effect_parts.append(f"+{stats.stamina_value} stamina")
                if stats.health_value:
                    effect_parts.append(f"+{stats.health_value} HP")
                if stats.attack_dice:
                    effect_parts.append(f"Dmg:{stats.attack_dice}")
                if effect_parts:
                    effect = "  ".join(effect_parts)
                    effect_surf = self.small_font.render(effect, True, (120, 120, 140))
                    self.screen.blit(effect_surf, (400, y))

                y += 22
                item_counter += 1

        # Controls
        ctrl = "Up/Down: Select  |  Enter/U: Use  |  E: Equip  |  D: Drop"
        ctrl_surf = self.small_font.render(ctrl, True, (100, 100, 100))
        self.screen.blit(ctrl_surf, (40, SCREEN_HEIGHT - 50))

    # --- Stats Tab ---

    def _draw_stats(self):
        p = self.player
        pc = p.player_class
        pad = 20
        tiny_font = pygame.font.Font(None, 20)

        # Header: character name and level
        cls_name = pc.name if pc else "Adventurer"
        header = self.title_font.render(f"{p.name} the {cls_name}", True, HIGHLIGHT_COLOR)
        self.screen.blit(header, ((SCREEN_WIDTH - header.get_width()) // 2, 42))
        level_text = self.small_font.render(
            f"Level {p.level}  |  HP: {p.health}/{p.max_health}  |  "
            f"Stamina: {p.stamina}/{p.max_stamina}  |  Gold: {p.money}",
            True, TEXT_COLOR,
        )
        self.screen.blit(level_text, ((SCREEN_WIDTH - level_text.get_width()) // 2, 72))

        # Load portrait
        portrait_surface = None
        if p.profile_image and os.path.exists(p.profile_image):
            try:
                portrait_surface = pygame.image.load(p.profile_image)
            except Exception:
                pass

        stats = pc.stats if pc else None
        if stats is None:
            return

        weapon_name = p.equipped_weapon or (pc.starting_weapon if pc else "")
        weapon_info = ""
        if p.weapon:
            w = p.weapon
            stat_mod = p.get_stat_mod(w.stat) if hasattr(p, 'get_stat_mod') else 0
            dmg_bonus = w.damage_bonus + stat_mod
            bonus_str = f"+{dmg_bonus}" if dmg_bonus > 0 else (str(dmg_bonus) if dmg_bonus < 0 else "")
            wtype = "Wild" if w.weapon_type == "wild" else w.weapon_type.title()
            weapon_info = (f"{wtype}  |  "
                           f"Hit: {stat_mod:+d} ({w.stat})  |  "
                           f"Dmg: 1d{w.damage_dice}{bonus_str}")
        elif pc:
            from src.models.weapon import STARTER_WEAPONS
            starter = STARTER_WEAPONS.get(pc.archetype)
            if starter:
                stat_mod = p.get_stat_mod(starter.stat) if hasattr(p, 'get_stat_mod') else 0
                dmg_bonus = starter.damage_bonus + stat_mod
                bonus_str = f"+{dmg_bonus}" if dmg_bonus > 0 else (str(dmg_bonus) if dmg_bonus < 0 else "")
                wtype = "Wild" if starter.weapon_type == "wild" else starter.weapon_type.title()
                weapon_info = (f"{wtype}  |  "
                               f"Hit: {stat_mod:+d} ({starter.stat})  |  "
                               f"Dmg: 1d{starter.damage_dice}{bonus_str}")

        flavor = pc.flavor_text if pc else ""
        abilities = list(p.abilities) if p.abilities else []
        spells = list(p.spells) if p.spells else []

        viewport_top = 92
        viewport_bottom = SCREEN_HEIGHT - 26
        viewport_h = viewport_bottom - viewport_top

        content_h = estimate_status_height(stats, flavor, weapon_name, abilities, spells)
        max_scroll = max(0, content_h - viewport_h)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        clip_rect = pygame.Rect(0, viewport_top, SCREEN_WIDTH, viewport_h)
        self.screen.set_clip(clip_rect)

        base_y = viewport_top - self.scroll_offset
        draw_status_layout(
            self.screen, self.font, self.small_font, tiny_font,
            portrait_surface, stats, flavor,
            weapon_name, weapon_info,
            abilities, spells,
            base_y, pad,
        )

        self.screen.set_clip(None)

        if self.scroll_offset > 0:
            arrow = self.small_font.render("\u25b2", True, (120, 120, 120))
            self.screen.blit(arrow, ((SCREEN_WIDTH - arrow.get_width()) // 2, viewport_top + 2))
        if self.scroll_offset < max_scroll:
            arrow = self.small_font.render("\u25bc", True, (120, 120, 120))
            self.screen.blit(arrow, ((SCREEN_WIDTH - arrow.get_width()) // 2, viewport_bottom - 14))

    def _stat_line(self, text: str, color, x: int, y: int):
        surf = self.small_font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def _stat_pair(self, label: str, value: str, x: int, y: int):
        label_surf = self.small_font.render(f"{label}:", True, STAT_LABEL_COLOR)
        value_surf = self.small_font.render(value, True, STAT_VALUE_COLOR)
        self.screen.blit(label_surf, (x, y))
        self.screen.blit(value_surf, (x + 160, y))

    # --- Spells/Abilities Tab ---

    def _draw_spells(self):
        y = 50

        # Spells section
        self._stat_line("-- Spells --", HEADER_COLOR, 40, y)
        y += 28

        if not self.player.spells:
            self._stat_line("No spells known.", TEXT_COLOR, 60, y)
            y += 24
        else:
            for spell in self.player.spells:
                is_learned = spell.name in self.player.learned_spells
                learned_tag = " (Learned)" if is_learned else ""
                name_color = EQUIPPED_COLOR if is_learned else TEXT_COLOR

                # Spell name and type
                spell_type = getattr(spell, 'spell_type', 'unknown')
                element = getattr(spell, 'element', '')
                element_tag = f" [{element}]" if element else ""
                line = f"{spell.name}{learned_tag} - {spell_type}{element_tag}"
                self._stat_line(line, name_color, 60, y)
                y += 20

                # Cost and effect
                s_cost = getattr(spell, 'stamina_cost', 0)
                cost_parts = []
                if s_cost:
                    cost_parts.append(f"Stamina: {s_cost}")
                cost_str = "  |  ".join(cost_parts) if cost_parts else "Free"

                desc = getattr(spell, 'description', '')
                detail = f"Cost: {cost_str}"
                if desc:
                    detail += f"  |  {desc[:50]}"
                detail_surf = self.small_font.render(detail, True, (120, 120, 140))
                self.screen.blit(detail_surf, (80, y))
                y += 24

                if y > SCREEN_HEIGHT - 120:
                    self._stat_line("... (more)", (120, 120, 120), 60, y)
                    break

        y += 12

        # Abilities section
        self._stat_line("-- Abilities --", HEADER_COLOR, 40, y)
        y += 28

        if not self.player.abilities:
            self._stat_line("No abilities known.", TEXT_COLOR, 60, y)
            y += 24
        else:
            for ability in self.player.abilities:
                line = f"{ability.name} ({ability.stat})"
                self._stat_line(line, TEXT_COLOR, 60, y)
                y += 20

                s_cost = getattr(ability, 'stamina_cost', 0)
                cost_parts = []
                if s_cost:
                    cost_parts.append(f"Stamina: {s_cost}")
                cost_str = "  |  ".join(cost_parts) if cost_parts else "Free"

                desc = getattr(ability, 'description', '')
                detail = f"Cost: {cost_str}"
                if desc:
                    detail += f"  |  {desc[:50]}"
                detail_surf = self.small_font.render(detail, True, (120, 120, 140))
                self.screen.blit(detail_surf, (80, y))
                y += 24

                if y > SCREEN_HEIGHT - 60:
                    self._stat_line("... (more)", (120, 120, 120), 60, y)
                    break

    def handle_input(self, event) -> str | None:
        """Returns 'close' on Esc, or None. Handles tab switching and item actions."""
        if event.key == pygame.K_ESCAPE:
            return "close"

        if event.key == pygame.K_TAB:
            self.active_tab = (self.active_tab + 1) % len(TABS)
            self.selected_index = 0
            self.scroll_offset = 0
            return None

        if event.key == pygame.K_UP:
            self.scroll_offset = max(0, self.scroll_offset - 24)
        elif event.key == pygame.K_DOWN:
            self.scroll_offset += 24

        return None

    def _handle_inventory_input(self, event) -> str | None:
        items = list(self.player.inventory.values())
        if not items:
            return None

        if event.key == pygame.K_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif event.key == pygame.K_DOWN:
            self.selected_index = min(len(items) - 1, self.selected_index + 1)
        elif event.key in (pygame.K_RETURN, pygame.K_u):
            self.player.selected_item_index = self.selected_index
            message = self.player.use_item()
            self.action_message = message
            self.action_message_timer = 60
        elif event.key == pygame.K_e:
            inv_list = self.player.get_inventory()
            if self.selected_index < len(inv_list):
                item_name = inv_list[self.selected_index][0]
                message = self.player.equip_weapon(item_name)
                self.action_message = message
                self.action_message_timer = 60
        elif event.key == pygame.K_d:
            inv_list = self.player.get_inventory()
            if self.selected_index < len(inv_list):
                item_name = inv_list[self.selected_index][0]
                self.player.remove_from_inventory(item_name)
                self.action_message = f"Dropped {item_name}."
                self.action_message_timer = 60
                if self.selected_index >= len(self.player.inventory):
                    self.selected_index = max(0, len(self.player.inventory) - 1)
        return None
