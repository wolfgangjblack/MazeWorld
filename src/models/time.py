"""Day/Night cycle data model — real-time based.

A full cycle is ~16 minutes (~4 min per phase) using pygame.time.get_ticks().
Actions and rest still advance the timer, but the clock also ticks in real-time.
"""

from pydantic import BaseModel
from enum import Enum


class TimePeriod(str, Enum):
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


# Period order and percentage of full cycle
PERIOD_SEQUENCE = [
    (TimePeriod.DAWN, 0.15),
    (TimePeriod.DAY, 0.35),
    (TimePeriod.DUSK, 0.15),
    (TimePeriod.NIGHT, 0.35),
]

# Real-time: full cycle duration in milliseconds (~16 minutes)
FULL_CYCLE_MS = 16 * 60 * 1000  # 960_000 ms
PHASE_DURATION_MS = 4 * 60 * 1000  # ~4 min per phase (approximate)


class DayNightCycle(BaseModel):
    """Real-time day/night cycle.

    Primary time source is wall-clock milliseconds (via pygame.time.get_ticks).
    Actions and rest can push the timer forward. A full cycle = ~16 minutes.
    """
    ticks: int = 0
    cycle_length: int = 200  # kept for action-based compat / serialization

    # Real-time tracking (ms). Set start_ms on first update().
    elapsed_ms: int = 0
    last_update_ms: int = 0  # last pygame.time.get_ticks value

    class Config:
        arbitrary_types_allowed = True

    def update_realtime(self, current_ms: int) -> None:
        """Call each frame with pygame.time.get_ticks(). Advances elapsed_ms."""
        if self.last_update_ms <= 0:
            # First call — record the baseline, no delta yet
            self.last_update_ms = max(1, current_ms)
            return
        delta = current_ms - self.last_update_ms
        if delta > 0:
            self.elapsed_ms += delta
        self.last_update_ms = current_ms

    @property
    def _effective_ms(self) -> int:
        """Total effective time: real-time + action advances."""
        # Actions map to ms: each tick = FULL_CYCLE_MS / cycle_length
        action_ms = int(self.ticks * (FULL_CYCLE_MS / self.cycle_length))
        return self.elapsed_ms + action_ms

    @property
    def current_period(self) -> TimePeriod:
        """Derive the current period from effective time."""
        position = self._effective_ms % FULL_CYCLE_MS
        cumulative = 0.0
        for period, fraction in PERIOD_SEQUENCE:
            cumulative += fraction * FULL_CYCLE_MS
            if position < cumulative:
                return period
        return TimePeriod.NIGHT

    @property
    def period_progress(self) -> float:
        """Progress within the current period (0.0 to 1.0)."""
        position = self._effective_ms % FULL_CYCLE_MS
        cumulative = 0.0
        for period, fraction in PERIOD_SEQUENCE:
            period_ms = fraction * FULL_CYCLE_MS
            if position < cumulative + period_ms:
                return (position - cumulative) / period_ms
            cumulative += period_ms
        return 1.0

    @property
    def is_night(self) -> bool:
        return self.current_period == TimePeriod.NIGHT

    @property
    def day_number(self) -> int:
        """Which day it is (starting from 1)."""
        return self._effective_ms // FULL_CYCLE_MS + 1

    def advance(self, steps: int = 1) -> None:
        """Advance time by action steps (each step = fraction of a cycle)."""
        self.ticks += steps

    def advance_hours(self, hours: int) -> None:
        """Advance time by in-game hours. A full cycle = 24 hours."""
        ms_per_hour = FULL_CYCLE_MS / 24
        self.elapsed_ms += int(ms_per_hour * hours)

    def serialize(self) -> dict:
        return {
            "ticks": self.ticks,
            "cycle_length": self.cycle_length,
            "elapsed_ms": self.elapsed_ms,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "DayNightCycle":
        return cls(
            ticks=data.get("ticks", 0),
            cycle_length=data.get("cycle_length", 200),
            elapsed_ms=data.get("elapsed_ms", 0),
        )
