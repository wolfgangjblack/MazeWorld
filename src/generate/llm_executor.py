"""Concurrent LLM request executor with bounded parallelism.

API backends use a thread pool; local backends run sequentially since the
model can only handle one inference at a time.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.generate.llm_client import generate
from src.prompts.base import LLMRequest

logger = logging.getLogger(__name__)


def generate_batch(
    requests: list[LLMRequest],
    max_workers: int | None = None,
) -> list[str | None]:
    """Run multiple LLM requests with bounded concurrency.

    Returns a list of raw response strings in the same order as *requests*.
    Failed requests (after retries in ``generate()``) return ``None``.
    """
    if max_workers is None:
        from config import LLM_CONCURRENCY

        max_workers = LLM_CONCURRENCY

    from config import LLM_BACKEND

    if LLM_BACKEND != "api":
        max_workers = 1

    results: list[str | None] = [None] * len(requests)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {pool.submit(generate, req): idx for idx, req in enumerate(requests)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception:
                logger.warning(
                    "LLM batch request %d/%d failed after retries",
                    idx + 1,
                    len(requests),
                    exc_info=True,
                )

    succeeded = sum(1 for r in results if r is not None)
    logger.info("LLM batch: %d/%d succeeded", succeeded, len(requests))
    return results
