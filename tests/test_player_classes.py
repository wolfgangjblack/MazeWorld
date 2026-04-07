"""Tests for Phase 2: Player Classes & Stats."""

import pytest
from src.models.player import (
    Stats, Ability, PlayerClass, PlayerCharacter,
    STAT_BUDGET,
)
from src.generate.class_gen import (
    _fix_stats, _check_classes, _validate_classes,
    _fallback_class,
)


# ---------------------------------------------------------------------------
# Stats tests
# ---------------------------------------------------------------------------

class TestStats:
    def test_modifier_positive(self):
        s = Stats(STR=16)
        assert s.modifier("STR") == 3

    def test_modifier_negative(self):
        s = Stats(INT=6)
        assert s.modifier("INT") == -2

    def test_modifier_zero(self):
        s = Stats(DEX=10)
        assert s.modifier("DEX") == 0

    def test_modifier_eleven(self):
        s = Stats(WIS=11)
        assert s.modifier("WIS") == 0

    def test_validate_guardrails_warrior_valid(self):
        # Total = 16+12+14+8+6+12+4 = 72, but LUCK=4 is not in warrior role ranges
        s = Stats(STR=16, DEX=12, CON=14, INT=8, WIS=6, CHA=12, LUCK=4)
        errors = s.validate_guardrails("warrior")
        # LUCK isn't in warrior's stat roles, so guardrails don't check it
        # All other stats are in valid ranges, total=72
        assert len(errors) == 0

    def test_validate_guardrails_warrior_stats_in_range(self):
        s = Stats(STR=16, DEX=12, CON=14, INT=8, WIS=6, CHA=12, LUCK=4)
        errors = s.validate_guardrails("warrior")
        range_errors = [e for e in errors if "total" not in e]
        assert len(range_errors) == 0

    def test_validate_guardrails_mage_out_of_range(self):
        s = Stats(STR=16, DEX=12, CON=14, INT=8, WIS=6, CHA=12, LUCK=8)
        errors = s.validate_guardrails("mage")
        # INT=8 should be primary (14-18), STR=16 should be dump (6-10)
        assert any("INT" in e for e in errors)


# ---------------------------------------------------------------------------
# Stat fixer tests
# ---------------------------------------------------------------------------

class TestFixStats:
    def test_fix_stats_warrior_hits_budget(self):
        raw = {"STR": 16, "DEX": 12, "CON": 14, "INT": 8, "WIS": 7, "CHA": 12, "LUCK": 8}
        stats = _fix_stats(raw, "warrior")
        assert stats.total() == STAT_BUDGET

    def test_fix_stats_mage_hits_budget(self):
        raw = {"STR": 7, "DEX": 12, "CON": 8, "INT": 16, "WIS": 13, "CHA": 7, "LUCK": 8}
        stats = _fix_stats(raw, "mage")
        assert stats.total() == STAT_BUDGET

    def test_fix_stats_healer_hits_budget(self):
        raw = {"STR": 7, "DEX": 8, "CON": 12, "INT": 7, "WIS": 16, "CHA": 13, "LUCK": 8}
        stats = _fix_stats(raw, "healer")
        assert stats.total() == STAT_BUDGET

    def test_fix_stats_jester_hits_budget(self):
        raw = {"STR": 12, "DEX": 12, "CON": 12, "INT": 12, "WIS": 12, "CHA": 8, "LUCK": 16}
        stats = _fix_stats(raw, "jester")
        assert stats.total() == STAT_BUDGET

    def test_fix_stats_clamps_primary_range(self):
        raw = {"STR": 20, "DEX": 12, "CON": 20, "INT": 8, "WIS": 7, "CHA": 12, "LUCK": 8}
        stats = _fix_stats(raw, "warrior")
        assert 14 <= stats.STR <= 18
        assert 14 <= stats.CON <= 18

    def test_fix_stats_clamps_dump_range(self):
        raw = {"STR": 16, "DEX": 12, "CON": 14, "INT": 3, "WIS": 2, "CHA": 12, "LUCK": 8}
        stats = _fix_stats(raw, "warrior")
        assert 6 <= stats.INT <= 10
        assert 6 <= stats.WIS <= 10

    def test_fix_stats_empty_input(self):
        stats = _fix_stats({}, "warrior")
        assert stats.total() == STAT_BUDGET

    def test_fix_stats_all_archetypes_produce_valid_budget(self):
        for arch in ["warrior", "mage", "healer", "jester"]:
            stats = _fix_stats({}, arch)
            assert stats.total() == STAT_BUDGET, f"{arch} total={stats.total()}"


