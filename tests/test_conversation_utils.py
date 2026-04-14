from unittest.mock import patch, MagicMock
from src.models.npc import StaticNPC
from src.models.quest import Quest, QuestReward
from src.systems.quest_manager import QuestManager
from src.utils.conversation_utils import (
    generate_npc_response, _extract_response, has_dialogue_choices,
    _extract_response_with_cha,
)


def _make_npc(**overrides):
    defaults = dict(x=0, y=0, id=1000, name="Arin", job="hunter",
                    personality="cheerful", hobby="tracking",
                    environment="forest")
    defaults.update(overrides)
    npc = StaticNPC(**defaults)
    npc.prepare()
    return npc


# ---------------------------------------------------------------------------
# Three-branch dispatch in generate_npc_response
# ---------------------------------------------------------------------------

class TestGenerateNpcResponse:
    @patch("src.utils.conversation_utils.generate", return_value="Hello traveler!")
    def test_first_meeting_sets_has_met_player(self, _mock_gen):
        npc = _make_npc()
        assert npc.has_met_player is False

        result = generate_npc_response(npc, "")

        assert npc.has_met_player is True
        assert "Arin" in result
        assert "Hello traveler" in result

    @patch("src.utils.conversation_utils.generate", return_value="Hello traveler!")
    def test_first_meeting_adds_npc_turn(self, _mock_gen):
        npc = _make_npc()
        generate_npc_response(npc, "")

        assert len(npc.interaction_history) == 1
        assert npc.interaction_history[0]["role"] == "npc"

    @patch("src.utils.conversation_utils.generate", return_value="Welcome back!")
    def test_return_visit_greeting(self, _mock_gen):
        npc = _make_npc()
        npc.has_met_player = True

        result = generate_npc_response(npc, "")

        assert "Welcome back" in result
        assert len(npc.interaction_history) == 2
        assert npc.interaction_history[0]["role"] == "user"
        assert npc.interaction_history[1]["role"] == "npc"

    @patch("src.utils.conversation_utils.generate", return_value="I hunt deer.")
    def test_normal_response(self, _mock_gen):
        npc = _make_npc()
        npc.has_met_player = True

        result = generate_npc_response(npc, "What do you do?")

        assert "I hunt deer" in result
        assert npc.interaction_history[0] == {"role": "user", "content": "What do you do?"}
        assert npc.interaction_history[1]["role"] == "npc"

    @patch("src.utils.conversation_utils.generate", return_value="chibi stuff here")
    def test_inappropriate_response_returns_fallback(self, _mock_gen):
        npc = _make_npc()
        npc.has_met_player = True
        fallbacks = [
            "I'm not sure how to respond to that.",
            "Let's talk about something else.",
            "I don't have anything to say about that.",
        ]

        result = generate_npc_response(npc, "say something")

        assert result in fallbacks

    @patch("src.utils.conversation_utils.generate", return_value="Good day!")
    def test_history_accumulates_across_calls(self, _mock_gen):
        npc = _make_npc()
        generate_npc_response(npc, "")
        assert npc.has_met_player is True

        generate_npc_response(npc, "Hello again")
        assert len(npc.interaction_history) >= 3


# ---------------------------------------------------------------------------
# _extract_response
# ---------------------------------------------------------------------------

class TestExtractResponse:
    def test_strips_output_prefix(self):
        raw = "preamble\n##Output: Hello there!\nmore stuff"
        assert _extract_response(raw) == "Hello there!"

    def test_plain_text(self):
        assert _extract_response("Just a response") == "Just a response"

    def test_takes_first_line_only(self):
        raw = "Line one\nLine two\nLine three"
        assert _extract_response(raw) == "Line one"

    def test_strips_whitespace(self):
        assert _extract_response("  padded  ") == "padded"

    def test_output_prefix_takes_last_occurrence(self):
        raw = "##Output: first\n##Output: second"
        assert _extract_response(raw) == "second"


# ---------------------------------------------------------------------------
# has_dialogue_choices
# ---------------------------------------------------------------------------

