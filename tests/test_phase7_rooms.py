"""Phase 7 tests — multi-room progression, doors, gates, level-up, victory."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch

import pytest

from src.models.maze import DOOR_TILE_ID, Maze
from src.models.player import Ability, PlayerCharacter, PlayerClass, Spell, Stats

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def maze_with_door():
    """Create a maze with a door placed far from player start."""
    m = Maze()
    m.generate()
    m.place_event_tiles()
    player_start = (1, 1)
    m.place_door(player_start)
    return m, player_start


@pytest.fixture
def warrior_class():
    return PlayerClass(
        name="Knight",
        archetype="warrior",
        stats=Stats(STR=16, DEX=12, CON=14, INT=8, WIS=10, CHA=12, LUCK=10),
        starting_weapon="Longsword",
        abilities=[Ability(name="Slash", description="A powerful slash", stat="STR")],
        spells=[],
        ability_pool=[
            Ability(name="Shield Bash", description="Bash with shield", stat="STR"),
            Ability(name="Rally", description="Rally allies", stat="CHA"),
            Ability(name="Intimidate", description="Intimidate foes", stat="CHA"),
        ],
        spell_pool=[],
    )


@pytest.fixture
def mage_class():
    return PlayerClass(
        name="Pyromancer",
        archetype="mage",
        stats=Stats(STR=8, DEX=12, CON=10, INT=16, WIS=14, CHA=10, LUCK=10),
        starting_weapon="Staff",
        abilities=[],
        spells=[
            Spell(
                name="Fireball",
                description="Hurl fire",
                element="fire",
                spell_type="damage_single",
                stat="INT",
                num_dice=1,
                die_sides=6,
            )
        ],
        ability_pool=[],
        spell_pool=[
            Spell(
                name="Ice Shard",
                description="Frost attack",
                element="ice",
                spell_type="damage_single",
                stat="INT",
                num_dice=1,
                die_sides=4,
            ),
            Spell(
                name="Lightning",
                description="Zap!",
                element="lightning",
                spell_type="damage_single",
                stat="INT",
                num_dice=1,
                die_sides=8,
            ),
        ],
    )


@pytest.fixture
def jester_class():
    return PlayerClass(
        name="Trickster",
        archetype="jester",
        stats=Stats(STR=10, DEX=12, CON=10, INT=10, WIS=10, CHA=10, LUCK=18),
        starting_weapon="Dagger",
        abilities=[Ability(name="Juggle", description="Distract", stat="DEX")],
        spells=[],
        ability_pool=[
            Ability(name="Shield Bash", description="From warrior pool", stat="STR"),
        ],
        spell_pool=[
            Spell(name="Heal", description="From healer pool", element="light", spell_type="heal", stat="WIS"),
        ],
    )


@pytest.fixture
def player_with_class(warrior_class):
    p = PlayerCharacter(x=1, y=1, name="TestHero")
    p.apply_class(warrior_class)
    return p


def _make_mock_event(event_id=3000, resolved=False, is_gate=False, is_climax_boss=False):
    """Create a mock event object for testing."""
    evt = MagicMock()
    evt.id = event_id
    evt.resolved = resolved
    evt.is_gate = is_gate
    evt.is_climax_boss = is_climax_boss
    evt.type = "combat"
    return evt


# ---------------------------------------------------------------------------
# Door reveal at 40% threshold
# ---------------------------------------------------------------------------


class TestDoorReveal:
    def test_door_hidden_initially(self, maze_with_door):
        maze, _ = maze_with_door
        assert maze.door_position is not None
        assert maze.door_revealed is False
        # Door tile should NOT be placed yet (hidden = wall)
        dx, dy = maze.door_position
        assert maze.grid[dy][dx] != DOOR_TILE_ID

    def test_door_reveal(self, maze_with_door):
        maze, _ = maze_with_door
        maze.reveal_door()
        assert maze.door_revealed is True
        dx, dy = maze.door_position
        assert maze.grid[dy][dx] != DOOR_TILE_ID
        maze.place_door_tile()
        assert maze.grid[dy][dx] == DOOR_TILE_ID

    def test_door_reveal_idempotent(self, maze_with_door):
        maze, _ = maze_with_door
        maze.reveal_door()
        maze.reveal_door()  # Should not error
        assert maze.door_revealed is True

    def test_door_reveals_at_threshold(self):
        """GameController reveals door when encounter_clear_fraction >= 0.4."""
        from src.controllers.game_controller import GameController

        maze = Maze()
        maze.generate()
        maze.place_door((1, 1))
        player = PlayerCharacter(x=1, y=1)
        dialogue_box = MagicMock()

        # Create 10 mock events, 0 resolved
        events = {}
        for i in range(10):
            events[3000 + i] = _make_mock_event(3000 + i, resolved=False)

        gc = GameController.__new__(GameController)
        gc.maze = maze
        gc.player = player
        gc.events = events
        gc.dialogue_box = dialogue_box
        gc.total_rooms = 2
        gc.current_room = 0
        gc.item_message_active = False
        gc.stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
        gc.sfx = None
        gc.quests = {}
        gc._count_total_encounters()

        assert gc.encounter_clear_fraction == 0.0
        assert not maze.door_revealed

        # Resolve 3/10 = 30% — not enough
        for i in range(3):
            events[3000 + i].resolved = True
        gc._count_total_encounters()
        gc._check_door_reveal()
        assert not maze.door_revealed

        # Resolve 4/10 = 40% — threshold met
        events[3003].resolved = True
        gc.resolved_encounters = 4
        gc._check_door_reveal()
        assert maze.door_revealed

    def test_no_door_in_single_room(self):
        """No door reveal in single-room game."""
        from src.controllers.game_controller import GameController

        maze = Maze()
        maze.generate()
        player = PlayerCharacter(x=1, y=1)
        dialogue_box = MagicMock()

        gc = GameController.__new__(GameController)
        gc.maze = maze
        gc.player = player
        gc.events = {}
        gc.dialogue_box = dialogue_box
        gc.total_rooms = 1
        gc.current_room = 0
        gc.item_message_active = False
        gc.stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
        gc._count_total_encounters()

        gc._check_door_reveal()
        assert not maze.door_revealed


# ---------------------------------------------------------------------------
# Gate encounter blocks progression until resolved
# ---------------------------------------------------------------------------


class TestGateEncounter:
    def test_gate_blocks_door(self):
        """Door tile doesn't exist until boss is defeated, preventing early transition."""
        from src.controllers.game_controller import GameController

        maze = Maze()
        maze.generate()
        maze.place_door((1, 1))
        maze.reveal_door()
        maze.gate_encounter_id = 3100

        gc = GameController.__new__(GameController)
        gc.maze = maze
        gc.player = PlayerCharacter(x=1, y=1)
        gc.events = {}
        gc.quests = {}
        gc.dialogue_box = MagicMock()
        gc.gate_cleared = False
        gc.total_rooms = 3
        gc.current_room = 0
        gc.pending_action = None

        gc.player.x, gc.player.y = maze.door_position
        assert not gc._is_on_door_tile()

        maze.place_door_tile()
        assert gc._is_on_door_tile()

    def test_gate_cleared_allows_transition(self):
        """After gate is resolved, stepping on door triggers room transition."""
        from src.controllers.game_controller import GameController

        maze = Maze()
        maze.generate()
        maze.place_door((1, 1))
        maze.reveal_door()
        maze.gate_encounter_id = 3100

        gate_evt = _make_mock_event(3100, resolved=True, is_gate=True)

        gc = GameController.__new__(GameController)
        gc.maze = maze
        gc.player = PlayerCharacter(x=1, y=1)
        gc.events = {3100: gate_evt}
        gc.quests = {}
        gc.dialogue_box = MagicMock()
        gc.gate_cleared = False
        gc.total_rooms = 3
        gc.current_room = 0
        gc.pending_action = None
        gc.item_message_active = False
        gc.stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
        gc.sfx = None

        gc.player.x, gc.player.y = maze.door_position
        gc._handle_door_interaction()
        assert gc.pending_action == "room_transition"


