"""Lyra 3 music generation via Google GenAI.

Generates .mp3 tracks in parallel alongside portrait generation (Phase 7).
All tracks are synthwave-style, instrumental, loop-friendly.

Track types:
  combat          — story faction-themed, 2 min, Pro model
  maze_{env}      — one per unique environment type, 2 min, Pro model
  puzzle_event    — fixed style, 2 min, Pro model
  start_screen    — fixed style, 2 min, Pro model
  victory         — fixed style, 2 min, Pro model
  game_over       — fixed style, 30 sec, Clip model
"""

import asyncio
import logging
import os

from config import DATA_DIR

logger = logging.getLogger(__name__)

_active_stats = None


def set_stats(stats) -> None:
    """Wire a GenerationStats instance to accumulate music track counts."""
    global _active_stats
    _active_stats = stats


_LYRA_PRO = "lyria-3-pro-preview"
_LYRA_CLIP = "lyria-3-clip-preview"

MUSIC_DIR = os.path.join(DATA_DIR, "music")

# ---------------------------------------------------------------------------
# Hardcoded prompts for story-independent tracks
# ---------------------------------------------------------------------------

FIXED_PROMPTS: dict[str, str] = {
    "puzzle_event": (
        "[0:00-0:20] Single contemplative synth melody, curious and mysterious. "
        "[0:20-1:10] Warm analog pad chords and a light synthesized marimba, playful but thoughtful, "
        "moderate tempo. Feels like solving a riddle with something at stake. "
        "[1:10-1:40] Additional melodic layers build, sense of discovery and forward momentum. "
        "[1:40-2:00] Return to opening melody texture for seamless loop. "
        "Synthwave, retrowave, analog synths. Instrumental only, no vocals. Loop-friendly."
    ),
    "start_screen": (
        "[0:00-0:25] Slow sweeping analog synth pad, minor key, mysterious and cinematic. "
        "Sets an adventurous tone with danger underneath. "
        "[0:25-1:15] Main theme: memorable synthwave hero melody, rich layered pads, "
        "rising heroic energy with an undercurrent of threat. "
        "[1:15-1:50] Lush chord swells, additional synth layers, sense of a vast world waiting. "
        "[1:50-2:00] Fade back to opening pad texture for seamless loop. "
        "Synthwave, retrowave, 80s-inspired video game title screen. "
        "Instrumental only, no vocals. Epic and inviting."
    ),
    "victory": (
        "[0:00-0:15] Triumphant synthwave fanfare: bright lead synth, punchy drum machine, major key. "
        "[0:15-1:10] Full celebration theme: soaring synth melody, driving drum machine, "
        "uplifting chord progression, the feeling of an earned triumph. "
        "[1:10-1:50] Climax: additional layers, anthemic momentum, everything together. "
        "[1:50-2:00] Resolve back to opening fanfare texture for seamless loop. "
        "Synthwave, retrowave. Instrumental only, no vocals. Triumphant victory screen."
    ),
    "game_over": (
        "A melancholic synthwave piece in a minor key. 30 seconds. "
        "Slow analog pad with a single lonely synth melody. "
        "Brief swell of quiet regret, then fades toward near-silence. "
        "Instrumental only, no vocals. Somber and still — the quiet after a journey ends."
    ),
}

# ---------------------------------------------------------------------------
# Async generation core
# ---------------------------------------------------------------------------


async def _generate_track_async(
    client,
    prompt: str,
    track_name: str,
    save_dir: str,
    use_clip: bool,
) -> tuple[str, str | None]:
    """Generate one track asynchronously. Returns (track_name, filepath_or_None)."""
    from google.genai import types

    model = _LYRA_CLIP if use_clip else _LYRA_PRO
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO", "TEXT"],
                ),
            )
            if not response.candidates or not response.candidates[0].content:
                logger.warning(
                    "Lyria track '%s' attempt %d/%d: no audio in response",
                     track_name, attempt + 1, max_attempts
                )
                if attempt < max_attempts - 1:
                    await asyncio.sleep(3 * (attempt + 1))
                continue
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    os.makedirs(save_dir, exist_ok=True)
                    filepath = os.path.join(save_dir, f"{track_name}.mp3")
                    with open(filepath, "wb") as f:
                        f.write(part.inline_data.data)
                    logger.info("Music track saved: %s", filepath)
                    return track_name, filepath
            logger.warning(
                "Lyria track '%s' attempt %d/%d: no audio in response",
                 track_name, attempt + 1, max_attempts
            )
        except Exception as e:
            logger.warning("Lyria track '%s' attempt %d/%d failed: %s", track_name, attempt + 1, max_attempts, e)
        if attempt < max_attempts - 1:
            await asyncio.sleep(3 * (attempt + 1))
    return track_name, None


async def generate_all_music_async(
    prompts: dict[str, str],
    save_dir: str = MUSIC_DIR,
) -> dict[str, str]:
    """Generate all tracks concurrently.

    Parameters
    ----------
    prompts : dict mapping track_name -> prompt string
    save_dir : directory to write .mp3 files

    Returns
    -------
    dict mapping track_name -> filepath (only successful tracks included)
    """
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        logger.warning("GOOGLE_API_KEY not set — skipping music generation.")
        return {}

    from config import MUSIC_BACKEND

    if MUSIC_BACKEND != "api":
        logger.info("MUSIC_BACKEND=%s — skipping Lyria music generation.", MUSIC_BACKEND)
        return {}

    from google import genai

    client = genai.Client(api_key=key)

    tasks = [
        _generate_track_async(
            client,
            prompt,
            name,
            save_dir,
            use_clip=(name == "game_over"),
        )
        for name, prompt in prompts.items()
        if prompt
    ]

    logger.info("Generating %d music tracks in parallel...", len(tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    music_paths: dict[str, str] = {}
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Lyria task raised exception: %s", result)
        elif isinstance(result, tuple) and result[1] is not None:
            name, fp = result
            music_paths[name] = fp

    logger.info("Music generation complete: %d/%d tracks saved.", len(music_paths), len(tasks))
    if _active_stats is not None:
        clip_count = 1 if "game_over" in music_paths else 0
        _active_stats.record_music(
            attempted=len(tasks),
            succeeded=len(music_paths),
            clip_succeeded=clip_count,
        )
    return music_paths


def build_full_prompt_dict(
    llm_prompts: dict[str, str | None],
) -> dict[str, str]:
    """Merge LLM-generated prompts with FIXED_PROMPTS, using fixed as fallback for nulls."""
    merged: dict[str, str] = {}

    for name, prompt in llm_prompts.items():
        if prompt:
            merged[name] = prompt

    for name, prompt in FIXED_PROMPTS.items():
        if name not in merged or not merged.get(name):
            merged[name] = prompt

    return merged
