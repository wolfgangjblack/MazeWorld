"""Day/Night cycle data model."""

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


class DayNightCycle(BaseModel):
    """Action-based day/night cycle.

    Time advances with movement steps, combat turns, and rest actions.
    A full cycle = ``cycle_length`` actions (default 200).
    """
    ticks: int = 0
    cycle_length: int = 200

    @property
    def current_period(self) -> TimePeriod:
        """Derive the current period from ticks."""
        position = self.ticks % self.cycle_length
        cumulative = 0.0
        for period, fraction in PERIOD_SEQUENCE:
            cumulative += fraction * self.cycle_length
            if position < cumulative:
                return period
        return TimePeriod.NIGHT  # fallback

    @property
    def period_progress(self) -> float:
        """Progress within the current period (0.0 to 1.0)."""
        position = self.ticks % self.cycle_length
        cumulative = 0.0
        for period, fraction in PERIOD_SEQUENCE:
            period_ticks = fraction * self.cycle_length
            if position < cumulative + period_ticks:
                return (position - cumulative) / period_ticks
            cumulative += period_ticks
        return 1.0

    @property
    def is_night(self) -> bool:
        return self.current_period == TimePeriod.NIGHT

    @property
    def day_number(self) -> int:
        """Which day it is (starting from 1)."""
        return self.ticks // self.cycle_length + 1

    def advance(self, steps: int = 1) -> None:
        """Advance time by the given number of action steps."""
        self.ticks += steps

    def advance_hours(self, hours: int) -> None:
        """Advance time by a number of in-game hours.

        A full cycle = 24 hours, so 1 hour = cycle_length / 24 ticks.
        """
        ticks_per_hour = self.cycle_length / 24
        self.advance(int(ticks_per_hour * hours))

    def serialize(self) -> dict:
        return {"ticks": self.ticks, "cycle_length": self.cycle_length}

    @classmethod
    def deserialize(cls, data: dict) -> "DayNightCycle":
        return cls(ticks=data.get("ticks", 0),
                   cycle_length=data.get("cycle_length", 200))
