"""Day/Night cycle data model."""

from pydantic import BaseModel
from enum import Enum


class TimePeriod(str, Enum):
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"
    DAWN = "dawn"


class DayNightCycle(BaseModel):
    ticks: int = 0
    ticks_per_period: int = 100
    current_period: TimePeriod = TimePeriod.DAY

    def advance(self, steps: int = 1):
        self.ticks += steps
        periods = list(TimePeriod)
        index = self.ticks // self.ticks_per_period % len(periods)
        self.current_period = periods[index]
