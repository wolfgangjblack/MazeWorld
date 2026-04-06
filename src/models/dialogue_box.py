import threading
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
        self.dialogue_active = False
        self.input_active = False
        self.max_width = SCREEN_WIDTH - 20
        self.event_active = False
        self.current_event = None
        self.awaiting_roll = False
        self.event_context = {}

        # Combat state
        self.combat_active = False
        self.combat_phase = None  # "initiative" | "player_turn" | "monster_turn" | "result" | "victory" | "defeat" | "fled"
        self.combat_log = []
        self.player_stunned_turns = 0
        self.player_poison_turns = 0

        # Scroll state: top-anchored (0 = top of history)
        self.scroll_position = 0
        self.max_scroll = 0
        self.auto_scroll = False
        self._scroll_target = "top"

        # Story context for NPC dialogue flavoring
        self.story_context = ""

        # Async generation state
        self.generating = False
        self._generation_thread = None
        self._generation_result = None

    def get_display_window(self, total_lines, max_lines):
        """Compute the visible slice of wrapped lines for the view."""
        self.max_scroll = max(0, total_lines - max_lines)
        if self.auto_scroll:
            if self._scroll_target == "bottom":
                self.scroll_position = self.max_scroll
            else:
                self.scroll_position = 0
            self.auto_scroll = False
        self.scroll_position = max(0, min(self.scroll_position, self.max_scroll))
        return self.scroll_position, self.scroll_position + max_lines

    def scroll_up(self):
        self.scroll_position = max(0, self.scroll_position - 1)
        self.auto_scroll = False

    def scroll_down(self):
        self.scroll_position = min(self.scroll_position + 1, self.max_scroll)
        self.auto_scroll = False

    def set_item_message(self, message):
        self.item_message = message
        self.current_npc = None
        self.input_active = False

    def clear_item_message(self):
        self.item_message = None
        self.input_active = True

    def _build_display_history(self, npc):
        """Reconstruct display strings from the NPC's persistent interaction_history."""
        lines = []
        for turn in npc.interaction_history:
            if turn["role"] == "npc":
                lines.append(f"{npc.name}: {turn['content']}")
            elif turn["role"] == "user":
                lines.append(f"You: {turn['content']}")
        return lines

    def _start_generation(self, npc, user_input):
        """Launch LLM response generation on a background thread."""
        ctx = self.story_context

        def _run():
            try:
                self._generation_result = generate_npc_response(
                    npc, user_input, story_context=ctx)
            except Exception:
                self._generation_result = f"{npc.name}: [Unable to generate response]"
        self._generation_thread = threading.Thread(target=_run, daemon=True)
        self._generation_thread.start()

    def check_generation(self):
        """Poll the background thread; append result when finished."""
        if not self.generating or self._generation_thread is None:
            return
        if self._generation_thread.is_alive():
            return
        self.conversation_history.append(self._generation_result)
        self.generating = False
        self.input_active = True
        self.auto_scroll = True
        self._scroll_target = "bottom"
        self._generation_thread = None

    def start_dialogue(self, npc):
        self.dialogue_active = True
        self.current_npc = npc
        self.conversation_history = self._build_display_history(npc)
        self.user_message = ""
        self.input_active = False
        self.generating = True
        self._start_generation(npc, '')
        self.auto_scroll = True
        self._scroll_target = "top" if not npc.has_met_player else "bottom"

    def update_dialogue(self, user_input):
        self.conversation_history.append(f"You: {user_input}")
        self.user_message = ""
        self.input_active = False
        self.generating = True
        self._start_generation(self.current_npc, user_input)
        self.auto_scroll = True
        self._scroll_target = "bottom"

    def end_dialogue(self):
        self.dialogue_active = False
        self.current_npc = None
        self.npc_message = ""
        self.user_message = ""
        self.conversation_history = []
        self.scroll_position = 0
        self.auto_scroll = False
        self.generating = False

    def start_event(self, event):
        """Activate an event in the dialogue box."""
        self.event_active = True
        self.current_event = event
        self.event_context = {}
        self.dialogue_active = False
        self.input_active = False

        if event.type == "combat" and hasattr(event, 'monsters') and event.monsters:
            # Multi-turn combat
            self.combat_active = True
            self.combat_phase = "initiative"
            self.combat_log = []
            self.player_stunned_turns = 0
            self.player_poison_turns = 0
            self.awaiting_roll = False
        elif event.type == "combat":
            # Legacy single-roll combat
            self.combat_active = False
            self.awaiting_roll = True
        else:
            self.combat_active = False
            self.awaiting_roll = False

    def start_combat_turns(self, init_result: dict):
        """Called after initiative is rolled to begin turn-based combat."""
        self.combat_phase = "player_turn"  # Will be set correctly by controller
        self.combat_log = list(self.current_event.combat_log)

    def set_combat_phase(self, phase: str):
        self.combat_phase = phase

    def add_combat_log(self, message: str):
        self.combat_log.append(message)
        # Keep scrolled to bottom
        self.auto_scroll = True
        self._scroll_target = "bottom"

    def end_event(self):
        """Close the event panel."""
        self.event_active = False
        self.current_event = None
        self.awaiting_roll = False
        self.event_context = {}
        self.combat_active = False
        self.combat_phase = None
        self.combat_log = []
        self.player_stunned_turns = 0
        self.player_poison_turns = 0
