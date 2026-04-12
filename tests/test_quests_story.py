"""Phase 6 tests: Quests, Story & Followers."""

from unittest.mock import MagicMock

from src.models.story import OverarchingStory, Faction, RoomStoryBeat
from src.models.quest import (
    Quest, FetchQuest, DialogueQuest,
    CombatQuest, MultiStepQuest, QuestReward, QuestFailurePenalty,
    create_quest_from_data, QUEST_TYPE_MAP,
)
from src.models.follower import Follower, MAX_FOLLOWERS
from src.models.player import PlayerCharacter


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
                RoomStoryBeat(room_id="room_0", summary="Cult symbols appear",
                              faction_presence="Graffiti on walls", escalation=1),
                RoomStoryBeat(room_id="room_1", summary="Cult ambush",
                              faction_presence="Armed cultists", escalation=3),
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
        r = QuestReward(item_id=5, xp=10, money=50, story_info="A clue", door_reveal=True)
        assert r.money == 50
        assert r.story_info == "A clue"
        assert r.door_reveal is True

    def test_quest_failure_penalty(self):
        p = QuestFailurePenalty(hp_damage=10, stamina_damage=5)
        assert p.hp_damage == 10

    def test_quest_is_story_quest(self):
        q = Quest(id="q1", type="fetch", title="T", description="D",
                  giver_npc_id=100, is_story_quest=True)
        assert q.is_story_quest is True

    def test_quest_room_id(self):
        q = Quest(id="q1", type="fetch", title="T", description="D",
                  giver_npc_id=100, room_id="room_0")
        assert q.room_id == "room_0"

    def test_quest_time_gate(self):
        q = Quest(id="q1", type="fetch", title="T", description="D",
                  giver_npc_id=100, time_gate="night")
        assert q.time_gate == "night"

    def test_apply_failure_penalty(self):
        player = _make_player()
        q = Quest(
            id="q1", type="fetch", title="T", description="D", giver_npc_id=100,
            failure_penalty=QuestFailurePenalty(hp_damage=20, stamina_damage=15),
        )
        msg = q.apply_failure_penalty(player)
        assert player.health == 80
        assert player.stamina == 85
        assert "Lost 20 HP" in msg
        assert "Lost 15 stamina" in msg

    def test_apply_failure_penalty_empty(self):
        player = _make_player()
        q = Quest(id="q1", type="fetch", title="T", description="D", giver_npc_id=100)
        msg = q.apply_failure_penalty(player)
        assert msg == ""
        assert player.health == 100


class TestCombatQuest:
    def test_check_already_cleared(self):
        q = CombatQuest(id="q1", title="Kill", description="D",
                        giver_npc_id=100, target_event_id="evt_001")
        resolved_events = {"evt_001": MagicMock(resolved=True)}
        assert q.check_already_cleared(resolved_events) is True

    def test_check_not_cleared(self):
        q = CombatQuest(id="q1", title="Kill", description="D",
                        giver_npc_id=100, target_event_id="evt_001")
        resolved_events = {"evt_001": MagicMock(resolved=False)}
        assert q.check_already_cleared(resolved_events) is False

    def test_check_missing_event(self):
        q = CombatQuest(id="q1", title="Kill", description="D",
                        giver_npc_id=100, target_event_id="evt_999")
        assert q.check_already_cleared({}) is False

    def test_target_monster_name(self):
        q = CombatQuest(id="q1", title="Kill", description="D",
                        giver_npc_id=100, target_event_id="evt_001",
                        target_monster_name="Goblin Chief")
        assert q.target_monster_name == "Goblin Chief"


class TestDialogueQuest:
    def test_cha_check_pass(self):
        player = _make_player()
        q = DialogueQuest(id="q1", title="Convince", description="D",
                          giver_npc_id=100, dc=12)
        # Roll 15 + 0 CHA mod (stats at 10 = mod 0) = 15 >= 12
        assert q.check_completion_cha(player, 15) is True

    def test_cha_check_fail(self):
        player = _make_player()
        q = DialogueQuest(id="q1", title="Convince", description="D",
                          giver_npc_id=100, dc=15)
        # Roll 10 + 0 = 10 < 15
        assert q.check_completion_cha(player, 10) is False

    def test_can_retry_default(self):
        q = DialogueQuest(id="q1", title="T", description="D", giver_npc_id=100)
        assert q.can_retry is True


