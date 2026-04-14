"""Tests for GenerationStats: accumulation, cost calculation, serialisation, and timing."""

import re
import time

import pytest

from src.generate.generation_stats import (
    _CLAUDE_INPUT_COST_PER_M,
    _CLAUDE_OUTPUT_COST_PER_M,
    _ELEVENLABS_COST_PER_SFX,
    _FAL_COST_PER_IMAGE,
    _LYRIA_CLIP_COST_PER_TRACK,
    _LYRIA_PRO_COST_PER_TRACK,
    GenerationStats,
)


class TestAccumulation:
    def test_record_llm_calls_accumulates(self):
        stats = GenerationStats()
        stats.record_llm_call(100, 50)
        stats.record_llm_call(100, 50)
        stats.record_llm_call(100, 50)

        assert stats.llm_calls == 3
        assert stats.input_tokens == 300
        assert stats.output_tokens == 150

    def test_record_images_accumulates_across_batches(self):
        stats = GenerationStats()
        stats.record_images(attempted=10, succeeded=9)
        stats.record_images(attempted=5, succeeded=5)

        assert stats.images_attempted == 15
        assert stats.images_succeeded == 14

    def test_record_music_accumulates(self):
        stats = GenerationStats()
        stats.record_music(attempted=8, succeeded=7, clip_succeeded=1)
        stats.record_music(attempted=2, succeeded=2, clip_succeeded=0)

        assert stats.music_attempted == 10
        assert stats.music_succeeded == 9
        assert stats.music_clip_succeeded == 1

    def test_record_sfx_accumulates(self):
        stats = GenerationStats()
        stats.record_sfx(attempted=15, succeeded=14)
        stats.record_sfx(attempted=3, succeeded=3)

        assert stats.sfx_attempted == 18
        assert stats.sfx_succeeded == 17


class TestCostCalculation:
    def test_cost_calculation_api_mode(self):
        stats = GenerationStats(llm_backend="api", image_backend="api")
        stats.record_llm_call(input_tokens=1_000_000, output_tokens=1_000_000)

        expected_llm = _CLAUDE_INPUT_COST_PER_M + _CLAUDE_OUTPUT_COST_PER_M
        assert stats.llm_cost_usd == pytest.approx(expected_llm, rel=1e-6)

    def test_cost_calculation_matches_pricing_formula(self):
        stats = GenerationStats(llm_backend="api", image_backend="api")
        stats.record_llm_call(input_tokens=45_230, output_tokens=18_400)
        stats.record_images(attempted=87, succeeded=85)

        expected_llm = (
            45_230 / 1_000_000 * _CLAUDE_INPUT_COST_PER_M
            + 18_400 / 1_000_000 * _CLAUDE_OUTPUT_COST_PER_M
        )
        expected_img = 85 * _FAL_COST_PER_IMAGE
        assert stats.llm_cost_usd == pytest.approx(expected_llm, rel=1e-6)
        assert stats.image_cost_usd == pytest.approx(expected_img, rel=1e-6)
        assert stats.total_cost_usd == pytest.approx(expected_llm + expected_img, rel=1e-6)

    def test_cost_null_for_local_mode(self):
        stats = GenerationStats(llm_backend="local", image_backend="local")
        stats.record_llm_call(0, 0)
        stats.record_images(10, 10)

        assert stats.llm_cost_usd is None
        assert stats.image_cost_usd is None
        assert stats.total_cost_usd is None

    def test_mixed_backends_partial_cost(self):
        """API LLM + local images: llm cost known, image cost null, total = llm cost."""
        stats = GenerationStats(llm_backend="api", image_backend="local")
        stats.record_llm_call(input_tokens=1_000_000, output_tokens=0)

        assert stats.llm_cost_usd == pytest.approx(_CLAUDE_INPUT_COST_PER_M, rel=1e-6)
        assert stats.image_cost_usd is None
        assert stats.total_cost_usd == pytest.approx(_CLAUDE_INPUT_COST_PER_M, rel=1e-6)

    def test_music_cost_with_clip_and_pro(self):
        """Music cost splits Pro and Clip tracks at their respective rates."""
        stats = GenerationStats(music_backend="api")
        stats.record_music(attempted=8, succeeded=8, clip_succeeded=1)

        expected = 7 * _LYRIA_PRO_COST_PER_TRACK + 1 * _LYRIA_CLIP_COST_PER_TRACK
        assert stats.music_cost_usd == pytest.approx(expected, rel=1e-6)

    def test_music_cost_none_when_backend_is_none(self):
        stats = GenerationStats(music_backend="none")
        stats.record_music(attempted=5, succeeded=5)
        assert stats.music_cost_usd is None

    def test_sfx_cost_calculation(self):
        stats = GenerationStats(sfx_backend="elevenlabs")
        stats.record_sfx(attempted=15, succeeded=14)

        expected = 14 * _ELEVENLABS_COST_PER_SFX
        assert stats.sfx_cost_usd == pytest.approx(expected, rel=1e-6)

    def test_sfx_cost_none_when_backend_is_none(self):
        stats = GenerationStats(sfx_backend="none")
        stats.record_sfx(attempted=10, succeeded=10)
        assert stats.sfx_cost_usd is None

    def test_audio_cost_combines_music_and_sfx(self):
        stats = GenerationStats(music_backend="api", sfx_backend="elevenlabs")
        stats.record_music(attempted=8, succeeded=8, clip_succeeded=1)
        stats.record_sfx(attempted=15, succeeded=15)

        expected_music = 7 * _LYRIA_PRO_COST_PER_TRACK + 1 * _LYRIA_CLIP_COST_PER_TRACK
        expected_sfx = 15 * _ELEVENLABS_COST_PER_SFX
        assert stats.audio_cost_usd == pytest.approx(expected_music + expected_sfx, rel=1e-6)

    def test_audio_cost_none_when_both_backends_none(self):
        stats = GenerationStats(music_backend="none", sfx_backend="none")
        assert stats.audio_cost_usd is None

    def test_total_cost_includes_all_categories(self):
        """total_cost_usd = LLM + images + audio when all backends are active."""
        stats = GenerationStats(
            llm_backend="api", image_backend="api",
            music_backend="api", sfx_backend="elevenlabs",
        )
        stats.record_llm_call(input_tokens=100_000, output_tokens=50_000)
        stats.record_images(attempted=10, succeeded=10)
        stats.record_music(attempted=8, succeeded=8, clip_succeeded=1)
        stats.record_sfx(attempted=15, succeeded=15)

        expected_llm = (
            100_000 / 1_000_000 * _CLAUDE_INPUT_COST_PER_M
            + 50_000 / 1_000_000 * _CLAUDE_OUTPUT_COST_PER_M
        )
        expected_img = 10 * _FAL_COST_PER_IMAGE
        expected_music = 7 * _LYRIA_PRO_COST_PER_TRACK + 1 * _LYRIA_CLIP_COST_PER_TRACK
        expected_sfx = 15 * _ELEVENLABS_COST_PER_SFX
        expected_total = expected_llm + expected_img + expected_music + expected_sfx

        assert stats.total_cost_usd == pytest.approx(expected_total, rel=1e-6)

    def test_total_cost_none_when_all_local(self):
        stats = GenerationStats(
            llm_backend="local", image_backend="local",
            music_backend="none", sfx_backend="none",
        )
        assert stats.total_cost_usd is None


class TestSerialization:
    def test_to_dict_contains_required_keys(self):
        stats = GenerationStats(
            llm_backend="api", image_backend="api",
            music_backend="api", sfx_backend="elevenlabs",
        )
        stats.record_llm_call(100, 50)
        stats.record_images(5, 4)
        stats.record_music(8, 7, clip_succeeded=1)
        stats.record_sfx(15, 14)
        stats.finish()

        d = stats.to_dict()
        required = [
            "llm_backend", "image_backend", "music_backend", "sfx_backend",
            "llm_calls", "input_tokens", "output_tokens", "total_tokens",
            "images_attempted", "images_succeeded",
            "music_attempted", "music_succeeded",
            "sfx_attempted", "sfx_succeeded",
            "llm_cost_usd", "image_cost_usd", "audio_cost_usd", "total_cost_usd",
            "generation_time_seconds", "generation_time_human",
        ]
        for key in required:
            assert key in d, f"Missing key: {key}"

    def test_to_dict_total_tokens_is_sum(self):
        stats = GenerationStats()
        stats.record_llm_call(300, 150)
        d = stats.to_dict()
        assert d["total_tokens"] == 450

    def test_to_dict_local_costs_are_none(self):
        stats = GenerationStats(
            llm_backend="local", image_backend="local",
            music_backend="none", sfx_backend="none",
        )
        stats.finish()
        d = stats.to_dict()
        assert d["llm_cost_usd"] is None
        assert d["image_cost_usd"] is None
        assert d["audio_cost_usd"] is None
        assert d["total_cost_usd"] is None

    def test_to_dict_api_costs_are_rounded(self):
        stats = GenerationStats(llm_backend="api", image_backend="api")
        stats.record_llm_call(input_tokens=123, output_tokens=456)
        stats.record_images(1, 1)
        stats.finish()
        d = stats.to_dict()
        assert isinstance(d["llm_cost_usd"], float)
        assert isinstance(d["image_cost_usd"], float)
        assert d["llm_cost_usd"] == round(d["llm_cost_usd"], 4)

    def test_to_dict_audio_cost_rounded(self):
        stats = GenerationStats(music_backend="api", sfx_backend="elevenlabs")
        stats.record_music(attempted=3, succeeded=3, clip_succeeded=1)
        stats.record_sfx(attempted=5, succeeded=5)
        stats.finish()
        d = stats.to_dict()
        assert isinstance(d["audio_cost_usd"], float)
        assert d["audio_cost_usd"] == round(d["audio_cost_usd"], 4)


class TestTiming:
    def test_generation_time_human_format(self):
        stats = GenerationStats()
        stats.finish()
        assert re.match(r"^\d+m \d{2}s$", stats.generation_time_human), (
            f"Unexpected format: {stats.generation_time_human!r}"
        )

    def test_finish_freezes_elapsed_time(self):
        stats = GenerationStats()
        stats.finish()
        t1 = stats.generation_seconds
        time.sleep(0.05)
        assert stats.generation_seconds == t1

    def test_generation_time_seconds_nonnegative(self):
        stats = GenerationStats()
        stats.finish()
        assert stats.generation_seconds >= 0.0

    def test_known_duration_formats_correctly(self):
        """Directly set generation_seconds to verify human format."""
        stats = GenerationStats()
        stats.generation_seconds = 1580.0  # 26m 20s
        assert stats.generation_time_human == "26m 20s"

    def test_sub_minute_duration_formats_correctly(self):
        stats = GenerationStats()
        stats.generation_seconds = 45.0  # 0m 45s
        assert stats.generation_time_human == "0m 45s"
