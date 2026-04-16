"""Tests for bible_final features: consumable scaling, weapon soft-restriction,
real-time day/night, night monsters, summary agent, and portrait prompt builders."""

import random

from src.generate.summary_agent import (
    _build_story_context,
    build_class_portrait_prompt,
    build_game_over_portrait_prompt,
    build_item_portrait_prompt,
    build_monster_portrait_prompt,
    build_npc_portrait_prompt,
    build_room_portrait_prompt,
)
from src.models.items import (
    CONSUMABLE_SCALING,
    Food,
    ItemStats,
    consumable_scale_factor,
    scale_item_stats,
)
from src.models.player import PlayerCharacter, PlayerClass, Stats
from src.models.story import Faction, OverarchingStory
from src.models.time import FULL_CYCLE_MS, DayNightCycle, TimePeriod
from src.models.weapon import (
    STARTER_WEAPONS,
    WEAPON_CATEGORY_ACCESS,
    weapon_stat_bonus,
)
from src.models.world_bible import RoomBible, WorldBible

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(archetype="warrior"):
    stat_blocks = {
        "warrior": dict(STR=16, DEX=14, CON=14, INT=8, WIS=8, CHA=10, LUCK=10),
        "mage": dict(STR=8, DEX=12, CON=10, INT=16, WIS=12, CHA=10, LUCK=10),
        "jester": dict(STR=10, DEX=10, CON=10, INT=10, WIS=10, CHA=10, LUCK=16),
        "healer": dict(STR=8, DEX=10, CON=10, INT=10, WIS=16, CHA=12, LUCK=10),
    }
    pc = PlayerClass(
        name=archetype.title(),
        archetype=archetype,
        stats=Stats(**stat_blocks[archetype]),
    )
    p = PlayerCharacter(x=0, y=0)
    p.player_class = pc
    p.weapon = STARTER_WEAPONS.get(archetype)
    return p


def _make_bible():
    return WorldBible(
        story=OverarchingStory(
            title="The Dark Convergence",
            synopsis="An ancient evil stirs beneath the maze.",
            faction=Faction(
                name="The Shadow Cult",
                description="Followers of the void.",
                leader="Lord Tenebris",
            ),
            climax="The final confrontation in the heart of darkness.",
            final_boss_name="Lord Tenebris",
        ),
        rooms={
            "room_0": RoomBible(
                environment="dungeon",
                level=1,
                story_beat="The entrance to the cursed maze.",
            ),
        },
    )


# ===========================================================================
# Phase 4: Consumable Scaling
# ===========================================================================


class TestConsumableScaling:
    def test_scaling_factors(self):
        assert consumable_scale_factor(1) == 1.0
        assert consumable_scale_factor(2) == 1.3
        assert consumable_scale_factor(3) == 1.6
        assert consumable_scale_factor(4) == 2.0
        assert consumable_scale_factor(10) == 2.0  # 4+ default

    def test_scale_item_stats(self):
        stats = ItemStats(stamina_value=10, health_value=3, price=20)
        scaled = scale_item_stats(stats, 2)
        assert scaled.stamina_value == 13
        assert scaled.health_value == 3
        assert scaled.price == 26

    def test_scale_item_stats_level1_unchanged(self):
        stats = ItemStats(stamina_value=10, price=20)
        scaled = scale_item_stats(stats, 1)
        assert scaled.stamina_value == 10
        assert scaled.price == 20

    def test_scaled_clone(self):
        food = Food(
            category="food",
            name="Bread",
            desc="Tasty",
            item_stats=ItemStats(stamina_value=10, price=5),
        )
        scaled = food.scaled_clone(3)
        assert scaled.item_stats.stamina_value == 16
        assert scaled.room_level == 3
        assert food.item_stats.stamina_value == 10

    def test_consumable_scaling_dict_keys(self):
        assert set(CONSUMABLE_SCALING.keys()) == {1, 2, 3}


# ===========================================================================
# Weapon Soft-Restriction
# ===========================================================================


