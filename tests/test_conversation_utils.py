from unittest.mock import patch
from src.models.npc import StaticNPC
from src.utils.conversation_utils import generate_npc_response, _extract_response


def _make_npc(**overrides):
    defaults = dict(x=0, y=0, id=1, name="Arin", job="hunter",
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
