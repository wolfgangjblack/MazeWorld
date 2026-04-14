import pygame

from config import (
    BLACK,
    DIALOGUE_BOX_HEIGHT,
    DIALOGUE_BOX_HEIGHT_ACTIVE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WHITE,
)
from src.views.portrait_utils import load_portrait


class DialogueBoxView:
    def __init__(self, screen, font):
        self.font = font
        self.screen = screen

    def draw(self, dialogue_box):
        """Render the dialogue box and its contents."""
        if dialogue_box.event_active:
            if dialogue_box.combat_active:
                self._draw_combat(dialogue_box)
            else:
                self._draw_event(dialogue_box)
            return

        if dialogue_box.dialogue_active:
            dialogue_box_height = DIALOGUE_BOX_HEIGHT_ACTIVE
        else:
            dialogue_box_height = DIALOGUE_BOX_HEIGHT

        padding = 10
        dialogue_box_rect = pygame.Rect(
            0,
            SCREEN_HEIGHT - dialogue_box_height,
            SCREEN_WIDTH,
            dialogue_box_height,
        )
        pygame.draw.rect(self.screen, WHITE, dialogue_box_rect)

        line_height = self.font.get_linesize()
        input_prompt_height = line_height + padding
        available_height = dialogue_box_height - input_prompt_height - padding

        if dialogue_box.item_message:
            item_text_surface = self.font.render(dialogue_box.item_message, True, BLACK)
            self.screen.blit(item_text_surface, (10, SCREEN_HEIGHT - dialogue_box_height + padding))
        elif dialogue_box.current_npc:
            y = SCREEN_HEIGHT - dialogue_box_height + padding
            portrait_offset = 0

            npc = dialogue_box.current_npc
            portrait = load_portrait(getattr(npc, "profile_image", None))
            if portrait:
                self.screen.blit(portrait, (padding, y))
                portrait_offset = 74

            header = f"--- {npc.name} ({npc.job}) ---"
            header_surface = self.font.render(header, True, BLACK)
            header_x = (SCREEN_WIDTH - header_surface.get_width()) // 2
            self.screen.blit(header_surface, (header_x, y))
            y += line_height
            available_height -= line_height

            wrapped_lines = []
            for message in dialogue_box.conversation_history:
                wrapped_lines.extend(self.wrap_text(message, self.font, dialogue_box.max_width - portrait_offset))

            max_lines = available_height // line_height
            total_lines = len(wrapped_lines)

            start_line, end_line = dialogue_box.get_display_window(total_lines, max_lines)
            display_lines = wrapped_lines[start_line:end_line]

            for line in display_lines:
                text_surface = self.font.render(line, True, BLACK)
                self.screen.blit(text_surface, (10 + portrait_offset, y))
                y += line_height

            if dialogue_box.generating:
                dots = "." * (1 + (pygame.time.get_ticks() // 500) % 3)
                indicator = f"{npc.name} is thinking{dots}"
                text_surface = self.font.render(indicator, True, BLACK)
                self.screen.blit(text_surface, (10 + portrait_offset, y))

            input_prompt = f"You: {dialogue_box.user_message}"
            text_surface = self.font.render(input_prompt, True, BLACK)
            self.screen.blit(text_surface, (padding, SCREEN_HEIGHT - line_height - padding))

    def _draw_combat(self, dialogue_box):
        """Render the multi-turn combat interface."""
        event = dialogue_box.current_event
        if not event:
            return

        box_height = DIALOGUE_BOX_HEIGHT_ACTIVE
        padding = 10
        box_rect = pygame.Rect(0, SCREEN_HEIGHT - box_height, SCREEN_WIDTH, box_height)
        pygame.draw.rect(self.screen, WHITE, box_rect)

        y = SCREEN_HEIGHT - box_height + padding
        line_height = self.font.get_linesize()
        phase = dialogue_box.combat_phase

        # Header
        header_color = (180, 0, 0)
        header = f"[COMBAT] {event.name}"
        self.screen.blit(self.font.render(header, True, header_color), (padding, y))
        y += line_height + 2

        if phase == "initiative":
            self.screen.blit(
                self.font.render("Press Enter to roll initiative", True, BLACK),
                (padding, y),
            )
            return

        # Monster status panel (right side)
        monsters = getattr(event, "monsters", [])
        monster_x = SCREEN_WIDTH // 2 + 20
        monster_y = SCREEN_HEIGHT - box_height + padding + line_height + 4

        for i, monster in enumerate(monsters):
            if not monster.is_alive:
                color = (128, 128, 128)
                name_text = f"  {monster.name} [DEFEATED]"
            else:
                # HP bar
                hp_pct = monster.hp / monster.max_hp if monster.max_hp > 0 else 0
                color = (0, 128, 0) if hp_pct > 0.5 else (200, 200, 0) if hp_pct > 0.25 else (200, 0, 0)
                indicator = (
                    ">"
                    if (
                        phase == "player_turn"
                        and hasattr(dialogue_box, "_controller_target")
                        and i == getattr(dialogue_box, "_controller_target", -1)
                    )
                    else " "
                )
                name_text = f"{indicator} {monster.name} HP:{monster.hp}/{monster.max_hp} AC:{monster.ac}"

            self.screen.blit(self.font.render(name_text, True, color), (monster_x, monster_y))
            monster_y += line_height

            # HP bar visual
            if monster.is_alive:
                bar_w = 120
                bar_h = 6
                bar_x = monster_x
                bar_y_pos = monster_y
                pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y_pos, bar_w, bar_h))
                pygame.draw.rect(self.screen, color, (bar_x, bar_y_pos, int(bar_w * hp_pct), bar_h))
                monster_y += bar_h + 4

        # Combat log (left side, scrollable)
        log_max_lines = (box_height - line_height * 3 - padding * 2) // line_height
        log_lines = dialogue_box.combat_log[-log_max_lines:] if dialogue_box.combat_log else []
        log_y = y
        for log_line in log_lines:
            wrapped = self.wrap_text(log_line, self.font, SCREEN_WIDTH // 2 - padding * 2)
            for wl in wrapped:
                if log_y + line_height > SCREEN_HEIGHT - line_height - padding:
                    break
                self.screen.blit(self.font.render(wl, True, BLACK), (padding, log_y))
                log_y += line_height

        # Action prompt at bottom
        prompt_y = SCREEN_HEIGHT - line_height - padding
        if phase == "player_turn":
            if dialogue_box.player_stunned_turns > 0:
                prompt = "You are stunned! Press Enter to skip turn"
            else:
                prompt = "[A]ttack  [F]lee  [I]tem  | Up/Down: select target"
            self.screen.blit(self.font.render(prompt, True, (0, 0, 180)), (padding, prompt_y))
        elif phase == "monster_turn":
            self.screen.blit(
                self.font.render("Enemy turn... Press Enter to continue", True, (180, 0, 0)),
                (padding, prompt_y),
            )
        elif phase == "victory":
            self.screen.blit(
                self.font.render("VICTORY! Press Enter to continue", True, (0, 128, 0)),
                (padding, prompt_y),
            )
        elif phase == "defeat":
            self.screen.blit(
                self.font.render("DEFEATED! Press Enter to continue", True, (180, 0, 0)),
                (padding, prompt_y),
            )
        elif phase == "fled":
            self.screen.blit(
                self.font.render("You fled! Press Enter to continue", True, (180, 128, 0)),
                (padding, prompt_y),
            )

    def _draw_event(self, dialogue_box):
        """Render the event interaction panel."""
        event = dialogue_box.current_event
        if not event:
            return

        box_height = DIALOGUE_BOX_HEIGHT_ACTIVE
        padding = 10
        box_rect = pygame.Rect(0, SCREEN_HEIGHT - box_height, SCREEN_WIDTH, box_height)
        pygame.draw.rect(self.screen, WHITE, box_rect)

        y = SCREEN_HEIGHT - box_height + padding
        line_height = self.font.get_linesize()
        portrait_offset = 0

        portrait = load_portrait(getattr(event, "profile_image", None))
        if portrait:
            self.screen.blit(portrait, (padding, y))
            portrait_offset = 74

        # Event name with type-based color
        type_colors = {
            "combat": (180, 0, 0),
            "puzzle": (0, 0, 180),
            "event": (128, 0, 128),
        }
        name_color = type_colors.get(event.type, BLACK)
        name_surface = self.font.render(f"[{event.type.upper()}] {event.name}", True, name_color)
        self.screen.blit(name_surface, (padding + portrait_offset, y))
        y += line_height + 4

        # Description
        for line in self.wrap_text(event.description, self.font, SCREEN_WIDTH - 20 - portrait_offset):
            text_surface = self.font.render(line, True, BLACK)
            self.screen.blit(text_surface, (padding + portrait_offset, y))
            y += line_height

        y += 4
        result = dialogue_box.event_context.get("result")

        if event.type == "combat":
            if result:
                roll = dialogue_box.event_context.get("dice_roll", 0)
                roll_text = f"You rolled: {roll}"
                self.screen.blit(self.font.render(roll_text, True, BLACK), (padding, y))
                y += line_height
                result_color = (0, 128, 0) if result.get("success") else (180, 0, 0)
                self.screen.blit(
                    self.font.render(result["message"], True, result_color),
                    (padding, y),
                )
                y += line_height + 4
                self.screen.blit(
                    self.font.render("Press Enter or Escape to continue", True, BLACK),
                    (padding, y),
                )
            elif dialogue_box.awaiting_roll:
                self.screen.blit(
                    self.font.render("Press R to roll (1-20)  |  Escape to flee", True, BLACK),
                    (padding, y),
                )

        elif event.type in ("puzzle", "event"):
            choices = getattr(event, "choices", [])
            selected = dialogue_box.event_context.get("selected_choice")

            if result:
                roll = dialogue_box.event_context.get("dice_roll", 0)
                if roll:
                    self.screen.blit(self.font.render(f"You rolled: {roll}", True, BLACK), (padding, y))
                    y += line_height
                result_color = (0, 128, 0) if result.get("success") else (180, 0, 0)
                self.screen.blit(
                    self.font.render(result["message"], True, result_color),
                    (padding, y),
                )
                y += line_height + 4
                self.screen.blit(
                    self.font.render("Press Enter or Escape to continue", True, BLACK),
                    (padding, y),
                )
            elif dialogue_box.awaiting_roll:
                chosen = choices[selected] if selected is not None and selected < len(choices) else None
                if chosen:
                    self.screen.blit(
                        self.font.render(f"Chose: {chosen.text}", True, BLACK),
                        (padding, y),
                    )
                    y += line_height
                self.screen.blit(
                    self.font.render("Press R to roll  |  Escape to flee", True, BLACK),
                    (padding, y),
                )
            else:
                for i, choice in enumerate(choices):
                    color = (0, 0, 180)
                    # Show stat/tool hints for event encounters
                    hint = ""
                    if choice.stat_check:
                        hint += f" [{choice.stat_check}]"
                    if choice.tool_attribute:
                        hint += f" [needs: {choice.tool_attribute}]"
                    if choice.auto_success:
                        hint += " [safe]"
                    text = f"  {i + 1}. {choice.text}{hint}"
                    self.screen.blit(self.font.render(text, True, color), (padding, y))
                    y += line_height
                y += 4
                num = min(len(choices), 9)
                self.screen.blit(
                    self.font.render(f"Press 1-{num} to choose  |  Escape to leave", True, BLACK),
                    (padding, y),
                )

    def wrap_text(self, text, font, max_width):
        """Wrap text into multiple lines to fit within max_width."""
        if not text:
            return []
        words = text.split(" ")
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            line_width, _ = font.size(test_line)
            if line_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines
