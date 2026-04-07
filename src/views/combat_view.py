"""Combat view — renders the turn-based combat UI in Pygame.

Layout (top to bottom):
  1. Monster area: portraits (colored rects for now), names, HP bars
  2. Turn order indicator
  3. Player stats bar (HP, hunger, thirst)
  4. Action menu (when it's the player's turn)
  5. Combat log (last N messages)
"""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE
from src.controllers.combat_controller import CombatController
from src.models.combat import CombatState

# Colors
RED = (220, 50, 50)
GREEN = (50, 200, 50)
BLUE = (65, 105, 225)
ORANGE = (255, 165, 0)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (180, 180, 180)
YELLOW = (255, 220, 50)


class CombatView:
    """Renders combat state to a Pygame surface."""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.SysFont(None, 20)
        self.log_font = pygame.font.SysFont(None, 18)

    def draw(self, combat: CombatController, selected_action: int = 0,
             selected_target: int = 0, selecting_target: bool = False,
             selecting_spell: bool = False, selected_spell: int = 0,
             selecting_item: bool = False, selected_item: int = 0,
             game_over_selection: int = 0):
        """Draw the full combat screen."""
        self.screen.fill(DARK_GRAY)
        self._draw_monsters(combat)
        self._draw_turn_order(combat)
        self._draw_player_stats(combat.player)
        self._draw_action_menu(combat, selected_action, selected_target,
                               selecting_target, selecting_spell, selected_spell,
                               selecting_item, selected_item)
        self._draw_combat_log(combat)
        self._draw_state_banner(combat, game_over_selection)

    # ------------------------------------------------------------------
    # Monster area
    # ------------------------------------------------------------------

    def _draw_monsters(self, combat: CombatController):
        alive = [m for m in combat.monsters if m.is_alive]
        if not alive:
            return

        area_y = 30
        slot_width = min(160, (SCREEN_WIDTH - 40) // max(len(alive), 1))

        for i, monster in enumerate(alive):
            x = 20 + i * slot_width
            # Portrait placeholder (colored rect)
            color = RED if monster.elemental_affinity == "fire" else \
                    BLUE if monster.elemental_affinity == "water" else \
                    GREEN if monster.elemental_affinity == "forest" else \
                    YELLOW if monster.elemental_affinity == "light" else \
                    (100, 50, 150) if monster.elemental_affinity == "dark" else \
                    LIGHT_GRAY
            pygame.draw.rect(self.screen, color, (x, area_y, 50, 50))
            pygame.draw.rect(self.screen, WHITE, (x, area_y, 50, 50), 1)

            # Name
            name_surf = self.small_font.render(monster.display_name, True, WHITE)
            self.screen.blit(name_surf, (x, area_y + 55))

            # HP bar
            bar_w = slot_width - 20
            bar_h = 8
            bar_x = x
            bar_y = area_y + 72
            hp_ratio = max(0, monster.hp / monster.max_hp)
            pygame.draw.rect(self.screen, (80, 0, 0), (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(self.screen, RED, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))
            pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)

            hp_text = self.small_font.render(f"{monster.hp}/{monster.max_hp}", True, WHITE)
            self.screen.blit(hp_text, (bar_x, bar_y + 10))

    # ------------------------------------------------------------------
    # Turn order
    # ------------------------------------------------------------------

    def _draw_turn_order(self, combat: CombatController):
        y = 130
        label = self.font.render("Turn Order:", True, YELLOW)
        self.screen.blit(label, (20, y))

        x = 160
        for c in combat.combatants:
            if not c.is_alive:
                continue
            is_current = c is combat.current_combatant()
            color = YELLOW if is_current else LIGHT_GRAY
            prefix = "> " if is_current else "  "
            text = self.small_font.render(f"{prefix}{c.name} ({c.initiative})", True, color)
            self.screen.blit(text, (x, y + 3))
            x += text.get_width() + 15

    # ------------------------------------------------------------------
    # Player stats
    # ------------------------------------------------------------------

    def _draw_player_stats(self, player):
        y = 165
        bar_w = 150
        bar_h = 14

        stats = [
            ("HP", player.health, player.max_health, RED),
            ("Hunger", player.hunger, player.max_hunger, ORANGE),
            ("Thirst", player.thirst, player.max_thirst, BLUE),
        ]

        for i, (label, current, maximum, color) in enumerate(stats):
            x = 20 + i * (bar_w + 40)
            lbl = self.small_font.render(label, True, WHITE)
            self.screen.blit(lbl, (x, y))
            ratio = max(0, current / maximum) if maximum > 0 else 0
            pygame.draw.rect(self.screen, (50, 50, 50), (x, y + 18, bar_w, bar_h))
            pygame.draw.rect(self.screen, color, (x, y + 18, int(bar_w * ratio), bar_h))
            pygame.draw.rect(self.screen, WHITE, (x, y + 18, bar_w, bar_h), 1)
            val = self.small_font.render(f"{int(current)}/{maximum}", True, WHITE)
            self.screen.blit(val, (x + bar_w + 5, y + 16))

    # ------------------------------------------------------------------
    # Action menu
    # ------------------------------------------------------------------

    ACTIONS = ["Attack", "Multi-Attack", "Cast Spell", "Use Item", "Flee", "Swap Weapon", "Gamble"]

    def _draw_action_menu(self, combat: CombatController, selected: int,
                          selected_target: int, selecting_target: bool,
                          selecting_spell: bool = False, selected_spell: int = 0,
                          selecting_item: bool = False, selected_item: int = 0):
        y = 220
        if not combat.is_player_turn() or combat.state != CombatState.ONGOING:
            hint = self.font.render("Enemy turn..." if combat.state == CombatState.ONGOING else "", True, LIGHT_GRAY)
            self.screen.blit(hint, (20, y))
            return

        if selecting_spell:
            self._draw_spell_selector(combat, y, selected_spell)
            return

        if selecting_item:
            self._draw_item_selector(combat, y, selected_item)
            return

        if selecting_target:
            self._draw_target_selector(combat, y, selected_target)
            return

        label = self.font.render("Choose action:", True, WHITE)
        self.screen.blit(label, (20, y))

        actions = list(self.ACTIONS)
        if not combat.player.player_class or combat.player.player_class.archetype != "jester":
            actions = actions[:-1]  # remove Gamble for non-jesters

        for i, action in enumerate(actions):
            color = YELLOW if i == selected else LIGHT_GRAY
            prefix = "> " if i == selected else "  "
            text = self.font.render(f"{prefix}{action}", True, color)
            self.screen.blit(text, (30, y + 28 + i * 24))

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
        for i, spell in enumerate(spells):
            color = YELLOW if i == selected_spell else LIGHT_GRAY
            prefix = "> " if i == selected_spell else "  "
            cost_parts = []
            if spell.hunger_cost:
                cost_parts.append(f"{spell.hunger_cost} hunger")
            if spell.thirst_cost:
                cost_parts.append(f"{spell.thirst_cost} thirst")
            cost_str = ", ".join(cost_parts) if cost_parts else "free"
            text = self.font.render(
                f"{prefix}{spell.name}  [{spell.element}]  ({cost_str})", True, color)
            self.screen.blit(text, (30, y + 28 + i * 24))

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
    # Combat log
    # ------------------------------------------------------------------

    def _draw_combat_log(self, combat: CombatController):
        log_y = SCREEN_HEIGHT - 160
        pygame.draw.rect(self.screen, BLACK, (10, log_y - 5, SCREEN_WIDTH - 20, 155))
        pygame.draw.rect(self.screen, LIGHT_GRAY, (10, log_y - 5, SCREEN_WIDTH - 20, 155), 1)

        label = self.small_font.render("Combat Log", True, YELLOW)
        self.screen.blit(label, (15, log_y))

        recent = combat.log[-7:]  # show last 7 messages
        for i, msg in enumerate(recent):
            # Truncate long messages
            display = msg[:90] + "..." if len(msg) > 90 else msg
            text = self.log_font.render(display, True, LIGHT_GRAY)
            self.screen.blit(text, (15, log_y + 18 + i * 18))

    # ------------------------------------------------------------------
    # State banner (victory / defeat / fled)
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

        # Semi-transparent backdrop
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

    # ------------------------------------------------------------------
    # Game Over screen (defeat only)
    # ------------------------------------------------------------------

    GAME_OVER_OPTIONS = ["Load Save", "Quit to Menu"]

    def _draw_game_over_menu(self, y: int, selected: int = 0):
        """Show load/quit options after defeat."""
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
