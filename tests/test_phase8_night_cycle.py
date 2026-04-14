"""Tests for Phase 8: time-gated encounters/NPCs, real-time day cycle."""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.encounter import CombatEvent
from src.models.npc import StaticNPC
from src.models.time import DayNightCycle, TimePeriod
from src.systems.day_night import (
    is_event_active_at_time,
    is_npc_available,
)

# ---------------------------------------------------------------------------
# Real-time day cycle
# ---------------------------------------------------------------------------


class TestRealTimeDayCycle:
    def test_enable_real_time(self):
        cycle = DayNightCycle()
        cycle.enable_real_time()
        assert cycle.real_time is True

    def test_disable_real_time(self):
        cycle = DayNightCycle()
        cycle.enable_real_time()
        cycle.disable_real_time()
        assert cycle.real_time is False

    def test_real_time_advances_ticks(self):
        """Real-time mode should advance ticks based on elapsed wall time."""
        cycle = DayNightCycle(cycle_length=200, real_time_seconds_per_cycle=1.0)
        cycle.enable_real_time()

        # Wait a small amount and check ticks advanced
        time.sleep(0.15)
        cycle.update()
        assert cycle.ticks > 0, "Real-time should have advanced ticks"

    def test_real_time_does_not_double_count_action_ticks(self):
        """Action ticks should re-anchor so real-time doesn't double-count."""
        cycle = DayNightCycle(cycle_length=200, real_time_seconds_per_cycle=100.0)
        cycle.enable_real_time()

        cycle.advance(50)
        assert cycle.ticks == 50

        # After advance, the anchor is reset — no double-counting
        cycle.update()
        assert cycle.ticks >= 50  # Should be 50 or very close

    def test_real_time_serialization_round_trip(self):
        cycle = DayNightCycle(
            cycle_length=200,
            real_time_seconds_per_cycle=300.0,
        )
        cycle.enable_real_time()
        cycle.advance(100)

        data = cycle.serialize()
        assert data["real_time"] is True
        assert data["real_time_seconds_per_cycle"] == 300.0
        assert data["ticks"] == 100

        restored = DayNightCycle.deserialize(data)
        assert restored.real_time is True
        assert restored.ticks == 100
        assert restored.real_time_seconds_per_cycle == 300.0

    def test_non_real_time_serialization_backward_compat(self):
        """Old save data without real_time fields should load fine."""
        data = {"ticks": 75, "cycle_length": 200}
        restored = DayNightCycle.deserialize(data)
        assert restored.ticks == 75
        assert restored.real_time is False

    def test_update_noop_when_not_real_time(self):
        cycle = DayNightCycle()
        cycle.ticks = 50
        cycle.update()
        assert cycle.ticks == 50  # No change

    def test_period_just_changed(self):
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 29  # Last tick of dawn
        assert not cycle.period_just_changed()

        cycle.ticks = 30  # First tick of day
        assert cycle.period_just_changed()

    def test_previous_period(self):
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 30  # First tick of day, previous was dawn
        assert cycle.previous_period == TimePeriod.DAWN
        assert cycle.current_period == TimePeriod.DAY


# Night monster generation tests removed: roaming night encounter system
# replaced with LLM-generated time-gated event tiles.


# ---------------------------------------------------------------------------
# Time-gated events (model-level field)
# ---------------------------------------------------------------------------


class TestEventTimeGate:
    def test_event_has_time_gate_field(self):
        event = CombatEvent(id=3000, name="Test", description="desc")
        assert event.time_gate is None

    def test_event_time_gate_night(self):
        event = CombatEvent(
            id=3001,
            name="Night Fight",
            description="desc",
            time_gate="night",
        )
        assert event.time_gate == "night"
        assert is_event_active_at_time(event, TimePeriod.NIGHT)
        assert not is_event_active_at_time(event, TimePeriod.DAY)

    def test_event_time_gate_day(self):
        event = CombatEvent(
            id=3002,
            name="Day Fight",
            description="desc",
            time_gate="day",
        )
        assert is_event_active_at_time(event, TimePeriod.DAY)
        assert is_event_active_at_time(event, TimePeriod.DAWN)
        assert not is_event_active_at_time(event, TimePeriod.NIGHT)


# ---------------------------------------------------------------------------
# NPC availability (model-level field)
# ---------------------------------------------------------------------------


class TestNPCAvailabilityField:
    def test_npc_has_availability_field(self):
        npc = StaticNPC(x=0, y=0, id=1000)
        assert npc.availability is None

    def test_npc_day_availability(self):
        npc = StaticNPC(x=0, y=0, id=1000, availability="day")
        assert is_npc_available(npc, TimePeriod.DAY)
        assert not is_npc_available(npc, TimePeriod.NIGHT)

    def test_npc_night_availability(self):
        npc = StaticNPC(x=0, y=0, id=1000, availability="night")
        assert is_npc_available(npc, TimePeriod.NIGHT)
        assert is_npc_available(npc, TimePeriod.DUSK)
        assert not is_npc_available(npc, TimePeriod.DAY)


# Night encounter spawning tests removed: roaming system replaced with
# LLM-generated time-gated event tiles.