# ---------------------------------------------------------------------------
# Fallback class generation tests
# ---------------------------------------------------------------------------

class TestFallbackClass:
    @pytest.mark.parametrize("archetype", ["warrior", "mage", "healer", "jester"])
    def test_fallback_has_correct_archetype(self, archetype):
        fb = _fallback_class(archetype, "forest", "Shadowleaf")
        assert fb["archetype"] == archetype

    @pytest.mark.parametrize("archetype", ["warrior", "mage", "healer", "jester"])
    def test_fallback_stats_hit_budget(self, archetype):
        fb = _fallback_class(archetype, "forest", "Shadowleaf")
        total = sum(fb["stats"].values())
        assert total == STAT_BUDGET, f"{archetype} fallback total={total}"


# ---------------------------------------------------------------------------
# Check classes tests (fills missing archetypes)
# ---------------------------------------------------------------------------

class TestCheckClasses:
    def test_check_fills_missing(self):
        partial = [{"archetype": "warrior", "name": "W"}]
        result = _check_classes(partial, "forest", "Shadowleaf")
        archetypes = [c["archetype"] for c in result]
        assert archetypes == ["warrior", "mage", "healer", "jester"]

    def test_check_preserves_existing(self):
        full = [
            {"archetype": "warrior", "name": "W"},
            {"archetype": "mage", "name": "M"},
            {"archetype": "healer", "name": "H"},
            {"archetype": "jester", "name": "J"},
        ]
        result = _check_classes(full, "forest", "Shadowleaf")
        names = [c["name"] for c in result]
        assert names == ["W", "M", "H", "J"]


# ---------------------------------------------------------------------------
# Validate classes tests (convert to PlayerClass)
# ---------------------------------------------------------------------------

class TestValidateClasses:
    def test_validate_produces_player_class_objects(self):
        raw = [_fallback_class(a, "forest", "Shadowleaf")
               for a in ["warrior", "mage", "healer", "jester"]]
        result = _validate_classes(raw, "forest", "Shadowleaf")
        assert len(result) == 4
        for pc in result:
            assert isinstance(pc, PlayerClass)

    def test_validate_warrior_has_abilities(self):
        raw = [_fallback_class(a, "forest", "Shadowleaf")
               for a in ["warrior", "mage", "healer", "jester"]]
        result = _validate_classes(raw, "forest", "Shadowleaf")
        warrior = result[0]
        assert warrior.archetype == "warrior"
        assert len(warrior.abilities) >= 4

    def test_validate_mage_has_spells(self):
        raw = [_fallback_class(a, "forest", "Shadowleaf")
               for a in ["warrior", "mage", "healer", "jester"]]
        result = _validate_classes(raw, "forest", "Shadowleaf")
        mage = result[1]
        assert mage.archetype == "mage"
        assert len(mage.spells) >= 4

    def test_validate_healer_has_spells(self):
        raw = [_fallback_class(a, "forest", "Shadowleaf")
               for a in ["warrior", "mage", "healer", "jester"]]
        result = _validate_classes(raw, "forest", "Shadowleaf")
        healer = result[2]
        assert healer.archetype == "healer"
        assert len(healer.spells) >= 4

    def test_validate_all_stats_on_budget(self):
        raw = [_fallback_class(a, "forest", "Shadowleaf")
               for a in ["warrior", "mage", "healer", "jester"]]
        result = _validate_classes(raw, "forest", "Shadowleaf")
        for pc in result:
            assert pc.stats.total() == STAT_BUDGET, f"{pc.archetype} total={pc.stats.total()}"


# ---------------------------------------------------------------------------
# PlayerCharacter class integration tests
# ---------------------------------------------------------------------------