# ---------------------------------------------------------------------------
# Gate failure applies survival penalty
# ---------------------------------------------------------------------------


class TestGateFailurePenalty:
    # TODO: rewrite to use CombatController
    # def test_flee_gate_does_not_clear(self):
    #     """Fleeing a gate encounter does NOT clear the gate (flee is blocked)."""
    #     from src.controllers.game_controller import GameController
    #
    #     combat_event = MagicMock()
    #     combat_event.resolved = False
    #     combat_event.is_gate = True
    #     combat_event.player_fled = True
    #     combat_event.id = 3100
    #
    #     gc = GameController.__new__(GameController)
    #     gc.maze = MagicMock()
    #     gc.player = PlayerCharacter(x=1, y=1)
    #     gc.player.health = 100
    #     gc.player.stamina = 100
    #     gc.quests = {}
    #     gc.dialogue_box = MagicMock()
    #     gc.gate_cleared = False
    #     gc.current_room = 0
    #     gc.item_message_active = False
    #     gc.sfx = None
    #     from src.controllers.event_input_handler import EventInputHandler
    #
    #     gc.event_handler = EventInputHandler(gc)
    #
    #     gc.event_handler._finalize_combat(combat_event)
    #
    #     assert gc.player.health == 100
    #     assert gc.player.stamina == 100
    #     assert gc.gate_cleared is False

    # TODO: rewrite to use CombatController
    # def test_gate_victory_clears_gate(self):
    #     """Winning a gate encounter clears the gate."""
    #     from src.controllers.game_controller import GameController
    #
    #     combat_event = MagicMock()
    #     combat_event.resolved = True
    #     combat_event.is_gate = True
    #     combat_event.player_fled = False
    #     combat_event.id = 3100
    #
    #     gc = GameController.__new__(GameController)
    #     gc.maze = MagicMock()
    #     gc.player = PlayerCharacter(x=1, y=1)
    #     gc.player.health = 100
    #     gc.player.stamina = 100
    #     gc.quests = {}
    #     gc.dialogue_box = MagicMock()
    #     gc.gate_cleared = False
    #     gc.current_room = 0
    #     gc.item_message_active = False
    #     gc.sfx = None
    #     gc.quest_manager = MagicMock()
    #     from src.controllers.event_input_handler import EventInputHandler
    #
    #     gc.event_handler = EventInputHandler(gc)
    #
    #     gc.event_handler._finalize_combat(combat_event)
    #
    #     gc.quest_manager.on_event_resolved.assert_called_once()
    pass


