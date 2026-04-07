"""Day/Night cycle data model.

Supports two modes:
- **Action-based** (default): ticks advance on movement/combat/rest actions.
- **Real-time**: ticks also advance continuously based on wall-clock time,
  controlled by ``real_time_seconds_per_cycle`` (default 600 = 10 minutes
  per full in-game day).  Action ticks still apply on top.
"""

import time as _time

from pydantic import BaseModel, PrivateAttr
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
    """Day/night cycle with optional real-time advancement.

    Time advances with movement steps, combat turns, and rest actions.
    A full cycle = ``cycle_length`` actions (default 200).

    When ``real_time`` is True, ticks also advance continuously based on
    elapsed wall-clock seconds (``real_time_seconds_per_cycle`` seconds
    = one full day cycle).
    """
    ticks: int = 0
    cycle_length: int = 200

    # Real-time mode
    real_time: bool = False
    real_time_seconds_per_cycle: float = 600.0  # 10 minutes = 1 full day
    _rt_anchor_time: float = PrivateAttr(default=0.0)
    _rt_anchor_ticks: int = PrivateAttr(default=0)

    def enable_real_time(self) -> None:
        """Enable real-time mode, anchoring to the current wall clock."""
        self.real_time = True
        self._rt_anchor_time = _time.monotonic()
        self._rt_anchor_ticks = self.ticks

    def disable_real_time(self) -> None:
        """Disable real-time mode, freezing ticks at their current value."""
        if self.real_time:
            self._sync_real_time()
            self.real_time = False

    def _sync_real_time(self) -> None:
        """Update ticks from elapsed wall-clock time (internal)."""
        if not self.real_time:
            return
        now = _time.monotonic()
        elapsed = now - self._rt_anchor_time
        ticks_per_second = self.cycle_length / self.real_time_seconds_per_cycle
        rt_ticks = int(elapsed * ticks_per_second)
        new_ticks = self._rt_anchor_ticks + rt_ticks
        if new_ticks > self.ticks:
            self.ticks = new_ticks

    def update(self) -> None:
        """Called each frame to advance real-time ticks. No-op if not real-time."""
        self._sync_real_time()

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
        self._sync_real_time()
        self.ticks += steps
        # Re-anchor so real-time doesn't double-count these ticks
        if self.real_time:
            self._rt_anchor_time = _time.monotonic()
            self._rt_anchor_ticks = self.ticks

    def advance_hours(self, hours: int) -> None:
        """Advance time by a number of in-game hours.

        A full cycle = 24 hours, so 1 hour = cycle_length / 24 ticks.
        """
        ticks_per_hour = self.cycle_length / 24
        self.advance(int(ticks_per_hour * hours))

    @property
    def previous_period(self) -> TimePeriod:
        """The period that was active one tick ago (useful for transition detection)."""
        if self.ticks == 0:
            return TimePeriod.DAWN
        position = (self.ticks - 1) % self.cycle_length
        cumulative = 0.0
        for period, fraction in PERIOD_SEQUENCE:
            cumulative += fraction * self.cycle_length
            if position < cumulative:
                return period
        return TimePeriod.NIGHT

    def period_just_changed(self) -> bool:
        """True if the current tick is the first tick of a new period."""
        return self.current_period != self.previous_period

    def serialize(self) -> dict:
        return {
            "ticks": self.ticks,
            "cycle_length": self.cycle_length,
            "real_time": self.real_time,
            "real_time_seconds_per_cycle": self.real_time_seconds_per_cycle,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "DayNightCycle":
        cycle = cls(
            ticks=data.get("ticks", 0),
            cycle_length=data.get("cycle_length", 200),
            real_time=data.get("real_time", False),
            real_time_seconds_per_cycle=data.get("real_time_seconds_per_cycle", 600.0),
        )
        if cycle.real_time:
            cycle.enable_real_time()
        return cycle
