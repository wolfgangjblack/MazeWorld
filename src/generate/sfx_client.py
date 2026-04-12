"""ElevenLabs SFX generation for MazeWorld.

Generates .mp3 sound effects in parallel alongside music generation (Phase 7).
Dynamic prompts (weapons, spells, ambience) are written by the LLM using
story/faction/element context.  Fixed prompts (UI, dice, item use) are
hardcoded here.

SFX categories:
  weapon_{type}_{swing|hit}  — per weapon_type (light/heavy/simple)
  spell_{type}_cast/impact   — per spell_type, element-aware
  ambience_{env}             — one per generated environment, looped
  player_take_damage         — universal hit-taken
  player_death               — player dies
  item_pickup                — pick up item from maze
  door_open / door_reveal    — door interactions
  event_complete             — puzzle/event reward sting
  dice_roll                  — universal dice check
  item_food / item_drink / item_tool — consumable use
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_active_stats = None


def set_stats(stats) -> None:
    """Wire a GenerationStats instance to accumulate SFX generation counts."""
    global _active_stats
    _active_stats = stats

SFX_DIR = "data/sfx"

# ---------------------------------------------------------------------------
# Hardcoded prompts for universal (non-story-dependent) sounds
# ---------------------------------------------------------------------------

FIXED_SFX_PROMPTS: dict[str, dict] = {
    "player_take_damage": {
        "prompt": (
            "A short, punchy impact sound of a person being struck in combat. "
            "Dull thud with a slight grunt of pain. Fantasy video game hit sound. "
            "Quick and visceral."
        ),
        "duration": 0.5,
        "loop": False,
    },
    "player_death": {
        "prompt": (
            "A dramatic death sound: body collapsing, final exhale, with a low "
            "reverberating tone that fades to silence. Dark fantasy video game "
            "death sound. Somber and final."
        ),
        "duration": 2,
        "loop": False,
    },
    "item_pickup": {
        "prompt": (
            "A bright, satisfying item pickup chime. Short crystalline ding "
            "with a slight sparkle tail. Retro fantasy video game pickup sound."
        ),
        "duration": 0.5,
        "loop": False,
    },
    "door_open": {
        "prompt": (
            "A heavy wooden door creaking open with stone scraping. Medieval "
            "dungeon door opening. Deep, weighty, with echo."
        ),
        "duration": 1.5,
        "loop": False,
    },
    "door_reveal": {
        "prompt": (
            "A magical reveal sound: rising shimmer with a deep resonant tone, "
            "like a hidden passage appearing. Fantasy discovery sound with "
            "mystical energy building to a soft chime."
        ),
        "duration": 2,
        "loop": False,
    },
    "event_complete": {
        "prompt": (
            "A triumphant short fanfare: a bright ascending chime sequence "
            "signaling a puzzle solved or quest completed. Rewarding and "
            "satisfying. Fantasy video game success jingle."
        ),
        "duration": 1.5,
        "loop": False,
    },
    "dice_roll": {
        "prompt": (
            "Dice rolling on a wooden tavern table: rattling, tumbling, then "
            "settling with a final clack. Tabletop RPG dice roll. Crisp and "
            "tactile."
        ),
        "duration": 1,
        "loop": False,
    },
    "item_food": {
        "prompt": (
            "Crunchy eating and chewing sound. Biting into bread or dried meat. "
            "Short, satisfying food consumption sound effect."
        ),
        "duration": 1,
        "loop": False,
    },
    "item_drink": {
        "prompt": (
            "Gulping and swallowing a drink from a flask. Liquid pouring then "
            "a refreshed exhale. Short drinking sound effect."
        ),
        "duration": 1,
        "loop": False,
    },
    "item_tool": {
        "prompt": (
            "A metallic tool being used: scraping, clinking, mechanical "
            "interaction. Short and utilitarian. Fantasy tool use sound."
        ),
        "duration": 1,
        "loop": False,
    },
}


# ---------------------------------------------------------------------------
# Async generation core
# ---------------------------------------------------------------------------

def _generate_one_sfx_sync(
    client,
    prompt: str,
    sfx_name: str,
    save_dir: str,
    duration: float,
    loop: bool,
) -> tuple[str, str | None]:
    """Generate one SFX synchronously via ElevenLabs. Returns (sfx_name, filepath_or_None)."""
    try:
        audio_iter = client.text_to_sound_effects.convert(
            text=prompt,
            duration_seconds=duration,
            output_format="mp3_44100_128",
            **({"loop": True} if loop else {}),
        )
        audio_bytes = b"".join(audio_iter)

        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, f"{sfx_name}.mp3")
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        logger.info("SFX saved: %s (%d bytes)", filepath, len(audio_bytes))
        return sfx_name, filepath
    except Exception as e:
        logger.warning("SFX '%s' failed: %s", sfx_name, e)
    return sfx_name, None


async def _generate_sfx_async(
    client,
    prompt: str,
    sfx_name: str,
    save_dir: str,
    duration: float,
    loop: bool,
) -> tuple[str, str | None]:
    """Wrap synchronous ElevenLabs call in a thread for async concurrency."""
    return await asyncio.to_thread(
        _generate_one_sfx_sync, client, prompt, sfx_name, save_dir, duration, loop,
    )


async def generate_all_sfx_async(
    prompts: dict[str, dict],
    save_dir: str = SFX_DIR,
) -> dict[str, str]:
    """Generate all SFX concurrently via ElevenLabs.

    Parameters
    ----------
    prompts : dict mapping sfx_name -> {"prompt": str, "duration": float, "loop": bool}
    save_dir : base directory to write .mp3 files

    Returns
    -------
    dict mapping sfx_name -> filepath (only successful SFX included)
    """
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        logger.warning("ELEVENLABS_API_KEY not set — skipping SFX generation.")
        return {}

    from config import MUSIC_BACKEND
    if MUSIC_BACKEND != "api":
        logger.info("MUSIC_BACKEND=%s — skipping SFX generation.", MUSIC_BACKEND)
        return {}

    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=key)

    tasks = []
    for name, spec in prompts.items():
        if not spec or not spec.get("prompt"):
            continue
        tasks.append(
            _generate_sfx_async(
                client,
                spec["prompt"],
                name,
                save_dir,
                spec.get("duration", 1.0),
                spec.get("loop", False),
            )
        )

    logger.info("Generating %d SFX in parallel...", len(tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    sfx_paths: dict[str, str] = {}
    for result in results:
        if isinstance(result, Exception):
            logger.warning("SFX task raised exception: %s", result)
        elif isinstance(result, tuple) and result[1] is not None:
            name, fp = result
            sfx_paths[name] = fp

    logger.info("SFX generation complete: %d/%d saved.", len(sfx_paths), len(tasks))
    if _active_stats is not None:
        _active_stats.record_sfx(attempted=len(tasks), succeeded=len(sfx_paths))
    return sfx_paths


def build_full_sfx_prompt_dict(
    llm_prompts: dict[str, dict] | None,
) -> dict[str, dict]:
    """Merge LLM-generated SFX prompts with FIXED_SFX_PROMPTS.

    LLM provides dynamic prompts for weapons, spells, and ambience.
    Fixed prompts cover UI, dice, and item-use sounds.
    """
    merged: dict[str, dict] = {}

    if llm_prompts:
        for name, spec in llm_prompts.items():
            if spec and spec.get("prompt"):
                merged[name] = spec

    for name, spec in FIXED_SFX_PROMPTS.items():
        if name not in merged:
            merged[name] = spec

    return merged