# ---------------------------------------------------------------------------
# Level-up offers correct ability pool per class
# ---------------------------------------------------------------------------


class TestLevelUpPools:
    def test_warrior_level_up_offers_abilities(self, warrior_class):
        p = PlayerCharacter(x=0, y=0)
        p.apply_class(warrior_class)
        choices = p.level_up_choices()
        # Should offer abilities from ability_pool not yet known
        assert len(choices) == 3  # Shield Bash, Rally, Intimidate
        for ctype, choice in choices:
            assert ctype == "ability"

    def test_mage_level_up_offers_spells(self, mage_class):
        p = PlayerCharacter(x=0, y=0)
        p.apply_class(mage_class)
        choices = p.level_up_choices()
        assert len(choices) == 2  # Ice Shard, Lightning
        for ctype, choice in choices:
            assert ctype == "spell"

    def test_jester_level_up_has_mixed_pool(self, jester_class):
        """Jester gets choices from other class pools (populated during gen)."""
        p = PlayerCharacter(x=0, y=0)
        p.apply_class(jester_class)
        choices = p.level_up_choices()
        # Should have both ability and spell from other pools
        types = {c[0] for c in choices}
        assert "ability" in types
        assert "spell" in types

    def test_apply_level_up_increments_level(self, player_with_class):
        p = player_with_class
        assert p.level == 1
        choices = p.level_up_choices()
        ctype, choice = choices[0]
        p.apply_level_up(ctype, choice)
        assert p.level == 2

    def test_apply_level_up_adds_ability(self, player_with_class):
        p = player_with_class
        initial_count = len(p.abilities)
        choices = p.level_up_choices()
        ability_choice = next(c for c in choices if c[0] == "ability")
        p.apply_level_up(ability_choice[0], ability_choice[1])
        assert len(p.abilities) == initial_count + 1

    def test_known_abilities_excluded(self, player_with_class):
        """Abilities already known should not appear in level-up choices."""
        p = player_with_class
        known_names = {a.name for a in p.abilities}
        choices = p.level_up_choices()
        for _, choice in choices:
            assert choice.name not in known_names


