"""Image generation — delegates to the backend registry.

Public API preserved: callers import portrait helpers from this module.
"""

import os

from src.generate.backends.registry import get_image_backend


def generate_portraits(entity_database: dict, save_dir: str = "data/portraits",
                       prefix: str = ""):
    """Generate and save a portrait for each entity. Updates profile_image in-place."""
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


def generate_npc_portraits(npc_database: dict, save_dir: str = "data/portraits/npcs"):
    generate_portraits(npc_database, save_dir, prefix="npc_")


def generate_item_portraits(item_database: dict, save_dir: str = "data/portraits/items"):
    generate_portraits(item_database, save_dir, prefix="item_")


def generate_event_illustrations(event_database: dict, save_dir: str = "data/portraits/events"):
    generate_portraits(event_database, save_dir, prefix="evt_")


def generate_class_portraits(class_database: dict, save_dir: str = "data/portraits/classes"):
    generate_portraits(class_database, save_dir, prefix="class_")


def generate_and_save_image(prompt: str, filepath: str) -> bool:
    """Generate a single image and save to *filepath*. Returns True on success."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    return get_image_backend().generate_and_save(prompt, filepath)


def generate_player_portrait(portrait_prompt: str, save_dir: str = "data/portraits") -> str | None:
    filepath = os.path.join(save_dir, "player.png")
    if get_image_backend().generate_and_save(portrait_prompt, filepath):
        return filepath
    return None
