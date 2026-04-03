import os
import urllib.request
from config import IMAGE_BACKEND, FAL_MODEL, FAL_KEY_ENV

_pipe = None


def _get_local_pipe():
    global _pipe
    if _pipe is not None:
        return _pipe
    import torch
    from diffusers import FluxPipeline

    try:
        _pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell", torch_dtype=torch.bfloat16
        )
        _pipe.enable_model_cpu_offload()
    except Exception as e:
        raise RuntimeError(f"Failed to load local Flux pipeline: {e}") from e
    return _pipe


def _generate_image_local(prompt: str, width: int = 256, height: int = 256):
    pipe = _get_local_pipe()
    result = pipe(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=12,
        max_sequence_length=256,
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


def generate_npc_portraits(npc_database: dict, save_dir: str = "data/portraits"):
    """Generate and save a portrait for each NPC. Updates profile_image in-place."""
    os.makedirs(save_dir, exist_ok=True)

    for npc_id, npc in npc_database.items():
        prompt = npc.get("description", "a fantasy character portrait")
        filename = f"npc_{npc_id}.png"
        filepath = os.path.join(save_dir, filename)

        if IMAGE_BACKEND == "api":
            image_url = _generate_image_api(prompt)
            urllib.request.urlretrieve(image_url, filepath)
        else:
            image = _generate_image_local(prompt)
            image.save(filepath)

        npc["profile_image"] = filepath
