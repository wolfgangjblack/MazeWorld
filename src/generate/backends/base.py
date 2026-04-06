from abc import ABC, abstractmethod

from src.prompts.base import LLMRequest


class LLMBackend(ABC):
    """Abstract interface for text generation backends."""

    @abstractmethod
    def generate(self, request: LLMRequest) -> str:
        """Generate text from a prompt request."""
        ...


class ImageBackend(ABC):
    """Abstract interface for image generation backends."""

    @abstractmethod
    def generate_image(self, prompt: str, width: int = 256, height: int = 256):
        """Generate an image from a text prompt. Returns a PIL Image or URL string."""
        ...

    @abstractmethod
    def generate_and_save(self, prompt: str, filepath: str) -> bool:
        """Generate an image and save to filepath. Returns True on success."""
        ...


class MusicBackend(ABC):
    """Abstract interface for music generation backends.

    # TODO: Music research spike is humans-only. No implementations yet.
    """

    @abstractmethod
    def generate_track(self, prompt: str, duration_seconds: int = 30) -> bytes:
        """Generate a music track from a text prompt. Returns raw audio bytes."""
        ...
