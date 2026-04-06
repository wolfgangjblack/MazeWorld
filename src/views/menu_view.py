"""Tabbed player menu view — Inventory, Stats, Spells/Abilities tabs."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT

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

TABS = ["Inventory", "Stats", "Spells"]

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

    def __init__(self, screen, font, player):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 40)
        self.player = player
        self.active_tab = 0
        self.selected_index = 0
        self.scroll_offset = 0
        self.action_message = ""
        self.action_message_timer = 0

    def draw(self):
        self.screen.fill((20, 20, 30))

        # Tab bar
        self._draw_tabs()

        # Content area
        if self.active_tab == 0:
            self._draw_inventory()
        elif self.active_tab == 1:
            self._draw_stats()
        elif self.active_tab == 2:
            self._draw_spells()

        # Action message
        if self.action_message and self.action_message_timer > 0:
            msg = self.font.render(self.action_message, True, (100, 255, 100))
            self.screen.blit(msg, ((SCREEN_WIDTH - msg.get_width()) // 2, SCREEN_HEIGHT - 30))
            self.action_message_timer -= 1

        # Controls hint
        hint = "Tab: Switch Tab  |  Esc: Close"
        hint_surf = self.small_font.render(hint, True, (100, 100, 100))
        self.screen.blit(hint_surf, (10, SCREEN_HEIGHT - 20))

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
                if stats.nutrition_value:
                    effect_parts.append(f"+{stats.nutrition_value} food")
                if stats.hydration_value:
                    effect_parts.append(f"+{stats.hydration_value} water")
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
        y = 50
        col1 = 40
        col2 = SCREEN_WIDTH // 2 + 20

        # Character info
        cls_name = pc.name if pc else "Adventurer"
        env = pc.environment if pc else "Unknown"
        self._stat_line(f"{p.name} the {cls_name}", HIGHLIGHT_COLOR, col1, y)
        y += 28
        self._stat_line(f"Level {p.level}  |  {env}", TEXT_COLOR, col1, y)
        y += 36

        # Stat array
        self._stat_line("-- Attributes --", HEADER_COLOR, col1, y)
        y += 24
        if pc:
            stats_dict = pc.stats.as_dict()
            for stat_name, val in stats_dict.items():
                mod = pc.stats.modifier(stat_name)
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
                self._stat_pair(stat_name, f"{val} ({mod_str})", col1, y)
                y += 22
        y += 10

        # Derived stats
        self._stat_line("-- Derived Stats --", HEADER_COLOR, col1, y)
        y += 24
        ac = p.get_ac()
        atk_mod = p.get_stat_mod("STR")
        spell_stat = "WIS" if (pc and pc.archetype == "healer") else "INT"
        spell_mod = p.get_stat_mod(spell_stat)
        self._stat_pair("AC", str(ac), col1, y)
        y += 22
        atk_str = f"+{atk_mod}" if atk_mod >= 0 else str(atk_mod)
        self._stat_pair("Attack Mod", atk_str, col1, y)
        y += 22
        spell_str = f"+{spell_mod}" if spell_mod >= 0 else str(spell_mod)
        self._stat_pair(f"Spell Mod ({spell_stat})", spell_str, col1, y)
        y += 30

        # Right column: Survival and Records
        y2 = 50
        self._stat_line("-- Survival --", HEADER_COLOR, col2, y2)
        y2 += 24
        self._stat_pair("HP", f"{p.health}/{p.max_health}", col2, y2)
        y2 += 22
        self._stat_pair("Hunger", f"{p.hunger}/{p.max_hunger}", col2, y2)
        y2 += 22
        self._stat_pair("Thirst", f"{p.thirst}/{p.max_thirst}", col2, y2)
        y2 += 36

        self._stat_line("-- Quest Record --", HEADER_COLOR, col2, y2)
        y2 += 24
        self._stat_pair("Active", str(len(p.active_quests)), col2, y2)
        y2 += 22
        self._stat_pair("Completed", str(len(p.completed_quests)), col2, y2)
        y2 += 22
        self._stat_pair("Failed", str(len(p.failed_quests)), col2, y2)
        y2 += 36

        self._stat_line("-- Equipment --", HEADER_COLOR, col2, y2)
        y2 += 24
        weapon_name = p.equipped_weapon or "(none)"
        self._stat_pair("Weapon", weapon_name, col2, y2)
        y2 += 22
        self._stat_pair("Gold", str(p.money), col2, y2)

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
                h_cost = getattr(spell, 'cost_hunger', getattr(spell, 'hunger_cost', 0))
                t_cost = getattr(spell, 'cost_thirst', getattr(spell, 'thirst_cost', 0))
                cost_parts = []
                if h_cost:
                    cost_parts.append(f"Hunger: {h_cost}")
                if t_cost:
                    cost_parts.append(f"Thirst: {t_cost}")
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

                h_cost = getattr(ability, 'cost_hunger', 0)
                t_cost = getattr(ability, 'cost_thirst', 0)
                cost_parts = []
                if h_cost:
                    cost_parts.append(f"Hunger: {h_cost}")
                if t_cost:
                    cost_parts.append(f"Thirst: {t_cost}")
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

        # Inventory-specific controls
        if self.active_tab == 0:
            return self._handle_inventory_input(event)

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
