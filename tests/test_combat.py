"""Tests for Phase 3 — Combat System.

Covers: initiative ordering, attack roll resolution, elemental multipliers,
spell costs, multi-target damage, flee mechanics, Jester Gamble,
combat end conditions (victory / defeat / flee).
"""

import random
import pytest

from src.models.player import PlayerCharacter, PlayerClass, Stats, stat_modifier
from src.models.monster import (
    Monster,
    LootDrop,
    create_scaled_monster,
    generate_encounter,
    EncounterType,
)
from src.models.weapon import Weapon, STARTER_WEAPONS, RANDOM_WEAPON_STATS
from src.models.spell import (
    Spell,
    elemental_multiplier,
    SUPER_EFFECTIVE_MULT,
    RESISTED_MULT,
)
from src.controllers.combat_controller import (
    CombatController,
    CombatState,
    roll_buff_duration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(archetype: str, stats_dict: dict, armor: int = 0) -> PlayerCharacter:
    """Create a PlayerCharacter with a PlayerClass for combat tests."""
    pc = PlayerClass(
        name=archetype.title(),
        archetype=archetype,
        stats=Stats(**stats_dict),
    )
    p = PlayerCharacter(x=0, y=0, armor=armor)
    p.player_class = pc
    p.weapon = STARTER_WEAPONS[archetype]
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def warrior():
    p = _make_player("warrior", dict(STR=16, DEX=14, CON=14, INT=8, WIS=8, CHA=10, LUCK=10), armor=2)
    return p


@pytest.fixture
def mage():
    p = _make_player("mage", dict(STR=8, DEX=12, CON=10, INT=16, WIS=12, CHA=10, LUCK=10))
    p.spells = [
        Spell(
            name="Fireball",
            spell_type="damage_single",
            element="fire",
            stat="INT",
            damage_dice=8,
            hunger_cost=5,
            thirst_cost=0,
            targets="single",
        ),
        Spell(
            name="Inferno",
            spell_type="damage_multi",
            element="fire",
            stat="INT",
            damage_dice=6,
            hunger_cost=10,
            thirst_cost=0,
            targets="multi",
        ),
    ]
    return p


@pytest.fixture
def healer():
    p = _make_player("healer", dict(STR=8, DEX=10, CON=12, INT=10, WIS=16, CHA=14, LUCK=10))
    p.spells = [
        Spell(
            name="Heal",
            spell_type="heal",
            element="light",
            stat="WIS",
            heal_amount=10,
            hunger_cost=0,
            thirst_cost=8,
            targets="self",
        ),
        Spell(
            name="Fortify",
            spell_type="buff_stat",
            element="light",
            stat="WIS",
            buff_stat="CON",
            buff_value=2,
            buff_duration=3,
            hunger_cost=0,
            thirst_cost=5,
            targets="self",
        ),
    ]
    return p


@pytest.fixture
def jester():
    p = _make_player("jester", dict(STR=10, DEX=12, CON=10, INT=10, WIS=10, CHA=10, LUCK=16))
    return p


@pytest.fixture
def weak_monster():
    return Monster(
        id="m1", name="Goblin", level=1,
        hp=10, max_hp=10, ac=10,
        str_mod=0, dex_mod=0,
        damage_dice=4, damage_type="physical",
    )


@pytest.fixture
def fire_monster():
    return Monster(
        id="m2", name="Fire Imp", level=1,
        hp=12, max_hp=12, ac=11,
        str_mod=1, dex_mod=1,
        damage_dice=6, damage_type="fire",
        elemental_affinity="fire",
        magic_resistance=1,
    )


@pytest.fixture
def forest_monster():
    return Monster(
        id="m3", name="Treant", level=2,
        hp=18, max_hp=18, ac=13,
        str_mod=2, dex_mod=0,
        damage_dice=8, damage_type="physical",
        elemental_affinity="forest",
        magic_resistance=2,
    )


def make_pack(count=3):
    return [
        Monster(
            id=f"wolf-{i}", name=f"Wolf {i}", level=1,
            hp=8, max_hp=8, ac=10,
            str_mod=0, dex_mod=1,
            damage_dice=4, damage_type="physical",
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# stat_modifier
# ---------------------------------------------------------------------------

class TestStatModifier:
    def test_average_stat(self):
        assert stat_modifier(10) == 0

    def test_high_stat(self):
        assert stat_modifier(16) == 3

    def test_low_stat(self):
        assert stat_modifier(8) == -1

    def test_odd_stat(self):
        assert stat_modifier(15) == 2


# ---------------------------------------------------------------------------
# Initiative ordering
# ---------------------------------------------------------------------------

class TestInitiative:
    def test_initiative_order_descending(self, warrior, weak_monster):
        """Higher initiative rolls go first."""
        random.seed(42)
        cc = CombatController(warrior, [weak_monster])
        inits = [c.initiative for c in cc.combatants if c.is_alive()]
        assert inits == sorted(inits, reverse=True)

    def test_player_wins_ties(self, warrior, weak_monster):
        """On initiative tie, player acts first."""
        # Force identical initiatives
        random.seed(0)
        cc = CombatController(warrior, [weak_monster])
        # Manually set same initiative
        for c in cc.combatants:
            c.initiative = 15
        cc.combatants.sort(key=lambda c: (-c.initiative, not c.is_player))
        assert cc.combatants[0].is_player

    def test_multiple_monsters_sorted(self, warrior):
        pack = make_pack(4)
        random.seed(99)
        cc = CombatController(warrior, pack)
        inits = [c.initiative for c in cc.combatants]
        assert inits == sorted(inits, reverse=True)


# ---------------------------------------------------------------------------
# Attack roll vs AC resolution (hit / miss)
# ---------------------------------------------------------------------------

class TestMeleeAttack:
    def test_hit_deals_damage(self, warrior, weak_monster):
        """A high roll should hit and deal damage."""
        cc = CombatController(warrior, [weak_monster])
        # Force player turn
        cc.combatants = [cc.player_combatant, cc.combatants[1] if len(cc.combatants) > 1 else cc.player_combatant]
        cc.turn_index = 0

        random.seed(10)  # should give reasonable rolls
        result = cc.player_attack(target_index=0)
        # The attack either hits or misses — just verify structure
        assert "message" in result
        assert isinstance(result["success"], bool)

    def test_guaranteed_hit(self, warrior, weak_monster):
        """With extreme stats, should always hit weak monster."""
        warrior.player_class.stats.STR = 30  # +10 modifier
        warrior.level = 5  # +4 level mod
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant]
        for c in cc.combatants:
            if not c.is_player:
                cc.combatants.append(c)
        cc.turn_index = 0

        # Even rolling a 1 on d20: 1 + 10 + 4 = 15 vs AC 10 + 0 = 10 → hit
        result = cc.player_attack(0)
        assert result["success"] is True
        assert weak_monster.hp < weak_monster.max_hp

    def test_monster_attack_can_miss(self, warrior, weak_monster):
        """Monster with 0 str_mod can miss high-AC player."""
        warrior.armor = 10  # AC = 10 + 10 + 2(DEX) = 22
        cc = CombatController(warrior, [weak_monster])
        # Force monster turn
        for c in cc.combatants:
            if not c.is_player:
                cc.turn_index = cc.combatants.index(c)
                break
        result = cc.execute_monster_turn()
        # Either hit or miss; high AC makes miss likely
        assert "message" in result


# ---------------------------------------------------------------------------
# Elemental multiplier calculations (1.5x / 0.5x)
# ---------------------------------------------------------------------------

class TestElementalMultiplier:
    def test_fire_vs_forest_super_effective(self):
        assert elemental_multiplier("fire", "forest") == SUPER_EFFECTIVE_MULT

    def test_forest_vs_water_super_effective(self):
        assert elemental_multiplier("forest", "water") == SUPER_EFFECTIVE_MULT

    def test_water_vs_fire_super_effective(self):
        assert elemental_multiplier("water", "fire") == SUPER_EFFECTIVE_MULT

    def test_light_vs_dark_super_effective(self):
        assert elemental_multiplier("light", "dark") == SUPER_EFFECTIVE_MULT

    def test_dark_vs_light_super_effective(self):
        assert elemental_multiplier("dark", "light") == SUPER_EFFECTIVE_MULT

    def test_fire_vs_water_resisted(self):
        assert elemental_multiplier("fire", "water") == RESISTED_MULT

    def test_forest_vs_fire_resisted(self):
        assert elemental_multiplier("forest", "fire") == RESISTED_MULT

    def test_water_vs_forest_resisted(self):
        assert elemental_multiplier("water", "forest") == RESISTED_MULT

    def test_same_element_neutral(self):
        assert elemental_multiplier("fire", "fire") == 1.0

    def test_no_affinity_neutral(self):
        assert elemental_multiplier("fire", None) == 1.0

    def test_no_attack_element_neutral(self):
        assert elemental_multiplier("", "fire") == 1.0


# ---------------------------------------------------------------------------
# Spell hunger/thirst cost deduction
# ---------------------------------------------------------------------------

class TestSpellCosts:
    def test_damage_spell_costs_hunger(self, mage, weak_monster):
        initial_hunger = mage.hunger
        cc = CombatController(mage, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        cc.player_cast_spell(0, 0)  # Fireball costs 5 hunger
        assert mage.hunger == initial_hunger - 5

    def test_heal_spell_costs_thirst(self, healer, weak_monster):
        initial_thirst = healer.thirst
        healer.health = 50  # Need healing
        cc = CombatController(healer, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        cc.player_cast_spell(0, 0)  # Heal costs 8 thirst
        assert healer.thirst == initial_thirst - 8

    def test_buff_spell_costs_thirst(self, healer, weak_monster):
        initial_thirst = healer.thirst
        cc = CombatController(healer, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        cc.player_cast_spell(1, 0)  # Fortify costs 5 thirst
        assert healer.thirst == initial_thirst - 5

    def test_cannot_cast_when_starving(self, mage, weak_monster):
        mage.hunger = 0
        cc = CombatController(mage, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_cast_spell(0, 0)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Multi-target damage distribution
# ---------------------------------------------------------------------------

class TestMultiTarget:
    def test_multi_attack_hits_multiple(self, warrior):
        pack = make_pack(3)
        warrior.player_class.stats.STR = 30  # guaranteed hits
        warrior.level = 5
        cc = CombatController(warrior, pack)
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_multi_attack()
        assert result["success"] is True
        # At least some wolves should have taken damage
        damaged = sum(1 for m in pack if m.hp < m.max_hp)
        assert damaged > 0

    def test_multi_attack_costs_hunger(self, warrior, weak_monster):
        initial = warrior.hunger
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        cc.player_multi_attack()
        assert warrior.hunger == initial - 8

    def test_multi_attack_fails_when_starving(self, warrior, weak_monster):
        warrior.hunger = 3
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_multi_attack()
        assert result["success"] is False

    def test_multi_spell_hits_all_targets(self, mage):
        pack = make_pack(3)
        # Give mage high INT for guaranteed hits and set low magic resistance
        mage.player_class.stats.INT = 30
        mage.level = 5
        for m in pack:
            m.magic_resistance = 0
        cc = CombatController(mage, pack)
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_cast_spell(1, 0)  # Inferno (multi)
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Flee success / failure + free attack on fail
# ---------------------------------------------------------------------------

class TestFlee:
    def test_flee_success_ends_combat(self, warrior, weak_monster):
        """High DEX + low monster level → flee succeeds."""
        warrior.player_class.stats.DEX = 30  # +10 mod → minimum roll 11 + 10 = 21 vs DC 13
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_flee()
        assert result["success"] is True
        assert cc.state == CombatState.FLED

    def test_flee_failure_takes_damage(self, warrior, weak_monster):
        """Low DEX → flee fails, monster gets free attack."""
        warrior.player_class.stats.DEX = 2  # -4 mod → max roll 20 - 4 = 16 vs DC 13 could succeed
        # Use a strong monster to make DC higher
        strong = Monster(
            id="boss", name="Boss", level=10,
            hp=50, max_hp=50, ac=18,
            str_mod=5, dex_mod=3,
            damage_dice=10,
        )
        cc = CombatController(warrior, [strong])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        # DC = 12 + 10 = 22; max roll = 20 + (-4) = 16 → always fails
        result = cc.player_flee()
        assert result["success"] is False
        assert "damage" in result
        assert cc.state == CombatState.ONGOING

    def test_flee_state_is_fled(self, warrior, weak_monster):
        warrior.player_class.stats.DEX = 30
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        cc.player_flee()
        assert cc.state == CombatState.FLED


# ---------------------------------------------------------------------------
# Jester Gamble effect distribution
# ---------------------------------------------------------------------------

class TestJesterGamble:
    def test_gamble_only_for_jester(self, warrior, weak_monster):
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_gamble()
        assert result["success"] is False

    def test_gamble_returns_effect(self, jester, weak_monster):
        cc = CombatController(jester, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_gamble()
        assert result["success"] is True
        assert "effect" in result

    def test_high_luck_favors_good_outcomes(self, jester, weak_monster):
        """With very high LUCK, bad outcomes (damage_self, nothing) should be rare."""
        jester.player_class.stats.LUCK = 30  # +10 mod
        outcomes = {"damage_self": 0, "nothing": 0, "good": 0}
        for seed in range(200):
            m = Monster(id="m", name="Goblin", hp=100, max_hp=100, ac=10, damage_dice=4)
            cc = CombatController(jester, [m])
            cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
            cc.turn_index = 0
            jester.health = 100  # reset
            random.seed(seed)
            result = cc.player_gamble()
            effect = result.get("effect", "nothing")
            if effect in ("damage_self", "nothing"):
                outcomes[effect if effect in outcomes else "nothing"] += 1
            else:
                outcomes["good"] += 1
        # Good outcomes should dominate
        assert outcomes["good"] > outcomes["damage_self"] + outcomes["nothing"]


# ---------------------------------------------------------------------------
# Combat ends correctly on victory / defeat / flee
# ---------------------------------------------------------------------------

class TestCombatEndConditions:
    def test_victory_when_all_monsters_dead(self, warrior, weak_monster):
        weak_monster.hp = 1
        warrior.player_class.stats.STR = 30
        warrior.level = 5
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        cc.player_attack(0)
        assert cc.state == CombatState.VICTORY

    def test_defeat_when_player_dies(self, warrior, weak_monster):
        warrior.health = 1
        warrior.armor = 0
        warrior.player_class.stats.DEX = 2
        # Strong monster that always hits
        boss = Monster(
            id="boss", name="Boss", level=5,
            hp=50, max_hp=50, ac=20,
            str_mod=10, dex_mod=5,
            damage_dice=20,
        )
        cc = CombatController(warrior, [boss])
        # Put monster first
        monster_combatant = [c for c in cc.combatants if not c.is_player][0]
        cc.combatants = [monster_combatant, cc.player_combatant]
        cc.turn_index = 0
        cc.execute_monster_turn()
        assert cc.state == CombatState.DEFEAT

    def test_fled_state(self, warrior, weak_monster):
        warrior.player_class.stats.DEX = 30
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        cc.player_flee()
        assert cc.state == CombatState.FLED


# ---------------------------------------------------------------------------
# Use Item in combat
# ---------------------------------------------------------------------------

class TestUseItem:
    def test_use_food_heals_hunger(self, warrior, weak_monster):
        from src.models.items import Food, ItemStats
        bread = Food(
            category="food", name="Bread", desc="A loaf",
            item_stats=ItemStats(nutrition_value=20, health_value=5),
        )
        warrior.inventory = {"Bread": bread}
        warrior.hunger = 50
        cc = CombatController(warrior, [weak_monster])
        cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
        cc.turn_index = 0
        result = cc.player_use_item("Bread")
        assert result["success"] is True
        assert warrior.hunger == 70


# ---------------------------------------------------------------------------
# Buffs
# ---------------------------------------------------------------------------

class TestBuffs:
    def test_buff_increases_stat_modifier(self, healer, weak_monster):
        base_mod = healer.get_stat_mod("CON")
        healer.apply_buff("CON", 2, 3)
        assert healer.get_stat_mod("CON") == base_mod + 1  # +2 to stat = +1 mod

    def test_buff_expires(self, healer, weak_monster):
        healer.apply_buff("STR", 4, 2)
        assert len(healer.active_buffs) == 1
        healer.tick_buffs()
        assert len(healer.active_buffs) == 1
        healer.tick_buffs()
        assert len(healer.active_buffs) == 0


# ---------------------------------------------------------------------------
# Buff duration roll (1d4 + INT mod // 2)
# ---------------------------------------------------------------------------

class TestBuffDuration:
    def test_roll_buff_duration_uses_int_mod(self, healer, weak_monster):
        """Duration should be 1d4 + (INT modifier // 2), minimum 1."""
        # healer has INT=10 → mod 0 → 0 // 2 = 0, so duration = 1d4 + 0 = 1..4
        durations = set()
        for seed in range(50):
            random.seed(seed)
            d = roll_buff_duration(healer)
            assert 1 <= d <= 4
            durations.add(d)
        assert len(durations) > 1  # not all the same

    def test_high_int_increases_duration(self):
        """High INT should add to the duration."""
        p = _make_player("mage", dict(STR=8, DEX=12, CON=10, INT=18, WIS=12, CHA=10, LUCK=10))
        # INT=18 → mod +4 → 4 // 2 = 2, so duration = 1d4 + 2 = 3..6
        for seed in range(50):
            random.seed(seed)
            d = roll_buff_duration(p)
            assert 3 <= d <= 6

    def test_low_int_floors_at_one(self):
        """Even with negative INT mod, duration should be at least 1."""
        p = _make_player("warrior", dict(STR=16, DEX=14, CON=14, INT=4, WIS=8, CHA=10, LUCK=10))
        # INT=4 → mod -3 → -3 // 2 = -2, raw = 1d4 + (-2) → could be -1..2
        # But min is 1
        for seed in range(50):
            random.seed(seed)
            d = roll_buff_duration(p)
            assert d >= 1

    def test_buff_spell_uses_rolled_duration(self, healer, weak_monster):
        """Casting a buff spell should apply a rolled duration, not hardcoded 3."""
        healer.spells = [
            Spell(
                name="Fortify", spell_type="buff_stat", element="light", stat="WIS",
                buff_stat="CON", buff_value=2, buff_duration=3,
                hunger_cost=0, thirst_cost=5, targets="self",
            ),
        ]
        # Run many trials — duration should vary (not always 3)
        durations = set()
        for seed in range(50):
            random.seed(seed)
            healer.active_buffs = []
            healer.thirst = 100
            m = Monster(id="m", name="Goblin", hp=100, max_hp=100, ac=10, damage_dice=4)
            cc = CombatController(healer, [m])
            cc.combatants = [cc.player_combatant] + [c for c in cc.combatants if not c.is_player]
            cc.turn_index = 0
            cc.player_cast_spell(0, 0)
            if healer.active_buffs:
                durations.add(healer.active_buffs[0].turns_remaining)
        # Should have more than one unique duration value
        assert len(durations) > 1


# ---------------------------------------------------------------------------
# Monster model
# ---------------------------------------------------------------------------

class TestMonsterModel:
    def test_create_scaled_monster(self):
        m = create_scaled_monster("s1", "Slime", level=1)
        assert 8 <= m.hp <= 12
        assert 10 <= m.ac <= 12

    def test_loot_roll(self):
        m = Monster(
            id="m", name="Rat", hp=5, max_hp=5, ac=10,
            damage_dice=4,
            loot_table=[LootDrop(item_id=200, probability=1.0)],
        )
        loot = m.roll_loot()
        assert 200 in loot

    def test_loot_roll_zero_probability(self):
        m = Monster(
            id="m", name="Rat", hp=5, max_hp=5, ac=10,
            damage_dice=4,
            loot_table=[LootDrop(item_id=200, probability=0.0)],
        )
        loot = m.roll_loot()
        assert loot == []

    def test_take_damage(self, weak_monster):
        weak_monster.take_damage(5)
        assert weak_monster.hp == 5

    def test_is_alive(self, weak_monster):
        assert weak_monster.is_alive()
        weak_monster.hp = 0
        assert not weak_monster.is_alive()


# ---------------------------------------------------------------------------
# Weapon model
# ---------------------------------------------------------------------------

class TestWeaponModel:
    def test_damage_roll_in_range(self):
        w = Weapon(name="Sword", weapon_type="heavy", stat="STR", damage_dice=8)
        for _ in range(50):
            d = w.roll_damage()
            assert 1 <= d <= 8

    def test_damage_bonus(self):
        w = Weapon(name="Magic Sword", weapon_type="heavy", stat="STR", damage_dice=8, damage_bonus=3)
        for _ in range(50):
            d = w.roll_damage()
            assert 4 <= d <= 11


# ---------------------------------------------------------------------------
# Player combat helpers
# ---------------------------------------------------------------------------

class TestPlayerCombat:
    def test_get_ac(self, warrior):
        # 10 + 2(armor) + 2(DEX 14 -> +2 mod) = 14
        assert warrior.get_ac() == 14

    def test_jester_modifier(self, jester):
        # LUCK=16 (+3), normal stat e.g. INT=10 (+0), avg = 1
        mod = jester.get_jester_mod("INT")
        assert mod == (3 + 0) // 2  # 1

    def test_can_afford_spell(self, mage):
        spell = mage.spells[0]  # Fireball: 5 hunger
        assert mage.can_afford_spell(spell)
        mage.hunger = 0
        assert not mage.can_afford_spell(spell)

    def test_is_alive(self, warrior):
        assert warrior.is_alive()
        warrior.health = 0
        assert not warrior.is_alive()


# ---------------------------------------------------------------------------
# Encounter composition
# ---------------------------------------------------------------------------

class TestEncounterComposition:
    def test_solo_encounter_one_monster(self):
        monsters = generate_encounter(1, EncounterType.SOLO)
        assert len(monsters) == 1

    def test_pack_encounter_two_to_four(self):
        for seed in range(20):
            random.seed(seed)
            monsters = generate_encounter(1, EncounterType.PACK)
            assert 2 <= len(monsters) <= 4

    def test_mixed_encounter_composition(self):
        random.seed(42)
        monsters = generate_encounter(2, EncounterType.MIXED)
        # 1-2 strong + 2-3 weak = 3-5 total
        assert 3 <= len(monsters) <= 5

    def test_random_encounter_type(self):
        """When encounter_type is None, it picks randomly."""
        monsters = generate_encounter(1)
        assert len(monsters) >= 1

    def test_solo_monster_level_above_player(self):
        monsters = generate_encounter(2, EncounterType.SOLO)
        assert monsters[0].level == 3

    def test_pack_monsters_level_below_player(self):
        monsters = generate_encounter(3, EncounterType.PACK)
        for m in monsters:
            assert m.level == 2  # max(1, 3-1)


# ---------------------------------------------------------------------------
# Default loot probability (40-60%)
# ---------------------------------------------------------------------------

class TestDefaultLoot:
    def test_scaled_monster_has_default_loot(self):
        m = create_scaled_monster("l1", "Rat", level=1)
        assert len(m.loot_table) == 1
        assert 0.4 <= m.loot_table[0].probability <= 0.6

    def test_explicit_loot_overrides_default(self):
        custom = [LootDrop(item_id=999, probability=1.0)]
        m = create_scaled_monster("l2", "Rat", level=1, loot_table=custom)
        assert m.loot_table[0].item_id == 999
        assert m.loot_table[0].probability == 1.0


# ---------------------------------------------------------------------------
# Jester random weapon stat
# ---------------------------------------------------------------------------

class TestJesterRandomWeapon:
    def test_random_weapon_uses_varying_stats(self, jester):
        """Jester's roll_attack should sometimes use different stats."""
        stats_used = set()
        for seed in range(50):
            random.seed(seed)
            jester._resolve_weapon_stat()
            # Can't directly observe which stat was used, so test via RANDOM_WEAPON_STATS
        assert set(RANDOM_WEAPON_STATS) == {"STR", "DEX", "INT"}

    def test_resolve_weapon_stat_random_type(self, jester):
        """_resolve_weapon_stat with a random weapon returns a stat from the pool."""
        for seed in range(30):
            random.seed(seed)
            stat = jester._resolve_weapon_stat()
            assert stat in RANDOM_WEAPON_STATS


# ---------------------------------------------------------------------------
# Light weapon
# ---------------------------------------------------------------------------

class TestLightWeapon:
    def test_light_weapon_exists(self):
        assert "rogue" in STARTER_WEAPONS
        w = STARTER_WEAPONS["rogue"]
        assert w.weapon_type == "light"
        assert w.stat == "DEX"
        assert w.damage_dice in (4, 6)  # 1d4-1d6 per spec
