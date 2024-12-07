import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE
from src.utils.llm_service import generate_npc_response

class DialogueBox:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.current_npc = None
        self.npc_message = ""
        self.user_message = ""
        self.item_message = None
        self.conversation_history = []
        self.scroll_offset = 0
        self.dialogue_active = False
        self.input_active = False
        self.max_scroll = 0 #initialize max scroll
        self.max_width = SCREEN_WIDTH - 20
        self.event_active = False
        self.current_event = None
        self.awaiting_roll = False
        self.event_context = {}
        
    def draw(self):
        """Draw the dialogue box at the bottom of the screen."""
        dialogue_box_height = 100
        padding = 10
        dialogue_box_rect = pygame.Rect(0, SCREEN_HEIGHT - dialogue_box_height, SCREEN_WIDTH, dialogue_box_height)
        pygame.draw.rect(self.screen, WHITE, dialogue_box_rect)

        line_height = self.font.get_linesize()
        input_prompt_height = line_height + padding
        available_height = dialogue_box_height - input_prompt_height - padding

        # If there is an item message, show it at the top of the box
        if self.item_message:
            item_text_surface = self.font.render(f"{self.item_message}", True, BLACK)
            self.screen.blit(item_text_surface, (10, SCREEN_HEIGHT - 90))
        
        elif self.current_npc:
            # NPC message
            wrapped_lines = []
            for message in self.conversation_history:
                wrapped_lines.extend(self.wrap_text(message, self.font, self.max_width))
            
            #max viewable lines at one time
            max_lines = available_height // line_height
            
            #Ensure scroll is within bounds
            total_lines = len(wrapped_lines)
            self.max_scroll = max(0, total_lines - max_lines)
            self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
            
            #apply scrolling
            start_line = max(0, total_lines - max_lines - self.scroll_offset)
            end_line = start_line + max_lines
            display_lines = wrapped_lines[start_line:end_line]
            
            #render convo history
            y = SCREEN_HEIGHT - dialogue_box_height + padding
            for line in display_lines:
                text_surface = self.font.render(line, True, BLACK)
                self.screen.blit(text_surface, (10, y))
                y += line_height
                
            input_prompt = f"You: {self.user_message}"
            text_surface = self.font.render(input_prompt, True, BLACK)
            self.screen.blit(text_surface, (padding, SCREEN_HEIGHT - line_height - padding))
        else:
            pass
        
    def handle_npc_response(self, user_input):
        if self.current_npc:
            npc_message = generate_npc_response(self.current_npc, user_input)
            return npc_message
        else:
            return "There is no one here to talk too..."
        
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
    
    def set_item_message(self, message):
        self.item_message = message
        self.current_npc = None
        
    def clear_item_message(self):
        self.item_message = None
        
    def start_dialogue(self, npc):
        self.dialogue_active = True
        self.current_npc = npc
        self.npc_message = generate_npc_response(npc, '')
        self.user_message = ""
        self.input_active = True
        self.conversation_history = []
        self.conversation_history.append(self.npc_message)
        self.scroll_offset = 0
        
    def update_dialogue(self, user_input):
        self.conversation_history.append(f"You: {user_input}")
        self.npc_message = self.handle_npc_response(user_input)
        self.conversation_history.append(self.npc_message)
        self.user_message = ""
        self.scroll_offset = 0
        
    def end_dialogue(self):
        self.dialogue_active = False
        self.current_npc = None
        self.npc_message = ""
        self.user_message = ""
        self.conversation_history = []
        self.scroll_offset = 0
        
    def scroll_up(self):
        """Scroll up the conversation history."""
        self.scroll_offset += 1
        self.scroll_offset = min(self.scroll_offset, self.max_scroll)
        
    def scroll_down(self):
        """Scroll down the conversation history."""
        self.scroll_offset -= 1
        self.scroll_offset = max(self.scroll_offset, 0)
        
    def start_event(self, environment):
        pass
        # self.event_active = True
        # self.dialogue_active = True
        # self.input_actice = True
        # self.awaiting_roll = False
        # self.conversation_history = []
        
        # #Generate the event using the LLM
        # self.current_event = self.generate_event(environment)
        # self.conversation_history.append(self.current_event['description'])
        # self.user_message = ""
    
    def generate_event(self, environment):
        #Generate event using the LLM
        pass
    