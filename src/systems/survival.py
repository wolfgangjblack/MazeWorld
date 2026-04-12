"""Stamina survival system — real-time drain with threshold warnings.

Stamina drains 10 points per 12-minute real-time day cycle.
No movement-based drain.  Spells, abilities, multi-attack, and events
spend stamina directly.  Food and drink restore stamina.

Thresholds (percentage of max_stamina):
  50% — warning ("getting tired")
  25% — penalty (speed 0.7x, spell effectiveness 0.5x)
  10% — critical ("collapsing", no casting, spell effectiveness 0.0x)

HP thresholds (percentage of max_health):
  50% — "You are wounded."
  25% — "You are critically wounded!"
  10% — "You are near death!"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.player import PlayerCharacter

# --- Stamina drain ---
STAMINA_DRAIN_PER_CYCLE = 10
STAMINA_DRAIN_INTERVAL_MS = 12 * 60 * 1000  # 12 minutes real-time = 1 day cycle

# --- Stamina thresholds (percentage of max_stamina) ---
THRESHOLD_WARNING = 50
THRESHOLD_PENALTY = 25
THRESHOLD_CRITICAL = 10

# --- HP thresholds (percentage of max_health) ---
HP_WARNING = 0.50
HP_CRITICAL = 0.25
HP_DIRE = 0.10

# --- Penalty multipliers ---
SPEED_PENALTY_FACTOR = 0.7


class SurvivalSystem:
    """Manages stamina drain and threshold warnings."""

    def __init__(self):
        self._accumulated_ms: int = 0
        self._last_stamina_pct: int = 100
        self._last_hp_pct: float = 1.0

    def on_time_update(self, player: PlayerCharacter, elapsed_ms: int) -> list[str]:
        """Called each frame with milliseconds elapsed since last call.

        Drains stamina based on real-time. Returns warning messages when
        thresholds are crossed.
        """
        messages: list[str] = []

        if elapsed_ms <= 0:
            return messages

        self._accumulated_ms += elapsed_ms

        if STAMINA_DRAIN_INTERVAL_MS > 0:
            drain_points = (self._accumulated_ms * STAMINA_DRAIN_PER_CYCLE) // STAMINA_DRAIN_INTERVAL_MS
            if drain_points > 0:
                consumed_ms = (drain_points * STAMINA_DRAIN_INTERVAL_MS) // STAMINA_DRAIN_PER_CYCLE
                self._accumulated_ms -= consumed_ms
                player.stamina = max(0, player.stamina - drain_points)

        messages.extend(self._check_stamina_warnings(player))
        messages.extend(self._check_hp_warnings(player))
        self._apply_penalties(player)

        return messages

    def _stamina_pct(self, player: PlayerCharacter) -> int:
        if player.max_stamina <= 0:
            return 0
        return (player.stamina * 100) // player.max_stamina

    def _hp_pct(self, player: PlayerCharacter) -> float:
        if player.max_health <= 0:
            return 0.0
        return player.health / player.max_health

    def _check_stamina_warnings(self, player: PlayerCharacter) -> list[str]:
        msgs: list[str] = []
        pct = self._stamina_pct(player)
        prev = self._last_stamina_pct

        if pct <= THRESHOLD_CRITICAL < prev:
            msgs.append("You are collapsing from exhaustion! You can no longer cast spells.")
        elif pct <= THRESHOLD_PENALTY < prev:
            msgs.append("You are exhausted! Your speed and spell power are reduced.")
        elif pct <= THRESHOLD_WARNING < prev:
            msgs.append("You are getting tired.")

        self._last_stamina_pct = pct
        return msgs

    def _check_hp_warnings(self, player: PlayerCharacter) -> list[str]:
        msgs: list[str] = []
        pct = self._hp_pct(player)
        prev = self._last_hp_pct

        if pct <= HP_DIRE < prev:
            msgs.append("You are near death!")
        elif pct <= HP_CRITICAL < prev:
            msgs.append("You are critically wounded!")
        elif pct <= HP_WARNING < prev:
            msgs.append("You are wounded.")

        self._last_hp_pct = pct
        return msgs

    def _apply_penalties(self, player: PlayerCharacter):
        pct = self._stamina_pct(player)
        if pct <= THRESHOLD_PENALTY:
            player.speed = player.max_speed * SPEED_PENALTY_FACTOR
        else:
            player.speed = player.max_speed

    def can_cast(self, player: PlayerCharacter) -> bool:
        """Returns False when stamina is at or below critical threshold."""
        return self._stamina_pct(player) > THRESHOLD_CRITICAL

    def get_spell_effectiveness(self, player: PlayerCharacter) -> float:
        """Spell damage/heal multiplier based on stamina level."""
        pct = self._stamina_pct(player)
        if pct <= THRESHOLD_CRITICAL:
            return 0.0
        if pct <= THRESHOLD_PENALTY:
            return 0.5
        return 1.0

    def get_status(self, player: PlayerCharacter) -> dict:
        pct = self._stamina_pct(player)
        return {
            "stamina": player.stamina,
            "stamina_max": player.max_stamina,
            "stamina_pct": pct,
            "stamina_warning": pct <= THRESHOLD_WARNING,
            "stamina_penalty": pct <= THRESHOLD_PENALTY,
            "stamina_critical": pct <= THRESHOLD_CRITICAL,
            "can_cast": self.can_cast(player),
        }
