import logging
import os

from src.generate.backends.base import ImageBackend

logger = logging.getLogger(__name__)


class LocalImageBackend(ImageBackend):
    """Local diffusion pipeline backend for image generation."""

    def __init__(self):
        self._pipe = None
        self._pipe_type = None  # "sdxl" or "flux"

    def _get_device(self) -> str:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_pipe(self, device: str):
        """Load the appropriate image pipeline for the detected device.

        CUDA  -> FLUX.1-schnell (bfloat16, higher quality)
        MPS/CPU -> SDXL Turbo (float16, MPS-native)
        """
        import torch
        from config import LOCAL_IMAGE_MODEL_CUDA, LOCAL_IMAGE_MODEL_MPS

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

    def _get_pipe(self):
        if self._pipe is not None:
            return self._pipe

        device = self._get_device()
        try:
            self._pipe, self._pipe_type = self._load_pipe(device)
        except Exception as e:
            if device != "cpu":
                logger.warning(
                    "Failed to load pipeline on %s, falling back to CPU: %s",
                    device, e,
                )
                self._pipe, self._pipe_type = self._load_pipe("cpu")
            else:
                raise RuntimeError(
                    f"Failed to load local image pipeline: {e}"
                ) from e
        return self._pipe

    def generate_image(self, prompt: str, width: int | None = None,
                       height: int | None = None):
        """Returns a PIL Image at native resolution for the active model."""
        from config import IMAGE_WIDTH, IMAGE_HEIGHT
        pipe = self._get_pipe()

        if width is None:
            width = IMAGE_WIDTH
        if height is None:
            height = IMAGE_HEIGHT

        # SDXL Turbo is trained at 512x512 max; clamp to avoid artifacts
        if self._pipe_type == "sdxl":
            width = min(width, 512)
            height = min(height, 512)

        if self._pipe_type == "flux":
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

    def generate_and_save(self, prompt: str, filepath: str) -> bool:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            image = self.generate_image(prompt)
            image.save(filepath)
            return True
        except Exception as e:
            logger.warning("Portrait generation failed for %s: %s", filepath, e)
            return False
