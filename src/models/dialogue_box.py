from config import SCREEN_WIDTH
from src.utils.conversation_utils import generate_npc_response

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
        
    def handle_npc_response(self, user_input):
        if self.current_npc:
            npc_message = generate_npc_response(self.current_npc, user_input)
            return npc_message
        else:
            return "There is no one here to talk too..."
    
    def set_item_message(self, message):
        self.item_message = message
        self.current_npc = None
        self.input_active = False
        
    def clear_item_message(self):
        self.item_message = None
        self.input_active = True
        
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
    