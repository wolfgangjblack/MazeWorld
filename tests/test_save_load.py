"""Tests for the save/load system."""

import json
import os
import shutil
import tempfile

import pytest

from src.models.save import SaveState, SaveMetadata
from src.systems import save_manager
from src.models.player import PlayerCharacter, PlayerClass, Stats, Ability
from src.models.items import Food, Weapon, ItemStats
from src.models.follower import Follower


@pytest.fixture
def tmp_save_dir(monkeypatch):
    """Use a temp directory for saves."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(save_manager, "SAVE_DIR", tmpdir)
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def player_with_class():
    """Create a player with a class applied."""
    pc = PlayerClass(
        name="Knight",
        archetype="warrior",
        flavor_text="A brave knight.",
        environment="castle",
        stats=Stats(STR=16, DEX=12, CON=14, INT=8, WIS=10, CHA=12, LUCK=10),
        starting_weapon="Longsword",
        abilities=[Ability(name="Shield Bash", description="Bash with shield", stat="STR")],
        spells=[],
    )
    p = PlayerCharacter(x=5, y=10, name="Gandalf")
    p.apply_class(pc)
    p.money = 100
    p.health = 80
    p.stamina = 60
    p.active_quests = ["q1", "q2"]
    p.completed_quests = ["q0"]
    p.failed_quests = ["q_fail"]
    p.learned_spells = ["fireball"]

    # Add items to inventory
    food = Food(
        category="food", name="Bread", desc="Fresh bread",
        item_stats=ItemStats(stamina_value=20, health_value=5),
    )
    weapon = Weapon(
        category="weapon", name="Longsword", desc="A sharp blade",
        item_stats=ItemStats(attack_dice="1d8", stat_modifier="STR", price=50),
        weapon_type="heavy",
    )
    p.add_to_inventory(food)
    p.add_to_inventory(weapon)
    p.equipped_weapon = "Longsword"

    return p


class TestPlayerSerialization:
    def test_serialize_deserialize_roundtrip(self, player_with_class):
        """Player data survives a serialize -> deserialize round trip."""
        p = player_with_class
        data = save_manager.serialize_player(p)
        restored = save_manager.deserialize_player(data)

        assert restored.name == "Gandalf"
        assert restored.x == 5
        assert restored.y == 10
        assert restored.health == 80
        assert restored.stamina == 60
        assert restored.money == 100
        assert restored.level == 1
        assert restored.equipped_weapon == "Longsword"
        assert restored.active_quests == ["q1", "q2"]
        assert restored.completed_quests == ["q0"]
        assert restored.failed_quests == ["q_fail"]
        assert restored.learned_spells == ["fireball"]

    def test_inventory_preserved(self, player_with_class):
        """Inventory items are properly typed after deserialization."""
        data = save_manager.serialize_player(player_with_class)
        restored = save_manager.deserialize_player(data)

        assert "Bread" in restored.inventory
        assert "Longsword" in restored.inventory
        assert isinstance(restored.inventory["Bread"], Food)
        assert isinstance(restored.inventory["Longsword"], Weapon)
        assert restored.inventory["Bread"].item_stats.stamina_value == 20
        assert restored.inventory["Longsword"].weapon_type == "heavy"

    def test_player_class_preserved(self, player_with_class):
        """Player class data survives serialization."""
        data = save_manager.serialize_player(player_with_class)
        restored = save_manager.deserialize_player(data)

        assert restored.player_class is not None
        assert restored.player_class.name == "Knight"
        assert restored.player_class.archetype == "warrior"
        assert restored.player_class.stats.STR == 16

    def test_abilities_preserved(self, player_with_class):
        """Abilities survive serialization."""
        data = save_manager.serialize_player(player_with_class)
        restored = save_manager.deserialize_player(data)

        assert len(restored.abilities) == 1
        assert restored.abilities[0].name == "Shield Bash"

    def test_empty_player_roundtrip(self):
        """Minimal player with no class serializes cleanly."""
        p = PlayerCharacter(x=0, y=0)
        data = save_manager.serialize_player(p)
        restored = save_manager.deserialize_player(data)

        assert restored.name == "Adventurer"
        assert restored.player_class is None
        assert restored.inventory == {}


class TestSaveMetadata:
    def test_save_filename_generation(self):
        filename = save_manager._save_filename(1234, "Gandalf", "Knight")
        assert filename == "save_1234_gandalf_knight.json"

    def test_save_filename_special_chars(self):
        filename = save_manager._save_filename(42, "Sir Lancelot", "Holy Knight")
        assert filename == "save_42_sir_lancelot_holy_knight.json"


class TestSaveState:
    def test_save_state_model(self):
        """SaveState can be created with defaults."""
        state = SaveState()
        assert state.version == 1
        assert state.seed == -1
        assert state.player_data == {}

    def test_save_state_with_metadata(self):
        meta = SaveMetadata(
            character_name="Test",
            character_class="Warrior",
            room_level=2,
            time_played_seconds=3600,
            last_save_date="2026-04-06 12:00",
            seed=1234,
        )
        state = SaveState(metadata=meta, seed=1234)
        assert state.metadata.character_name == "Test"
        assert state.metadata.time_played_seconds == 3600


class TestListAndHasSaves:
    def test_list_saves_empty(self, tmp_save_dir):
        """No saves returns empty list."""
        assert save_manager.list_saves() == []

    def test_has_saves_false(self, tmp_save_dir):
        assert save_manager.has_saves() is False

    def test_list_saves_with_file(self, tmp_save_dir):
        """A valid save file is listed."""
        state = SaveState(
            metadata=SaveMetadata(
                character_name="Hero",
                character_class="Mage",
                seed=42,
            ),
            seed=42,
            player_data={"name": "Hero"},
        )
        filepath = os.path.join(tmp_save_dir, "save_42_hero_mage.json")
        with open(filepath, 'w') as f:
            json.dump(state.model_dump(), f)

        saves = save_manager.list_saves()
        assert len(saves) == 1
        assert saves[0]["character_name"] == "Hero"
        assert saves[0]["character_class"] == "Mage"
        assert saves[0]["seed"] == 42

    def test_has_saves_true(self, tmp_save_dir):
        filepath = os.path.join(tmp_save_dir, "save_1_a_b.json")
        state = SaveState(player_data={"name": "A"})
        with open(filepath, 'w') as f:
            json.dump(state.model_dump(), f)
        assert save_manager.has_saves() is True


class TestValidation:
    def test_validate_valid_save(self, tmp_save_dir):
        filepath = os.path.join(tmp_save_dir, "valid.json")
        with open(filepath, 'w') as f:
            json.dump({"version": 1, "player_data": {}}, f)
        assert save_manager.validate_save(filepath) is True

    def test_validate_corrupt_json(self, tmp_save_dir):
        filepath = os.path.join(tmp_save_dir, "corrupt.json")
        with open(filepath, 'w') as f:
            f.write("{broken json!!!")
        assert save_manager.validate_save(filepath) is False

    def test_validate_missing_fields(self, tmp_save_dir):
        filepath = os.path.join(tmp_save_dir, "bad.json")
        with open(filepath, 'w') as f:
            json.dump({"seed": 1}, f)
        assert save_manager.validate_save(filepath) is False

    def test_validate_nonexistent_file(self, tmp_save_dir):
        assert save_manager.validate_save("/nonexistent/path.json") is False

    def test_load_corrupt_returns_none(self, tmp_save_dir):
        filepath = os.path.join(tmp_save_dir, "corrupt.json")
        with open(filepath, 'w') as f:
            f.write("not json")
        assert save_manager.load_game(filepath) is None

    def test_load_nonexistent_returns_none(self, tmp_save_dir):
        assert save_manager.load_game("/no/such/file.json") is None


class TestDeleteSave:
    def test_delete_existing(self, tmp_save_dir):
        filepath = os.path.join(tmp_save_dir, "delete_me.json")
        with open(filepath, 'w') as f:
            f.write("{}")
        assert save_manager.delete_save(filepath) is True
        assert not os.path.exists(filepath)

    def test_delete_nonexistent(self, tmp_save_dir):
        assert save_manager.delete_save("/no/such/file.json") is False


class TestNpcSerialization:
    def test_serialize_npc_basic(self):
        from src.models.npc import StaticNPC
        npc = StaticNPC(x=3, y=7, id=1)
        data = save_manager.serialize_npc(npc)
        assert data["id"] == 1
        assert data["x"] == 3
        assert data["y"] == 7
        assert data["_npc_type"] == "StaticNPC"

    def test_serialize_npc_with_history(self):
        from src.models.npc import StaticNPC
        npc = StaticNPC(x=0, y=0, id=2)
        npc.add_turn("user", "Hello")
        npc.add_turn("assistant", "Hi there!")
        npc.has_met_player = True
        data = save_manager.serialize_npc(npc)
        assert len(data["interaction_history"]) == 2
        assert data["has_met_player"] is True


class TestEventSerialization:
    def test_serialize_resolved_event(self):
        from src.models.encounter import PuzzleEvent, EventChoice
        evt = PuzzleEvent(
            id="p1", name="Boulder", description="A boulder blocks the path",
            choices=[EventChoice(text="Push it", dc=12)],
        )
        evt.resolved = True
        data = save_manager.serialize_event(evt)
        assert data["resolved"] is True

    def test_serialize_combat_event(self):
        from src.models.encounter import CombatEvent
        from src.models.monster import Monster
        m = Monster(id="m1", species="Goblin", hp=5, max_hp=10)
        evt = CombatEvent(
            id="c1", name="Goblin fight", description="Goblins!",
            monsters=[m],
        )
        data = save_manager.serialize_event(evt)
        assert data["monster_states"][0]["hp"] == 5


class TestQuestSerialization:
    def test_serialize_quest(self):
        from src.models.quest import FetchQuest, QuestReward
        q = FetchQuest(
            id="q1", title="Find herbs", description="Get herbs",
            giver_npc_id=1, target_items=[{"item_id": 101, "count": 2}],
            reward=QuestReward(money=50),
        )
        q.status = "active"
        data = save_manager.serialize_quest(q)
        assert data["status"] == "active"

    def test_serialize_multistep_quest(self):
        from src.models.quest import MultiStepQuest, QuestReward
        q = MultiStepQuest(
            id="ms1", title="Epic chain", description="Do things",
            giver_npc_id=1, sub_quest_ids=["s1", "s2", "s3"],
            reward=QuestReward(),
        )
        q.current_step = 1
        q.status = "active"
        data = save_manager.serialize_quest(q)
        assert data["current_step"] == 1


class TestFollowerSerialization:
    def test_serialize_follower(self):
        f = Follower(
            npc_id=5, name="Bob", quest_id="q1",
            joined_in_room=1, destination_room=2,
            personality="friendly",
            dialogue_hints=["Stay close.", "Almost there."],
        )
        data = save_manager.serialize_follower(f)
        assert data["npc_id"] == 5
        assert data["name"] == "Bob"
        assert data["quest_id"] == "q1"
        assert len(data["dialogue_hints"]) == 2


class TestItemReconstruction:
    def test_reconstruct_food(self):
        item = save_manager._reconstruct_item(
            {"category": "food", "name": "Apple", "desc": "Red apple",
             "item_stats": {"stamina_value": 15}},
            "Food",
        )
        assert isinstance(item, Food)
        assert item.item_stats.stamina_value == 15

    def test_reconstruct_weapon(self):
        item = save_manager._reconstruct_item(
            {"category": "weapon", "name": "Dagger", "desc": "Sharp",
             "item_stats": {"attack_dice": "1d4"}, "weapon_type": "light"},
            "Weapon",
        )
        assert isinstance(item, Weapon)
        assert item.weapon_type == "light"

    def test_reconstruct_unknown_falls_back_to_item(self):
        from src.models.items import Item
        item = save_manager._reconstruct_item(
            {"category": "misc", "name": "Rock", "desc": "A rock",
             "item_stats": {}},
            "UnknownType",
        )
        assert isinstance(item, Item)