class TestHasDialogueChoices:
    @patch("src.utils.conversation_utils.GAME_MODE", "offline_static")
    def test_true_when_node_has_choices(self):
        npc = _make_npc()
        npc.dialogue_tree = {
            "nodes": {
                "start": {
                    "prompt": "Hello!",
                    "choices": [
                        {"text": "Hi", "next_node_id": "n2"},
                        {"text": "Bye", "next_node_id": "end"},
                    ],
                },
            },
        }
        assert has_dialogue_choices(npc) is True

    @patch("src.utils.conversation_utils.GAME_MODE", "offline_static")
    def test_false_when_node_has_no_choices(self):
        npc = _make_npc()
        npc.dialogue_tree = {
            "nodes": {
                "start": {"prompt": "Farewell."},
            },
        }
        assert has_dialogue_choices(npc) is False

    @patch("src.utils.conversation_utils.GAME_MODE", "offline_static")
    def test_false_when_no_dialogue_tree(self):
        npc = _make_npc()
        npc.dialogue_tree = None
        assert has_dialogue_choices(npc) is False

    @patch("src.utils.conversation_utils.GAME_MODE", "offline_static")
    def test_false_when_npc_is_none(self):
        assert has_dialogue_choices(None) is False

    @patch("src.utils.conversation_utils.GAME_MODE", "online")
    def test_false_in_online_mode(self):
        npc = _make_npc()
        npc.dialogue_tree = {
            "nodes": {
                "start": {
                    "prompt": "Hello!",
                    "choices": [{"text": "Hi", "next_node_id": "n2"}],
                },
            },
        }
        assert has_dialogue_choices(npc) is False

    @patch("src.utils.conversation_utils.GAME_MODE", "offline_static")
    def test_respects_current_node(self):
        npc = _make_npc()
        npc.dialogue_tree = {
            "_current": "end_node",
            "nodes": {
                "start": {
                    "prompt": "Hello!",
                    "choices": [{"text": "Hi", "next_node_id": "end_node"}],
                },
                "end_node": {"prompt": "Goodbye."},
            },
        }
        assert has_dialogue_choices(npc) is False


# ---------------------------------------------------------------------------
# _extract_response_with_cha
# ---------------------------------------------------------------------------

class TestExtractResponseWithCha:
    def test_parses_cha_json_from_last_line(self):
        raw = 'I am happy to help you.\n{"dc_next": 12, "tone": "friendly"}'
        text, cha = _extract_response_with_cha(raw)
        assert text == "I am happy to help you."
        assert cha == {"dc_next": 12, "tone": "friendly"}

    def test_no_cha_json(self):
        raw = "Just a normal response."
        text, cha = _extract_response_with_cha(raw)
        assert text == "Just a normal response."
        assert cha is None

    def test_malformed_json_ignored(self):
        raw = "Hello there.\n{dc_next: broken}"
        text, cha = _extract_response_with_cha(raw)
        assert "Hello there" in text
        assert cha is None

    def test_json_only_checked_on_last_line(self):
        raw = '{"dc_next": 99, "tone": "rude"}\nActual NPC response here.'
        text, cha = _extract_response_with_cha(raw)
        assert cha is None
        # _extract_response takes the first line, so the JSON text passes through
        assert text is not None

    def test_empty_input(self):
        text, cha = _extract_response_with_cha("")
        assert text == ""
        assert cha is None


# ---------------------------------------------------------------------------
# Dialogue tree swap via QuestManager
# ---------------------------------------------------------------------------

class TestDialogueTreeSwap:
    def _make_quest_npc(self):
        npc = _make_npc(quest_id=4000)
        npc.dialogue_tree_incomplete = {
            "nodes": {
                "start": {"prompt": "Help me!", "choices": [{"text": "OK", "next_node_id": "end"}]},
                "end": {"prompt": "Please hurry!", "choices": []},
            }
        }
        npc.dialogue_tree_complete = {
            "nodes": {
                "start": {"prompt": "Thank you!", "choices": [{"text": "Sure", "next_node_id": "end"}]},
                "end": {"prompt": "I am grateful.", "choices": []},
            }
        }
        npc.dialogue_tree_failed = {
            "nodes": {
                "start": {"prompt": "Oh no...", "choices": [{"text": "Sorry", "next_node_id": "end"}]},
                "end": {"prompt": "Maybe next time.", "choices": []},
            }
        }
        npc.dialogue_tree = npc.dialogue_tree_incomplete
        npc.has_met_player = True
        npc.dialogue_exhausted = True
        return npc

    def test_swap_to_complete_on_success(self):
        npc = self._make_quest_npc()
        quest = Quest(id=4000, type="combat", title="Slay the beast",
                      description="Kill it", giver_npc_id=npc.id)
        quest.status = "active"

        player = MagicMock()
        player.active_quests = [4000]
        player.completed_quests = []

        qm = QuestManager({4000: quest}, npcs=[npc])
        qm.complete_quest(quest, player)

        assert npc.dialogue_tree is npc.dialogue_tree_complete
        assert npc.dialogue_exhausted is False
        assert npc.has_met_player is False
        assert npc.finished_dialogue == "I am grateful."

    def test_swap_to_failed_on_failure(self):
        npc = self._make_quest_npc()
        quest = Quest(id=4000, type="combat", title="Slay the beast",
                      description="Kill it", giver_npc_id=npc.id)
        quest.status = "active"

        player = MagicMock()
        player.active_quests = [4000]

        qm = QuestManager({4000: quest}, npcs=[npc])
        qm.fail_quest(quest, player)

        assert npc.dialogue_tree is npc.dialogue_tree_failed
        assert npc.dialogue_exhausted is False
        assert npc.has_met_player is False
        assert npc.finished_dialogue == "Maybe next time."

    def test_no_swap_when_no_trees(self):
        npc = _make_npc(quest_id=4000)
        original_tree = {"nodes": {"start": {"prompt": "Hi", "choices": []}}}
        npc.dialogue_tree = original_tree

        quest = Quest(id=4000, type="fetch", title="Fetch herbs",
                      description="Get herbs", giver_npc_id=npc.id)
        quest.status = "active"

        player = MagicMock()
        player.active_quests = [4000]
        player.completed_quests = []

        qm = QuestManager({4000: quest}, npcs=[npc])
        qm.complete_quest(quest, player)

        assert npc.dialogue_tree is original_tree