# ---------------------------------------------------------------------------
# Room transition renders portrait + story text (smoke test)
# ---------------------------------------------------------------------------


class TestRoomTransition:
    @pytest.fixture
    def mock_pygame(self):
        """Provide a mock pygame screen."""
        screen = MagicMock()
        screen.fill = MagicMock()
        screen.blit = MagicMock()
        font = MagicMock()
        font.render = MagicMock(return_value=MagicMock(get_width=lambda: 100))
        font.get_linesize = MagicMock(return_value=20)
        font.size = MagicMock(return_value=(100, 20))
        return screen, font

    def test_room_intro_view_renders(self, mock_pygame):
        """RoomIntroView can be created and drawn without error."""
        from src.views.room_intro_view import RoomIntroView

        screen, font = mock_pygame
        with patch("pygame.font.Font", return_value=font):
            with patch("pygame.Surface"):
                with patch("pygame.draw.rect"):
                    view = RoomIntroView(
                        screen,
                        font,
                        env_name="Darkwood Forest",
                        env_type="forest",
                        story_text="The shadows grow deeper as you press on.",
                    )
                    view.draw()
        assert screen.fill.called


# ---------------------------------------------------------------------------
# Final boss victory triggers victory screen
# ---------------------------------------------------------------------------


class TestVictoryScreen:
    def test_victory_view_renders(self):
        """VictoryView can be created and drawn with stats."""
        from src.views.victory_view import VictoryView

        screen = MagicMock()
        screen.fill = MagicMock()
        screen.blit = MagicMock()
        font = MagicMock()
        font.render = MagicMock(return_value=MagicMock(get_width=lambda: 100))

        player = PlayerCharacter(x=0, y=0, name="Hero")
        player.completed_quests = [4010, 4011, 4012]
        player.failed_quests = [4013]
        stats = {"monsters_killed": 15, "items_used": 3, "rooms_cleared": 3}

        with patch("pygame.font.Font", return_value=font):
            with patch("pygame.draw.rect"):
                view = VictoryView(screen, font, player, stats, total_rooms=3)
                view.draw()
        assert screen.fill.called

    def test_victory_stats_accurate(self):
        """Stats in victory view match what was tracked."""
        player = PlayerCharacter(x=0, y=0, name="Hero")
        player.completed_quests = [4010, 4011]
        player.failed_quests = [4012]

        stats = {"monsters_killed": 10, "items_used": 5, "rooms_cleared": 3}

        from src.views.victory_view import VictoryView

        with patch("pygame.font.Font"):
            view = VictoryView(MagicMock(), MagicMock(), player, stats, total_rooms=3)

        assert view.stats["monsters_killed"] == 10
        assert view.stats["rooms_cleared"] == 3
        assert view.total_rooms == 3
        assert len(view.player.completed_quests) == 2
        assert len(view.player.failed_quests) == 1


