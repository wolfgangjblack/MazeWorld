"""Tests for SFX generation and playback infrastructure.

Covers:
  - FIXED_SFX_PROMPTS: structural contract validation
  - build_full_sfx_prompt_dict: merging LLM prompts with fixed fallbacks
  - SFXController: silent fallback when files are missing
  - SFXController: key-mapping logic for weapons, spells, and ambience

No API calls, no actual audio files, no pygame display required.
"""

from unittest.mock import patch

from src.generate.sfx_client import FIXED_SFX_PROMPTS, build_full_sfx_prompt_dict
from src.systems.sfx_controller import SFXController

# ---------------------------------------------------------------------------
# FIXED_SFX_PROMPTS: structural contract
# ---------------------------------------------------------------------------


class TestFixedSfxPromptStructure:
    def test_all_entries_have_required_keys(self):
        for name, spec in FIXED_SFX_PROMPTS.items():
            assert "prompt" in spec, f"'{name}' missing 'prompt'"
            assert "duration" in spec, f"'{name}' missing 'duration'"
            assert "loop" in spec, f"'{name}' missing 'loop'"

    def test_prompt_values_are_nonempty_strings(self):
        for name, spec in FIXED_SFX_PROMPTS.items():
            assert isinstance(spec["prompt"], str), f"'{name}' prompt is not a string"
            assert len(spec["prompt"]) > 0, f"'{name}' prompt is empty"

    def test_duration_values_are_positive_numbers(self):
        for name, spec in FIXED_SFX_PROMPTS.items():
            assert isinstance(spec["duration"], (int, float)), f"'{name}' duration not numeric"
            assert spec["duration"] > 0, f"'{name}' duration must be positive"

    def test_loop_values_are_bools(self):
        for name, spec in FIXED_SFX_PROMPTS.items():
            assert isinstance(spec["loop"], bool), f"'{name}' loop is not a bool"


# ---------------------------------------------------------------------------
# build_full_sfx_prompt_dict: prompt merging logic
# ---------------------------------------------------------------------------


class TestBuildFullSfxPromptDict:
    def test_llm_dynamic_prompt_preserved(self):
        llm = {"weapon_heavy_swing": {"prompt": "dark heavy sword swoosh", "duration": 0.5, "loop": False}}
        result = build_full_sfx_prompt_dict(llm)
        assert result["weapon_heavy_swing"]["prompt"] == "dark heavy sword swoosh"

    def test_null_llm_entry_filled_by_fixed(self):
        llm = {"weapon_heavy_swing": {"prompt": "swoosh", "duration": 0.5, "loop": False}, "dice_roll": None}
        result = build_full_sfx_prompt_dict(llm)
        assert result["dice_roll"] == FIXED_SFX_PROMPTS["dice_roll"]

    def test_empty_prompt_entry_filled_by_fixed(self):
        llm = {"dice_roll": {"prompt": "", "duration": 1, "loop": False}}
        result = build_full_sfx_prompt_dict(llm)
        assert result["dice_roll"] == FIXED_SFX_PROMPTS["dice_roll"]

    def test_all_fixed_present_when_llm_empty(self):
        result = build_full_sfx_prompt_dict({})
        for key in FIXED_SFX_PROMPTS:
            assert key in result, f"Expected fixed SFX '{key}' in result"

    def test_all_fixed_present_when_llm_is_none(self):
        result = build_full_sfx_prompt_dict(None)
        for key, spec in FIXED_SFX_PROMPTS.items():
            assert result[key] == spec

    def test_result_contains_no_none_values(self):
        llm = {"dice_roll": None, "item_pickup": None}
        result = build_full_sfx_prompt_dict(llm)
        for key, val in result.items():
            assert val is not None, f"SFX '{key}' has None value in result"

    def test_multiple_llm_dynamic_entries_preserved(self):
        llm = {
            "weapon_light_swing": {"prompt": "quick slash", "duration": 0.3, "loop": False},
            "spell_damage_single_cast": {"prompt": "fireball whoosh", "duration": 1, "loop": False},
            "ambience_cave": {"prompt": "dripping echo", "duration": 10, "loop": True},
        }
        result = build_full_sfx_prompt_dict(llm)
        assert result["weapon_light_swing"]["prompt"] == "quick slash"
        assert result["spell_damage_single_cast"]["prompt"] == "fireball whoosh"
        assert result["ambience_cave"]["prompt"] == "dripping echo"

    def test_llm_does_not_overwrite_fixed_when_missing_prompt_key(self):
        llm = {"dice_roll": {"duration": 2, "loop": False}}
        result = build_full_sfx_prompt_dict(llm)
        assert result["dice_roll"] == FIXED_SFX_PROMPTS["dice_roll"]


