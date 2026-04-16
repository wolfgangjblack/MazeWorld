"""Phase 6 tests: Quests, Story & Followers."""

from unittest.mock import MagicMock

from src.models.follower import MAX_FOLLOWERS, Follower
from src.models.player import PlayerCharacter
from src.models.quest import (
    QUEST_TYPE_MAP,
    CombatQuest,
    DialogueQuest,
    FetchQuest,
    MultiStepQuest,
    Quest,
    QuestFailurePenalty,
    QuestReward,
    create_quest_from_data,
)
from src.models.story import Faction, OverarchingStory, RoomStoryBeat

# ---------------------------------------------------------------------------
# Story model tests
# ---------------------------------------------------------------------------


class TestStoryModels:
    def test_faction_has_leader(self):
        f = Faction(name="Shadow Cult", description="Evil", leader="The Faceless One")
        assert f.leader == "The Faceless One"

    def test_faction_leader_default(self):
        f = Faction(name="X", description="Y")
        assert f.leader == ""

    def test_room_story_beat_escalation(self):
        beat = RoomStoryBeat(room_id="room_0", summary="Signs of evil", escalation=3)
        assert beat.escalation == 3

    def test_overarching_story_full(self):
        story = OverarchingStory(
            seed="A cult rises",
            title="The Dark Convergence",
            synopsis="A cult threatens the land.",
            faction=Faction(name="Shadow Cult", description="Evil", leader="Lord Kael"),
            escalation_arc=["Whispers", "Encounters", "Assault"],
            climax="Face Lord Kael in the temple.",
            final_boss_name="Lord Kael",
            key_npc_names=["Lord Kael", "Elder Mira"],
            beats=[
                RoomStoryBeat(
                    room_id="room_0", summary="Cult symbols appear", faction_presence="Graffiti on walls", escalation=1
                ),
                RoomStoryBeat(room_id="room_1", summary="Cult ambush", faction_presence="Armed cultists", escalation=3),
            ],
        )
        assert story.title == "The Dark Convergence"
        assert story.faction.leader == "Lord Kael"
        assert len(story.beats) == 2
        assert story.beats[1].escalation == 3
        assert story.final_boss_name == "Lord Kael"
        assert len(story.escalation_arc) == 3

    def test_story_default_empty(self):
        story = OverarchingStory()
        assert story.seed == ""
        assert story.faction is None
        assert story.beats == []
        assert story.escalation_arc == []
        assert story.final_boss_name == ""

    def test_story_serialization(self):
        story = OverarchingStory(
            seed="test",
            title="Test Story",
            faction=Faction(name="Test Faction", description="desc", leader="Boss"),
            beats=[RoomStoryBeat(room_id="r0", summary="s", escalation=2)],
        )
        data = story.model_dump()
        restored = OverarchingStory(**data)
        assert restored.faction.leader == "Boss"
        assert restored.beats[0].escalation == 2


# ---------------------------------------------------------------------------
# Quest model tests
# ---------------------------------------------------------------------------


