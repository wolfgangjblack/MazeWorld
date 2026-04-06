"""Singleton backend registry with lazy loading.

Resolves backend instances by type (llm, image) based on config values.
Backends are instantiated on first access and cached for the process lifetime.
"""

from src.generate.backends.base import LLMBackend, ImageBackend


class BackendRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._llm = None
            cls._instance._image = None
        return cls._instance

    @property
    def llm(self) -> LLMBackend:
        if self._llm is None:
            from config import LLM_BACKEND
            if LLM_BACKEND == "api":
                from src.generate.backends.llm_api import ApiLLMBackend
                self._llm = ApiLLMBackend()
            else:
                from src.generate.backends.llm_local import LocalLLMBackend
                self._llm = LocalLLMBackend()
        return self._llm

    @property
    def image(self) -> ImageBackend:
        if self._image is None:
            from config import IMAGE_BACKEND
            if IMAGE_BACKEND == "api":
                from src.generate.backends.image_api import ApiImageBackend
                self._image = ApiImageBackend()
            else:
                from src.generate.backends.image_local import LocalImageBackend
                self._image = LocalImageBackend()
        return self._image


_registry = BackendRegistry()


def get_llm_backend() -> LLMBackend:
    return _registry.llm


def get_image_backend() -> ImageBackend:
    return _registry.image