# ---------------------------------------------------------------------------
# SFXController: silent fallback tests
# ---------------------------------------------------------------------------


class TestSFXControllerFallback:
    def test_play_silent_on_nonexistent_file(self, tmp_path):
        sfx = SFXController({"player_death": str(tmp_path / "nonexistent.mp3")})
        sfx.play("player_death")

    def test_play_silent_on_missing_key(self):
        sfx = SFXController({})
        sfx.play("player_death")

    def test_play_silent_on_empty_manifest(self):
        sfx = SFXController({})
        for name in ["player_take_damage", "player_death", "item_pickup", "door_open", "dice_roll", "event_complete"]:
            sfx.play(name)

    def test_stop_ambience_safe_when_nothing_playing(self):
        sfx = SFXController({})
        sfx.stop_ambience()
        assert sfx.current_ambience is None

    def test_has_sfx_false_for_nonexistent_file(self, tmp_path):
        sfx = SFXController({"dice_roll": str(tmp_path / "missing.mp3")})
        assert sfx.has_sfx("dice_roll") is False

    def test_has_sfx_false_for_missing_key(self):
        sfx = SFXController({})
        assert sfx.has_sfx("dice_roll") is False

    def test_has_sfx_true_for_existing_file(self, tmp_path):
        mp3 = tmp_path / "dice_roll.mp3"
        mp3.write_bytes(b"ID3")
        sfx = SFXController({"dice_roll": str(mp3)})
        assert sfx.has_sfx("dice_roll") is True

    def test_play_ambience_silent_on_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sfx = SFXController({})
        sfx.play_ambience("village")
        assert sfx.current_ambience is None


# ---------------------------------------------------------------------------
# SFXController: key-mapping logic
# ---------------------------------------------------------------------------


class TestSFXControllerKeyMapping:
    def _make_controller(self):
        return SFXController({})

    def test_weapon_swing_key(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_weapon_swing("heavy")
            mock_play.assert_called_once_with("weapon_heavy_swing")

    def test_weapon_swing_wild_normalizes_to_light(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_weapon_swing("wild")
            mock_play.assert_called_once_with("weapon_light_swing")

    def test_weapon_hit_key(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_weapon_hit("simple")
            mock_play.assert_called_once_with("weapon_simple_hit")

    def test_weapon_hit_wild_normalizes_to_light(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_weapon_hit("wild")
            mock_play.assert_called_once_with("weapon_light_hit")

    def test_spell_damage_single_cast(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_spell("damage_single", "cast")
            mock_play.assert_called_once_with("spell_damage_single_cast")

    def test_spell_damage_multi_impact(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_spell("damage_multi", "impact")
            mock_play.assert_called_once_with("spell_damage_multi_impact")

    def test_spell_heal_cast(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_spell("heal", "cast")
            mock_play.assert_called_once_with("spell_heal_cast")

    def test_spell_buff_stat_maps_to_buff_cast(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_spell("buff_stat")
            mock_play.assert_called_once_with("spell_buff_cast")

    def test_spell_buff_sustain_maps_to_reveal_cast(self):
        sfx = self._make_controller()
        with patch.object(sfx, "play") as mock_play:
            sfx.play_spell("buff_sustain")
            mock_play.assert_called_once_with("spell_reveal_cast")

    def test_play_ambience_looks_up_prefixed_key(self):
        sfx = self._make_controller()
        with patch.object(sfx, "_get_sound", return_value=None) as mock_get:
            sfx.play_ambience("village")
            mock_get.assert_called_once_with("ambience_village")

    def test_play_ambience_skips_duplicate(self):
        sfx = self._make_controller()
        sfx._current_ambience = "ambience_cave"
        with patch.object(sfx, "_get_sound") as mock_get:
            sfx.play_ambience("cave")
            mock_get.assert_not_called()
