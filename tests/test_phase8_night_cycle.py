"""Tests for Phase 8: Night monsters, time-gated encounters/NPCs, real-time day cycle."""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.time import DayNightCycle, TimePeriod
from src.models.monster import (
    generate_night_monster, generate_night_encounter_monsters,
    NIGHT_MONSTER_POOLS, NIGHT_ATTACK_NAMES,
)
from src.models.encounter import Event, CombatEvent
from src.models.npc import NPC, StaticNPC
from src.systems.day_night import (
    is_event_active_at_time, is_npc_available, spawn_night_encounter,
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


# ---------------------------------------------------------------------------
# Night monster generation
# ---------------------------------------------------------------------------

class TestNightMonsters:
    def test_generate_night_monster_returns_monster(self):
        monster = generate_night_monster("forest", 1)
        assert monster is not None
        assert monster.species in NIGHT_MONSTER_POOLS["forest"]
        assert monster.damage_type == "dark"
        assert monster.elemental_affinity == "dark"

    def test_night_monster_boosted_level(self):
        """Night monsters should be one level tier higher."""
        monster = generate_night_monster("dungeon", 1)
        assert monster.level == 2  # Boosted from 1 to 2

    def test_night_monster_max_level_cap(self):
        """Night monster level boost should cap at max scaling level (4)."""
        monster = generate_night_monster("cave", 4)
        assert monster.level == 4  # Already at max, stays at 4

    def test_night_monster_has_dark_affinity(self):
        for _ in range(10):
            monster = generate_night_monster("city", 2)
            assert monster.elemental_affinity == "dark"

    def test_night_monster_all_environments(self):
        """All environment keys should work."""
        for env in NIGHT_MONSTER_POOLS:
            monster = generate_night_monster(env, 1)
            assert monster.species in NIGHT_MONSTER_POOLS[env]

    def test_generate_night_encounter_returns_list(self):
        monsters = generate_night_encounter_monsters("forest", 2)
        assert isinstance(monsters, list)
        assert len(monsters) >= 1
        for m in monsters:
            assert m.elemental_affinity == "dark"

    def test_night_monster_pools_all_environments(self):
        """Every environment in regular pools should have a night pool."""
        from src.models.monster import MONSTER_POOLS
        for env in MONSTER_POOLS:
            assert env in NIGHT_MONSTER_POOLS, f"Missing night pool for {env}"

    def test_night_attack_names_all_environments(self):
        """Every environment in night pools should have attack names."""
        for env in NIGHT_MONSTER_POOLS:
            assert env in NIGHT_ATTACK_NAMES, f"Missing night attacks for {env}"


# ---------------------------------------------------------------------------
# Time-gated events (model-level field)
# ---------------------------------------------------------------------------

class TestEventTimeGate:
    def test_event_has_time_gate_field(self):
        event = CombatEvent(id="test", name="Test", description="desc")
        assert event.time_gate is None

    def test_event_time_gate_night(self):
        event = CombatEvent(
            id="test", name="Night Fight",
            description="desc", time_gate="night",
        )
        assert event.time_gate == "night"
        assert is_event_active_at_time(event, TimePeriod.NIGHT)
        assert not is_event_active_at_time(event, TimePeriod.DAY)

    def test_event_time_gate_day(self):
        event = CombatEvent(
            id="test", name="Day Fight",
            description="desc", time_gate="day",
        )
        assert is_event_active_at_time(event, TimePeriod.DAY)
        assert is_event_active_at_time(event, TimePeriod.DAWN)
        assert not is_event_active_at_time(event, TimePeriod.NIGHT)


# ---------------------------------------------------------------------------
# NPC availability (model-level field)
# ---------------------------------------------------------------------------

class TestNPCAvailabilityField:
    def test_npc_has_availability_field(self):
        npc = StaticNPC(x=0, y=0, id=1)
        assert npc.availability is None

    def test_npc_day_availability(self):
        npc = StaticNPC(x=0, y=0, id=1, availability="day")
        assert is_npc_available(npc, TimePeriod.DAY)
        assert not is_npc_available(npc, TimePeriod.NIGHT)

    def test_npc_night_availability(self):
        npc = StaticNPC(x=0, y=0, id=1, availability="night")
        assert is_npc_available(npc, TimePeriod.NIGHT)
        assert is_npc_available(npc, TimePeriod.DUSK)
        assert not is_npc_available(npc, TimePeriod.DAY)


# ---------------------------------------------------------------------------
# Night encounter spawning
# ---------------------------------------------------------------------------

class TestNightEncounterSpawning:
    class FakeMaze:
        def __init__(self):
            self.grid = [[0] * 10 for _ in range(10)]
            self.environment = "forest"

    class FakePlayer:
        def __init__(self):
            self.x = 5
            self.y = 5

    def test_no_spawn_during_day(self):
        """Night encounters should never spawn during daytime."""
        maze = self.FakeMaze()
        player = self.FakePlayer()
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 50  # Daytime

        for _ in range(100):
            result = spawn_night_encounter(maze, player, cycle, room_level=1)
            assert result is None

    def test_spawn_possible_at_night(self):
        """Night encounters should be possible when it's night."""
        maze = self.FakeMaze()
        player = self.FakePlayer()
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 150  # Night

        spawned = False
        for _ in range(200):
            result = spawn_night_encounter(maze, player, cycle, room_level=1)
            if result is not None:
                spawned = True
                assert result.type == "combat"
                assert result.time_gate == "night"
                assert "night" in result.id.lower() or "Night" in result.name
                assert len(result.monsters) >= 1
                break

        assert spawned, "Should have spawned at least one night encounter in 200 attempts"

    def test_no_spawn_on_event_tile(self):
        """Night encounters should not spawn on non-open tiles."""
        maze = self.FakeMaze()
        maze.grid[5][5] = -1  # Event tile
        player = self.FakePlayer()
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 150

        for _ in range(100):
            result = spawn_night_encounter(maze, player, cycle, room_level=1)
            assert result is None

    def test_spawned_encounter_has_monsters(self):
        maze = self.FakeMaze()
        player = self.FakePlayer()
        cycle = DayNightCycle(cycle_length=200)
        cycle.ticks = 150

        for _ in range(200):
            result = spawn_night_encounter(maze, player, cycle, room_level=2)
            if result is not None:
                assert len(result.monsters) >= 1
                for m in result.monsters:
                    assert m.elemental_affinity == "dark"
                break