# ---------------------------------------------------------------------------
# Triple-tree mapping (pipeline assigns LLM response to NPC model fields)
# ---------------------------------------------------------------------------

class TestTripleTreeMapping:
    """Verify the mapping logic used in _phase4b_dialogue Step B."""

    SINGLE_TREE = {
        "nodes": {
            "start": {"prompt": "Hello!", "choices": [{"text": "Hi", "next_node_id": "end"}]},
            "end": {"prompt": "Goodbye.", "choices": []},
        }
    }

    TRIPLE_TREE = {
        "incomplete": {
            "nodes": {
                "start": {"prompt": "Help me!", "choices": [{"text": "OK", "next_node_id": "end"}]},
                "end": {"prompt": "Hurry!", "choices": []},
            }
        },
        "complete_success": {
            "nodes": {
                "start": {"prompt": "Thank you!", "choices": [{"text": "Sure", "next_node_id": "end"}]},
                "end": {"prompt": "Grateful.", "choices": []},
            }
        },
        "complete_failure": {
            "nodes": {
                "start": {"prompt": "Oh no.", "choices": [{"text": "Sorry", "next_node_id": "end"}]},
                "end": {"prompt": "Next time.", "choices": []},
            }
        },
    }

    @staticmethod
    def _apply_tree_mapping(npc_dict: dict, tree: dict):
        """Replicate the mapping logic from _phase4b_dialogue Step B."""
        if "error" in tree:
            return
        if "incomplete" in tree:
            inc = tree["incomplete"]
            if isinstance(inc, dict) and "nodes" in inc:
                npc_dict["dialogue_tree"] = inc
                npc_dict["dialogue_tree_incomplete"] = inc
            comp = tree.get("complete_success")
            if isinstance(comp, dict) and "nodes" in comp:
                npc_dict["dialogue_tree_complete"] = comp
            fail = tree.get("complete_failure")
            if isinstance(fail, dict) and "nodes" in fail:
                npc_dict["dialogue_tree_failed"] = fail
        elif "nodes" in tree:
            npc_dict["dialogue_tree"] = tree

    def test_single_tree_sets_dialogue_tree_only(self):
        npc = {"dialogue_tree": None}
        self._apply_tree_mapping(npc, self.SINGLE_TREE)

        assert npc["dialogue_tree"] is self.SINGLE_TREE
        assert "dialogue_tree_incomplete" not in npc
        assert "dialogue_tree_complete" not in npc
        assert "dialogue_tree_failed" not in npc

    def test_triple_tree_maps_all_fields(self):
        npc = {"dialogue_tree": None}
        self._apply_tree_mapping(npc, self.TRIPLE_TREE)

        assert npc["dialogue_tree"] is self.TRIPLE_TREE["incomplete"]
        assert npc["dialogue_tree_incomplete"] is self.TRIPLE_TREE["incomplete"]
        assert npc["dialogue_tree_complete"] is self.TRIPLE_TREE["complete_success"]
        assert npc["dialogue_tree_failed"] is self.TRIPLE_TREE["complete_failure"]

    def test_triple_tree_sets_active_to_incomplete(self):
        npc = {"dialogue_tree": None}
        self._apply_tree_mapping(npc, self.TRIPLE_TREE)

        assert npc["dialogue_tree"]["nodes"]["start"]["prompt"] == "Help me!"

    def test_error_response_leaves_npc_unchanged(self):
        npc = {"dialogue_tree": None}
        self._apply_tree_mapping(npc, {"error": "parse failed"})

        assert npc["dialogue_tree"] is None

    def test_flat_tree_for_quest_npc_fallback(self):
        """If LLM returns flat nodes for a quest NPC, it becomes a single tree."""
        npc = {"dialogue_tree": None}
        self._apply_tree_mapping(npc, self.SINGLE_TREE)

        assert npc["dialogue_tree"] is self.SINGLE_TREE
        assert "dialogue_tree_incomplete" not in npc

    def test_partial_triple_tree_missing_failure(self):
        """If the LLM omits one sub-tree, the others still get mapped."""
        partial = {
            "incomplete": self.TRIPLE_TREE["incomplete"],
            "complete_success": self.TRIPLE_TREE["complete_success"],
        }
        npc = {"dialogue_tree": None}
        self._apply_tree_mapping(npc, partial)

        assert npc["dialogue_tree"] is partial["incomplete"]
        assert npc["dialogue_tree_incomplete"] is partial["incomplete"]
        assert npc["dialogue_tree_complete"] is partial["complete_success"]
        assert "dialogue_tree_failed" not in npc
