"""Tests for the Day/Night cycle system."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.time import DayNightCycle, TimePeriod
from src.systems.day_night import (
    apply_rest, apply_combat_rest, player_has_torch, consume_torch_use,
    is_event_active_at_time, is_npc_available, get_night_overlay_alpha,
    COMBAT_REST_HP,
)
from src.models.player import PlayerCharacter, PlayerClass, Stats
from src.models.items import Tool, ItemStats


def _make_player(x=5, y=5, health=50, max_health=100,
                 hunger=80, thirst=80):
    p = PlayerCharacter(x=x, y=y)
    p.health = health
    p.max_health = max_health
    p.hunger = hunger
    p.thirst = thirst
    p.max_hunger = 100
    p.max_thirst = 100
    p.player_class = PlayerClass(
        name="Test",
        archetype="warrior",
        stats=Stats(STR=14, CON=14, DEX=12, CHA=12, INT=8, WIS=8, LUCK=10),
    )
    return p


def _make_torch(uses=10):
    return Tool(
        category="tool",
        name="torch",
        desc="A torch.",
        item_stats=ItemStats(attribute="light", uses=uses),
    )


class TestDayNightCycleModel:
    def test_starts_at_dawn(self):
        cycle = DayNightCycle()
        assert cycle.current_period == TimePeriod.DAWN

    def test_advance_moves_ticks(self):
        cycle = DayNightCycle()
        cycle.advance(10)
        assert cycle.ticks == 10

    def test_period_transitions(self):
        """Verify periods transition at correct thresholds.

        With cycle_length=200:
          Dawn: 0-29 (15%)
          Day: 30-99 (35%)
          Dusk: 100-129 (15%)
          Night: 130-199 (35%)
        """
        cycle = DayNightCycle(cycle_length=200)

        cycle.ticks = 0
        assert cycle.current_period == TimePeriod.DAWN

        cycle.ticks = 29
        assert cycle.current_period == TimePeriod.DAWN

        cycle.ticks = 30
        assert cycle.current_period == TimePeriod.DAY

        cycle.ticks = 99
        assert cycle.current_period == TimePeriod.DAY

        cycle.ticks = 100
        assert cycle.current_period == TimePeriod.DUSK

        cycle.ticks = 129
        assert cycle.current_period == TimePeriod.DUSK

        cycle.ticks = 130
        assert cycle.current_period == TimePeriod.NIGHT

        cycle.ticks = 199
        assert cycle.current_period == TimePeriod.NIGHT

    def test_cycle_wraps(self):
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 200  # Start of next cycle
        assert cycle.current_period == TimePeriod.DAWN

    def test_is_night(self):
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 150
        assert cycle.is_night

        cycle.ticks = 50
        assert not cycle.is_night

    def test_day_number(self):
        cycle = DayNightCycle(cycle_length=200)
        assert cycle.day_number == 1

        cycle.ticks = 200
        assert cycle.day_number == 2

        cycle.ticks = 599
        assert cycle.day_number == 3

    def test_advance_hours(self):
        cycle = DayNightCycle(cycle_length=200)
        # 1 hour = 200/24 ≈ 8.33 ticks, 6 hours = int(8.33 * 6) = 50
        cycle.advance_hours(6)
        assert cycle.ticks == 50

    def test_period_progress(self):
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 0
        assert cycle.period_progress == pytest.approx(0.0)

        # Midpoint of dawn (0-30): tick 15
        cycle.ticks = 15
        assert cycle.period_progress == pytest.approx(0.5)


class TestTimeAdvancesOnActions:
    def test_movement_advances_time(self):
        """Simulating that movement calls cycle.advance(1)."""
        cycle = DayNightCycle()
        initial = cycle.ticks
        cycle.advance(1)  # One movement step
        assert cycle.ticks == initial + 1

    def test_combat_advances_time(self):
        """Each combat turn should advance time."""
        cycle = DayNightCycle()
        # Simulate 5 combat turns
        for _ in range(5):
            cycle.advance(1)
        assert cycle.ticks == 5

    def test_rest_advances_time(self):
        """Rest should advance time by hours."""
        cycle = DayNightCycle(cycle_length=200)
        initial = cycle.ticks
        cycle.advance_hours(6)
        assert cycle.ticks > initial


class TestRestMechanic:
    def test_3hr_rest_recovery(self):
        player = _make_player(health=50, hunger=80, thirst=80)
        cycle = DayNightCycle()
        msg = apply_rest(player, 3, cycle)
        assert player.health == 65  # 50 + 15
        assert player.hunger == 75  # 80 - 5
        assert player.thirst == 75  # 80 - 5
        assert "3h" in msg

    def test_6hr_rest_recovery(self):
        player = _make_player(health=50, hunger=80, thirst=80)
        cycle = DayNightCycle()
        apply_rest(player, 6, cycle)
        assert player.health == 80  # 50 + 30
        assert player.hunger == 70  # 80 - 10
        assert player.thirst == 70  # 80 - 10

    def test_12hr_rest_capped_costs(self):
        """12hr rest has same hunger/thirst cost as 6hr (capped)."""
        player = _make_player(health=50, hunger=80, thirst=80)
        cycle = DayNightCycle()
        apply_rest(player, 12, cycle)
        assert player.health == 100  # 50 + 50, capped at max
        assert player.hunger == 70  # Same cost as 6hr
        assert player.thirst == 70

    def test_rest_caps_at_max_health(self):
        player = _make_player(health=95, max_health=100)
        cycle = DayNightCycle()
        apply_rest(player, 3, cycle)
        assert player.health == 100  # Capped at max

    def test_rest_advances_time(self):
        player = _make_player()
        cycle = DayNightCycle(cycle_length=200)
        initial_ticks = cycle.ticks
        apply_rest(player, 6, cycle)
        assert cycle.ticks > initial_ticks

    def test_combat_rest(self):
        player = _make_player(health=50)
        msg = apply_combat_rest(player)
        assert player.health == 50 + COMBAT_REST_HP
        assert str(COMBAT_REST_HP) in msg

    def test_invalid_rest_duration(self):
        player = _make_player()
        cycle = DayNightCycle()
        msg = apply_rest(player, 4, cycle)  # Invalid
        assert "Invalid" in msg


class TestTorchMechanic:
    def test_player_has_torch_with_light_item(self):
        player = _make_player()
        torch = _make_torch(uses=5)
        player.add_to_inventory(torch)
        assert player_has_torch(player)

    def test_player_no_torch_without_item(self):
        player = _make_player()
        assert not player_has_torch(player)

    def test_player_no_torch_if_exhausted(self):
        player = _make_player()
        torch = _make_torch(uses=0)
        player.add_to_inventory(torch)
        assert not player_has_torch(player)

    def test_consume_torch_use(self):
        player = _make_player()
        torch = _make_torch(uses=5)
        player.add_to_inventory(torch)
        consume_torch_use(player)
        assert player.inventory["torch"].item_stats.uses == 4


class TestTimeGatedEncounters:
    def _make_event(self, time_gate=None):
        class FakeEvent:
            def __init__(self, tg):
                self.time_gate = tg
        return FakeEvent(time_gate)

    def test_no_gate_always_active(self):
        event = self._make_event(None)
        assert is_event_active_at_time(event, TimePeriod.DAY)
        assert is_event_active_at_time(event, TimePeriod.NIGHT)

    def test_always_gate_always_active(self):
        event = self._make_event("always")
        assert is_event_active_at_time(event, TimePeriod.DAY)
        assert is_event_active_at_time(event, TimePeriod.NIGHT)

    def test_day_gate_active_during_day(self):
        event = self._make_event("day")
        assert is_event_active_at_time(event, TimePeriod.DAWN)
        assert is_event_active_at_time(event, TimePeriod.DAY)
        assert not is_event_active_at_time(event, TimePeriod.NIGHT)
        assert not is_event_active_at_time(event, TimePeriod.DUSK)

    def test_night_gate_active_during_night(self):
        event = self._make_event("night")
        assert is_event_active_at_time(event, TimePeriod.NIGHT)
        assert is_event_active_at_time(event, TimePeriod.DUSK)
        assert not is_event_active_at_time(event, TimePeriod.DAY)
        assert not is_event_active_at_time(event, TimePeriod.DAWN)


class TestNPCAvailability:
    def _make_npc(self, availability=None):
        class FakeNPC:
            def __init__(self, avail):
                self.availability = avail
        return FakeNPC(availability)

    def test_no_schedule_always_available(self):
        npc = self._make_npc(None)
        assert is_npc_available(npc, TimePeriod.DAY)
        assert is_npc_available(npc, TimePeriod.NIGHT)

    def test_day_npc_not_available_at_night(self):
        npc = self._make_npc("day")
        assert is_npc_available(npc, TimePeriod.DAY)
        assert not is_npc_available(npc, TimePeriod.NIGHT)

    def test_night_npc_available_at_night(self):
        npc = self._make_npc("night")
        assert is_npc_available(npc, TimePeriod.NIGHT)
        assert not is_npc_available(npc, TimePeriod.DAY)


class TestNightOverlay:
    def test_day_no_overlay(self):
        assert get_night_overlay_alpha(TimePeriod.DAY, 0.5) == 0
        assert get_night_overlay_alpha(TimePeriod.DAWN, 0.5) == 0

    def test_night_full_overlay(self):
        assert get_night_overlay_alpha(TimePeriod.NIGHT, 0.5) == 80

    def test_dusk_gradual_overlay(self):
        alpha_start = get_night_overlay_alpha(TimePeriod.DUSK, 0.0)
        alpha_mid = get_night_overlay_alpha(TimePeriod.DUSK, 0.5)
        alpha_end = get_night_overlay_alpha(TimePeriod.DUSK, 1.0)
        assert alpha_start == 0
        assert alpha_mid == 40
        assert alpha_end == 80


class TestDayNightSerialization:
    def test_round_trip(self):
        cycle = DayNightCycle(cycle_length=200)
        cycle.advance(75)

        data = cycle.serialize()
        restored = DayNightCycle.deserialize(data)

        assert restored.ticks == 75
        assert restored.cycle_length == 200
        assert restored.current_period == cycle.current_period
