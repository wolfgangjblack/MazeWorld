"""Tracks LLM tokens, image counts, audio counts, and wall-clock time for a generation run.

A GenerationStats instance is created at the start of generate_world(), wired to the
LLM, image, music, and SFX backends via set_stats(), and written to manifest.json at
completion.
"""

import time
from dataclasses import dataclass, field

# Anthropic claude-sonnet-4 pricing (USD per million tokens)
_CLAUDE_INPUT_COST_PER_M = 3.00
_CLAUDE_OUTPUT_COST_PER_M = 15.00

# fal-ai/nano-banana-pro pricing (USD per image, flat rate from fal.ai/pricing)
_FAL_COST_PER_IMAGE = 0.0398

# Google Lyria 3 pricing (USD per track via Gemini API)
_LYRIA_PRO_COST_PER_TRACK = 0.08
_LYRIA_CLIP_COST_PER_TRACK = 0.04

# ElevenLabs SFX pricing (USD per generation, Pro plan overage rate)
_ELEVENLABS_COST_PER_SFX = 0.04


@dataclass
class GenerationStats:
    """Accumulates stats during a single generate_world() run."""

    llm_backend: str = "local"    # "api" | "local"
    image_backend: str = "local"  # "api" | "local"
    music_backend: str = "none"   # "none" | "api"

    # LLM usage
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    # Image usage
    images_attempted: int = 0
    images_succeeded: int = 0

    # Music usage (Google Lyria)
    music_attempted: int = 0
    music_succeeded: int = 0
    music_clip_succeeded: int = 0

    # SFX usage (ElevenLabs)
    sfx_attempted: int = 0
    sfx_succeeded: int = 0

    # Timing — frozen by finish()
    generation_seconds: float = 0.0
    _start_time: float = field(default_factory=time.monotonic, repr=False)

    # ---------------------------------------------------------------------------
    # Accumulation
    # ---------------------------------------------------------------------------

    def record_llm_call(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Called after each LLM call with the token counts from the response."""
        self.llm_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def record_images(self, attempted: int, succeeded: int) -> None:
        """Called after each portrait batch with attempt and success counts."""
        self.images_attempted += attempted
        self.images_succeeded += succeeded

    def record_music(self, attempted: int, succeeded: int, clip_succeeded: int = 0) -> None:
        """Called after music generation with attempt and success counts.

        clip_succeeded counts tracks generated with the cheaper Lyria Clip model
        (e.g. game_over). The remainder are billed at the Pro model rate.
        """
        self.music_attempted += attempted
        self.music_succeeded += succeeded
        self.music_clip_succeeded += clip_succeeded

    def record_sfx(self, attempted: int, succeeded: int) -> None:
        """Called after SFX generation with attempt and success counts."""
        self.sfx_attempted += attempted
        self.sfx_succeeded += succeeded

    def finish(self) -> None:
        """Freeze elapsed wall-clock time. Call once before writing the manifest."""
        self.generation_seconds = time.monotonic() - self._start_time

    # ---------------------------------------------------------------------------
    # Cost computation (properties — recomputed each time)
    # ---------------------------------------------------------------------------

    @property
    def llm_cost_usd(self) -> float | None:
        """USD cost for LLM calls. None when using the local backend."""
        if self.llm_backend != "api":
            return None
        return (
            self.input_tokens / 1_000_000 * _CLAUDE_INPUT_COST_PER_M
            + self.output_tokens / 1_000_000 * _CLAUDE_OUTPUT_COST_PER_M
        )

    @property
    def image_cost_usd(self) -> float | None:
        """USD cost for image generation. None when using the local backend."""
        if self.image_backend != "api":
            return None
        return self.images_succeeded * _FAL_COST_PER_IMAGE

    @property
    def music_cost_usd(self) -> float | None:
        """USD cost for music generation. None when music backend is 'none'."""
        if self.music_backend == "none":
            return None
        pro_count = self.music_succeeded - self.music_clip_succeeded
        return (
            pro_count * _LYRIA_PRO_COST_PER_TRACK
            + self.music_clip_succeeded * _LYRIA_CLIP_COST_PER_TRACK
        )

    @property
    def sfx_cost_usd(self) -> float | None:
        """USD cost for SFX generation. None when music backend is 'none'."""
        if self.music_backend == "none":
            return None
        return self.sfx_succeeded * _ELEVENLABS_COST_PER_SFX

    @property
    def audio_cost_usd(self) -> float | None:
        """Combined music + SFX cost. None when both backends are 'none'."""
        music = self.music_cost_usd
        sfx = self.sfx_cost_usd
        if music is None and sfx is None:
            return None
        return (music or 0.0) + (sfx or 0.0)

    @property
    def total_cost_usd(self) -> float | None:
        """Sum of LLM + image + audio costs. None only when ALL backends are local/none."""
        costs = [self.llm_cost_usd, self.image_cost_usd, self.audio_cost_usd]
        if all(c is None for c in costs):
            return None
        return sum(c or 0.0 for c in costs)

    @property
    def generation_time_human(self) -> str:
        """Wall-clock time as 'Xm YYs' string."""
        mins, secs = divmod(int(self.generation_seconds), 60)
        return f"{mins}m {secs:02d}s"

    # ---------------------------------------------------------------------------
    # Output
    # ---------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return all stats as a JSON-serialisable dict for the manifest."""
        return {
            "llm_backend": self.llm_backend,
            "image_backend": self.image_backend,
            "music_backend": self.music_backend,
            "llm_calls": self.llm_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "images_attempted": self.images_attempted,
            "images_succeeded": self.images_succeeded,
            "music_attempted": self.music_attempted,
            "music_succeeded": self.music_succeeded,
            "sfx_attempted": self.sfx_attempted,
            "sfx_succeeded": self.sfx_succeeded,
            "llm_cost_usd": (
                round(self.llm_cost_usd, 4) if self.llm_cost_usd is not None else None
            ),
            "image_cost_usd": (
                round(self.image_cost_usd, 4) if self.image_cost_usd is not None else None
            ),
            "audio_cost_usd": (
                round(self.audio_cost_usd, 4) if self.audio_cost_usd is not None else None
            ),
            "total_cost_usd": (
                round(self.total_cost_usd, 4) if self.total_cost_usd is not None else None
            ),
            "generation_time_seconds": round(self.generation_seconds, 1),
            "generation_time_human": self.generation_time_human,
        }

    def log_summary(self, logger) -> None:
        """Log a human-readable stats summary to the given logger."""
        d = self.to_dict()
        logger.info("=== Generation Stats ===")
        logger.info("  Time: %s (%.0fs)", d["generation_time_human"],
                    d["generation_time_seconds"])
        logger.info(
            "  LLM: %d calls, %s tokens (%s in / %s out) [%s]",
            d["llm_calls"],
            f"{d['total_tokens']:,}",
            f"{d['input_tokens']:,}",
            f"{d['output_tokens']:,}",
            d["llm_backend"],
        )
        logger.info(
            "  Images: %d/%d generated [%s]",
            d["images_succeeded"],
            d["images_attempted"],
            d["image_backend"],
        )
        logger.info(
            "  Music: %d/%d tracks [%s]",
            d["music_succeeded"],
            d["music_attempted"],
            d["music_backend"],
        )
        logger.info(
            "  SFX: %d/%d effects [%s]",
            d["sfx_succeeded"],
            d["sfx_attempted"],
            d["music_backend"],
        )
        if d["total_cost_usd"] is not None:
            logger.info(
                "  Estimated cost: $%.4f (LLM: $%.4f, Images: $%.4f, Audio: $%.4f)",
                d["total_cost_usd"],
                d["llm_cost_usd"] or 0.0,
                d["image_cost_usd"] or 0.0,
                d["audio_cost_usd"] or 0.0,
            )
        else:
            logger.info("  Cost: local generation (no API charges)")
