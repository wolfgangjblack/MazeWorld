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

DARK_BG = (30, 30, 40)
PANEL_BG = (20, 20, 35, 220)
TITLE_COLOR = (220, 180, 60)
TEXT_COLOR = (200, 200, 210)
SELECTED_COLOR = (255, 220, 50)
CHOICE_COLOR = (100, 130, 220)
MED_GRAY = (60, 60, 70)
DIM = (150, 150, 150)


class DialogueBoxView:
    def __init__(self, screen, font):
        self.font = font
        self.screen = screen
        self.small_font = pygame.font.SysFont(None, 20)
        self.title_font = pygame.font.SysFont(None, 36)
        self.dialogue_choice_index = 0

    def draw(self, dialogue_box, choices=None, choice_index=0):
        """Render the dialogue box and its contents."""
        if dialogue_box.event_active:
            self._draw_event(dialogue_box)
            return

        if dialogue_box.dialogue_active and dialogue_box.current_npc:
            self._draw_fullscreen_dialogue(dialogue_box, choices=choices, choice_index=choice_index)
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

        if dialogue_box.item_message:
            max_w = SCREEN_WIDTH - 20
            lines = self.wrap_text(dialogue_box.item_message, self.font, max_w)
            y = SCREEN_HEIGHT - dialogue_box_height + padding
            for line in lines:
                surf = self.font.render(line, True, BLACK)
                self.screen.blit(surf, (10, y))
                y += self.font.get_linesize()

    def _draw_fullscreen_dialogue(self, dialogue_box, choices=None, choice_index=0):
        """Full-screen NPC dialogue with large portrait above, dialogue below."""
        npc = dialogue_box.current_npc
        self.screen.fill(DARK_BG)

        portrait_size = (300, 300)
        portrait = load_portrait(getattr(npc, "profile_image", None), size=portrait_size)

        portrait_y = 20
        if portrait:
            px = (SCREEN_WIDTH - portrait.get_width()) // 2
            self.screen.blit(portrait, (px, portrait_y))
            name_y = portrait_y + portrait.get_height() + 8
        else:
            name_y = portrait_y + 40

        name_surf = self.title_font.render(npc.name, True, TITLE_COLOR)
        self.screen.blit(name_surf, ((SCREEN_WIDTH - name_surf.get_width()) // 2, name_y))
        bottom_y = name_y + name_surf.get_height()
        if hasattr(npc, "job") and npc.job:
            job_surf = self.small_font.render(f"({npc.job})", True, DIM)
            self.screen.blit(job_surf, ((SCREEN_WIDTH - job_surf.get_width()) // 2, bottom_y + 2))
            bottom_y += 2 + job_surf.get_height()

        divider_y = bottom_y + 8
        pygame.draw.line(self.screen, MED_GRAY, (20, divider_y), (SCREEN_WIDTH - 20, divider_y))

        content_top = divider_y + 8
        prompt_y = SCREEN_HEIGHT - 30
        content_bottom = prompt_y - 10

        line_height = self.font.get_linesize()
        padding = 15

        if choices:
            choice_area_h = len(choices) * (line_height + 2) + 20
            conversation_bottom = content_bottom - choice_area_h
        else:
            conversation_bottom = content_bottom - line_height - 10

        avail_conv_h = conversation_bottom - content_top
        max_conv_lines = max(1, avail_conv_h // line_height)

        wrapped_lines = []
        for message in dialogue_box.conversation_history:
            wrapped_lines.extend(self.wrap_text(message, self.font, SCREEN_WIDTH - 2 * padding))

        total_lines = len(wrapped_lines)
        start_line, end_line = dialogue_box.get_display_window(total_lines, max_conv_lines)
        display_lines = wrapped_lines[start_line:end_line]

        clip = pygame.Rect(0, content_top, SCREEN_WIDTH, avail_conv_h)
        self.screen.set_clip(clip)
        cy = content_top
        for line in display_lines:
            surf = self.font.render(line, True, TEXT_COLOR)
            self.screen.blit(surf, (padding, cy))
            cy += line_height
        self.screen.set_clip(None)

        if dialogue_box.generating:
            dots = "." * (1 + (pygame.time.get_ticks() // 500) % 3)
            indicator = f"{npc.name} is thinking{dots}"
            surf = self.font.render(indicator, True, DIM)
            self.screen.blit(surf, (padding, cy))

        if choices:
            choice_y = conversation_bottom + 5
            pygame.draw.line(self.screen, MED_GRAY, (20, choice_y - 3), (SCREEN_WIDTH - 20, choice_y - 3))
            for i, choice in enumerate(choices):
                is_sel = i == choice_index
                prefix = "> " if is_sel else "  "
                color = SELECTED_COLOR if is_sel else CHOICE_COLOR
                text = f"{prefix}{i + 1}. {choice['text']}"
                surf = self.font.render(text, True, color)
                self.screen.blit(surf, (padding, choice_y))
                choice_y += line_height + 2

            prompt_text = "Up/Down select  |  Enter choose  |  Escape leave"
        elif dialogue_box.input_active:
            input_y = content_bottom - line_height - 5
            pygame.draw.line(self.screen, MED_GRAY, (20, input_y - 3), (SCREEN_WIDTH - 20, input_y - 3))
            input_prompt = f"You: {dialogue_box.user_message}_"
            surf = self.font.render(input_prompt, True, TEXT_COLOR)
            self.screen.blit(surf, (padding, input_y))
            prompt_text = "Type + Enter  |  Up/Down scroll  |  Escape leave"
        else:
            prompt_text = "Up/Down scroll  |  Escape leave"

        pygame.draw.rect(self.screen, BLACK, (0, prompt_y - 5, SCREEN_WIDTH, 35))
        pygame.draw.line(self.screen, MED_GRAY, (0, prompt_y - 5), (SCREEN_WIDTH, prompt_y - 5))
        prompt_surf = self.font.render(prompt_text, True, DIM)
        self.screen.blit(prompt_surf, ((SCREEN_WIDTH - prompt_surf.get_width()) // 2, prompt_y))

    def _draw_event(self, dialogue_box):
        """Render the event interaction panel (fallback for combat events)."""
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

        type_colors = {
            "combat": (180, 0, 0),
            "puzzle": (0, 0, 180),
            "event": (128, 0, 128),
        }
        name_color = type_colors.get(event.type, BLACK)
        name_surface = self.font.render(f"[{event.type.upper()}] {event.name}", True, name_color)
        self.screen.blit(name_surface, (padding + portrait_offset, y))
        y += line_height + 4

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
                highlight = dialogue_box.event_context.get("highlight", 0)
                for i, choice in enumerate(choices):
                    is_sel = i == highlight
                    color = (0, 0, 180)
                    hint = ""
                    if choice.stat_check:
                        hint += f" [{choice.stat_check}]"
                    if choice.tool_attribute:
                        hint += f" [needs: {choice.tool_attribute}]"
                    if choice.auto_success:
                        hint += " [safe]"
                    prefix = "> " if is_sel else "  "
                    text = f"{prefix}{i + 1}. {choice.text}{hint}"
                    self.screen.blit(self.font.render(text, True, color), (padding, y))
                    y += line_height
                y += 4
                self.screen.blit(
                    self.font.render("Up/Down select  |  Enter choose  |  Escape leave", True, BLACK),
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
