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

import pygame

from config import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.views.portrait_utils import load_portrait as _load_portrait

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


class EncounterView:
    """Renders the full-screen encounter UI for all event types."""

    PORTRAIT_SIZE = (350, 250)
    HEADER_H = 44
    PROMPT_H = 40

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.SysFont(None, 20)
        self.title_font = pygame.font.SysFont(None, 36)
        self.big_font = pygame.font.SysFont(None, 48)
        self.content_scroll = 0
        self._max_content_h = 0
        self._choice_y_positions: list[int] = []
        self._scroll_top = self.HEADER_H + 12

    def reset_scroll(self):
        """Reset scroll state for a new encounter."""
        self.content_scroll = 0
        self._choice_y_positions = []
        self._max_content_h = 0

    def draw(self, dialogue_box):
        """Draw the encounter screen based on current event state."""
        event = dialogue_box.current_event
        if not event:
            return

        self.screen.fill(DARK_GRAY)
        self._draw_header(event)

        portrait_bottom = self._draw_portrait(event, self.HEADER_H + 12)

        self._scroll_top = portrait_bottom
        clip_bottom = SCREEN_HEIGHT - self.PROMPT_H
        clip_rect = pygame.Rect(0, self._scroll_top, SCREEN_WIDTH, clip_bottom - self._scroll_top)
        self.screen.set_clip(clip_rect)

        content_y = self._scroll_top + 4 - self.content_scroll
        content_y = self._draw_description(event, content_y)

        if event.type == "puzzle":
            self._draw_puzzle(event, dialogue_box, content_y)
        elif event.type == "event":
            self._draw_event(event, dialogue_box, content_y)

        self.screen.set_clip(None)

    def scroll_content(self, direction: int):
        """Scroll the description+choices area. Positive = down."""
        self.content_scroll = max(0, self.content_scroll + direction * 20)
        viewport_h = SCREEN_HEIGHT - self.PROMPT_H - self._scroll_top
        max_scroll = max(0, self._max_content_h - viewport_h)
        self.content_scroll = min(self.content_scroll, max_scroll)

    def ensure_choice_visible(self, index: int):
        """Auto-scroll so the highlighted choice is visible below the portrait."""
        if not self._choice_y_positions or index >= len(self._choice_y_positions):
            return
        abs_y = self._choice_y_positions[index]
        viewport_h = SCREEN_HEIGHT - self.PROMPT_H - self._scroll_top
        content_y = abs_y - self._scroll_top
        line_h = self.font.get_linesize() + self.small_font.get_linesize()
        if content_y + line_h > self.content_scroll + viewport_h:
            self.content_scroll = content_y + line_h - viewport_h + 10
        elif content_y < self.content_scroll:
            self.content_scroll = max(0, content_y - 10)

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
    # Portrait (fixed, never scrolls)
    # ------------------------------------------------------------------

    def _draw_portrait(self, event, y: int = 58) -> int:
        """Draw portrait centered. Returns y position after portrait (fixed zone bottom)."""
        pw, ph = self.PORTRAIT_SIZE
        portrait = _load_portrait(getattr(event, "profile_image", None), size=self.PORTRAIT_SIZE)

        if portrait:
            px = (SCREEN_WIDTH - pw) // 2
            self.screen.blit(portrait, (px, y))
            y += ph + 6
        else:
            type_color = TYPE_COLORS.get(event.type, LIGHT_GRAY)
            px = (SCREEN_WIDTH - pw) // 2
            pygame.draw.rect(self.screen, type_color, (px, y, pw, ph))
            icon_text = event.type[0].upper()
            icon_surf = self.big_font.render(icon_text, True, WHITE)
            icon_rect = icon_surf.get_rect(center=(px + pw // 2, y + ph // 2))
            self.screen.blit(icon_surf, icon_rect)
            y += ph + 6

        return y

    # ------------------------------------------------------------------
    # Description (scrollable)
    # ------------------------------------------------------------------

    def _draw_description(self, event, y: int) -> int:
        """Draw difficulty + description text. Returns y after content."""
        desc_x = 30
        desc_max_w = SCREEN_WIDTH - 60

        diff = getattr(event, "difficulty", 3)
        diff_text = f"Difficulty: {'*' * min(diff, 10)}"
        diff_surf = self.small_font.render(diff_text, True, GOLD)
        self.screen.blit(diff_surf, (desc_x, y))
        y += 22

        lines = self._wrap_text(event.description, self.font, desc_max_w)
        for line in lines:
            surf = self.font.render(line, True, DIM_WHITE)
            self.screen.blit(surf, (desc_x, y))
            y += self.font.get_linesize()

        return y + 12

    # ------------------------------------------------------------------
    # Puzzle encounter
    # ------------------------------------------------------------------

    def _draw_puzzle(self, event, dialogue_box, y):
        """Puzzle encounter: dynamic choices (tool/ability prepended), dice roll, result."""
        choices = getattr(event, "choices", [])
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
                y += 24

            self._draw_prompt("Press R to roll (1d20)  |  Escape to leave", YELLOW)

        else:
            label = self.font.render("What do you do?", True, WHITE)
            self.screen.blit(label, (30, y))
            y += 26

            rendered = self._build_puzzle_choices(event, dialogue_box)
            ctx["rendered_choices"] = rendered
            highlight = ctx.get("highlight", 0)
            self._choice_y_positions = []

            max_text_w = SCREEN_WIDTH - 80

            for i, rc in enumerate(rendered):
                self._choice_y_positions.append(y + self.content_scroll)
                available = rc.get("available", True)
                is_highlighted = i == highlight
                prefix = "> " if is_highlighted else "  "
                text = f"{prefix}{i + 1}. {rc['text']}"

                if is_highlighted:
                    choice_color = YELLOW
                elif available:
                    choice_color = BLUE
                else:
                    choice_color = MED_GRAY

                lines = self._wrap_text(text, self.font, max_text_w)
                for line in lines:
                    choice_surf = self.font.render(line, True, choice_color)
                    self.screen.blit(choice_surf, (30, y))
                    y += self.font.get_linesize()
                if rc.get("hint"):
                    hint_surf = self.small_font.render(rc["hint"], True, GOLD)
                    self.screen.blit(hint_surf, (50, y))
                    y += self.small_font.get_linesize()

            self._max_content_h = y + self.content_scroll
            y += 8
            self._draw_prompt("Up/Down to select  |  Enter to choose  |  Escape to leave", LIGHT_GRAY)

    def _build_puzzle_choices(self, event, dialogue_box) -> list[dict]:
        """Build rendered choice list for puzzles with unified 5-slot structure."""
        rendered = []
        player = self._get_player(dialogue_box)

        if getattr(event, "correct_ability", None) and player:
            ability = event._find_matching_ability(player)
            if ability:
                cost = getattr(ability, "stamina_cost", 0)
                text = getattr(event, "ability_text", None) or f"Use {ability.name}"
                rendered.append(
                    {
                        "text": text,
                        "kind": "ability",
                        "hint": f"[ability: {ability.name}, -{cost} stam]",
                        "available": True,
                        "choice_idx": -1,
                    }
                )

        if getattr(event, "correct_spell", None) and player:
            spell = event._find_spell(player)
            if spell:
                cost = getattr(spell, "stamina_cost", 0)
                text = getattr(event, "spell_text", None) or f"Cast {spell.name}"
                rendered.append(
                    {
                        "text": text,
                        "kind": "spell",
                        "hint": f"[spell: {spell.name}, -{cost} stam]",
                        "available": True,
                        "choice_idx": -1,
                    }
                )

        for i, choice in enumerate(getattr(event, "choices", [])):
            hints = []
            if choice.stat_check:
                hints.append(f"[{choice.stat_check}]")
            if choice.tool_attribute:
                hints.append(f"[+5 with {choice.tool_attribute} tool]")
            if choice.auto_success:
                hints.append("[safe]")
            rendered.append(
                {
                    "text": choice.text,
                    "kind": "walk_away" if choice.auto_success else "stat",
                    "hint": "  ".join(hints) if hints else "",
                    "available": True,
                    "choice_idx": i,
                }
            )

        return rendered

    # ------------------------------------------------------------------
    # Event encounter
    # ------------------------------------------------------------------

    def _draw_event(self, event, dialogue_box, y):
        """Event encounter: 5-slot structured choices with availability."""
        choices = getattr(event, "choices", [])
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

            rendered = self._build_event_choices(event, dialogue_box)
            ctx["rendered_choices"] = rendered
            highlight = ctx.get("highlight", 0)
            self._choice_y_positions = []

            max_text_w = SCREEN_WIDTH - 80

            for i, rc in enumerate(rendered):
                self._choice_y_positions.append(y + self.content_scroll)
                available = rc.get("available", True)
                is_highlighted = i == highlight
                prefix = "> " if is_highlighted else "  "
                text = f"{prefix}{i + 1}. {rc['text']}"

                if is_highlighted:
                    choice_color = YELLOW
                elif available:
                    choice_color = PURPLE
                else:
                    choice_color = MED_GRAY

                lines = self._wrap_text(text, self.font, max_text_w)
                for line in lines:
                    choice_surf = self.font.render(line, True, choice_color)
                    self.screen.blit(choice_surf, (30, y))
                    y += self.font.get_linesize()
                if rc.get("hint"):
                    hint_color = GOLD if available else MED_GRAY
                    hint_surf = self.small_font.render(rc["hint"], True, hint_color)
                    self.screen.blit(hint_surf, (50, y))
                    y += self.small_font.get_linesize()

            self._max_content_h = y + self.content_scroll
            y += 8
            self._draw_prompt("Up/Down to select  |  Enter to choose  |  Escape to walk away", LIGHT_GRAY)

    def _build_event_choices(self, event, dialogue_box) -> list[dict]:
        """Build rendered choice list for events with unified 5-slot structure."""
        rendered = []
        player = self._get_player(dialogue_box)
        choices = getattr(event, "choices", [])

        if event.correct_ability:
            ability = event._find_ability(player) if player else None
            if ability:
                cost = getattr(ability, "stamina_cost", 0)
                text = getattr(event, "ability_text", None) or f"Use {ability.name}"
                rendered.append(
                    {
                        "text": text,
                        "kind": "ability",
                        "hint": f"[ability: {ability.name}, -{cost} stam]",
                        "available": True,
                        "choice_idx": -1,
                    },
                )

        if event.correct_spell:
            spell = event._find_spell(player) if player else None
            if spell:
                cost = getattr(spell, "stamina_cost", 0)
                text = getattr(event, "spell_text", None) or f"Cast {spell.name}"
                rendered.append(
                    {
                        "text": text,
                        "kind": "spell",
                        "hint": f"[spell: {spell.name}, -{cost} stam]",
                        "available": True,
                        "choice_idx": -1,
                    },
                )

        for i, choice in enumerate(choices):
            hints = []
            if choice.stat_check:
                hints.append(f"[{choice.stat_check}]")
            if choice.tool_attribute:
                hints.append(f"[+5 with {choice.tool_attribute} tool]")
            if choice.auto_success:
                hints.append("[safe]")
            rendered.append(
                {
                    "text": choice.text,
                    "kind": "walk_away" if choice.auto_success else "stat",
                    "hint": "  ".join(hints) if hints else "",
                    "available": True,
                    "choice_idx": i,
                }
            )

        return rendered

    # ------------------------------------------------------------------
    # Shared drawing helpers
    # ------------------------------------------------------------------

    def _draw_dice_result(self, ctx, y):
        """Draw the dice roll result display with DC comparison."""
        roll = ctx.get("dice_roll", 0)
        if not roll:
            return

        result = ctx.get("result", {})
        walked_away = result.get("walked_away", False)
        auto_solved = result.get("auto_solved", False)

        dice_x = 30
        pygame.draw.rect(self.screen, MED_GRAY, (dice_x, y, 36, 36), border_radius=4)
        pygame.draw.rect(self.screen, LIGHT_GRAY, (dice_x, y, 36, 36), width=2, border_radius=4)
        roll_surf = self.title_font.render(str(roll), True, WHITE)
        roll_rect = roll_surf.get_rect(center=(dice_x + 18, y + 18))
        self.screen.blit(roll_surf, roll_rect)

        if walked_away or auto_solved:
            roll_label = self.font.render(f"Rolled: {roll}", True, WHITE)
            self.screen.blit(roll_label, (dice_x + 44, y + 8))
        else:
            dc = ctx.get("roll_dc", 0)
            total = ctx.get("roll_total", roll)
            raw = ctx.get("roll_raw", roll)
            mod = ctx.get("roll_modifier", 0)
            success = result.get("success", False)
            vs_color = GREEN if success else RED
            vs_text = f"DC {dc}  vs  Roll {total}"
            if mod != 0:
                vs_text += f"  (d20: {raw} + mod: {mod:+d})"
            vs_surf = self.font.render(vs_text, True, vs_color)
            self.screen.blit(vs_surf, (dice_x + 44, y + 8))

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

    @staticmethod
    def _get_player(dialogue_box):
        """Extract the player from the dialogue_box's game controller, if available."""
        return getattr(dialogue_box, "player", None)

    def _wrap_text(self, text, font, max_width):
        """Wrap text to fit within max_width."""
        if not text:
            return []
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
