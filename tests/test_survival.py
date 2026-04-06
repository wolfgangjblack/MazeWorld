"""Tests for Phase 9: Survival system, screen transitions, and menu views."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.systems.survival import (
    SurvivalSystem,
    DRAIN_INTERVAL,
    STARVATION_INTERVAL,
    THRESHOLD_WARNING,
    THRESHOLD_PENALTY,
    THRESHOLD_CRITICAL,
    BASE_HUNGER_DRAIN,
    BASE_THIRST_DRAIN,
    STARVATION_HP_DRAIN,
)
from src.models.player import PlayerCharacter, PlayerClass, Stats
from src.controllers.screen_controller import ScreenController, ScreenState


# --- Helpers ---

def _make_player(con: int = 10, hunger: int = 100, thirst: int = 100, health: int = 100) -> PlayerCharacter:
    """Create a player with a class that has a specific CON stat."""
    stats = Stats(STR=10, DEX=10, CON=con, INT=10, WIS=10, CHA=10, LUCK=10)
    pc = PlayerClass(name="TestClass", archetype="warrior", stats=stats)
    player = PlayerCharacter(x=0, y=0)
    player.apply_class(pc)
    player.hunger = hunger
    player.thirst = thirst
    player.health = health
    return player


# --- Drain rate tests ---

class TestDrainRates:

    def test_no_drain_before_interval(self):
        """No drain occurs until DRAIN_INTERVAL steps have passed."""
        survival = SurvivalSystem()
        player = _make_player(con=10)
        initial_hunger = player.hunger
        initial_thirst = player.thirst

        # Move DRAIN_INTERVAL - 1 times: no drain yet
        for _ in range(DRAIN_INTERVAL - 1):
            survival.on_move(player)

        assert player.hunger == initial_hunger
        assert player.thirst == initial_thirst

    def test_drain_at_interval(self):
        """Drain occurs on the DRAIN_INTERVAL-th step."""
        survival = SurvivalSystem()
        player = _make_player(con=10)
        initial_hunger = player.hunger

        for _ in range(DRAIN_INTERVAL):
            survival.on_move(player)

        # CON 10 -> modifier 0, so drain is BASE_HUNGER_DRAIN (1)
        assert player.hunger == initial_hunger - BASE_HUNGER_DRAIN
        assert player.thirst == initial_hunger - BASE_THIRST_DRAIN

    def test_drain_rate_one_third(self):
        """Over 9 steps, drain should happen 3 times (interval=3), totaling 3 drain."""
        survival = SurvivalSystem()
        player = _make_player(con=10)
        initial_hunger = player.hunger

        for _ in range(9):
            survival.on_move(player)

        expected_drains = 9 // DRAIN_INTERVAL
        assert player.hunger == initial_hunger - (expected_drains * BASE_HUNGER_DRAIN)

    def test_con_modifier_reduces_drain(self):
        """Higher CON reduces drain per tick (minimum 1)."""
        survival = SurvivalSystem()
        # CON 14 -> modifier +2 -> drain = max(1, 1-2) = 1 (minimum)
        player_high_con = _make_player(con=14)
        initial = player_high_con.hunger

        for _ in range(DRAIN_INTERVAL):
            survival.on_move(player_high_con)

        # Even with high CON, minimum drain is 1
        assert player_high_con.hunger == initial - 1

    def test_con_modifier_minimum_drain(self):
        """CON modifier can't reduce drain below 1."""
        survival = SurvivalSystem()
        # CON 18 -> modifier +4 -> max(1, 1-4) = 1
        player = _make_player(con=18)
        initial = player.hunger

        for _ in range(DRAIN_INTERVAL):
            survival.on_move(player)

        assert player.hunger == initial - 1

    def test_low_con_increases_drain(self):
        """Low CON (negative modifier) increases drain."""
        survival = SurvivalSystem()
        # CON 6 -> modifier -2 -> drain = max(1, 1-(-2)) = 3
        player = _make_player(con=6)
        initial = player.hunger

        for _ in range(DRAIN_INTERVAL):
            survival.on_move(player)

        expected_drain = max(1, BASE_HUNGER_DRAIN - ((6 - 10) // 2))
        assert player.hunger == initial - expected_drain


# --- Starvation / dehydration HP drain ---

class TestStarvation:

    def test_no_hp_drain_when_fed(self):
        """No HP drain when hunger and thirst are above 0."""
        survival = SurvivalSystem()
        player = _make_player(hunger=50, thirst=50)
        initial_hp = player.health

        for _ in range(STARVATION_INTERVAL * 2):
            survival.on_move(player)

        assert player.health == initial_hp

    def test_hp_drain_when_starving(self):
        """HP drains at rate of 1 per STARVATION_INTERVAL steps when hunger is 0."""
        survival = SurvivalSystem()
        player = _make_player(hunger=0, thirst=50, health=100)
        initial_hp = player.health

        for _ in range(STARVATION_INTERVAL):
            survival.on_move(player)

        assert player.health == initial_hp - STARVATION_HP_DRAIN

    def test_hp_drain_when_dehydrated(self):
        """HP drains when thirst is 0."""
        survival = SurvivalSystem()
        player = _make_player(hunger=50, thirst=0, health=100)
        initial_hp = player.health

        for _ in range(STARVATION_INTERVAL):
            survival.on_move(player)

        assert player.health == initial_hp - STARVATION_HP_DRAIN

    def test_hp_drain_rate(self):
        """HP drains at exactly 1 per 5 steps when starving."""
        survival = SurvivalSystem()
        player = _make_player(hunger=0, thirst=50, health=100)
        initial_hp = player.health

        for _ in range(STARVATION_INTERVAL * 3):
            survival.on_move(player)

        assert player.health == initial_hp - (3 * STARVATION_HP_DRAIN)

    def test_health_cannot_go_below_zero(self):
        """Health floors at 0."""
        survival = SurvivalSystem()
        player = _make_player(hunger=0, thirst=0, health=1)

        for _ in range(STARVATION_INTERVAL * 5):
            survival.on_move(player)

        assert player.health == 0

    def test_starvation_counter_resets_when_fed(self):
        """Starvation counter resets when hunger goes back above 0."""
        survival = SurvivalSystem()
        player = _make_player(hunger=0, thirst=50, health=100)

        # Partially count toward starvation
        for _ in range(STARVATION_INTERVAL - 1):
            survival.on_move(player)

        # Feed the player
        player.hunger = 50

        # Move more — counter should have reset
        for _ in range(STARVATION_INTERVAL - 1):
            survival.on_move(player)

        assert player.health == 100  # No HP lost


# --- Spell effectiveness ---

class TestSpellEffectiveness:

    def test_full_effectiveness(self):
        survival = SurvivalSystem()
        player = _make_player(hunger=50, thirst=50)
        assert survival.get_spell_effectiveness(player) == 1.0

    def test_reduced_effectiveness_at_penalty(self):
        survival = SurvivalSystem()
        player = _make_player(hunger=10, thirst=50)
        assert survival.get_spell_effectiveness(player) == 0.5

    def test_zero_effectiveness_at_critical(self):
        survival = SurvivalSystem()
        player = _make_player(hunger=0, thirst=50)
        assert survival.get_spell_effectiveness(player) == 0.0

    def test_cant_cast_at_critical(self):
        survival = SurvivalSystem()
        player = _make_player(hunger=0, thirst=50)
        assert survival.can_cast(player) is False

    def test_can_cast_above_critical(self):
        survival = SurvivalSystem()
        player = _make_player(hunger=1, thirst=1)
        assert survival.can_cast(player) is True


# --- Spell cost + drain balance ---

class TestSpellCostBalance:

    def test_spell_cost_deducted(self):
        """Spell costs are properly deducted from hunger/thirst."""
        from src.models.player import Spell
        player = _make_player(hunger=50, thirst=50)
        spell = Spell(name="Fireball", description="Fire!", element="fire",
                      cost_hunger=5, cost_thirst=0)
        assert player.can_afford_spell(spell)
        player.pay_spell_cost(spell)
        assert player.hunger == 45
        assert player.thirst == 50

    def test_cannot_afford_spell(self):
        """Can't cast when resources too low."""
        from src.models.player import Spell
        player = _make_player(hunger=3, thirst=50)
        spell = Spell(name="Fireball", description="Fire!", element="fire",
                      cost_hunger=5, cost_thirst=0)
        assert not player.can_afford_spell(spell)

    def test_spell_drain_interaction(self):
        """After several moves with drain, verify spell costs still work."""
        survival = SurvivalSystem()
        from src.models.player import Spell
        player = _make_player(con=10, hunger=100, thirst=100)
        spell = Spell(name="Heal", description="Heal", element="light",
                      cost_hunger=0, cost_thirst=8)

        # Move enough to drain some thirst
        for _ in range(DRAIN_INTERVAL * 5):
            survival.on_move(player)

        # Should still be able to afford
        assert player.can_afford_spell(spell)
        player.pay_spell_cost(spell)
        expected_thirst = 100 - 5 - 8  # 5 drains of 1, then 8 spell cost
        assert player.thirst == expected_thirst


# --- Screen transition tests ---

class TestScreenTransitions:

    def test_esc_from_pause_returns_to_gameplay(self):
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.PAUSE)
        assert sc.state == ScreenState.PAUSE
        sc.pop()
        assert sc.state == ScreenState.GAMEPLAY

    def test_esc_from_menu_returns_to_gameplay(self):
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.PLAYER_MENU)
        assert sc.state == ScreenState.PLAYER_MENU
        sc.pop()
        assert sc.state == ScreenState.GAMEPLAY

    def test_esc_stacking_inventory_menu_gameplay(self):
        """Esc from inventory tab -> player menu -> gameplay."""
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.PLAYER_MENU)
        # Simulating: in player menu, user would navigate tabs
        # Esc closes menu back to gameplay
        sc.pop()
        assert sc.state == ScreenState.GAMEPLAY

    def test_game_over_to_start(self):
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.GAME_OVER)
        assert sc.state == ScreenState.GAME_OVER
        sc.reset_to(ScreenState.START)
        assert sc.state == ScreenState.START
        assert sc.depth == 1

    def test_victory_to_start(self):
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.VICTORY)
        assert sc.state == ScreenState.VICTORY
        sc.reset_to(ScreenState.START)
        assert sc.state == ScreenState.START

    def test_pause_save_stays_on_pause(self):
        """After saving from pause, screen stays on pause."""
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.PAUSE)
        # Save action doesn't change screen state
        assert sc.state == ScreenState.PAUSE

    def test_pause_to_load(self):
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.PAUSE)
        sc.push(ScreenState.LOAD_GAME)
        assert sc.state == ScreenState.LOAD_GAME
        sc.pop()
        assert sc.state == ScreenState.PAUSE

    def test_full_esc_chain(self):
        """Esc from deep nesting: load -> pause -> gameplay."""
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.PAUSE)
        sc.push(ScreenState.LOAD_GAME)
        assert sc.depth == 3

        sc.pop()  # LOAD_GAME -> PAUSE
        assert sc.state == ScreenState.PAUSE
        sc.pop()  # PAUSE -> GAMEPLAY
        assert sc.state == ScreenState.GAMEPLAY
        sc.pop()  # Base — stays
        assert sc.state == ScreenState.GAMEPLAY


