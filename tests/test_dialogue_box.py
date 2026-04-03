from unittest.mock import patch, MagicMock
from src.models.npc import StaticNPC
from src.models.dialogue_box import DialogueBox


def _make_npc(**overrides):
    defaults = dict(x=0, y=0, id=1, name="Arin", job="hunter",
                    personality="cheerful", hobby="tracking",
                    environment="forest")
    defaults.update(overrides)
    npc = StaticNPC(**defaults)
    npc.prepare()
    return npc


def _make_db():
    return DialogueBox(screen=MagicMock(), font=MagicMock())


# ---------------------------------------------------------------------------
# get_display_window  (scroll math — the original bug)
# ---------------------------------------------------------------------------

class TestGetDisplayWindow:
    def test_content_fits_starts_at_zero(self):
        db = _make_db()
        start, end = db.get_display_window(total_lines=3, max_lines=10)
        assert start == 0
        assert end == 10

    def test_auto_scroll_top(self):
        db = _make_db()
        db.auto_scroll = True
        db._scroll_target = "top"
        start, _ = db.get_display_window(total_lines=20, max_lines=5)
        assert start == 0
        assert db.auto_scroll is False

    def test_auto_scroll_bottom(self):
        db = _make_db()
        db.auto_scroll = True
        db._scroll_target = "bottom"
        start, end = db.get_display_window(total_lines=20, max_lines=5)
        assert start == 15
        assert end == 20
        assert db.auto_scroll is False

    def test_clamps_position_above_max(self):
        db = _make_db()
        db.scroll_position = 999
        start, _ = db.get_display_window(total_lines=10, max_lines=5)
        assert start == 5
        assert db.scroll_position == 5

    def test_clamps_position_below_zero(self):
        db = _make_db()
        db.scroll_position = -5
        start, _ = db.get_display_window(total_lines=10, max_lines=5)
        assert start == 0
        assert db.scroll_position == 0

    def test_max_scroll_computed_correctly(self):
        db = _make_db()
        db.get_display_window(total_lines=12, max_lines=4)
        assert db.max_scroll == 8

    def test_max_scroll_zero_when_all_fits(self):
        db = _make_db()
        db.get_display_window(total_lines=3, max_lines=10)
        assert db.max_scroll == 0

    def test_auto_scroll_consumed_after_one_call(self):
        db = _make_db()
        db.auto_scroll = True
        db._scroll_target = "bottom"
        db.get_display_window(total_lines=20, max_lines=5)
        assert db.auto_scroll is False
        db.get_display_window(total_lines=20, max_lines=5)
        assert db.scroll_position == 15


# ---------------------------------------------------------------------------
# scroll_up / scroll_down
# ---------------------------------------------------------------------------

class TestScrollUpDown:
    def test_scroll_up_decrements(self):
        db = _make_db()
        db.scroll_position = 5
        db.max_scroll = 10
        db.scroll_up()
        assert db.scroll_position == 4

    def test_scroll_up_clamps_at_zero(self):
        db = _make_db()
        db.scroll_position = 0
        db.scroll_up()
        assert db.scroll_position == 0

    def test_scroll_down_increments(self):
        db = _make_db()
        db.scroll_position = 3
        db.max_scroll = 10
        db.scroll_down()
        assert db.scroll_position == 4

    def test_scroll_down_clamps_at_max(self):
        db = _make_db()
        db.scroll_position = 10
        db.max_scroll = 10
        db.scroll_down()
        assert db.scroll_position == 10

    def test_scroll_disables_auto_scroll(self):
        db = _make_db()
        db.auto_scroll = True
        db.scroll_up()
        assert db.auto_scroll is False

        db.auto_scroll = True
        db.scroll_down()
        assert db.auto_scroll is False


# ---------------------------------------------------------------------------
# _build_display_history
# ---------------------------------------------------------------------------

class TestBuildDisplayHistory:
    def test_formats_npc_and_user_turns(self):
        npc = _make_npc(name="Arin")
        npc.add_turn("npc", "Hello traveler")
        npc.add_turn("user", "Hi there")
        npc.add_turn("npc", "Welcome")

        db = _make_db()
        lines = db._build_display_history(npc)
        assert lines == [
            "Arin: Hello traveler",
            "You: Hi there",
            "Arin: Welcome",
        ]

    def test_empty_history(self):
        npc = _make_npc()
        db = _make_db()
        assert db._build_display_history(npc) == []

    def test_ignores_unknown_roles(self):
        npc = _make_npc(name="Arin")
        npc.add_turn("system", "Internal note")
        npc.add_turn("npc", "Hello")

        db = _make_db()
        lines = db._build_display_history(npc)
        assert lines == ["Arin: Hello"]