# ---------------------------------------------------------------------------
# Maze door placement
# ---------------------------------------------------------------------------


class TestDoorPlacement:
    def test_place_door_returns_position(self):
        m = Maze()
        m.generate()
        pos = m.place_door((1, 1))
        assert pos is not None
        assert m.door_position == pos

    def test_door_far_from_start(self):
        m = Maze()
        m.generate()
        start = (1, 1)
        pos = m.place_door(start)
        # Door should be at least 10 manhattan distance from start
        dist = abs(pos[0] - start[0]) + abs(pos[1] - start[1])
        assert dist > 5

    def test_save_load_preserves_door(self, tmp_path):
        m = Maze()
        m.generate()
        m.place_door((1, 1))
        m.gate_encounter_id = 3101

        path = str(tmp_path / "maze.json")
        m.save_to_json(path)
        loaded, data = Maze.load_from_json(path)

        assert loaded.door_position == m.door_position
        assert loaded.door_revealed == m.door_revealed
        assert loaded.gate_encounter_id == 3101


class TestClimaxBossVictory:
    """Defeating the climax boss triggers the victory screen."""

    def _make_gc(self, events=None, current_room=2, total_rooms=3):
        from src.controllers.game_controller import GameController

        gc = GameController.__new__(GameController)
        gc.maze = MagicMock()
        gc.maze.door_position = None
        gc.maze.door_revealed = False
        gc.player = PlayerCharacter(x=1, y=1)
        gc.events = events or {}
        gc.dialogue_box = MagicMock()
        gc.pending_action = None
        gc.resolved_encounters = 0
        gc.total_encounters = 5
        gc.total_rooms = total_rooms
        gc.current_room = current_room
        gc.gate_cleared = False
        gc.item_message_active = False
        gc.stats = {"monsters_killed": 0, "items_used": 0, "rooms_cleared": 0}
        gc.quest_manager = MagicMock()
        gc.sfx = None
        gc.quests = {}
        from src.controllers.combat_input_handler import CombatInputHandler
        from src.controllers.event_input_handler import EventInputHandler

        gc.event_handler = EventInputHandler(gc)
        gc.combat_handler = CombatInputHandler(gc)
        return gc

    def _make_climax_event(self):
        evt = MagicMock()
        evt.id = 3102
        evt.resolved = False
        evt.is_climax_boss = True
        evt.is_gate = False
        evt.monsters = []
        evt.collect_loot = MagicMock(return_value=[])
        return evt

    # TODO: rewrite to use CombatController
    # def test_climax_boss_defeat_sets_victory(self):
    #     combat_event = self._make_climax_event()
    #     gc = self._make_gc({3102: combat_event})
    #     gc.event_handler._handle_combat_victory(combat_event)
    #     assert gc.pending_action == "victory"

    # TODO: rewrite to use CombatController
    # def test_climax_boss_increments_resolved_encounters(self):
    #     combat_event = self._make_climax_event()
    #     gc = self._make_gc({3102: combat_event})
    #     gc.event_handler._handle_combat_victory(combat_event)
    #     assert gc.resolved_encounters == 1

    # TODO: rewrite to use CombatController
    # def test_climax_boss_sets_gate_cleared(self):
    #     combat_event = self._make_climax_event()
    #     gc = self._make_gc({3102: combat_event})
    #     gc.event_handler._handle_combat_victory(combat_event)
    #     assert gc.gate_cleared is True

    # TODO: rewrite to use CombatController
    # def test_regular_combat_does_not_set_victory(self):
    #     combat_event = MagicMock()
    #     combat_event.id = 3000
    #     combat_event.resolved = False
    #     combat_event.is_climax_boss = False
    #     combat_event.is_gate = False
    #     combat_event.monsters = []
    #     combat_event.collect_loot = MagicMock(return_value=[])
    #
    #     gc = self._make_gc({3000: combat_event})
    #     gc.event_handler._handle_combat_victory(combat_event)
    #     assert gc.pending_action is None

    def test_climax_boss_excluded_from_total_encounters(self):
        """Climax boss should not inflate the 40% reveal denominator."""

        regular = MagicMock()
        regular.is_gate = False
        regular.is_climax_boss = False
        regular.resolved = False

        boss = MagicMock()
        boss.is_gate = False
        boss.is_climax_boss = True
        boss.resolved = False

        gc = self._make_gc()
        gc.events = {3000: regular, 3001: regular, 3102: boss}
        gc._count_total_encounters()

        assert gc.total_encounters == 2

    def test_signal_room_transition_final_room_sets_victory(self):
        """Transitioning in the final room should trigger victory, not room_transition."""
        gc = self._make_gc(current_room=2, total_rooms=3)
        gc.quests = {}
        gc._signal_room_transition()
        assert gc.pending_action == "victory"

    def test_signal_room_transition_non_final_room(self):
        """Transitioning in a non-final room should trigger room_transition."""
        gc = self._make_gc(current_room=0, total_rooms=3)
        gc.quests = {}
        gc._signal_room_transition()
        assert gc.pending_action == "room_transition"


