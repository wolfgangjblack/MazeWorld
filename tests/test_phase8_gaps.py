"""Tests for Phase 8 gap fills: real-time day/night, night monsters,
time-gated events, and NPC availability scheduling."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.time import DayNightCycle, TimePeriod, DEFAULT_CYCLE_MS
from src.models.monster import (
    Monster, generate_night_monster,
    generate_night_variant, NIGHT_MONSTER_POOLS,
)
from src.models.encounter import Event, CombatEvent, PuzzleEvent, EventEncounter
from src.models.npc import NPC, StaticNPC, MerchantNPC
from src.systems.day_night import is_event_active_at_time, is_npc_available


# ── Real-time DayNightCycle ──────────────────────────────────────────────


class TestRealTimeCycle:
    def test_starts_at_dawn(self):
        cycle = DayNightCycle()
        assert cycle.current_period == TimePeriod.DAWN

    def test_update_advances_elapsed(self):
        cycle = DayNightCycle()
        cycle.update(1000)  # First call sets baseline
        cycle.update(2000)  # Second call adds 1000 ms
        assert cycle.elapsed_ms == 1000

    def test_update_multiple_frames(self):
        cycle = DayNightCycle()
        cycle.update(100)  # First call sets baseline, no advance
        cycle.update(200)  # +100
        cycle.update(500)  # +300
        assert cycle.elapsed_ms == 400

    def test_period_transitions_real_time(self):
        """With default 960,000 ms cycle:
        Dawn: 0 - 143,999 ms (15%)
        Day: 144,000 - 479,999 ms (35%)
        Dusk: 480,000 - 623,999 ms (15%)
        Night: 624,000 - 959,999 ms (35%)
        """
        cycle = DayNightCycle()
        assert cycle.current_period == TimePeriod.DAWN

        cycle.elapsed_ms = 143_999
        assert cycle.current_period == TimePeriod.DAWN

        cycle.elapsed_ms = 144_000
        assert cycle.current_period == TimePeriod.DAY

        cycle.elapsed_ms = 479_999
        assert cycle.current_period == TimePeriod.DAY

        cycle.elapsed_ms = 480_000
        assert cycle.current_period == TimePeriod.DUSK

        cycle.elapsed_ms = 623_999
        assert cycle.current_period == TimePeriod.DUSK

        cycle.elapsed_ms = 624_000
        assert cycle.current_period == TimePeriod.NIGHT

        cycle.elapsed_ms = 959_999
        assert cycle.current_period == TimePeriod.NIGHT

    def test_cycle_wraps(self):
        cycle = DayNightCycle()
        cycle.elapsed_ms = DEFAULT_CYCLE_MS  # Start of next cycle
        assert cycle.current_period == TimePeriod.DAWN

    def test_is_night(self):
        cycle = DayNightCycle()
        cycle.elapsed_ms = 700_000  # Well into night
        assert cycle.is_night

        cycle.elapsed_ms = 300_000  # Daytime
        assert not cycle.is_night

    def test_day_number(self):
        cycle = DayNightCycle()
        assert cycle.day_number == 1

        cycle.elapsed_ms = DEFAULT_CYCLE_MS
        assert cycle.day_number == 2

        cycle.elapsed_ms = DEFAULT_CYCLE_MS * 3 - 1
        assert cycle.day_number == 3

    def test_advance_hours_jumps_forward(self):
        cycle = DayNightCycle()
        ms_per_hour = DEFAULT_CYCLE_MS / 24
        cycle.advance_hours(6)
        assert cycle.elapsed_ms == int(ms_per_hour * 6)

    def test_advance_steps_for_combat(self):
        cycle = DayNightCycle()
        ms_per_step = DEFAULT_CYCLE_MS // 200
        cycle.advance(5)
        assert cycle.elapsed_ms == ms_per_step * 5

    def test_period_progress(self):
        cycle = DayNightCycle()
        cycle.elapsed_ms = 0
        assert cycle.period_progress == pytest.approx(0.0)

        # Midpoint of dawn (0 to 144,000): 72,000 ms
        cycle.elapsed_ms = 72_000
        assert cycle.period_progress == pytest.approx(0.5)

    def test_serialize_deserialize(self):
        cycle = DayNightCycle()
        cycle.elapsed_ms = 500_000
        data = cycle.serialize()
        restored = DayNightCycle.deserialize(data)
        assert restored.elapsed_ms == 500_000
        assert restored.current_period == cycle.current_period

    def test_deserialize_legacy_ticks(self):
        """Legacy saves with ticks/cycle_length should convert to elapsed_ms."""
        legacy_data = {"ticks": 100, "cycle_length": 200}
        cycle = DayNightCycle.deserialize(legacy_data)
        # 100 / 200 = 0.5 of cycle = 480,000 ms
        assert cycle.elapsed_ms == 480_000
        assert cycle.current_period == TimePeriod.DUSK

    def test_update_ignores_negative_delta(self):
        cycle = DayNightCycle()
        cycle.update(1000)
        cycle.update(500)  # Time went backwards (shouldn't happen, but be safe)
        assert cycle.elapsed_ms == 0


# ── Night monster variants ───────────────────────────────────────────────


class TestNightMonsterVariants:
    def test_monster_has_time_availability_field(self):
        m = Monster(species="Wolf", hp=10, max_hp=10)
        assert m.time_availability == "always"

    def test_generate_night_variant_stats(self):
        base = Monster(
            species="Wolf", name="Wolf", hp=20, max_hp=20,
            str_mod=2, elemental_affinity=None, damage_type="physical",
        )
        variant = generate_night_variant(base)
        assert variant.hp == 25  # 20 * 1.25
        assert variant.max_hp == 25
        assert variant.str_mod == 3  # 2 + 1
        assert variant.elemental_affinity == "dark"
        assert variant.damage_type == "dark"
        assert variant.time_availability == "night"
        assert variant.name.startswith("Nightstalker")
        assert variant.species.startswith("Nightstalker")

    def test_generate_night_variant_no_double_prefix(self):
        base = Monster(
            species="Wolf", name="Nightstalker Wolf",
            hp=20, max_hp=20, str_mod=1,
        )
        variant = generate_night_variant(base)
        assert variant.name == "Nightstalker Wolf"  # No double prefix

    def test_generate_night_variant_unique_id(self):
        base = Monster(species="Wolf", hp=10, max_hp=10)
        variant = generate_night_variant(base)
        assert variant.id != base.id

    def test_generate_night_monster(self):
        m = generate_night_monster("forest", 2)
        assert m.time_availability == "night"
        assert m.elemental_affinity == "dark"
        assert m.damage_type == "dark"
        assert m.species in NIGHT_MONSTER_POOLS["forest"]

    def test_generate_night_monster_harder_stats(self):
        """Night monsters should have +25% HP vs normal level scaling."""
        # Generate many and check HP is boosted
        monsters = [generate_night_monster("cave", 1) for _ in range(20)]
        # Level 1 normal HP range: 8-12. With 1.25x: 10-15
        for m in monsters:
            assert m.hp >= 10  # int(8 * 1.25)

    def test_night_monster_pools_all_environments(self):
        """Every environment should have a night monster pool."""
        from src.models.monster import MONSTER_POOLS
        for env in MONSTER_POOLS:
            assert env in NIGHT_MONSTER_POOLS, f"Missing night pool for {env}"

    def test_monster_to_dict_includes_time_availability(self):
        m = Monster(species="Wolf", hp=10, max_hp=10, time_availability="night")
        d = m.to_dict()
        assert d["time_availability"] == "night"

    def test_monster_from_dict_time_availability(self):
        d = {"species": "Wolf", "hp": 10, "max_hp": 10, "time_availability": "night"}
        m = Monster.from_dict(d)
        assert m.time_availability == "night"


# ── Time-gated events ───────────────────────────────────────────────────


class TestTimeGatedEvents:
    def test_event_has_time_gate_field(self):
        e = Event(id="test", type="combat", name="Test", description="desc")
        assert e.time_gate is None

    def test_event_time_gate_day(self):
        e = Event(id="test", type="combat", name="Test", description="desc", time_gate="day")
        assert e.time_gate == "day"
        assert is_event_active_at_time(e, TimePeriod.DAY)
        assert is_event_active_at_time(e, TimePeriod.DAWN)
        assert not is_event_active_at_time(e, TimePeriod.NIGHT)
        assert not is_event_active_at_time(e, TimePeriod.DUSK)

    def test_event_time_gate_night(self):
        e = Event(id="test", type="combat", name="Test", description="desc", time_gate="night")
        assert is_event_active_at_time(e, TimePeriod.NIGHT)
        assert is_event_active_at_time(e, TimePeriod.DUSK)
        assert not is_event_active_at_time(e, TimePeriod.DAY)
        assert not is_event_active_at_time(e, TimePeriod.DAWN)

    def test_event_time_gate_none_always_active(self):
        e = Event(id="test", type="combat", name="Test", description="desc")
        for period in TimePeriod:
            assert is_event_active_at_time(e, period)

    def test_combat_event_inherits_time_gate(self):
        ce = CombatEvent(id="c1", name="Fight", description="desc", time_gate="night")
        assert ce.time_gate == "night"
        assert is_event_active_at_time(ce, TimePeriod.NIGHT)
        assert not is_event_active_at_time(ce, TimePeriod.DAY)

    def test_puzzle_event_inherits_time_gate(self):
        pe = PuzzleEvent(id="p1", name="Puzzle", description="desc", time_gate="day")
        assert pe.time_gate == "day"
        assert is_event_active_at_time(pe, TimePeriod.DAY)

    def test_event_encounter_inherits_time_gate(self):
        ee = EventEncounter(id="e1", name="Event", description="desc", time_gate="night")
        assert ee.time_gate == "night"


# ── NPC availability scheduling ──────────────────────────────────────────


class TestNPCAvailability:
    def test_npc_has_availability_field(self):
        npc = NPC(x=0, y=0, id=1)
        assert npc.availability is None

    def test_npc_availability_day(self):
        npc = NPC(x=0, y=0, id=1, availability="day")
        assert is_npc_available(npc, TimePeriod.DAY)
        assert is_npc_available(npc, TimePeriod.DAWN)
        assert not is_npc_available(npc, TimePeriod.NIGHT)
        assert not is_npc_available(npc, TimePeriod.DUSK)

    def test_npc_availability_night(self):
        npc = NPC(x=0, y=0, id=1, availability="night")
        assert is_npc_available(npc, TimePeriod.NIGHT)
        assert is_npc_available(npc, TimePeriod.DUSK)
        assert not is_npc_available(npc, TimePeriod.DAY)
        assert not is_npc_available(npc, TimePeriod.DAWN)

    def test_npc_availability_always(self):
        npc = NPC(x=0, y=0, id=1, availability="always")
        for period in TimePeriod:
            assert is_npc_available(npc, period)

    def test_npc_availability_none_always_available(self):
        npc = NPC(x=0, y=0, id=1)
        for period in TimePeriod:
            assert is_npc_available(npc, period)

    def test_static_npc_availability(self):
        npc = StaticNPC(x=0, y=0, id=1, availability="night")
        assert not is_npc_available(npc, TimePeriod.DAY)
        assert is_npc_available(npc, TimePeriod.NIGHT)

    def test_merchant_npc_availability(self):
        npc = MerchantNPC(x=0, y=0, id=1, availability="day")
        assert is_npc_available(npc, TimePeriod.DAY)
        assert not is_npc_available(npc, TimePeriod.NIGHT)
