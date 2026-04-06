"""Day/Night cycle data model — real-time based."""

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

# Default full cycle: ~16 real minutes (4 min per phase)
DEFAULT_CYCLE_MS = 960_000


class DayNightCycle(BaseModel):
    """Real-time day/night cycle.

    Time advances with wall-clock time via ``update(current_time_ms)``.
    Each phase (dawn/day/dusk/night) lasts ~4 real minutes by default.
    Full cycle = ``cycle_duration_ms`` (default ~16 minutes).
    Rest can still jump the timer forward via ``advance_hours``.
    """
    elapsed_ms: int = 0
    cycle_duration_ms: int = DEFAULT_CYCLE_MS
    last_update_ms: int = 0

    @property
    def current_period(self) -> TimePeriod:
        """Derive the current period from elapsed real time."""
        position = self.elapsed_ms % self.cycle_duration_ms
        cumulative = 0.0
        for period, fraction in PERIOD_SEQUENCE:
            cumulative += fraction * self.cycle_duration_ms
            if position < cumulative:
                return period
        return TimePeriod.NIGHT  # fallback

    @property
    def period_progress(self) -> float:
        """Progress within the current period (0.0 to 1.0)."""
        position = self.elapsed_ms % self.cycle_duration_ms
        cumulative = 0.0
        for period, fraction in PERIOD_SEQUENCE:
            period_ms = fraction * self.cycle_duration_ms
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
        return self.elapsed_ms // self.cycle_duration_ms + 1

    def update(self, current_time_ms: int) -> None:
        """Advance elapsed time by the real-time delta since last update.

        Call this once per frame with ``pygame.time.get_ticks()``.
        """
        if self.last_update_ms == 0:
            self.last_update_ms = current_time_ms
            return
        delta = current_time_ms - self.last_update_ms
        if delta > 0:
            self.elapsed_ms += delta
        self.last_update_ms = current_time_ms

    def advance(self, steps: int = 1) -> None:
        """Advance time by action steps (for combat turns / legacy callers).

        Each step = 1/200th of a full cycle.
        """
        ms_per_step = self.cycle_duration_ms // 200
        self.elapsed_ms += ms_per_step * steps

    def advance_hours(self, hours: int) -> None:
        """Jump timer forward by in-game hours (for rest mechanic).

        A full cycle = 24 hours, so 1 hour = cycle_duration_ms / 24 ms.
        """
        ms_per_hour = self.cycle_duration_ms / 24
        self.elapsed_ms += int(ms_per_hour * hours)

    def serialize(self) -> dict:
        return {
            "elapsed_ms": self.elapsed_ms,
            "cycle_duration_ms": self.cycle_duration_ms,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "DayNightCycle":
        if "elapsed_ms" in data:
            return cls(
                elapsed_ms=data["elapsed_ms"],
                cycle_duration_ms=data.get("cycle_duration_ms", DEFAULT_CYCLE_MS),
            )
        # Legacy: convert action-based ticks to elapsed_ms
        ticks = data.get("ticks", 0)
        cycle_length = data.get("cycle_length", 200)
        elapsed_ms = int(ticks * DEFAULT_CYCLE_MS / cycle_length)
        return cls(elapsed_ms=elapsed_ms, cycle_duration_ms=DEFAULT_CYCLE_MS)