# ---------------------------------------------------------------------------
# start_dialogue
# ---------------------------------------------------------------------------

class TestStartDialogue:
    @patch("src.models.dialogue_box.generate_npc_response", return_value="Arin: Hello!")
    def test_first_meeting_state(self, _mock_gen):
        npc = _make_npc()
        npc.has_met_player = False
        db = _make_db()
        db.start_dialogue(npc)

        assert db.dialogue_active is True
        assert db.generating is True
        assert db.input_active is False
        assert db.current_npc is npc
        assert db._scroll_target == "top"
        assert db.auto_scroll is True

    @patch("src.models.dialogue_box.generate_npc_response", return_value="Arin: Welcome back!")
    def test_return_visit_scrolls_to_bottom(self, _mock_gen):
        npc = _make_npc()
        npc.has_met_player = True
        db = _make_db()
        db.start_dialogue(npc)

        assert db._scroll_target == "bottom"

    @patch("src.models.dialogue_box.generate_npc_response", return_value="Arin: Welcome back!")
    def test_return_visit_rebuilds_history(self, _mock_gen):
        npc = _make_npc(name="Arin")
        npc.has_met_player = True
        npc.add_turn("npc", "Previous greeting")
        npc.add_turn("user", "Previous reply")

        db = _make_db()
        db.start_dialogue(npc)

        assert db.conversation_history == [
            "Arin: Previous greeting",
            "You: Previous reply",
        ]


# ---------------------------------------------------------------------------
# update_dialogue
# ---------------------------------------------------------------------------

class TestUpdateDialogue:
    @patch("src.models.dialogue_box.generate_npc_response", return_value="Arin: Sure thing")
    def test_appends_user_message_and_starts_generation(self, _mock_gen):
        npc = _make_npc()
        db = _make_db()
        db.dialogue_active = True
        db.current_npc = npc
        db.conversation_history = ["Arin: Hello"]

        db.update_dialogue("How are you?")

        assert db.conversation_history == ["Arin: Hello", "You: How are you?"]
        assert db.generating is True
        assert db.input_active is False
        assert db.user_message == ""
        assert db._scroll_target == "bottom"


# ---------------------------------------------------------------------------
# end_dialogue
# ---------------------------------------------------------------------------

class TestEndDialogue:
    def test_resets_all_state(self):
        db = _make_db()
        db.dialogue_active = True
        db.generating = True
        db.conversation_history = ["something"]
        db.scroll_position = 10
        db.auto_scroll = True
        db.current_npc = _make_npc()
        db.user_message = "partial typing"

        db.end_dialogue()

        assert db.dialogue_active is False
        assert db.generating is False
        assert db.conversation_history == []
        assert db.scroll_position == 0
        assert db.auto_scroll is False
        assert db.current_npc is None
        assert db.user_message == ""


# ---------------------------------------------------------------------------
# check_generation (async)
# ---------------------------------------------------------------------------

class TestCheckGeneration:
    @patch("src.models.dialogue_box.generate_npc_response", return_value="Arin: Reply")
    def test_picks_up_result_when_thread_done(self, _mock_gen):
        npc = _make_npc()
        db = _make_db()
        db.generating = True
        db._start_generation(npc, "hello")
        db._generation_thread.join()

        db.check_generation()

        assert db.generating is False
        assert db.input_active is True
        assert "Arin: Reply" in db.conversation_history
        assert db.auto_scroll is True
        assert db._scroll_target == "bottom"
        assert db._generation_thread is None

    def test_noop_when_not_generating(self):
        db = _make_db()
        db.generating = False
        db.check_generation()
        assert db.conversation_history == []

    def test_noop_when_thread_still_alive(self):
        db = _make_db()
        db.generating = True
        db._generation_thread = MagicMock()
        db._generation_thread.is_alive.return_value = True

        db.check_generation()

        assert db.generating is True
        assert db.conversation_history == []


# ---------------------------------------------------------------------------
# set_item_message / clear_item_message
# ---------------------------------------------------------------------------

class TestItemMessage:
    def test_set_item_message(self):
        db = _make_db()
        db.current_npc = _make_npc()
        db.set_item_message("You found a potion!")

        assert db.item_message == "You found a potion!"
        assert db.current_npc is None
        assert db.input_active is False

    def test_clear_item_message(self):
        db = _make_db()
        db.item_message = "old message"
        db.input_active = False
        db.clear_item_message()

        assert db.item_message is None
        assert db.input_active is True
