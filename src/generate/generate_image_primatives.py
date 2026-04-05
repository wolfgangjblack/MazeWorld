import logging
import os
import urllib.request
from config import (
    IMAGE_BACKEND, FAL_MODEL, FAL_KEY_ENV,
    LOCAL_IMAGE_MODEL_MPS, LOCAL_IMAGE_MODEL_CUDA,
)

logger = logging.getLogger(__name__)

_pipe = None
_pipe_type = None  # "sdxl" or "flux"


def _get_device():
    """Return the best available torch device."""
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load_pipe(device: str):
    """Load the appropriate image pipeline for the detected device.

    CUDA  -> FLUX.1-schnell (bfloat16, higher quality)
    MPS/CPU -> SDXL Turbo (float16, MPS-native)
    """
    import torch

    if device == "cuda":
        from diffusers import FluxPipeline
        pipe = FluxPipeline.from_pretrained(
            LOCAL_IMAGE_MODEL_CUDA, torch_dtype=torch.bfloat16
        )
        pipe.enable_model_cpu_offload()
        return pipe, "flux"

    from diffusers import AutoPipelineForText2Image
    pipe = AutoPipelineForText2Image.from_pretrained(
        LOCAL_IMAGE_MODEL_MPS, torch_dtype=torch.float16, variant="fp16"
    )
    pipe = pipe.to(device)
    return pipe, "sdxl"


def _get_local_pipe():
    global _pipe, _pipe_type
    if _pipe is not None:
        return _pipe

    device = _get_device()
    try:
        _pipe, _pipe_type = _load_pipe(device)
    except Exception as e:
        if device != "cpu":
            logger.warning("Failed to load pipeline on %s, falling back to CPU: %s", device, e)
            _pipe, _pipe_type = _load_pipe("cpu")
        else:
            raise RuntimeError(f"Failed to load local image pipeline: {e}") from e
    return _pipe


def _generate_image_local(prompt: str, width: int = 256, height: int = 256):
    pipe = _get_local_pipe()

    if _pipe_type == "flux":
        result = pipe(
            prompt=prompt,
            height=height,
            width=width,
            num_inference_steps=12,
            max_sequence_length=256,
        )
    else:
        result = pipe(
            prompt=prompt,
            height=height,
            width=width,
            num_inference_steps=4,
            guidance_scale=0.0,
        )
    return result.images[0]


def _generate_image_api(prompt: str, width: int = 256, height: int = 256) -> str:
    """Returns a URL to the generated image via fal.ai."""
    import fal_client

    fal_key = os.getenv(FAL_KEY_ENV)
    if not fal_key:
        raise RuntimeError(
            f"'{FAL_KEY_ENV}' env var is not set. "
            "Provide a fal API key or set IMAGE_BACKEND='local'."
        )
    os.environ["FAL_KEY"] = fal_key

    result = fal_client.subscribe(
        FAL_MODEL,
        arguments={
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
        },
    )
    return result["images"][0]["url"]


def _generate_and_save(prompt: str, filepath: str) -> bool:
    """Generate an image and save to filepath. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if IMAGE_BACKEND == "api":
            image_url = _generate_image_api(prompt)
            urllib.request.urlretrieve(image_url, filepath)
        else:
            image = _generate_image_local(prompt)
            image.save(filepath)
        return True
    except Exception as e:
        logger.warning("Portrait generation failed for %s: %s", filepath, e)
        return False


def generate_portraits(entity_database: dict, save_dir: str = "data/portraits",
                       prefix: str = ""):
    """Generate and save a portrait for each entity. Updates profile_image in-place.

    entity_database: dict keyed by id, each value has 'portrait_prompt' or 'description'.
    """
    os.makedirs(save_dir, exist_ok=True)

    for entity_id, entity in entity_database.items():
        prompt = entity.get("portrait_prompt") or entity.get("description", "a fantasy character portrait")
        filename = f"{prefix}{entity_id}.png"
        filepath = os.path.join(save_dir, filename)

        if _generate_and_save(prompt, filepath):
            entity["profile_image"] = filepath
        else:
            entity["profile_image"] = None


def generate_npc_portraits(npc_database: dict, save_dir: str = "data/portraits/npcs"):
    """Generate and save a portrait for each NPC."""
    generate_portraits(npc_database, save_dir, prefix="npc_")


def generate_item_portraits(item_database: dict, save_dir: str = "data/portraits/items"):
    """Generate and save a portrait for each item."""
    generate_portraits(item_database, save_dir, prefix="item_")


def generate_event_illustrations(event_database: dict, save_dir: str = "data/portraits/events"):
    """Generate and save an illustration for each event."""
    generate_portraits(event_database, save_dir, prefix="evt_")


def generate_player_portrait(portrait_prompt: str, save_dir: str = "data/portraits") -> str | None:
    """Generate and save the player character portrait. Returns path or None."""
    filepath = os.path.join(save_dir, "player.png")
    if _generate_and_save(portrait_prompt, filepath):
        return filepath
    return None