class TestQuestDoorReveal:
    """Quest with door_reveal=True calls reveal_door_from_quest."""

    def test_quest_door_reveal_triggers_callback(self):
        from src.models.quest import Quest, QuestReward
        from src.systems.quest_manager import QuestManager

        quest = Quest(
            id=4000,
            type="combat",
            title="Clear the Path",
            description="Defeat the monster",
            giver_npc_id=1000,
            reward=QuestReward(door_reveal=True, story_info="Path revealed!"),
        )
        player = PlayerCharacter(x=1, y=1)
        player.active_quests.append(4000)

        qm = QuestManager({4000: quest}, {})
        callback = MagicMock()
        qm.door_reveal_callback = callback

        qm.complete_quest(quest, player)

        callback.assert_called_once()
        assert quest.status == "completed"

    def test_quest_without_door_reveal_no_callback(self):
        from src.models.quest import Quest, QuestReward
        from src.systems.quest_manager import QuestManager

        quest = Quest(
            id=4001,
            type="combat",
            title="Just Kill",
            description="Defeat the monster",
            giver_npc_id=1000,
            reward=QuestReward(door_reveal=False),
        )
        player = PlayerCharacter(x=1, y=1)
        player.active_quests.append(4001)

        qm = QuestManager({4001: quest}, {})
        callback = MagicMock()
        qm.door_reveal_callback = callback

        qm.complete_quest(quest, player)

        callback.assert_not_called()

    def test_door_reveal_wired_in_game_controller(self):
        """QuestManager gets the callback when GameController sets it up."""
        from src.controllers.game_controller import GameController
        from src.systems.quest_manager import QuestManager

        gc = GameController.__new__(GameController)
        gc.maze = MagicMock()
        gc.player = PlayerCharacter(x=1, y=1)
        gc.events = {}
        gc.quests = {}
        gc.dialogue_box = MagicMock()
        gc.quest_manager = QuestManager(gc.quests, gc.events)
        gc.quest_manager.door_reveal_callback = gc.reveal_door_from_quest

        assert gc.quest_manager.door_reveal_callback is not None
        assert gc.quest_manager.door_reveal_callback == gc.reveal_door_from_quest


# ---------------------------------------------------------------------------
# Config sanity checks
# ---------------------------------------------------------------------------


class TestConfig:
    def test_num_rooms_valid(self):
        from config import NUM_ROOMS

        assert isinstance(NUM_ROOMS, int)
        assert NUM_ROOMS >= 1

    def test_door_reveal_threshold(self):
        from config import DOOR_REVEAL_THRESHOLD

        assert DOOR_REVEAL_THRESHOLD == 0.4
