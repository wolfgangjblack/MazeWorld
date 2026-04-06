"""Screen state machine — manages which screen is active and transitions."""

from enum import Enum


class ScreenState(Enum):
    START = "start"
    CLASS_SELECT = "class_select"
    ROOM_INTRO = "room_intro"
    GAMEPLAY = "gameplay"
    PLAYER_MENU = "player_menu"
    LOAD_GAME = "load_game"
    COMBAT = "combat"
    ENCOUNTER = "encounter"
    DIALOGUE = "dialogue"
    SHOP = "shop"
    PAUSE = "pause"
    LEVEL_UP = "level_up"
    GAME_OVER = "game_over"
    VICTORY = "victory"


class ScreenController:
    """Stack-based screen manager. Esc always pops."""

    def __init__(self, initial_state: ScreenState = ScreenState.START):
        self._stack: list[ScreenState] = [initial_state]

    @property
    def state(self) -> ScreenState:
        return self._stack[-1]

    def push(self, state: ScreenState):
        """Open a new screen on top of the current one."""
        self._stack.append(state)

    def pop(self) -> ScreenState | None:
        """Close the current screen, returning to the one beneath.

        Returns the popped state, or None if only one screen remains
        (never empties the stack).
        """
        if len(self._stack) <= 1:
            return None
        return self._stack.pop()

    def replace(self, state: ScreenState):
        """Replace the current screen (e.g., room_intro -> gameplay)."""
        if self._stack:
            self._stack[-1] = state
        else:
            self._stack.append(state)

    @property
    def depth(self) -> int:
        return len(self._stack)