class TestQuestModels:
    def test_quest_types_registered(self):
        for qt in ["fetch", "escort", "delivery", "dialogue", "combat", "multi_step"]:
            assert qt in QUEST_TYPE_MAP

    def test_backward_compat_dialogue_gated(self):
        assert QUEST_TYPE_MAP["dialogue_gated"] is DialogueQuest

    def test_quest_reward_extended(self):
        r = QuestReward(item_id=2005, xp=10, money=50, story_info="A clue", door_reveal=True)
        assert r.money == 50
        assert r.story_info == "A clue"
        assert r.door_reveal is True

    def test_quest_failure_penalty(self):
        p = QuestFailurePenalty(hp_damage=10, stamina_damage=5)
        assert p.hp_damage == 10

    def test_quest_is_story_quest(self):
        q = Quest(id=4000, type="fetch", title="T", description="D", giver_npc_id=1000, is_story_quest=True)
        assert q.is_story_quest is True

    def test_quest_room_id(self):
        q = Quest(id=4000, type="fetch", title="T", description="D", giver_npc_id=1000, room_id="room_0")
        assert q.room_id == "room_0"

    def test_quest_time_gate(self):
        q = Quest(id=4000, type="fetch", title="T", description="D", giver_npc_id=1000, time_gate="night")
        assert q.time_gate == "night"

    def test_apply_failure_penalty(self):
        player = _make_player()
        q = Quest(
            id=4000,
            type="fetch",
            title="T",
            description="D",
            giver_npc_id=1000,
            failure_penalty=QuestFailurePenalty(hp_damage=20, stamina_damage=15),
        )
        msg = q.apply_failure_penalty(player)
        assert player.health == 80
        assert player.stamina == 85
        assert "Lost 20 HP" in msg
        assert "Lost 15 stamina" in msg

    def test_apply_failure_penalty_empty(self):
        player = _make_player()
        q = Quest(id=4000, type="fetch", title="T", description="D", giver_npc_id=1000)
        msg = q.apply_failure_penalty(player)
        assert msg == ""
        assert player.health == 100


class TestCombatQuest:
    def test_check_already_cleared(self):
        q = CombatQuest(id=4000, title="Kill", description="D", giver_npc_id=1000, target_event_id=3000)
        resolved_events = {3000: MagicMock(resolved=True)}
        assert q.check_already_cleared(resolved_events) is True

    def test_check_not_cleared(self):
        q = CombatQuest(id=4000, title="Kill", description="D", giver_npc_id=1000, target_event_id=3000)
        resolved_events = {3000: MagicMock(resolved=False)}
        assert q.check_already_cleared(resolved_events) is False

    def test_check_missing_event(self):
        q = CombatQuest(id=4000, title="Kill", description="D", giver_npc_id=1000, target_event_id=3999)
        assert q.check_already_cleared({}) is False

    def test_target_monster_name(self):
        q = CombatQuest(
            id=4000,
            title="Kill",
            description="D",
            giver_npc_id=1000,
            target_event_id=3000,
            target_monster_name="Goblin Chief",
        )
        assert q.target_monster_name == "Goblin Chief"


class TestDialogueQuest:
    def test_cha_check_pass(self):
        player = _make_player()
        q = DialogueQuest(id=4000, title="Convince", description="D", giver_npc_id=1000, dc=12)
        # Roll 15 + 0 CHA mod (stats at 10 = mod 0) = 15 >= 12
        assert q.check_completion_cha(player, 15) is True

    def test_cha_check_fail(self):
        player = _make_player()
        q = DialogueQuest(id=4000, title="Convince", description="D", giver_npc_id=1000, dc=15)
        # Roll 10 + 0 = 10 < 15
        assert q.check_completion_cha(player, 10) is False

    def test_can_retry_default(self):
        q = DialogueQuest(id=4000, title="T", description="D", giver_npc_id=1000)
        assert q.can_retry is True


class TestMultiStepQuest:
    def test_construction(self):
        q = MultiStepQuest(
            id=4003,
            title="Chain",
            description="D",
            giver_npc_id=1000,
            sub_quest_ids=[4000, 4001, 4002],
        )
        assert q.type == "multi_step"
        assert len(q.sub_quest_ids) == 3
        assert q.current_step == 0

    def test_get_current_sub_quest(self):
        q = MultiStepQuest(
            id=4003,
            title="Chain",
            description="D",
            giver_npc_id=1000,
            sub_quest_ids=[4000, 4001],
        )
        assert q.get_current_sub_quest_id() == 4000

    def test_advance_step(self):
        q = MultiStepQuest(
            id=4003,
            title="Chain",
            description="D",
            giver_npc_id=1000,
            sub_quest_ids=[4000, 4001],
        )
        done = q.advance_step()
        assert done is False
        assert q.current_step == 1
        assert q.get_current_sub_quest_id() == 4001

    def test_advance_completes(self):
        q = MultiStepQuest(
            id=4003,
            title="Chain",
            description="D",
            giver_npc_id=1000,
            sub_quest_ids=[4000],
        )
        done = q.advance_step()
        assert done is True
        assert q.check_completion() is True

    def test_not_complete_initially(self):
        q = MultiStepQuest(
            id=4003,
            title="Chain",
            description="D",
            giver_npc_id=1000,
            sub_quest_ids=[4000, 4001],
        )
        assert q.check_completion() is False

    def test_get_current_returns_none_when_done(self):
        q = MultiStepQuest(
            id=4003,
            title="Chain",
            description="D",
            giver_npc_id=1000,
            sub_quest_ids=[4000],
        )
        q.advance_step()
        assert q.get_current_sub_quest_id() is None


class TestCreateQuestFromData:
    def test_create_fetch(self):
        q = create_quest_from_data(
            {"id": 4000, "type": "fetch", "title": "T", "description": "D", "giver_npc_id": 1000}
        )
        assert isinstance(q, FetchQuest)

    def test_create_multi_step(self):
        q = create_quest_from_data(
            {
                "id": 4000,
                "type": "multi_step",
                "title": "T",
                "description": "D",
                "giver_npc_id": 1000,
                "sub_quest_ids": [4001, 4002],
            }
        )
        assert isinstance(q, MultiStepQuest)
        assert q.sub_quest_ids == [4001, 4002]

    def test_create_with_failure_penalty(self):
        q = create_quest_from_data(
            {
                "id": 4000,
                "type": "combat",
                "title": "T",
                "description": "D",
                "giver_npc_id": 1000,
                "target_event_id": 3000,
                "failure_penalty": {"hp_damage": 10},
            }
        )
        assert isinstance(q, CombatQuest)
        assert q.failure_penalty.hp_damage == 10

    def test_create_dialogue_gated_alias(self):
        q = create_quest_from_data(
            {
                "id": 4000,
                "type": "dialogue_gated",
                "title": "T",
                "description": "D",
                "giver_npc_id": 1000,
            }
        )
        assert isinstance(q, DialogueQuest)

    def test_create_with_story_quest_flag(self):
        q = create_quest_from_data(
            {
                "id": 4000,
                "type": "fetch",
                "title": "T",
                "description": "D",
                "giver_npc_id": 1000,
                "is_story_quest": True,
            }
        )
        assert q.is_story_quest is True


# ---------------------------------------------------------------------------
# Follower tests
# ---------------------------------------------------------------------------


class TestFollowerModel:
    def test_construction(self):
        f = Follower(npc_id=1000, name="Elara")
        assert f.npc_id == 1000
        assert f.name == "Elara"
        assert f.quest_id is None

    def test_get_hint_with_hints(self):
        f = Follower(npc_id=1000, name="Elara", dialogue_hints=["Watch out!", "I see something."])
        hint = f.get_hint()
        assert hint in ["Watch out!", "I see something."]

    def test_get_hint_no_hints(self):
        f = Follower(npc_id=1000, name="Elara")
        hint = f.get_hint()
        assert "Elara" in hint

    def test_should_leave_past_destination(self):
        f = Follower(npc_id=1000, name="Elara", destination_room=2)
        assert f.should_leave(3) is True

    def test_should_not_leave_at_destination(self):
        f = Follower(npc_id=1000, name="Elara", destination_room=2)
        assert f.should_leave(2) is False

    def test_should_not_leave_before_destination(self):
        f = Follower(npc_id=1000, name="Elara", destination_room=2)
        assert f.should_leave(1) is False

    def test_farewell_text(self):
        f = Follower(npc_id=1000, name="Elara", farewell_text="Goodbye, friend!")
        assert f.farewell_text == "Goodbye, friend!"

    def test_max_followers_constant(self):
        assert MAX_FOLLOWERS == 2


# ---------------------------------------------------------------------------
# Player follower management tests
# ---------------------------------------------------------------------------


class TestPlayerFollowers:
    def test_add_follower(self):
        player = _make_player()
        f = Follower(npc_id=1000, name="Elara")
        assert player.add_follower(f) is True
        assert len(player.followers) == 1

    def test_add_follower_max(self):
        player = _make_player()
        player.add_follower(Follower(npc_id=1000, name="A"))
        player.add_follower(Follower(npc_id=1001, name="B"))
        result = player.add_follower(Follower(npc_id=1002, name="C"))
        assert result is False
        assert len(player.followers) == 2

    def test_remove_follower(self):
        player = _make_player()
        player.add_follower(Follower(npc_id=1000, name="A"))
        player.add_follower(Follower(npc_id=1001, name="B"))
        player.remove_follower(1000)
        assert len(player.followers) == 1
        assert player.followers[0].npc_id == 1001

    def test_get_follower_by_quest(self):
        player = _make_player()
        player.add_follower(Follower(npc_id=1000, name="A", quest_id=4000))
        player.add_follower(Follower(npc_id=1001, name="B", quest_id=4001))
        f = player.get_follower_by_quest(4001)
        assert f is not None
        assert f.npc_id == 1001

    def test_get_follower_by_quest_not_found(self):
        player = _make_player()
        assert player.get_follower_by_quest(4999) is None


# ---------------------------------------------------------------------------
# Player quest state tests
# ---------------------------------------------------------------------------


class TestPlayerQuestState:
    def test_fail_quest(self):
        player = _make_player()
        player.accept_quest(4000)
        player.fail_quest(4000)
        assert 4000 not in player.active_quests
        assert 4000 in player.failed_quests

    def test_fail_quest_not_active(self):
        player = _make_player()
        player.fail_quest(4000)
        assert 4000 in player.failed_quests

    def test_quest_state_transitions(self):
        player = _make_player()
        # not_started -> active
        player.accept_quest(4000)
        assert 4000 in player.active_quests
        # active -> completed
        player.complete_quest(4000)
        assert 4000 not in player.active_quests
        assert 4000 in player.completed_quests
        assert player.has_completed(4000)

    def test_quest_state_fail_path(self):
        player = _make_player()
        player.accept_quest(4000)
        player.fail_quest(4000)
        assert 4000 not in player.active_quests
        assert 4000 in player.failed_quests
        assert not player.has_completed(4000)


# ---------------------------------------------------------------------------
# Cross-room quest validation (pipeline helper)
# ---------------------------------------------------------------------------


class TestQuestValidation:
    def test_validate_basic_quest(self):
        from src.generate.pipeline_utils import _validate_quest

        npc_pool = [{"id": 1000, "selected": True}]
        item_placements = [{"item_id": 2000}]
        event_list = [{"id": 3000}]
        quest = {
            "id": 4000,
            "type": "fetch",
            "giver_npc_id": 1000,
            "target_items": [{"item_id": 2000}],
        }
        assert _validate_quest(quest, npc_pool, item_placements, event_list, []) is True

    def test_validate_missing_npc(self):
        from src.generate.pipeline_utils import _validate_quest

        quest = {"id": 4000, "type": "fetch", "giver_npc_id": 1999}
        assert _validate_quest(quest, [], [], [], []) is False

    def test_validate_combat_quest(self):
        from src.generate.pipeline_utils import _validate_quest

        npc_pool = [{"id": 1000, "selected": True}]
        event_list = [{"id": 3000}]
        quest = {"id": 4000, "type": "combat", "giver_npc_id": 1000, "target_event_id": 3000}
        assert _validate_quest(quest, npc_pool, [], event_list, []) is True

    def test_validate_combat_missing_event(self):
        from src.generate.pipeline_utils import _validate_quest

        npc_pool = [{"id": 1000, "selected": True}]
        quest = {"id": 4000, "type": "combat", "giver_npc_id": 1000, "target_event_id": 3999}
        assert _validate_quest(quest, npc_pool, [], [], []) is False

    def test_validate_escort_quest(self):
        from src.generate.pipeline_utils import _validate_quest

        npc_pool = [{"id": 1000, "selected": True}, {"id": 1001, "selected": True}]
        quest = {"id": 4000, "type": "escort", "giver_npc_id": 1000, "escort_npc_id": 1001}
        assert _validate_quest(quest, npc_pool, [], [], []) is True

    def test_validate_delivery_quest(self):
        from src.generate.pipeline_utils import _validate_quest

        npc_pool = [{"id": 1000, "selected": True}, {"id": 1001, "selected": True}]
        item_placements = [{"item_id": 2000}]
        quest = {"id": 4000, "type": "delivery", "giver_npc_id": 1000, "delivery_item_id": 2000, "target_npc_id": 1001}
        assert _validate_quest(quest, npc_pool, item_placements, [], []) is True

    def test_validate_prerequisite_depth_limit(self):
        from src.generate.pipeline_utils import _validate_quest

        npc_pool = [{"id": 1000, "selected": True}]
        existing = [
            {"id": 4000, "type": "fetch", "prerequisite_quest_id": None},
            {"id": 4001, "type": "fetch", "prerequisite_quest_id": 4000},
            {"id": 4002, "type": "fetch", "prerequisite_quest_id": 4001},
        ]
        # depth 3 should fail (max 2)
        quest = {"id": 4003, "type": "fetch", "giver_npc_id": 1000, "prerequisite_quest_id": 4002}
        assert _validate_quest(quest, npc_pool, [], [], existing) is False


# ---------------------------------------------------------------------------
# Quest log tests
# ---------------------------------------------------------------------------


class TestQuestLog:
    def _make_qm(self, quests=None):
        from src.systems.quest_manager import QuestManager

        return QuestManager(quests or {})

    def test_quest_log_empty(self):
        qm = self._make_qm()
        log = qm.get_quest_log()
        assert log == {"active": [], "completed": [], "failed": []}

    def test_quest_log_active(self):
        qm = self._make_qm(
            {
                4000: FetchQuest(
                    id=4000, title="Get mushrooms", description="Find mushrooms", giver_npc_id=1000, status="active"
                ),
            }
        )
        log = qm.get_quest_log()
        assert len(log["active"]) == 1
        assert log["active"][0]["title"] == "Get mushrooms"

    def test_quest_log_story_quest_flagged(self):
        qm = self._make_qm(
            {
                4000: CombatQuest(
                    id=4000,
                    title="Purge cult",
                    description="D",
                    giver_npc_id=1000,
                    status="active",
                    is_story_quest=True,
                    target_event_id=3000,
                ),
            }
        )
        log = qm.get_quest_log()
        assert log["active"][0]["is_story_quest"] is True

    def test_quest_log_multi_step_progress(self):
        qm = self._make_qm(
            {
                4003: MultiStepQuest(
                    id=4003,
                    title="Chain",
                    description="D",
                    giver_npc_id=1000,
                    status="active",
                    sub_quest_ids=[4000, 4001, 4002],
                    current_step=1,
                ),
            }
        )
        log = qm.get_quest_log()
        entry = log["active"][0]
        assert entry["current_step"] == 1
        assert entry["total_steps"] == 3

    def test_quest_log_all_sections(self):
        qm = self._make_qm(
            {
                4000: FetchQuest(id=4000, title="A", description="D", giver_npc_id=1000, status="active"),
                4001: FetchQuest(id=4001, title="B", description="D", giver_npc_id=1000, status="completed"),
                4002: FetchQuest(id=4002, title="C", description="D", giver_npc_id=1000, status="failed"),
            }
        )
        log = qm.get_quest_log()
        assert len(log["active"]) == 1
        assert len(log["completed"]) == 1
        assert len(log["failed"]) == 1


# ---------------------------------------------------------------------------
# QuestManager tests
# ---------------------------------------------------------------------------


class TestQuestManager:
    def _make_qm(self, quests=None, events=None):
        from src.systems.quest_manager import QuestManager

        return QuestManager(quests or {}, events or {})

    def test_kill_quest_already_cleared_at_startup(self):
        """Kill quests are completable out of order — if encounter already cleared."""
        q = CombatQuest(
            id=4000, title="Kill boss", description="D", giver_npc_id=1000, target_event_id=3000, status="not_started"
        )
        event = MagicMock(resolved=True, id=3000)
        qm = self._make_qm({4000: q}, {3000: event})
        player = _make_player()

        qm.check_kill_quests_already_cleared(player)

        assert q.status == "completed"
        assert 4000 in player.completed_quests

    def test_kill_quest_not_cleared_stays_not_started(self):
        q = CombatQuest(
            id=4000, title="Kill boss", description="D", giver_npc_id=1000, target_event_id=3000, status="not_started"
        )
        event = MagicMock(resolved=False, id=3000)
        qm = self._make_qm({4000: q}, {3000: event})
        player = _make_player()

        qm.check_kill_quests_already_cleared(player)

        assert q.status == "not_started"
        assert 4000 not in player.completed_quests

    def test_complete_quest_grants_money(self):
        q = FetchQuest(
            id=4000, title="T", description="D", giver_npc_id=1000, status="active", reward=QuestReward(money=50)
        )
        qm = self._make_qm({4000: q})
        player = _make_player()
        player.accept_quest(4000)

        msg = qm.complete_quest(q, player)

        assert q.status == "completed"
        assert 4000 in player.completed_quests
        assert player.money == 50
        assert "+50 gold" in msg

    def test_fail_quest_applies_penalties(self):
        q = FetchQuest(
            id=4000,
            title="T",
            description="D",
            giver_npc_id=1000,
            status="active",
            failure_penalty=QuestFailurePenalty(hp_damage=15, stamina_damage=10),
        )
        qm = self._make_qm({4000: q})
        player = _make_player()
        player.accept_quest(4000)

        msg = qm.fail_quest(q, player)

        assert q.status == "failed"
        assert 4000 in player.failed_quests
        assert player.health == 85
        assert player.stamina == 90
        assert "Lost 15 HP" in msg

    def test_on_event_resolved_completes_combat_quest(self):
        q = CombatQuest(
            id=4000, title="Kill", description="D", giver_npc_id=1000, target_event_id=3000, status="active"
        )
        qm = self._make_qm({4000: q})
        player = _make_player()
        player.accept_quest(4000)

        result = qm.on_event_resolved(3000, player)

        assert result is q
        assert q.status == "completed"

    def test_multi_step_advancement(self):
        sub1 = FetchQuest(id=4004, title="Step 1", description="D", giver_npc_id=1000, status="active")
        sub2 = FetchQuest(id=4005, title="Step 2", description="D", giver_npc_id=1000, status="not_started")
        parent = MultiStepQuest(
            id=4006, title="Chain", description="D", giver_npc_id=1000, status="active", sub_quest_ids=[4004, 4005]
        )
        qm = self._make_qm({4004: sub1, 4005: sub2, 4006: parent})
        player = _make_player()
        player.accept_quest(4006)
        player.accept_quest(4004)

        qm.complete_quest(sub1, player)

        assert parent.current_step == 1
        assert sub2.status == "active"
        assert 4005 in player.active_quests

    def test_multi_step_completes_parent(self):
        sub1 = FetchQuest(id=4004, title="Step 1", description="D", giver_npc_id=1000, status="active")
        parent = MultiStepQuest(
            id=4006, title="Chain", description="D", giver_npc_id=1000, status="active", sub_quest_ids=[4004]
        )
        qm = self._make_qm({4004: sub1, 4006: parent})
        player = _make_player()
        player.accept_quest(4006)
        player.accept_quest(4004)

        qm.complete_quest(sub1, player)

        assert parent.status == "completed"
        assert 4006 in player.completed_quests

    def test_quest_log_state_transitions(self):
        """Quest log correctly reflects state transitions: active -> completed."""
        q = FetchQuest(id=4000, title="T", description="D", giver_npc_id=1000, status="active")
        qm = self._make_qm({4000: q})
        player = _make_player()
        player.accept_quest(4000)

        log = qm.get_quest_log()
        assert len(log["active"]) == 1
        assert len(log["completed"]) == 0

        qm.complete_quest(q, player)

        log = qm.get_quest_log()
        assert len(log["active"]) == 0
        assert len(log["completed"]) == 1

    def test_quest_log_fail_transition(self):
        q = FetchQuest(id=4000, title="T", description="D", giver_npc_id=1000, status="active")
        qm = self._make_qm({4000: q})
        player = _make_player()
        player.accept_quest(4000)

        qm.fail_quest(q, player)

        log = qm.get_quest_log()
        assert len(log["active"]) == 0
        assert len(log["failed"]) == 1

    def test_try_offer_quest_with_prereq(self):
        q = FetchQuest(
            id=4001, title="T", description="D", giver_npc_id=1000, status="not_started", prerequisite_quest_id=4000
        )
        qm = self._make_qm({4001: q})
        npc = MagicMock(quest_id=4001, id=1000)
        player = _make_player()

        # Prereq not met
        result = qm.try_offer_quest(npc, player)
        assert result is None
        assert q.status == "not_started"

        # Prereq met
        player.completed_quests.append(4000)
        result = qm.try_offer_quest(npc, player)
        assert result is q
        assert q.status == "active"

    def test_check_room_quest_failures(self):
        q = FetchQuest(
            id=4000,
            title="Room task",
            description="D",
            giver_npc_id=1000,
            status="active",
            room_id="room_1",
            failure_penalty=QuestFailurePenalty(hp_damage=5),
        )
        qm = self._make_qm({4000: q})
        player = _make_player()
        player.accept_quest(4000)

        msgs = qm.check_room_quest_failures(player, current_room=2)

        assert len(msgs) == 1
        assert q.status == "failed"
        assert player.health == 95


# ---------------------------------------------------------------------------
# FollowerManager tests
# ---------------------------------------------------------------------------


class TestFollowerManager:
    def _make_fm(self, player=None, npcs=None, quests=None):
        from src.systems.follower_manager import FollowerManager

        return FollowerManager(player or _make_player(), npcs or [], quests or {})

    def test_talk_to_follower_none(self):
        fm = self._make_fm()
        msg = fm.talk_to_follower()
        assert "No followers" in msg

    def test_talk_to_follower_with_hints(self):
        player = _make_player()
        f = Follower(npc_id=1000, name="Elara", dialogue_hints=["Watch out!", "Keep moving."])
        player.add_follower(f)
        fm = self._make_fm(player)
        msg = fm.talk_to_follower()
        assert "Elara" in msg

    def test_talk_to_follower_with_story_context(self):
        player = _make_player()
        f = Follower(npc_id=1000, name="Elara", dialogue_hints=["Watch out!"])
        player.add_follower(f)
        fm = self._make_fm(player)
        msg = fm.talk_to_follower(story_context="The cult grows stronger")
        assert "recent events" in msg.lower()

    def test_follower_joins_via_escort(self):
        from src.models.quest import EscortQuest

        player = _make_player()
        npc = MagicMock(id=1200, personality="brave", profile_image=None, backstory="A brave guard.", description="")
        npc.name = "GuardNPC"
        quest = EscortQuest(
            id=4007,
            title="Escort",
            description="D",
            giver_npc_id=1000,
            escort_npc_id=1200,
            target_zone=[10, 10],
            destination_room=2,
        )
        fm = self._make_fm(player, [npc], {4007: quest})
        msg = fm.start_escort(quest, npc)
        assert msg is not None
        assert "following you" in msg
        assert len(player.followers) == 1
        assert player.followers[0].npc_id == 1200

    def test_follower_leaves_on_room_progression(self):
        """Follower quest fails when player passes drop-off room."""
        player = _make_player()
        q = Quest(
            id=4007,
            type="escort",
            title="Escort quest",
            description="D",
            giver_npc_id=1000,
            status="active",
            failure_penalty=QuestFailurePenalty(hp_damage=10),
        )
        f = Follower(npc_id=1200, name="Elara", quest_id=4007, destination_room=1, farewell_text="Goodbye!")
        player.add_follower(f)
        player.accept_quest(4007)
        fm = self._make_fm(player, [], {4007: q})

        msgs = fm.check_room_progression(current_room=2)

        assert len(msgs) == 1
        assert "Goodbye!" in msgs[0]
        assert "Quest failed" in msgs[0]
        assert len(player.followers) == 0
        assert q.status == "failed"
        assert player.health == 90

    def test_follower_stays_at_destination(self):
        player = _make_player()
        f = Follower(npc_id=1200, name="Elara", quest_id=4007, destination_room=2)
        player.add_follower(f)
        fm = self._make_fm(player)

        msgs = fm.check_room_progression(current_room=2)

        assert len(msgs) == 0
        assert len(player.followers) == 1

    def test_remove_follower_for_quest(self):
        player = _make_player()
        f = Follower(npc_id=1200, name="Elara", quest_id=4007, farewell_text="Until we meet again!")
        player.add_follower(f)
        fm = self._make_fm(player)

        farewell = fm.remove_follower_for_quest(4007)

        assert farewell is not None
        assert "Until we meet again!" in farewell
        assert len(player.followers) == 0

    def test_get_follower_info(self):
        player = _make_player()
        q = Quest(id=4007, type="escort", title="Escort Guard", description="D", giver_npc_id=1000)
        f = Follower(npc_id=1200, name="Guard", quest_id=4007, personality="loyal", destination_room=2)
        player.add_follower(f)
        fm = self._make_fm(player, [], {4007: q})

        info = fm.get_follower_info()

        assert len(info) == 1
        assert info[0]["name"] == "Guard"
        assert info[0]["quest_summary"] == "Escort Guard"
        assert info[0]["destination_room"] == 2


# ---------------------------------------------------------------------------
# Story generation validation tests
# ---------------------------------------------------------------------------


class TestStoryGeneration:
    def test_story_produces_faction(self):
        story = OverarchingStory(
            seed="test",
            title="The Dark Convergence",
            synopsis="A cult threatens the land.",
            faction=Faction(name="Shadow Cult", description="Evil", leader="Lord Kael"),
            escalation_arc=["Whispers", "Encounters", "Assault"],
            climax="Face Lord Kael.",
            final_boss_name="Lord Kael",
        )
        assert story.faction is not None
        assert story.faction.name == "Shadow Cult"

    def test_story_produces_arc(self):
        story = OverarchingStory(
            seed="test",
            escalation_arc=["Low tension", "Rising", "Climax"],
        )
        assert len(story.escalation_arc) == 3

    def test_story_produces_final_boss(self):
        story = OverarchingStory(
            seed="test",
            final_boss_name="Lord Kael",
        )
        assert story.final_boss_name == "Lord Kael"

    def test_story_beats_match_rooms(self):
        beats = [RoomStoryBeat(room_id=f"room_{i}", summary=f"Beat {i}", escalation=i + 1) for i in range(3)]
        story = OverarchingStory(seed="test", beats=beats)
        assert len(story.beats) == 3
        assert story.beats[0].room_id == "room_0"
        assert story.beats[2].escalation == 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(**kwargs) -> PlayerCharacter:
    defaults = {
        "x": 0,
        "y": 0,
        "name": "TestHero",
        "health": 100,
        "stamina": 100,
    }
    defaults.update(kwargs)
    return PlayerCharacter(**defaults)
