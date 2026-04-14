"""Day/Night cycle data model.

Supports two modes:
- **Action-based** (default): ticks advance on movement/combat/rest actions.
- **Real-time**: ticks also advance continuously based on wall-clock time,
  controlled by ``real_time_seconds_per_cycle`` (default 600 = 10 minutes
  per full in-game day).  Action ticks still apply on top.
  A pygame-driven real-time clock (``update_realtime``) also tracks elapsed
  milliseconds for smooth rendering (full cycle ~16 minutes).
"""

import time as _time
from enum import Enum

from pydantic import BaseModel, PrivateAttr


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


class DayNightCycle(BaseModel):
    """Day/night cycle with optional real-time advancement.

    Time advances with movement steps, combat turns, and rest actions.
    A full cycle = ``cycle_length`` actions (default 200).

    When ``real_time`` is True, ticks also advance continuously based on
    elapsed wall-clock seconds (``real_time_seconds_per_cycle`` seconds
    = one full day cycle).  A pygame-driven millisecond clock
    (``update_realtime``) is also maintained for smooth rendering.
    """
    ticks: int = 0
    cycle_length: int = 200  # kept for action-based compat / serialization

    # Real-time tracking (ms). Set start_ms on first update().
    elapsed_ms: int = 0
    last_update_ms: int = 0  # last pygame.time.get_ticks value

    @property
    def _effective_ms(self) -> int:
        """Total effective time: real-time + action advances."""
        # Actions map to ms: each tick = FULL_CYCLE_MS / cycle_length
        action_ms = int(self.ticks * (FULL_CYCLE_MS / self.cycle_length))
        return self.elapsed_ms + action_ms

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

    # Pausing support — freezes both real-time and pygame-based advancement
    _paused: bool = PrivateAttr(default=False)
    _pause_elapsed_ms: int = PrivateAttr(default=0)
    _pause_start_ticks: int = PrivateAttr(default=0)

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        """Freeze time advancement (for menus, combat, events)."""
        if self._paused:
            return
        self._paused = True
        self._pause_elapsed_ms = self.elapsed_ms
        self._pause_start_ticks = self.last_update_ms

    def resume(self) -> None:
        """Resume time advancement, discarding time spent paused."""
        if not self._paused:
            return
        self._paused = False
        self.elapsed_ms = self._pause_elapsed_ms
        if self.real_time:
            self._rt_anchor_time = _time.monotonic()
            self._rt_anchor_ticks = self.ticks

    def update_realtime(self, current_ms: int) -> None:
        """Call each frame with pygame.time.get_ticks(). Advances elapsed_ms."""
        if self._paused:
            self.last_update_ms = current_ms
            return
        if self.last_update_ms <= 0:
            self.last_update_ms = max(1, current_ms)
            return
        delta = current_ms - self.last_update_ms
        if delta > 0:
            self.elapsed_ms += delta
        self.last_update_ms = current_ms

    def advance(self, steps: int = 1) -> None:
        """Advance time by the given number of action steps."""
        self._sync_real_time()
        self.ticks += steps
        # Re-anchor so real-time doesn't double-count these ticks
        if self.real_time:
            self._rt_anchor_time = _time.monotonic()
            self._rt_anchor_ticks = self.ticks

    def advance_hours(self, hours: int) -> None:
        """Advance time by in-game hours. A full cycle = 24 hours."""
        ms_per_hour = FULL_CYCLE_MS / 24
        self.elapsed_ms += int(ms_per_hour * hours)

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
            "elapsed_ms": self.elapsed_ms,
            "real_time": self.real_time,
            "real_time_seconds_per_cycle": self.real_time_seconds_per_cycle,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "DayNightCycle":
        cycle = cls(
            ticks=data.get("ticks", 0),
            cycle_length=data.get("cycle_length", 200),
            elapsed_ms=data.get("elapsed_ms", 0),
            real_time=data.get("real_time", False),
            real_time_seconds_per_cycle=data.get("real_time_seconds_per_cycle", 600.0),
        )
        if cycle.real_time:
            cycle.enable_real_time()
        return cycle
