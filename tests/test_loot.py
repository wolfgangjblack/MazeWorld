from src.models.encounter import CombatEvent, LootEntry
from src.models.player import PlayerCharacter, PlayerClass, Stats
from src.models.items import Weapon, ItemStats


def _make_player(**kwargs):
    return PlayerCharacter(x=0, y=0, money=0, **kwargs)


def _make_combat_event(loot_table=None, money_drop=None, difficulty=2):
    return CombatEvent(
        id="evt_test",
        name="Test Monster",
        description="A test monster",
        difficulty=difficulty,
        damage_range=[5, 10],
        loot_table=loot_table or [],
        money_drop=money_drop or [0, 0],
    )


class TestLootTable:
    def test_loot_entry_model(self):
        entry = LootEntry(item_id=200, drop_chance=0.5)
        assert entry.item_id == 200
        assert entry.drop_chance == 0.5

    def test_combat_victory_drops_loot(self):
        """On a high roll, loot should drop based on probability."""
        loot = [LootEntry(item_id=200, drop_chance=1.0)]  # 100% drop
        event = _make_combat_event(loot_table=loot, difficulty=1)
        player = _make_player()
        # Roll high enough to always win (difficulty=1, threshold=3)
        result = event.resolve(20, player)
        assert result["success"] is True
        assert 200 in result.get("loot_item_ids", [])

    def test_combat_victory_money_drop(self):
        event = _make_combat_event(money_drop=[10, 10], difficulty=1)
        player = _make_player()
        result = event.resolve(20, player)
        assert result["success"] is True
        assert result["money_dropped"] == 10
        assert player.money == 10

    def test_combat_failure_no_loot(self):
        loot = [LootEntry(item_id=200, drop_chance=1.0)]
        event = _make_combat_event(loot_table=loot, money_drop=[10, 10], difficulty=5)
        player = _make_player()
        player.health = 100
        # Roll too low (difficulty=5, threshold=15)
        result = event.resolve(1, player)
        assert result["success"] is False
        assert "loot_item_ids" not in result
        assert player.money == 0

    def test_combat_zero_chance_no_loot(self):
        loot = [LootEntry(item_id=200, drop_chance=0.0)]
        event = _make_combat_event(loot_table=loot, difficulty=1)
        player = _make_player()
        result = event.resolve(20, player)
        assert result["success"] is True
        assert 200 not in result.get("loot_item_ids", [])

    def test_weapon_stat_modifier_in_combat(self):
        """Equipped weapon's stat modifier adds to the combat check."""
        event = _make_combat_event(difficulty=3)  # threshold = 9
        player = _make_player()
        # Give the player a class with STR 18 -> modifier +4
        player.player_class = PlayerClass(
            name="Fighter", archetype="warrior",
            stats=Stats(STR=18, DEX=10, CON=10, INT=10, WIS=10, CHA=10, LUCK=10),
        )
        weapon = Weapon(
            category="weapon", name="big sword", desc="test",
            weapon_type="heavy",
            item_stats=ItemStats(attack_dice="1d12", stat_modifier="STR"),
        )
        player.inventory = {"big sword": weapon}
        player.equipped_weapon = "big sword"

        # dice_roll=5 + STR mod +4 = 9, exactly meets threshold=9
        result = event.resolve(5, player)
        assert result["success"] is True

    def test_weapon_no_stat_modifier_no_bonus(self):
        """Weapon without stat_modifier gives no bonus."""
        event = _make_combat_event(difficulty=3)  # threshold = 9
        player = _make_player()
        weapon = Weapon(
            category="weapon", name="plain stick", desc="test",
            weapon_type="simple",
            item_stats=ItemStats(attack_dice="1d4"),
        )
        player.inventory = {"plain stick": weapon}
        player.equipped_weapon = "plain stick"

        # dice_roll=8 < threshold=9, no stat_modifier so no bonus
        result = event.resolve(8, player)
        assert result["success"] is False

    def test_no_weapon_no_bonus(self):
        event = _make_combat_event(difficulty=4)  # threshold = 12
        player = _make_player()
        # Roll exactly at threshold fails because no weapon bonus
        result = event.resolve(11, player)
        assert result["success"] is False

    def test_combat_empty_loot_table(self):
        event = _make_combat_event(loot_table=[], money_drop=[0, 0], difficulty=1)
        player = _make_player()
        result = event.resolve(20, player)
        assert result["success"] is True
        assert result.get("loot_item_ids", []) == []
        assert result.get("money_dropped", 0) == 0
