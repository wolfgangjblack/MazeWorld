import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE

class DialogueBoxView:    
    def __init__(self, screen, font):
        self.font = font
        self.screen = screen

    def draw(self, dialogue_box):
        """Render the dialogue box and its contents based on `dialogue_box_state`."""
        dialogue_box_height = 100
        padding = 10
        dialogue_box_rect = pygame.Rect(0, SCREEN_HEIGHT - dialogue_box_height, SCREEN_WIDTH, dialogue_box_height)
        pygame.draw.rect(self.screen, WHITE, dialogue_box_rect)

        line_height = self.font.get_linesize()
        input_prompt_height = line_height + padding
        available_height = dialogue_box_height - input_prompt_height - padding

        # If there is an item message, show it at the top of the box
        if dialogue_box.item_message:
            # Show item message
            item_text_surface = self.font.render(dialogue_box.item_message, True, BLACK)
            self.screen.blit(item_text_surface, (10, SCREEN_HEIGHT - 90))
        elif dialogue_box.current_npc:
            # Show NPC conversation history
            wrapped_lines = []
            for message in dialogue_box.conversation_history:
                wrapped_lines.extend(self.wrap_text(message, self.font, dialogue_box.max_width))

            max_lines = available_height // line_height
            total_lines = len(wrapped_lines)
            dialogue_box.max_scroll = max(0, total_lines - max_lines)
            dialogue_box.scroll_offset = max(0, min(dialogue_box.scroll_offset, dialogue_box.max_scroll))

            start_line = max(0, total_lines - max_lines - dialogue_box.scroll_offset)
            end_line = start_line + max_lines
            display_lines = wrapped_lines[start_line:end_line]

            y = SCREEN_HEIGHT - dialogue_box_height + padding
            for line in display_lines:
                text_surface = self.font.render(line, True, BLACK)
                self.screen.blit(text_surface, (10, y))
                y += line_height

            input_prompt = f"You: {dialogue_box.user_message}"
            text_surface = self.font.render(input_prompt, True, BLACK)
            self.screen.blit(text_surface, (padding, SCREEN_HEIGHT - line_height - padding))

    def wrap_text(self, text, font, max_width):
        """Wrap text into multiple lines to fit within max_width."""
        words = text.split(' ')
        lines = []
        current_line = ''
        for word in words:
            test_line = current_line + (' ' if current_line else '') + word
            line_width, _ = font.size(test_line)
            if line_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines
