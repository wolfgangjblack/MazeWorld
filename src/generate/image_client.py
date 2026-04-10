"""Image generation — delegates to the backend registry.

Public API preserved: callers import portrait helpers from this module.
Parallel generation (API backend only) uses fal_client.subscribe_async
with a concurrency cap to keep within rate limits.
"""

import asyncio
import logging
import os

from src.generate.backends.registry import get_image_backend

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sequential fallback (local backend or single images)
# ---------------------------------------------------------------------------

def generate_portraits(entity_database: dict, save_dir: str = "data/portraits",
                       prefix: str = ""):
    """Generate and save a portrait for each entity. Updates profile_image in-place.
    Sequential — used for local backend or when parallelism is not available.
    """
    os.makedirs(save_dir, exist_ok=True)
    backend = get_image_backend()

    for entity_id, entity in entity_database.items():
        prompt = entity.get("portrait_prompt") or entity.get(
            "description", "a fantasy character portrait"
        )
        filename = f"{prefix}{entity_id}.png"
        filepath = os.path.join(save_dir, filename)

        if backend.generate_and_save(prompt, filepath):
            entity["profile_image"] = filepath
        else:
            entity["profile_image"] = None


# ---------------------------------------------------------------------------
# Parallel generation (API backend — fal.ai)
# ---------------------------------------------------------------------------

async def _generate_one_async(fal_model: str, prompt: str, filepath: str,
                               entity: dict) -> None:
    """Single async portrait job via fal_client.subscribe_async."""
    try:
        import fal_client
        import aiohttp
        result = await fal_client.subscribe_async(
            fal_model,
            arguments={
                "prompt": prompt,
                "image_size": {"width": 256, "height": 256},
                "num_images": 1,
            },
        )
        url = result["images"][0]["url"]
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "wb") as f:
                        f.write(await resp.read())
                    entity["profile_image"] = filepath
                    return
    except Exception as e:
        logger.warning("Portrait failed for %s: %s", filepath, e)
    entity["profile_image"] = None


def generate_portraits_parallel(entity_database: dict, save_dir: str,
                                 prefix: str = "",
                                 max_concurrent: int = 15):
    """Generate all portraits in parallel (API backend only).

    Falls back to sequential generation for local backend.
    Uses a semaphore to cap concurrent fal.ai requests.
    """
    from config import IMAGE_BACKEND
    if IMAGE_BACKEND != "api":
        generate_portraits(entity_database, save_dir, prefix)
        return

    from config import FAL_MODEL
    os.makedirs(save_dir, exist_ok=True)

    async def _run_all():
        sem = asyncio.Semaphore(max_concurrent)

        async def _bounded(entity_id: str, entity: dict):
            async with sem:
                prompt = entity.get("portrait_prompt") or entity.get(
                    "description", "a fantasy character portrait, pixel art"
                )
                filepath = os.path.join(save_dir, f"{prefix}{entity_id}.png")
                await _generate_one_async(FAL_MODEL, prompt, filepath, entity)

        await asyncio.gather(
            *[_bounded(eid, e) for eid, e in entity_database.items()]
        )

    asyncio.run(_run_all())
    generated = sum(1 for e in entity_database.values() if e.get("profile_image"))
    logger.info("Portraits: %d/%d generated (parallel, max_concurrent=%d).",
                generated, len(entity_database), max_concurrent)


# ---------------------------------------------------------------------------
# Named helpers — all route through generate_portraits_parallel
# ---------------------------------------------------------------------------

def generate_npc_portraits(npc_database: dict,
                            save_dir: str = "data/portraits/npcs"):
    generate_portraits_parallel(npc_database, save_dir, prefix="npc_")


def generate_item_portraits(item_database: dict,
                             save_dir: str = "data/portraits/items"):
    generate_portraits_parallel(item_database, save_dir, prefix="item_")


def generate_event_illustrations(event_database: dict,
                                  save_dir: str = "data/portraits/events"):
    generate_portraits_parallel(event_database, save_dir, prefix="evt_")


def generate_class_portraits(class_database: dict,
                              save_dir: str = "data/portraits/classes"):
    generate_portraits_parallel(class_database, save_dir, prefix="class_")


def generate_monster_portraits(monster_database: dict,
                                save_dir: str = "data/portraits/monsters"):
    generate_portraits_parallel(monster_database, save_dir, prefix="mon_")


def generate_and_save_image(prompt: str, filepath: str) -> bool:
    """Generate a single image and save to *filepath*. Returns True on success."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    return get_image_backend().generate_and_save(prompt, filepath)


def generate_player_portrait(portrait_prompt: str,
                              save_dir: str = "data/portraits") -> str | None:
    filepath = os.path.join(save_dir, "player.png")
    if get_image_backend().generate_and_save(portrait_prompt, filepath):
        return filepath
    return None


def generate_room_portrait(prompt: str, room_id: str,
                            save_dir: str = "data/portraits/rooms") -> str | None:
    """Generate a room/environment portrait. Returns filepath or None."""
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, f"{room_id}.png")
    if get_image_backend().generate_and_save(prompt, filepath):
        return filepath
    return None


def generate_game_over_portrait(prompt: str,
                                 save_dir: str = "data/portraits") -> str | None:
    """Generate a game-over portrait. Returns filepath or None."""
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, "game_over.png")
    if get_image_backend().generate_and_save(prompt, filepath):
        return filepath
    return None
