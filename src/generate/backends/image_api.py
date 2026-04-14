import logging
import os
import urllib.request

from src.generate.backends.base import ImageBackend

logger = logging.getLogger(__name__)


class ApiImageBackend(ImageBackend):
    """fal.ai API backend for image generation."""

    def generate_image(self, prompt: str, width: int = 256, height: int = 256) -> str:
        """Returns a URL to the generated image."""
        import fal_client

        from config import FAL_KEY_ENV, FAL_MODEL

        fal_key = os.getenv(FAL_KEY_ENV)
        if not fal_key:
            raise RuntimeError(
                f"'{FAL_KEY_ENV}' env var is not set. "
                "Provide a fal API key or set IMAGE_BACKEND='local'."
            )

        result = fal_client.subscribe(
            FAL_MODEL,
            arguments={
                "prompt": prompt,
                "image_size": {"width": width, "height": height},
                "num_images": 1,
            },
        )
        return result["images"][0]["url"]

    def generate_and_save(self, prompt: str, filepath: str) -> bool:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            image_url = self.generate_image(prompt)
            urllib.request.urlretrieve(image_url, filepath)
            return True
        except Exception as e:
            logger.warning("Portrait generation failed for %s: %s", filepath, e)
            return False