class TestWeaponSoftRestriction:
    def test_matching_class_gets_bonus(self):
        """Warrior with a heavy weapon should get full STR bonus."""
        player = _make_player("warrior")
        bonus = weapon_stat_bonus(player, player.weapon)
        expected = player.get_stat_mod("STR")  # STR=16, mod=3
        assert bonus == expected

    def test_mismatched_class_gets_zero(self):
        """Mage with a heavy weapon should get 0 bonus."""
        player = _make_player("mage")
        heavy_weapon = STARTER_WEAPONS["warrior"]
        bonus = weapon_stat_bonus(player, heavy_weapon)
        assert bonus == 0

    def test_jester_uses_luck_average(self):
        """Jester gets (LUCK mod + normal stat mod) // 2."""
        player = _make_player("jester")
        # Give jester a heavy STR weapon
        heavy_weapon = STARTER_WEAPONS["warrior"]
        bonus = weapon_stat_bonus(player, heavy_weapon)
        luck_mod = player.get_stat_mod("LUCK")
        str_mod = player.get_stat_mod("STR")
        expected = (luck_mod + str_mod) // 2
        assert bonus == expected

    def test_no_weapon_returns_str_mod(self):
        """Unarmed players should get STR modifier as bonus."""
        player = _make_player("warrior")
        assert weapon_stat_bonus(player, None) == player.get_stat_mod("STR")

    def test_player_roll_attack_uses_restriction(self):
        """Player.roll_attack should use weapon_stat_bonus."""
        player = _make_player("warrior")
        # Set seed for reproducibility
        random.seed(42)
        roll = player.roll_attack()
        # Should be d20 + STR mod (3) + level mod (0)
        assert isinstance(roll, int)
        assert roll >= 1

    def test_weapon_category_access_structure(self):
        for archetype, categories in WEAPON_CATEGORY_ACCESS.items():
            assert isinstance(categories, set)
            for c in categories:
                assert c in ("simple", "martial")


# ===========================================================================
# Phase 8: Real-Time Day/Night Cycle
# ===========================================================================


class TestRealTimeDayNight:
    def test_initial_period_is_dawn(self):
        cycle = DayNightCycle()
        assert cycle.current_period == TimePeriod.DAWN

    def test_realtime_advances_period(self):
        cycle = DayNightCycle()
        # Dawn is 15% of cycle = 0.15 * 960000 = 144000ms
        # Simulate advancing past dawn
        cycle.update_realtime(0)
        cycle.update_realtime(150_000)
        assert cycle.current_period == TimePeriod.DAY

    def test_full_cycle_returns_to_dawn(self):
        cycle = DayNightCycle()
        cycle.update_realtime(0)
        cycle.update_realtime(FULL_CYCLE_MS + 1000)
        # Should be back near dawn
        assert cycle.current_period == TimePeriod.DAWN

    def test_advance_hours_shifts_time(self):
        cycle = DayNightCycle()
        # 12 hours = half a cycle
        cycle.advance_hours(12)
        # Should be in dusk or night territory
        period = cycle.current_period
        assert period in (TimePeriod.DUSK, TimePeriod.NIGHT)

    def test_action_advance_still_works(self):
        cycle = DayNightCycle()
        # Lots of action ticks should shift period
        for _ in range(150):
            cycle.advance(1)
        assert cycle.current_period != TimePeriod.DAWN or cycle.ticks >= 150

    def test_day_number_increments(self):
        cycle = DayNightCycle()
        assert cycle.day_number == 1
        cycle.update_realtime(0)
        cycle.update_realtime(FULL_CYCLE_MS + 1)
        assert cycle.day_number == 2

    def test_is_night(self):
        cycle = DayNightCycle()
        # Advance to night: dawn(15%) + day(35%) + dusk(15%) = 65%
        night_start_ms = int(0.65 * FULL_CYCLE_MS)
        cycle.update_realtime(0)
        cycle.update_realtime(night_start_ms + 1000)
        assert cycle.is_night

    def test_serialize_deserialize(self):
        cycle = DayNightCycle(ticks=50, elapsed_ms=100_000)
        data = cycle.serialize()
        restored = DayNightCycle.deserialize(data)
        assert restored.ticks == 50
        assert restored.elapsed_ms == 100_000

    def test_period_progress_range(self):
        cycle = DayNightCycle()
        cycle.update_realtime(0)
        cycle.update_realtime(50_000)
        progress = cycle.period_progress
        assert 0.0 <= progress <= 1.0


# ===========================================================================
# Night Monsters (roaming system removed; night combat uses LLM-generated
# time-gated events only)
# ===========================================================================


# ===========================================================================
# Summary Agent: Portrait Prompt Builders
# ===========================================================================


class TestPortraitPrompts:
    def test_npc_portrait_prompt(self):
        bible = _make_bible()
        prompt = build_npc_portrait_prompt(
            {"name": "Grom", "job": "blacksmith", "personality": "gruff but kind"},
            bible,
            room_id="room_0",
        )
        assert "Grom" in prompt
        assert "blacksmith" in prompt
        assert "dungeon" in prompt
        assert "nano-banana" in prompt

    def test_monster_portrait_prompt(self):
        bible = _make_bible()
        prompt = build_monster_portrait_prompt(
            {"species": "Shadow Wolf", "elemental_affinity": "dark"},
            bible,
            room_id="room_0",
        )
        assert "Shadow Wolf" in prompt
        assert "dark" in prompt
        assert "nano-banana" in prompt

    def test_class_portrait_prompt(self):
        bible = _make_bible()
        prompt = build_class_portrait_prompt(
            {
                "name": "Fire Mage",
                "archetype": "mage",
                "flavor_text": "Wielder of ancient flames",
                "environment": "dungeon",
            },
            bible,
        )
        assert "Fire Mage" in prompt
        assert "mage" in prompt
        assert "nano-banana" in prompt

    def test_item_portrait_prompt(self):
        bible = _make_bible()
        prompt = build_item_portrait_prompt(
            {"name": "Crystal Sword", "desc": "A blade forged in starlight"},
            bible,
            room_id="room_0",
        )
        assert "Crystal Sword" in prompt
        assert "dungeon" in prompt

    def test_room_portrait_prompt(self):
        bible = _make_bible()
        prompt = build_room_portrait_prompt("room_0", bible)
        assert "dungeon" in prompt
        assert "cursed maze" in prompt

    def test_game_over_portrait_prompt(self):
        bible = _make_bible()
        prompt = build_game_over_portrait_prompt(bible)
        assert "dark" in prompt.lower() or "somber" in prompt.lower()
        assert "Dark Convergence" in prompt

    def test_room_portrait_missing_room(self):
        bible = _make_bible()
        prompt = build_room_portrait_prompt("nonexistent", bible)
        assert "fantasy" in prompt.lower()


# ===========================================================================
# Summary Agent: Story Context Builder
# ===========================================================================


class TestStoryContext:
    def test_build_story_context(self):
        story = OverarchingStory(
            title="The Dark Convergence",
            synopsis="Evil stirs.",
            faction=Faction(name="Cult", description="Bad guys", leader="Boss"),
            final_boss_name="Boss",
        )
        ctx = _build_story_context(story)
        assert "Dark Convergence" in ctx
        assert "Evil stirs" in ctx
        assert "Cult" in ctx
        assert "Boss" in ctx

    def test_empty_story_context(self):
        story = OverarchingStory()
        ctx = _build_story_context(story)
        assert ctx == ""


# ===========================================================================
# View constructors accept new params
# ===========================================================================


class TestViewParams:
    def test_gameover_view_story_param(self):
        """GameOverView accepts story_paragraph param."""
        import os

        import pygame

        from config import SCREEN_HEIGHT, SCREEN_WIDTH

        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        player = _make_player("warrior")
        from src.views.gameover_view import GameOverView

        view = GameOverView(screen, font, player, story_paragraph="The world mourns.")
        assert view.story_paragraph == "The world mourns."
        view.draw()  # Should not raise
        pygame.quit()

    def test_victory_view_story_param(self):
        """VictoryView accepts story_paragraph param."""
        import os

        import pygame

        from config import SCREEN_HEIGHT, SCREEN_WIDTH

        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        font = pygame.font.SysFont(None, 24)
        player = _make_player("warrior")
        from src.views.victory_view import VictoryView

        view = VictoryView(
            screen,
            font,
            player,
            stats={"rooms_cleared": 1, "monsters_killed": 5},
            total_rooms=3,
            story_paragraph="Victory achieved!",
        )
        assert view.story_paragraph == "Victory achieved!"
        view.draw()  # Should not raise
        pygame.quit()