class TestPlayerCharacterClassIntegration:
    def _make_class(self, archetype="warrior"):
        return PlayerClass(
            name="Test Warrior",
            archetype=archetype,
            flavor_text="A test class",
            environment="forest",
            stats=Stats(STR=16, DEX=12, CON=14, INT=8, WIS=7, CHA=11, LUCK=4),
            starting_weapon="sword",
            abilities=[
                Ability(name="Bash", description="Hit hard", stat="STR"),
                Ability(name="Rally", description="Inspire", stat="CHA"),
            ],
            spells=[],
            ability_pool=[
                Ability(name="Cleave", description="Hit two", stat="STR"),
                Ability(name="Taunt", description="Draw attention", stat="CHA"),
            ],
            spell_pool=[],
        )

    def test_apply_class(self):
        pc = PlayerCharacter(x=0, y=0)
        cls = self._make_class()
        pc.apply_class(cls)
        assert pc.player_class is not None
        assert pc.equipped_weapon == "sword"
        assert len(pc.abilities) == 2
        assert pc.abilities[0].name == "Bash"

    def test_apply_class_sets_hp_from_con(self):
        pc = PlayerCharacter(x=0, y=0)
        cls = self._make_class()
        pc.apply_class(cls)
        # CON=14, modifier=2, max_health = 100 + 10*2 = 120
        assert pc.max_health == 120
        assert pc.health == 120

    def test_get_stat_modifier(self):
        pc = PlayerCharacter(x=0, y=0)
        cls = self._make_class()
        pc.apply_class(cls)
        assert pc.get_stat_modifier("STR") == 3  # (16-10)//2
        assert pc.get_stat_modifier("INT") == -1  # (8-10)//2

    def test_level_up_choices(self):
        pc = PlayerCharacter(x=0, y=0)
        cls = self._make_class()
        pc.apply_class(cls)
        choices = pc.level_up_choices()
        # Should have Cleave and Taunt from ability_pool
        assert len(choices) == 2
        assert choices[0][0] == "ability"

    def test_apply_level_up(self):
        pc = PlayerCharacter(x=0, y=0)
        cls = self._make_class()
        pc.apply_class(cls)
        choices = pc.level_up_choices()
        pc.apply_level_up(choices[0][0], choices[0][1])
        assert pc.level == 2
        assert len(pc.abilities) == 3

    def test_level_up_no_duplicates(self):
        pc = PlayerCharacter(x=0, y=0)
        cls = self._make_class()
        pc.apply_class(cls)
        choices = pc.level_up_choices()
        pc.apply_level_up(choices[0][0], choices[0][1])
        # After learning Cleave, only Taunt should remain
        remaining = pc.level_up_choices()
        assert len(remaining) == 1
        assert remaining[0][1].name == "Taunt"


# ---------------------------------------------------------------------------
# Screen state transition tests
# ---------------------------------------------------------------------------

class TestScreenTransitions:
    def test_class_select_state_exists(self):
        from src.controllers.screen_controller import ScreenController, ScreenState
        sc = ScreenController(ScreenState.START)
        sc.replace(ScreenState.CLASS_SELECT)
        assert sc.state == ScreenState.CLASS_SELECT

    def test_room_intro_state_exists(self):
        from src.controllers.screen_controller import ScreenController, ScreenState
        sc = ScreenController(ScreenState.START)
        sc.replace(ScreenState.CLASS_SELECT)
        sc.replace(ScreenState.ROOM_INTRO)
        assert sc.state == ScreenState.ROOM_INTRO

    def test_level_up_state_exists(self):
        from src.controllers.screen_controller import ScreenController, ScreenState
        sc = ScreenController(ScreenState.GAMEPLAY)
        sc.push(ScreenState.LEVEL_UP)
        assert sc.state == ScreenState.LEVEL_UP
        sc.pop()
        assert sc.state == ScreenState.GAMEPLAY

    def test_full_flow_transitions(self):
        from src.controllers.screen_controller import ScreenController, ScreenState
        sc = ScreenController(ScreenState.START)
        sc.replace(ScreenState.CLASS_SELECT)
        sc.replace(ScreenState.ROOM_INTRO)
        sc.replace(ScreenState.GAMEPLAY)
        assert sc.state == ScreenState.GAMEPLAY
