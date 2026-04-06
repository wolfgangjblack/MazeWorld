"""LLM text generation — delegates to the backend registry.

Public API preserved: callers import ``generate`` from this module.
"""

from src.generate.backends.registry import get_llm_backend
from src.prompts.base import LLMRequest


def generate(request: LLMRequest) -> str:
    return get_llm_backend().generate(request)
