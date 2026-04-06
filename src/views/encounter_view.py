"""Encounter view — full-screen UI for puzzle, event, and combat trigger encounters.

Layout:
  1. Header bar with encounter type + name
  2. Portrait image (GenAI or colored placeholder)
  3. Description text
  4. Type-specific content:
     - Combat: monster roster + "Press Enter to begin"
     - Puzzle: choices with tool/stat hints, dice roll, result
     - Event: multi-choice with hints, dice roll, result
  5. Action prompt at bottom
"""

import os
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE

# Colors
RED = (220, 50, 50)
GREEN = (50, 200, 50)
BLUE = (65, 105, 225)
ORANGE = (255, 165, 0)
PURPLE = (128, 60, 180)
DARK_GRAY = (30, 30, 40)
MED_GRAY = (60, 60, 70)
LIGHT_GRAY = (180, 180, 180)
YELLOW = (255, 220, 50)
GOLD = (218, 165, 32)
DIM_WHITE = (200, 200, 210)

TYPE_COLORS = {
    "combat": RED,
    "puzzle": BLUE,
    "event": PURPLE,
}

ELEMENT_COLORS = {
    "fire": RED,
    "water": BLUE,
    "forest": GREEN,
    "light": YELLOW,
    "dark": PURPLE,
}

_PORTRAIT_CACHE_MAX = 64
_portrait_cache: dict[str, pygame.Surface | None] = {}


def _load_portrait(path: str | None, size: tuple[int, int] = (128, 128)) -> pygame.Surface | None:
    if not path:
        return None
    if path in _portrait_cache:
        return _portrait_cache[path]
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, size)
            if len(_portrait_cache) >= _PORTRAIT_CACHE_MAX:
                _portrait_cache.pop(next(iter(_portrait_cache)))
            _portrait_cache[path] = img
            return img
        except Exception:
            pass
    _portrait_cache[path] = None
    return None