class TestMultiStepQuest:
    def test_construction(self):
        q = MultiStepQuest(
            id="mq1", title="Chain", description="D", giver_npc_id=100,
            sub_quest_ids=["q1", "q2", "q3"],
        )
        assert q.type == "multi_step"
        assert len(q.sub_quest_ids) == 3
        assert q.current_step == 0

    def test_get_current_sub_quest(self):
        q = MultiStepQuest(
            id="mq1", title="Chain", description="D", giver_npc_id=100,
            sub_quest_ids=["q1", "q2"],
        )
        assert q.get_current_sub_quest_id() == "q1"

    def test_advance_step(self):
        q = MultiStepQuest(
            id="mq1", title="Chain", description="D", giver_npc_id=100,
            sub_quest_ids=["q1", "q2"],
        )
        done = q.advance_step()
        assert done is False
        assert q.current_step == 1
        assert q.get_current_sub_quest_id() == "q2"

    def test_advance_completes(self):
        q = MultiStepQuest(
            id="mq1", title="Chain", description="D", giver_npc_id=100,
            sub_quest_ids=["q1"],
        )
        done = q.advance_step()
        assert done is True
        assert q.check_completion() is True

    def test_not_complete_initially(self):
        q = MultiStepQuest(
            id="mq1", title="Chain", description="D", giver_npc_id=100,
            sub_quest_ids=["q1", "q2"],
        )
        assert q.check_completion() is False

    def test_get_current_returns_none_when_done(self):
        q = MultiStepQuest(
            id="mq1", title="Chain", description="D", giver_npc_id=100,
            sub_quest_ids=["q1"],
        )
        q.advance_step()
        assert q.get_current_sub_quest_id() is None


class TestCreateQuestFromData:
    def test_create_fetch(self):
        q = create_quest_from_data({"id": "q1", "type": "fetch", "title": "T",
                                    "description": "D", "giver_npc_id": 100})
        assert isinstance(q, FetchQuest)

    def test_create_multi_step(self):
        q = create_quest_from_data({
            "id": "q1", "type": "multi_step", "title": "T",
            "description": "D", "giver_npc_id": 100,
            "sub_quest_ids": ["a", "b"],
        })
        assert isinstance(q, MultiStepQuest)
        assert q.sub_quest_ids == ["a", "b"]

    def test_create_with_failure_penalty(self):
        q = create_quest_from_data({
            "id": "q1", "type": "combat", "title": "T",
            "description": "D", "giver_npc_id": 100,
            "target_event_id": "evt_001",
            "failure_penalty": {"hp_damage": 10},
        })
        assert isinstance(q, CombatQuest)
        assert q.failure_penalty.hp_damage == 10

    def test_create_dialogue_gated_alias(self):
        q = create_quest_from_data({
            "id": "q1", "type": "dialogue_gated", "title": "T",
            "description": "D", "giver_npc_id": 100,
        })
        assert isinstance(q, DialogueQuest)

    def test_create_with_story_quest_flag(self):
        q = create_quest_from_data({
            "id": "q1", "type": "fetch", "title": "T",
            "description": "D", "giver_npc_id": 100,
            "is_story_quest": True,
        })
        assert q.is_story_quest is True


# ---------------------------------------------------------------------------
# Follower tests
# ---------------------------------------------------------------------------

class TestFollowerModel:
    def test_construction(self):
        f = Follower(npc_id=100, name="Elara")
        assert f.npc_id == 100
        assert f.name == "Elara"
        assert f.quest_id is None

    def test_get_hint_with_hints(self):
        f = Follower(npc_id=100, name="Elara",
                     dialogue_hints=["Watch out!", "I see something."])
        hint = f.get_hint()
        assert hint in ["Watch out!", "I see something."]

    def test_get_hint_no_hints(self):
        f = Follower(npc_id=100, name="Elara")
        hint = f.get_hint()
        assert "Elara" in hint

    def test_should_leave_past_destination(self):
        f = Follower(npc_id=100, name="Elara", destination_room=2)
        assert f.should_leave(3) is True

    def test_should_not_leave_at_destination(self):
        f = Follower(npc_id=100, name="Elara", destination_room=2)
        assert f.should_leave(2) is False

    def test_should_not_leave_before_destination(self):
        f = Follower(npc_id=100, name="Elara", destination_room=2)
        assert f.should_leave(1) is False

    def test_farewell_text(self):
        f = Follower(npc_id=100, name="Elara", farewell_text="Goodbye, friend!")
        assert f.farewell_text == "Goodbye, friend!"

    def test_max_followers_constant(self):
        assert MAX_FOLLOWERS == 2


# ---------------------------------------------------------------------------
# Player follower management tests
# ---------------------------------------------------------------------------

class TestPlayerFollowers:
    def test_add_follower(self):
        player = _make_player()
        f = Follower(npc_id=100, name="Elara")
        assert player.add_follower(f) is True
        assert len(player.followers) == 1

    def test_add_follower_max(self):
        player = _make_player()
        player.add_follower(Follower(npc_id=100, name="A"))
        player.add_follower(Follower(npc_id=101, name="B"))
        result = player.add_follower(Follower(npc_id=102, name="C"))
        assert result is False
        assert len(player.followers) == 2

    def test_remove_follower(self):
        player = _make_player()
        player.add_follower(Follower(npc_id=100, name="A"))
        player.add_follower(Follower(npc_id=101, name="B"))
        player.remove_follower(100)
        assert len(player.followers) == 1
        assert player.followers[0].npc_id == 101

    def test_get_follower_by_quest(self):
        player = _make_player()
        player.add_follower(Follower(npc_id=100, name="A", quest_id="q1"))
        player.add_follower(Follower(npc_id=101, name="B", quest_id="q2"))
        f = player.get_follower_by_quest("q2")
        assert f is not None
        assert f.npc_id == 101

    def test_get_follower_by_quest_not_found(self):
        player = _make_player()
        assert player.get_follower_by_quest("q999") is None


# ---------------------------------------------------------------------------
# Player quest state tests
# ---------------------------------------------------------------------------

class TestPlayerQuestState:
    def test_fail_quest(self):
        player = _make_player()
        player.accept_quest("q1")
        player.fail_quest("q1")
        assert "q1" not in player.active_quests
        assert "q1" in player.failed_quests

    def test_fail_quest_not_active(self):
        player = _make_player()
        player.fail_quest("q1")
        assert "q1" in player.failed_quests

    def test_quest_state_transitions(self):
        player = _make_player()
        # not_started -> active
        player.accept_quest("q1")
        assert "q1" in player.active_quests
        # active -> completed
        player.complete_quest("q1")
        assert "q1" not in player.active_quests
        assert "q1" in player.completed_quests
        assert player.has_completed("q1")

    def test_quest_state_fail_path(self):
        player = _make_player()
        player.accept_quest("q1")
        player.fail_quest("q1")
        assert "q1" not in player.active_quests
        assert "q1" in player.failed_quests
        assert not player.has_completed("q1")


# ---------------------------------------------------------------------------
# Cross-room quest validation (pipeline helper)
# ---------------------------------------------------------------------------

