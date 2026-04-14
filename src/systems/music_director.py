"""Music transition director — tracks combat/event state for music crossfades."""


class MusicDirector:
    """Owns the combat/event music transition state machine.

    Called each frame from the gameplay handler to detect transitions
    between exploration, combat, and puzzle/event music tracks.
    """

    def __init__(self, music_controller):
        self.music = music_controller
        self._was_in_combat = False
        self._was_in_event = False

    def update(self, game_controller):
        """Detect combat/event enter/exit and switch music tracks."""
        in_combat = game_controller.combat_handler.active
        in_event = game_controller.dialogue_box.event_active

        if in_combat and not self._was_in_combat:
            self.music.play_combat()
        elif in_event and not self._was_in_event and not in_combat:
            self.music.play_puzzle_event()
        elif not in_combat and not in_event and (self._was_in_combat or self._was_in_event):
            self.music.restore_maze()

        self._was_in_combat = in_combat
        self._was_in_event = in_event