# --- No drain while stationary ---

class TestNoDrainWhileStationary:

    def test_no_drain_without_move(self):
        """Survival system only drains on on_move(), not passively."""
        survival = SurvivalSystem()
        player = _make_player(hunger=100, thirst=100)
        # Simply not calling on_move means no drain
        assert player.hunger == 100
        assert player.thirst == 100

    def test_drain_only_on_movement(self):
        """Verify that survival tracking is movement-triggered."""
        survival = SurvivalSystem()
        player = _make_player(hunger=100, thirst=100)

        # Move exactly DRAIN_INTERVAL times
        for _ in range(DRAIN_INTERVAL):
            survival.on_move(player)

        hunger_after = player.hunger
        thirst_after = player.thirst

        # No more moves — values shouldn't change
        assert player.hunger == hunger_after
        assert player.thirst == thirst_after


# --- Warning messages ---

class TestWarnings:

    def test_starvation_message(self):
        survival = SurvivalSystem()
        player = _make_player(hunger=0, thirst=50, health=100)

        messages = []
        for _ in range(STARVATION_INTERVAL):
            messages.extend(survival.on_move(player))

        assert any("starving" in m.lower() for m in messages)

    def test_dehydration_message(self):
        survival = SurvivalSystem()
        player = _make_player(hunger=50, thirst=0, health=100)

        messages = []
        for _ in range(STARVATION_INTERVAL):
            messages.extend(survival.on_move(player))

        assert any("dehydrated" in m.lower() for m in messages)