class TestQuestValidation:
    def test_validate_basic_quest(self):
        from src.generate.pipeline_utils import _validate_quest
        npc_pool = [{"id": 100, "selected": True}]
        item_placements = [{"item_id": 200}]
        event_list = [{"id": "evt_001"}]
        quest = {
            "id": "q_000", "type": "fetch", "giver_npc_id": 100,
            "target_items": [{"item_id": 200}],
        }
        assert _validate_quest(quest, npc_pool, item_placements, event_list, []) is True

    def test_validate_missing_npc(self):
        from src.generate.pipeline_utils import _validate_quest
        quest = {"id": "q_000", "type": "fetch", "giver_npc_id": 999}
        assert _validate_quest(quest, [], [], [], []) is False

    def test_validate_combat_quest(self):
        from src.generate.pipeline_utils import _validate_quest
        npc_pool = [{"id": 100, "selected": True}]
        event_list = [{"id": "evt_001"}]
        quest = {"id": "q_000", "type": "combat", "giver_npc_id": 100,
                 "target_event_id": "evt_001"}
        assert _validate_quest(quest, npc_pool, [], event_list, []) is True

    def test_validate_combat_missing_event(self):
        from src.generate.pipeline_utils import _validate_quest
        npc_pool = [{"id": 100, "selected": True}]
        quest = {"id": "q_000", "type": "combat", "giver_npc_id": 100,
                 "target_event_id": "evt_999"}
        assert _validate_quest(quest, npc_pool, [], [], []) is False

    def test_validate_escort_quest(self):
        from src.generate.pipeline_utils import _validate_quest
        npc_pool = [{"id": 100, "selected": True}, {"id": 101, "selected": True}]
        quest = {"id": "q_000", "type": "escort", "giver_npc_id": 100,
                 "escort_npc_id": 101}
        assert _validate_quest(quest, npc_pool, [], [], []) is True

    def test_validate_delivery_quest(self):
        from src.generate.pipeline_utils import _validate_quest
        npc_pool = [{"id": 100, "selected": True}, {"id": 101, "selected": True}]
        item_placements = [{"item_id": 200}]
        quest = {"id": "q_000", "type": "delivery", "giver_npc_id": 100,
                 "delivery_item_id": 200, "target_npc_id": 101}
        assert _validate_quest(quest, npc_pool, item_placements, [], []) is True

    def test_validate_prerequisite_depth_limit(self):
        from src.generate.pipeline_utils import _validate_quest
        npc_pool = [{"id": 100, "selected": True}]
        existing = [
            {"id": "q_000", "type": "fetch", "prerequisite_quest_id": None},
            {"id": "q_001", "type": "fetch", "prerequisite_quest_id": "q_000"},
            {"id": "q_002", "type": "fetch", "prerequisite_quest_id": "q_001"},
        ]
        # depth 3 should fail (max 2)
        quest = {"id": "q_003", "type": "fetch", "giver_npc_id": 100,
                 "prerequisite_quest_id": "q_002"}
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
        qm = self._make_qm({
            "q1": FetchQuest(id="q1", title="Get mushrooms", description="Find mushrooms",
                             giver_npc_id=100, status="active"),
        })
        log = qm.get_quest_log()
        assert len(log["active"]) == 1
        assert log["active"][0]["title"] == "Get mushrooms"

    def test_quest_log_story_quest_flagged(self):
        qm = self._make_qm({
            "q1": CombatQuest(id="q1", title="Purge cult", description="D",
                              giver_npc_id=100, status="active",
                              is_story_quest=True, target_event_id="evt_001"),
        })
        log = qm.get_quest_log()
        assert log["active"][0]["is_story_quest"] is True

    def test_quest_log_multi_step_progress(self):
        qm = self._make_qm({
            "mq1": MultiStepQuest(id="mq1", title="Chain", description="D",
                                  giver_npc_id=100, status="active",
                                  sub_quest_ids=["q1", "q2", "q3"], current_step=1),
        })
        log = qm.get_quest_log()
        entry = log["active"][0]
        assert entry["current_step"] == 1
        assert entry["total_steps"] == 3

    def test_quest_log_all_sections(self):
        qm = self._make_qm({
            "q1": FetchQuest(id="q1", title="A", description="D",
                             giver_npc_id=100, status="active"),
            "q2": FetchQuest(id="q2", title="B", description="D",
                             giver_npc_id=100, status="completed"),
            "q3": FetchQuest(id="q3", title="C", description="D",
                             giver_npc_id=100, status="failed"),
        })
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
        q = CombatQuest(id="q1", title="Kill boss", description="D",
                        giver_npc_id=100, target_event_id="evt_001",
                        status="not_started")
        event = MagicMock(resolved=True, id="evt_001")
        qm = self._make_qm({"q1": q}, {"evt_001": event})
        player = _make_player()

        qm.check_kill_quests_already_cleared(player)

        assert q.status == "completed"
        assert "q1" in player.completed_quests

    def test_kill_quest_not_cleared_stays_not_started(self):
        q = CombatQuest(id="q1", title="Kill boss", description="D",
                        giver_npc_id=100, target_event_id="evt_001",
                        status="not_started")
        event = MagicMock(resolved=False, id="evt_001")
        qm = self._make_qm({"q1": q}, {"evt_001": event})
        player = _make_player()

        qm.check_kill_quests_already_cleared(player)

        assert q.status == "not_started"
        assert "q1" not in player.completed_quests

    def test_complete_quest_grants_money(self):
        q = FetchQuest(id="q1", title="T", description="D",
                       giver_npc_id=100, status="active",
                       reward=QuestReward(money=50))
        qm = self._make_qm({"q1": q})
        player = _make_player()
        player.accept_quest("q1")

        msg = qm.complete_quest(q, player)

        assert q.status == "completed"
        assert "q1" in player.completed_quests
        assert player.money == 50
        assert "+50 gold" in msg

    def test_fail_quest_applies_penalties(self):
        q = FetchQuest(id="q1", title="T", description="D",
                       giver_npc_id=100, status="active",
                       failure_penalty=QuestFailurePenalty(hp_damage=15, stamina_damage=10))
        qm = self._make_qm({"q1": q})
        player = _make_player()
        player.accept_quest("q1")

        msg = qm.fail_quest(q, player)

        assert q.status == "failed"
        assert "q1" in player.failed_quests
        assert player.health == 85
        assert player.stamina == 90
        assert "Lost 15 HP" in msg

    def test_on_event_resolved_completes_combat_quest(self):
        q = CombatQuest(id="q1", title="Kill", description="D",
                        giver_npc_id=100, target_event_id="evt_001",
                        status="active")
        qm = self._make_qm({"q1": q})
        player = _make_player()
        player.accept_quest("q1")

        result = qm.on_event_resolved("evt_001", player)

        assert result is q
        assert q.status == "completed"

    def test_multi_step_advancement(self):
        sub1 = FetchQuest(id="s1", title="Step 1", description="D",
                          giver_npc_id=100, status="active")
        sub2 = FetchQuest(id="s2", title="Step 2", description="D",
                          giver_npc_id=100, status="not_started")
        parent = MultiStepQuest(id="mq", title="Chain", description="D",
                                giver_npc_id=100, status="active",
                                sub_quest_ids=["s1", "s2"])
        qm = self._make_qm({"s1": sub1, "s2": sub2, "mq": parent})
        player = _make_player()
        player.accept_quest("mq")
        player.accept_quest("s1")

        qm.complete_quest(sub1, player)

        assert parent.current_step == 1
        assert sub2.status == "active"
        assert "s2" in player.active_quests

    def test_multi_step_completes_parent(self):
        sub1 = FetchQuest(id="s1", title="Step 1", description="D",
                          giver_npc_id=100, status="active")
        parent = MultiStepQuest(id="mq", title="Chain", description="D",
                                giver_npc_id=100, status="active",
                                sub_quest_ids=["s1"])
        qm = self._make_qm({"s1": sub1, "mq": parent})
        player = _make_player()
        player.accept_quest("mq")
        player.accept_quest("s1")

        qm.complete_quest(sub1, player)

        assert parent.status == "completed"
        assert "mq" in player.completed_quests

    def test_quest_log_state_transitions(self):
        """Quest log correctly reflects state transitions: active -> completed."""
        q = FetchQuest(id="q1", title="T", description="D",
                       giver_npc_id=100, status="active")
        qm = self._make_qm({"q1": q})
        player = _make_player()
        player.accept_quest("q1")

        log = qm.get_quest_log()
        assert len(log["active"]) == 1
        assert len(log["completed"]) == 0

        qm.complete_quest(q, player)

        log = qm.get_quest_log()
        assert len(log["active"]) == 0
        assert len(log["completed"]) == 1

    def test_quest_log_fail_transition(self):
        q = FetchQuest(id="q1", title="T", description="D",
                       giver_npc_id=100, status="active")
        qm = self._make_qm({"q1": q})
        player = _make_player()
        player.accept_quest("q1")

        qm.fail_quest(q, player)

        log = qm.get_quest_log()
        assert len(log["active"]) == 0
        assert len(log["failed"]) == 1

    def test_try_offer_quest_with_prereq(self):
        q = FetchQuest(id="q2", title="T", description="D",
                       giver_npc_id=100, status="not_started",
                       prerequisite_quest_id="q1")
        qm = self._make_qm({"q2": q})
        npc = MagicMock(quest_id="q2", id=100)
        player = _make_player()

        # Prereq not met
        result = qm.try_offer_quest(npc, player)
        assert result is None
        assert q.status == "not_started"

        # Prereq met
        player.completed_quests.append("q1")
        result = qm.try_offer_quest(npc, player)
        assert result is q
        assert q.status == "active"

    def test_check_room_quest_failures(self):
        q = FetchQuest(id="q1", title="Room task", description="D",
                       giver_npc_id=100, status="active", room_id="room_1",
                       failure_penalty=QuestFailurePenalty(hp_damage=5))
        qm = self._make_qm({"q1": q})
        player = _make_player()
        player.accept_quest("q1")

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
        f = Follower(npc_id=100, name="Elara",
                     dialogue_hints=["Watch out!", "Keep moving."])
        player.add_follower(f)
        fm = self._make_fm(player)
        msg = fm.talk_to_follower()
        assert "Elara" in msg

    def test_talk_to_follower_with_story_context(self):
        player = _make_player()
        f = Follower(npc_id=100, name="Elara",
                     dialogue_hints=["Watch out!"])
        player.add_follower(f)
        fm = self._make_fm(player)
        msg = fm.talk_to_follower(story_context="The cult grows stronger")
        assert "recent events" in msg.lower()

    def test_follower_joins_via_escort(self):
        from src.models.quest import EscortQuest
        player = _make_player()
        npc = MagicMock(id=200, personality="brave")
        npc.name = "GuardNPC"  # MagicMock 'name' kwarg is reserved
        quest = EscortQuest(
            id="eq1", title="Escort", description="D",
            giver_npc_id=100, escort_npc_id=200,
            target_zone=[10, 10], destination_room=2)
        fm = self._make_fm(player, [npc], {"eq1": quest})
        msg = fm.start_escort(quest, npc)
        assert msg is not None
        assert "following you" in msg
        assert len(player.followers) == 1
        assert player.followers[0].npc_id == 200

    def test_follower_leaves_on_room_progression(self):
        """Follower quest fails when player passes drop-off room."""
        player = _make_player()
        q = Quest(id="eq1", type="escort", title="Escort quest", description="D",
                  giver_npc_id=100, status="active",
                  failure_penalty=QuestFailurePenalty(hp_damage=10))
        f = Follower(npc_id=200, name="Elara", quest_id="eq1",
                     destination_room=1, farewell_text="Goodbye!")
        player.add_follower(f)
        player.accept_quest("eq1")
        fm = self._make_fm(player, [], {"eq1": q})

        msgs = fm.check_room_progression(current_room=2)

        assert len(msgs) == 1
        assert "Goodbye!" in msgs[0]
        assert "Quest failed" in msgs[0]
        assert len(player.followers) == 0
        assert q.status == "failed"
        assert player.health == 90

    def test_follower_stays_at_destination(self):
        player = _make_player()
        f = Follower(npc_id=200, name="Elara", quest_id="eq1",
                     destination_room=2)
        player.add_follower(f)
        fm = self._make_fm(player)

        msgs = fm.check_room_progression(current_room=2)

        assert len(msgs) == 0
        assert len(player.followers) == 1

    def test_remove_follower_for_quest(self):
        player = _make_player()
        f = Follower(npc_id=200, name="Elara", quest_id="eq1",
                     farewell_text="Until we meet again!")
        player.add_follower(f)
        fm = self._make_fm(player)

        farewell = fm.remove_follower_for_quest("eq1")

        assert farewell is not None
        assert "Until we meet again!" in farewell
        assert len(player.followers) == 0

    def test_get_follower_info(self):
        player = _make_player()
        q = Quest(id="eq1", type="escort", title="Escort Guard", description="D",
                  giver_npc_id=100)
        f = Follower(npc_id=200, name="Guard", quest_id="eq1",
                     personality="loyal", destination_room=2)
        player.add_follower(f)
        fm = self._make_fm(player, [], {"eq1": q})

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
        beats = [
            RoomStoryBeat(room_id=f"room_{i}", summary=f"Beat {i}", escalation=i+1)
            for i in range(3)
        ]
        story = OverarchingStory(seed="test", beats=beats)
        assert len(story.beats) == 3
        assert story.beats[0].room_id == "room_0"
        assert story.beats[2].escalation == 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(**kwargs) -> PlayerCharacter:
    defaults = {
        "x": 0, "y": 0, "name": "TestHero",
        "health": 100, "stamina": 100,
    }
    defaults.update(kwargs)
    return PlayerCharacter(**defaults)
