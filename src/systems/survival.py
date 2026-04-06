"""Hunger/thirst/HP drain, recovery system.

Drain rates are ~1/3 of the original (which was -1 per step).
CON modifier reduces drain per step (minimum 1 drain).
No drain while stationary (talking to NPCs, menus).
Thresholds: warning < 30, penalty < 15, critical = 0.
Starvation/dehydration: at 0, slow HP drain (1 per 5 steps).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.player import PlayerCharacter

# --- Thresholds ---
THRESHOLD_WARNING = 30
THRESHOLD_PENALTY = 15
THRESHOLD_CRITICAL = 0

# --- Drain tuning ---
BASE_HUNGER_DRAIN = 1       # Applied every DRAIN_INTERVAL steps
BASE_THIRST_DRAIN = 1       # Applied every DRAIN_INTERVAL steps
DRAIN_INTERVAL = 3          # Drain happens once every N movement steps (~1/3 rate)

# --- Starvation / dehydration ---
STARVATION_HP_DRAIN = 1
STARVATION_INTERVAL = 5     # HP lost once every N steps at 0 hunger or thirst

# --- Penalty multipliers ---
SPEED_PENALTY_FACTOR = 0.7  # Speed multiplier when hunger or thirst < 15


class SurvivalSystem:
    """Manages hunger/thirst drain and HP penalties for a player."""

    def __init__(self):
        self._step_counter: int = 0
        self._starvation_counter: int = 0

    def on_move(self, player: PlayerCharacter) -> list[str]:
        """Called once per movement step. Returns a list of warning/effect messages."""
        messages: list[str] = []

        self._step_counter += 1

        # --- Drain (every DRAIN_INTERVAL steps) ---
        if self._step_counter >= DRAIN_INTERVAL:
            self._step_counter = 0
            con_mod = player.get_stat_modifier("CON")
            hunger_drain = max(1, BASE_HUNGER_DRAIN - con_mod)
            thirst_drain = max(1, BASE_THIRST_DRAIN - con_mod)
            player.hunger = max(0, player.hunger - hunger_drain)
            player.thirst = max(0, player.thirst - thirst_drain)

        # --- Starvation / dehydration HP drain ---
        starving = player.hunger <= THRESHOLD_CRITICAL
        dehydrated = player.thirst <= THRESHOLD_CRITICAL
        if starving or dehydrated:
            self._starvation_counter += 1
            if self._starvation_counter >= STARVATION_INTERVAL:
                self._starvation_counter = 0
                player.health = max(0, player.health - STARVATION_HP_DRAIN)
                if starving and dehydrated:
                    messages.append("You are starving and dehydrated! Losing health.")
                elif starving:
                    messages.append("You are starving! Losing health.")
                else:
                    messages.append("You are dehydrated! Losing health.")
        else:
            self._starvation_counter = 0

        # --- Threshold warnings (once per drain tick) ---
        if 0 < player.hunger <= THRESHOLD_WARNING and player.hunger > THRESHOLD_PENALTY:
            messages.append("You are getting hungry.")
        if 0 < player.thirst <= THRESHOLD_WARNING and player.thirst > THRESHOLD_PENALTY:
            messages.append("You are getting thirsty.")

        # --- Penalty effects ---
        self._apply_penalties(player)

        return messages

    def _apply_penalties(self, player: PlayerCharacter):
        """Apply speed and capability penalties based on survival thresholds."""
        hunger_penalty = player.hunger <= THRESHOLD_PENALTY and player.hunger > THRESHOLD_CRITICAL
        thirst_penalty = player.thirst <= THRESHOLD_PENALTY and player.thirst > THRESHOLD_CRITICAL

        if hunger_penalty or thirst_penalty:
            player.speed = player.max_speed * SPEED_PENALTY_FACTOR
        elif player.hunger > THRESHOLD_PENALTY and player.thirst > THRESHOLD_PENALTY:
            player.speed = player.max_speed

    def can_cast(self, player: PlayerCharacter) -> bool:
        """Returns False if player is at critical hunger or thirst (can't cast)."""
        return player.hunger > THRESHOLD_CRITICAL and player.thirst > THRESHOLD_CRITICAL

    def get_spell_effectiveness(self, player: PlayerCharacter) -> float:
        """Returns spell damage/heal multiplier based on survival state.

        Full effectiveness above penalty threshold.
        Reduced (0.5x) when in penalty range.
        Zero when critical.
        """
        if player.hunger <= THRESHOLD_CRITICAL or player.thirst <= THRESHOLD_CRITICAL:
            return 0.0
        if player.hunger <= THRESHOLD_PENALTY or player.thirst <= THRESHOLD_PENALTY:
            return 0.5
        return 1.0

    def get_status(self, player: PlayerCharacter) -> dict:
        """Return current survival status for UI display."""
        return {
            "hunger": player.hunger,
            "thirst": player.thirst,
            "hunger_max": player.max_hunger,
            "thirst_max": player.max_thirst,
            "hunger_warning": player.hunger <= THRESHOLD_WARNING,
            "thirst_warning": player.thirst <= THRESHOLD_WARNING,
            "hunger_penalty": player.hunger <= THRESHOLD_PENALTY,
            "thirst_penalty": player.thirst <= THRESHOLD_PENALTY,
            "starving": player.hunger <= THRESHOLD_CRITICAL,
            "dehydrated": player.thirst <= THRESHOLD_CRITICAL,
            "can_cast": self.can_cast(player),
        }
