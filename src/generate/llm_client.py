"""LLM text generation — delegates to the backend registry.

Public API preserved: callers import ``generate`` from this module.
"""

import logging
import time

from src.generate.backends.registry import get_llm_backend
from src.prompts.base import LLMRequest

logger = logging.getLogger(__name__)
MAX_LLM_RETRIES = 3


def generate(request: LLMRequest) -> str:
    backend = get_llm_backend()
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            return backend.generate(request)
        except Exception as e:
            if attempt == MAX_LLM_RETRIES:
                raise
            logger.warning("LLM call attempt %d/%d failed: %s", attempt, MAX_LLM_RETRIES, e)
            time.sleep(2 * attempt)
    raise RuntimeError("LLM retries exhausted")
