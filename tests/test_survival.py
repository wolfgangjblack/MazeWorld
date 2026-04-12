"""Tests for the stamina-based survival system."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.systems.survival import (
    SurvivalSystem,
    STAMINA_DRAIN_PER_CYCLE,
    STAMINA_DRAIN_INTERVAL_MS,
    THRESHOLD_WARNING,
    THRESHOLD_PENALTY,
    THRESHOLD_CRITICAL,
    SPEED_PENALTY_FACTOR,
)
from src.models.player import PlayerCharacter


def _make_player(stamina=100) -> PlayerCharacter:
    player = PlayerCharacter(x=0, y=0)
    player.stamina = stamina
    player.max_stamina = 100
    return player


class TestStaminaDrain:

    def test_on_time_update_drains_stamina(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=100)

        ms_per_point = STAMINA_DRAIN_INTERVAL_MS // STAMINA_DRAIN_PER_CYCLE
        survival.on_time_update(player, ms_per_point)

        assert player.stamina == 99

    def test_no_drain_with_zero_elapsed(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=100)

        survival.on_time_update(player, 0)

        assert player.stamina == 100

    def test_stamina_floors_at_zero(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=1)

        survival.on_time_update(player, STAMINA_DRAIN_INTERVAL_MS)

        assert player.stamina == 0

    def test_multiple_drains_accumulate(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=100)

        ms_per_point = STAMINA_DRAIN_INTERVAL_MS // STAMINA_DRAIN_PER_CYCLE
        for _ in range(5):
            survival.on_time_update(player, ms_per_point)

        assert player.stamina == 95


class TestThresholdWarnings:

    def test_warning_at_50_percent(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=51)
        player.max_stamina = 100

        ms_per_point = STAMINA_DRAIN_INTERVAL_MS // STAMINA_DRAIN_PER_CYCLE
        msgs = survival.on_time_update(player, ms_per_point)

        assert any("tired" in m.lower() for m in msgs)

    def test_warning_at_25_percent(self):
        survival = SurvivalSystem()
        survival._last_stamina_pct = 26
        player = _make_player(stamina=25)

        msgs = survival.on_time_update(player, 1)

        assert any("exhausted" in m.lower() for m in msgs)

    def test_warning_at_10_percent(self):
        survival = SurvivalSystem()
        survival._last_stamina_pct = 11
        player = _make_player(stamina=10)

        msgs = survival.on_time_update(player, 1)

        assert any("collapsing" in m.lower() for m in msgs)

    def test_hp_warning_at_50_percent(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=100)
        player.health = 50
        player.max_health = 100

        msgs = survival.on_time_update(player, 1)

        assert any("wounded" in m.lower() for m in msgs)

    def test_hp_warning_at_25_percent(self):
        survival = SurvivalSystem()
        survival._last_hp_pct = 0.26
        player = _make_player(stamina=100)
        player.health = 25
        player.max_health = 100

        msgs = survival.on_time_update(player, 1)

        assert any("critically" in m.lower() for m in msgs)

    def test_hp_warning_at_10_percent(self):
        survival = SurvivalSystem()
        survival._last_hp_pct = 0.11
        player = _make_player(stamina=100)
        player.health = 10
        player.max_health = 100

        msgs = survival.on_time_update(player, 1)

        assert any("near death" in m.lower() for m in msgs)


class TestSpellEffectiveness:

    def test_full_effectiveness_above_25(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=26)
        assert survival.get_spell_effectiveness(player) == 1.0

    def test_half_effectiveness_at_25(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=25)
        assert survival.get_spell_effectiveness(player) == 0.5

    def test_zero_effectiveness_at_10(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=10)
        assert survival.get_spell_effectiveness(player) == 0.0


class TestSpeedPenalty:

    def test_speed_drops_at_25_percent(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=25)
        player.max_speed = 2.0
        player.speed = 2.0

        survival.on_time_update(player, 1)

        assert player.speed == player.max_speed * SPEED_PENALTY_FACTOR

    def test_speed_recovers_above_25_percent(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=26)
        player.max_speed = 2.0
        player.speed = player.max_speed * SPEED_PENALTY_FACTOR

        survival.on_time_update(player, 1)

        assert player.speed == player.max_speed


class TestCanCast:

    def test_cannot_cast_at_10_percent(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=10)
        assert survival.can_cast(player) is False

    def test_cannot_cast_below_10_percent(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=5)
        assert survival.can_cast(player) is False

    def test_can_cast_above_10_percent(self):
        survival = SurvivalSystem()
        player = _make_player(stamina=11)
        assert survival.can_cast(player) is True
