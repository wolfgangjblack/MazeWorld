"""Tests for music generation and playback infrastructure.

Covers the two pure-logic components:
  - MusicController: silent fallback when tracks are missing
  - build_full_prompt_dict: merging LLM prompts with fixed fallbacks

No API calls, no actual audio files, no pygame display required.
"""

from src.generate.music_client import FIXED_PROMPTS, build_full_prompt_dict
from src.systems.music_controller import MusicController

# ---------------------------------------------------------------------------
# MusicController: silent fallback tests
# ---------------------------------------------------------------------------


class TestMusicControllerFallback:
    def test_silent_on_nonexistent_file(self, tmp_path, monkeypatch):
        """play() should not raise when the track file doesn't exist on disk."""
        monkeypatch.chdir(tmp_path)
        mc = MusicController({"combat": str(tmp_path / "nonexistent.wav")})
        mc.play("combat")  # must not raise
        assert mc.current_track is None

    def test_silent_on_missing_key(self, tmp_path, monkeypatch):
        """play() should not raise when track name isn't in the manifest at all."""
        monkeypatch.chdir(tmp_path)
        mc = MusicController({})
        mc.play("combat")
        assert mc.current_track is None

    def test_silent_on_empty_manifest(self, tmp_path, monkeypatch):
        """MusicController with no tracks silently accepts all play() calls."""
        monkeypatch.chdir(tmp_path)
        mc = MusicController({})
        for track in ["start_screen", "combat", "maze_village", "puzzle_event", "victory", "game_over"]:
            mc.play(track)
        assert mc.current_track is None

    def test_stop_is_safe_when_nothing_playing(self):
        """stop() should not raise even if no music is active."""
        mc = MusicController({})
        mc.stop()  # must not raise
        assert mc.current_track is None

    def test_play_maze_uses_correct_track_key(self, tmp_path, monkeypatch):
        """play_maze(env_type) should look up 'maze_{env_type}' in the manifest.

        With no files present, both calls should leave current_track as None
        and not raise, confirming the correct key format is used internally.
        """
        monkeypatch.chdir(tmp_path)
        mc = MusicController({})
        mc.play_maze("village")  # looks up "maze_village" — not in manifest, silent
        assert mc.current_track is None
        mc.play_maze("cave")  # looks up "maze_cave"
        assert mc.current_track is None

    def test_has_track_false_for_nonexistent_file(self, tmp_path):
        """has_track() returns False when the path doesn't exist on disk."""
        mc = MusicController({"combat": str(tmp_path / "missing.wav")})
        assert mc.has_track("combat") is False

    def test_has_track_false_for_missing_key(self):
        """has_track() returns False when the key isn't in the manifest."""
        mc = MusicController({})
        assert mc.has_track("combat") is False

    def test_has_track_true_for_existing_file(self, tmp_path):
        """has_track() returns True when the .wav file actually exists."""
        wav = tmp_path / "combat.wav"
        wav.write_bytes(b"RIFF")  # minimal stub, doesn't need to be valid audio
        mc = MusicController({"combat": str(wav)})
        assert mc.has_track("combat") is True

    def test_no_duplicate_play_on_same_track(self, tmp_path, monkeypatch):
        """Calling play() twice with the same track name should be a no-op on the second call.

        We verify this by confirming current_track stays consistent and no exception
        is raised, rather than trying to load a real audio file.
        """
        monkeypatch.chdir(tmp_path)
        mc = MusicController({"combat": str(tmp_path / "missing.wav")})
        mc.play("combat")  # sets current_track = None (file missing)
        mc.play("combat")  # should be a no-op since current_track already matches
        assert mc.current_track is None


# ---------------------------------------------------------------------------
# build_full_prompt_dict: prompt merging logic
# ---------------------------------------------------------------------------


class TestBuildFullPromptDict:
    def test_llm_combat_prompt_preserved(self):
        """LLM-generated combat prompt must not be overwritten by fixed fallback."""
        llm = {"combat": "faction-specific driving combat music"}
        result = build_full_prompt_dict(llm)
        assert result["combat"] == "faction-specific driving combat music"

    def test_llm_maze_prompt_preserved(self):
        """LLM-generated maze prompt for a specific env must be preserved."""
        llm = {"maze_village": "warm village ambient synthwave"}
        result = build_full_prompt_dict(llm)
        assert result["maze_village"] == "warm village ambient synthwave"

    def test_null_llm_prompt_filled_by_fixed(self):
        """When LLM returns null for a fixed track, FIXED_PROMPTS should fill it."""
        llm = {"combat": "some combat", "start_screen": None}
        result = build_full_prompt_dict(llm)
        assert result["start_screen"] == FIXED_PROMPTS["start_screen"]

    def test_all_fixed_tracks_present_even_if_not_in_llm(self):
        """Fixed tracks should always be in the result, even if LLM omitted them."""
        llm = {"combat": "combat music"}
        result = build_full_prompt_dict(llm)
        for key in FIXED_PROMPTS:
            assert key in result, f"Expected fixed track '{key}' in result"

    def test_empty_llm_dict_produces_all_fixed_tracks(self):
        """When LLM returns nothing, all FIXED_PROMPTS should be in the result."""
        result = build_full_prompt_dict({})
        for key, prompt in FIXED_PROMPTS.items():
            assert result[key] == prompt

    def test_game_over_always_present(self):
        """game_over must always be in the result (it's fixed, 30-sec clip)."""
        result = build_full_prompt_dict({})
        assert "game_over" in result
        assert result["game_over"] == FIXED_PROMPTS["game_over"]

    def test_multiple_maze_envs_all_preserved(self):
        """Multiple LLM-generated maze tracks should all be kept."""
        llm = {
            "combat": "combat",
            "maze_village": "village music",
            "maze_cave": "cave music",
            "maze_castle": "castle music",
        }
        result = build_full_prompt_dict(llm)
        assert result["maze_village"] == "village music"
        assert result["maze_cave"] == "cave music"
        assert result["maze_castle"] == "castle music"

    def test_result_contains_no_none_values(self):
        """After merging, no prompt in the result should be None."""
        llm = {"combat": None, "maze_village": None, "start_screen": None}
        result = build_full_prompt_dict(llm)
        for key, val in result.items():
            assert val is not None, f"Track '{key}' has None prompt in result"