class EncounterView:
    """Renders the full-screen encounter UI for all event types."""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.SysFont(None, 20)
        self.title_font = pygame.font.SysFont(None, 36)
        self.big_font = pygame.font.SysFont(None, 48)

    def draw(self, dialogue_box):
        """Draw the encounter screen based on current event state."""
        event = dialogue_box.current_event
        if not event:
            return

        self.screen.fill(DARK_GRAY)

        # Header bar
        self._draw_header(event)

        # Portrait + description area
        content_y = self._draw_portrait_and_description(event)

        # Type-specific content
        if event.type == "combat":
            self._draw_combat_trigger(event, dialogue_box, content_y)
        elif event.type == "puzzle":
            self._draw_puzzle(event, dialogue_box, content_y)
        elif event.type == "event":
            self._draw_event(event, dialogue_box, content_y)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _draw_header(self, event):
        type_color = TYPE_COLORS.get(event.type, LIGHT_GRAY)
        # Header background
        pygame.draw.rect(self.screen, type_color, (0, 0, SCREEN_WIDTH, 44))
        pygame.draw.line(self.screen, WHITE, (0, 44), (SCREEN_WIDTH, 44), 1)

        label = f"  {event.type.upper()} ENCOUNTER"
        label_surf = self.title_font.render(label, True, WHITE)
        self.screen.blit(label_surf, (10, 8))

        name_surf = self.title_font.render(event.name, True, YELLOW)
        self.screen.blit(name_surf, (SCREEN_WIDTH - name_surf.get_width() - 15, 8))

    # ------------------------------------------------------------------
    # Portrait + description
    # ------------------------------------------------------------------

    def _draw_portrait_and_description(self, event) -> int:
        """Draw portrait and description. Returns y position after content."""
        y = 58
        portrait = _load_portrait(getattr(event, 'profile_image', None))

        if portrait:
            # Center portrait
            px = 20
            self.screen.blit(portrait, (px, y))
            pygame.draw.rect(self.screen, LIGHT_GRAY, (px, y, 128, 128), 1)
            desc_x = 165
            desc_max_w = SCREEN_WIDTH - desc_x - 20
        else:
            # Placeholder colored rect
            type_color = TYPE_COLORS.get(event.type, LIGHT_GRAY)
            pygame.draw.rect(self.screen, type_color, (20, y, 128, 128))
            pygame.draw.rect(self.screen, LIGHT_GRAY, (20, y, 128, 128), 1)
            icon_text = event.type[0].upper()
            icon_surf = self.big_font.render(icon_text, True, WHITE)
            icon_rect = icon_surf.get_rect(center=(84, y + 64))
            self.screen.blit(icon_surf, icon_rect)
            desc_x = 165
            desc_max_w = SCREEN_WIDTH - desc_x - 20

        # Difficulty indicator
        diff = getattr(event, 'difficulty', 3)
        diff_text = f"Difficulty: {'*' * min(diff, 10)}"
        diff_surf = self.small_font.render(diff_text, True, GOLD)
        self.screen.blit(diff_surf, (desc_x, y))
        desc_y = y + 22

        # Description text (wrapped)
        lines = self._wrap_text(event.description, self.font, desc_max_w)
        for line in lines:
            surf = self.font.render(line, True, DIM_WHITE)
            self.screen.blit(surf, (desc_x, desc_y))
            desc_y += self.font.get_linesize()

        return max(y + 140, desc_y + 12)

    # ------------------------------------------------------------------
    # Combat trigger screen
    # ------------------------------------------------------------------

    def _draw_combat_trigger(self, event, dialogue_box, y):
        """Combat encounter: show monster roster and begin prompt."""
        monsters = getattr(event, 'monsters', [])

        # Section header
        pygame.draw.line(self.screen, MED_GRAY, (20, y), (SCREEN_WIDTH - 20, y))
        y += 8
        roster_label = self.font.render("Enemies:", True, RED)
        self.screen.blit(roster_label, (20, y))
        y += 24

        if monsters:
            slot_w = min(160, (SCREEN_WIDTH - 60) // max(len(monsters), 1))
            for i, monster in enumerate(monsters):
                mx = 30 + i * slot_w
                self._draw_monster_card(monster, mx, y, slot_w - 10)
        else:
            hint = self.font.render("Unknown foe", True, LIGHT_GRAY)
            self.screen.blit(hint, (30, y))

        # Bottom prompt
        phase = dialogue_box.combat_phase
        if phase == "initiative":
            self._draw_prompt("Press Enter to begin combat  |  Escape to flee", YELLOW)
        elif phase in ("victory", "defeat", "fled"):
            banners = {
                "victory": ("VICTORY!", GREEN),
                "defeat": ("DEFEAT!", RED),
                "fled": ("ESCAPED!", YELLOW),
            }
            text, color = banners[phase]
            self._draw_banner(text, color)
            self._draw_prompt("Press Enter to continue", LIGHT_GRAY)
        else:
            # During combat turns, show combat log + turn info
            self._draw_combat_log(dialogue_box, y + 130)

    def _draw_monster_card(self, monster, x, y, width):
        """Draw a compact monster info card."""
        # Portrait placeholder
        elem = monster.elemental_affinity
        color = ELEMENT_COLORS.get(elem, LIGHT_GRAY)
        pygame.draw.rect(self.screen, color, (x, y, 48, 48))
        pygame.draw.rect(self.screen, WHITE, (x, y, 48, 48), 1)

        # Monster portrait if available
        portrait = _load_portrait(getattr(monster, 'profile_image', None), (48, 48))
        if portrait:
            self.screen.blit(portrait, (x, y))

        # Name
        name_surf = self.small_font.render(monster.display_name, True, WHITE)
        self.screen.blit(name_surf, (x, y + 52))

        # Level + HP
        info = f"Lv{monster.level}  HP:{monster.hp}/{monster.max_hp}  AC:{monster.ac}"
        info_surf = self.small_font.render(info, True, LIGHT_GRAY)
        self.screen.blit(info_surf, (x, y + 68))

        # HP bar
        bar_w = min(width, 120)
        bar_h = 6
        hp_ratio = max(0, monster.hp / monster.max_hp) if monster.max_hp > 0 else 0
        pygame.draw.rect(self.screen, (80, 0, 0), (x, y + 84, bar_w, bar_h))
        pygame.draw.rect(self.screen, RED, (x, y + 84, int(bar_w * hp_ratio), bar_h))
        pygame.draw.rect(self.screen, WHITE, (x, y + 84, bar_w, bar_h), 1)

        # Abilities hint
        if monster.abilities:
            ab_names = ", ".join(a.name for a in monster.abilities[:2])
            ab_surf = self.small_font.render(ab_names, True, ORANGE)
            self.screen.blit(ab_surf, (x, y + 94))

    def _draw_combat_log(self, dialogue_box, y):
        """Draw recent combat log entries."""
        log = dialogue_box.combat_log[-8:]
        pygame.draw.rect(self.screen, BLACK, (15, y - 2, SCREEN_WIDTH - 30, len(log) * 18 + 10))
        pygame.draw.rect(self.screen, MED_GRAY, (15, y - 2, SCREEN_WIDTH - 30, len(log) * 18 + 10), 1)
        for msg in log:
            display = msg[:100] + "..." if len(msg) > 100 else msg
            surf = self.small_font.render(display, True, LIGHT_GRAY)
            self.screen.blit(surf, (20, y))
            y += 18

        # Action hints based on phase
        phase = dialogue_box.combat_phase
        if phase == "player_turn":
            if dialogue_box.player_stunned_turns > 0:
                self._draw_prompt("Stunned! Press Enter to skip turn", ORANGE)
            else:
                self._draw_prompt("[A]ttack  [F]lee  [I]tem  |  Up/Down: select target", BLUE)
        elif phase == "monster_turn":
            self._draw_prompt("Enemy turn... Press Enter", RED)

    # ------------------------------------------------------------------
    # Puzzle encounter
    # ------------------------------------------------------------------

    def _draw_puzzle(self, event, dialogue_box, y):
        """Puzzle encounter: choices, dice roll, result."""
        choices = getattr(event, 'choices', [])
        ctx = dialogue_box.event_context
        result = ctx.get("result")
        selected = ctx.get("selected_choice")

        pygame.draw.line(self.screen, MED_GRAY, (20, y), (SCREEN_WIDTH - 20, y))
        y += 8

        if result:
            # Show result
            self._draw_dice_result(ctx, y)
            y += 50
            success = result.get("success", False)
            color = GREEN if success else RED
            msg = result.get("message", "")
            for line in self._wrap_text(msg, self.font, SCREEN_WIDTH - 60):
                surf = self.font.render(line, True, color)
                self.screen.blit(surf, (30, y))
                y += self.font.get_linesize()
            self._draw_prompt("Press Enter or Escape to continue", LIGHT_GRAY)

        elif dialogue_box.awaiting_roll:
            # Show selected choice, awaiting dice roll
            if selected is not None and selected < len(choices):
                chosen = choices[selected]
                choice_surf = self.font.render(f"Selected: {chosen.text}", True, YELLOW)
                self.screen.blit(choice_surf, (30, y))
                y += 28
                # Show DC hint
                dc_text = f"DC: {chosen.dc}"
                if chosen.stat_check:
                    dc_text += f"  [{chosen.stat_check} check]"
                if chosen.tool_attribute:
                    dc_text += f"  [tool: {chosen.tool_attribute}]"
                dc_surf = self.small_font.render(dc_text, True, LIGHT_GRAY)
                self.screen.blit(dc_surf, (30, y))
                y += 24

            self._draw_prompt("Press R to roll (1d20)  |  Escape to leave", YELLOW)

        else:
            # Show choices
            label = self.font.render("What do you do?", True, WHITE)
            self.screen.blit(label, (30, y))
            y += 26

            for i, choice in enumerate(choices):
                # Choice text
                text = f"  {i + 1}. {choice.text}"
                choice_color = BLUE
                choice_surf = self.font.render(text, True, choice_color)
                self.screen.blit(choice_surf, (30, y))

                # Hints on the right side
                hints = []
                if choice.stat_check:
                    hints.append(f"[{choice.stat_check}]")
                if choice.tool_attribute:
                    hints.append(f"[needs: {choice.tool_attribute}]")
                if choice.auto_success:
                    hints.append("[safe]")
                if hints:
                    hint_text = "  ".join(hints)
                    hint_surf = self.small_font.render(hint_text, True, GOLD)
                    self.screen.blit(hint_surf, (SCREEN_WIDTH - hint_surf.get_width() - 30, y + 3))

                y += 24

            y += 8
            num = min(len(choices), 9)
            self._draw_prompt(f"Press 1-{num} to choose  |  Escape to leave", LIGHT_GRAY)

    # ------------------------------------------------------------------
    # Event encounter
    # ------------------------------------------------------------------

    def _draw_event(self, event, dialogue_box, y):
        """Event encounter: multi-choice with hints, dice, result."""
        choices = getattr(event, 'choices', [])
        ctx = dialogue_box.event_context
        result = ctx.get("result")
        selected = ctx.get("selected_choice")

        pygame.draw.line(self.screen, MED_GRAY, (20, y), (SCREEN_WIDTH - 20, y))
        y += 8

        if result:
            self._draw_dice_result(ctx, y)
            y += 50
            success = result.get("success", False)
            color = GREEN if success else RED
            msg = result.get("message", "")
            for line in self._wrap_text(msg, self.font, SCREEN_WIDTH - 60):
                surf = self.font.render(line, True, color)
                self.screen.blit(surf, (30, y))
                y += self.font.get_linesize()

            # Show consequence details
            if not success and result.get("damage"):
                dmg_text = f"Lost {result['damage']} {result.get('damage_type', 'health')}"
                dmg_surf = self.small_font.render(dmg_text, True, RED)
                self.screen.blit(dmg_surf, (30, y + 4))

            self._draw_prompt("Press Enter or Escape to continue", LIGHT_GRAY)

        elif dialogue_box.awaiting_roll:
            if selected is not None and selected < len(choices):
                chosen = choices[selected]
                choice_surf = self.font.render(f"Selected: {chosen.text}", True, YELLOW)
                self.screen.blit(choice_surf, (30, y))
                y += 28
                dc_text = f"DC: {chosen.dc}"
                if chosen.stat_check:
                    dc_text += f"  [{chosen.stat_check} check]"
                if chosen.tool_attribute:
                    dc_text += f"  [tool: {chosen.tool_attribute}]"
                dc_surf = self.small_font.render(dc_text, True, LIGHT_GRAY)
                self.screen.blit(dc_surf, (30, y))

            self._draw_prompt("Press R to roll (1d20)  |  Escape to leave", YELLOW)

        else:
            label = self.font.render("Choose your action:", True, WHITE)
            self.screen.blit(label, (30, y))
            y += 26

            for i, choice in enumerate(choices):
                text = f"  {i + 1}. {choice.text}"
                choice_surf = self.font.render(text, True, PURPLE)
                self.screen.blit(choice_surf, (30, y))

                hints = []
                if choice.stat_check:
                    hints.append(f"[{choice.stat_check} check]")
                if choice.tool_attribute:
                    hints.append(f"[requires {choice.tool_attribute}]")
                if choice.auto_success:
                    hints.append("[safe]")
                if hints:
                    hint_text = "  ".join(hints)
                    hint_surf = self.small_font.render(hint_text, True, GOLD)
                    self.screen.blit(hint_surf, (SCREEN_WIDTH - hint_surf.get_width() - 30, y + 3))

                y += 24

            y += 8
            num = min(len(choices), 9)
            self._draw_prompt(f"Press 1-{num} to choose  |  Escape to walk away", LIGHT_GRAY)

    # ------------------------------------------------------------------
    # Shared drawing helpers
    # ------------------------------------------------------------------

    def _draw_dice_result(self, ctx, y):
        """Draw the dice roll result display."""
        roll = ctx.get("dice_roll", 0)
        if not roll:
            return

        # Dice icon area
        dice_x = 30
        pygame.draw.rect(self.screen, WHITE, (dice_x, y, 36, 36), border_radius=4)
        roll_surf = self.title_font.render(str(roll), True, BLACK)
        roll_rect = roll_surf.get_rect(center=(dice_x + 18, y + 18))
        self.screen.blit(roll_surf, roll_rect)

        roll_label = self.font.render(f"Rolled: {roll}", True, WHITE)
        self.screen.blit(roll_label, (dice_x + 44, y + 8))

    def _draw_banner(self, text, color):
        """Draw a large centered banner text."""
        surf = self.big_font.render(text, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        # Backdrop
        backdrop = pygame.Surface((rect.width + 60, rect.height + 30))
        backdrop.set_alpha(200)
        backdrop.fill(BLACK)
        self.screen.blit(backdrop, (rect.x - 30, rect.y - 15))
        self.screen.blit(surf, rect)

    def _draw_prompt(self, text, color):
        """Draw action prompt at the bottom of the screen."""
        prompt_y = SCREEN_HEIGHT - 35
        # Background strip
        pygame.draw.rect(self.screen, BLACK, (0, prompt_y - 5, SCREEN_WIDTH, 40))
        pygame.draw.line(self.screen, MED_GRAY, (0, prompt_y - 5), (SCREEN_WIDTH, prompt_y - 5))
        surf = self.font.render(text, True, color)
        self.screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, prompt_y))

    def _wrap_text(self, text, font, max_width):
        """Wrap text to fit within max_width."""
        if not text:
            return []
        words = text.split(' ')
        lines = []
        current = ''
        for word in words:
            test = current + (' ' if current else '') + word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
