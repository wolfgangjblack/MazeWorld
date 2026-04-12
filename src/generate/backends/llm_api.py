import os

from src.generate.backends.base import LLMBackend
from src.prompts.base import LLMRequest

_active_stats = None


def set_stats(stats) -> None:
    """Wire a GenerationStats instance to accumulate token counts from this backend."""
    global _active_stats
    _active_stats = stats


class ApiLLMBackend(LLMBackend):
    """Anthropic Claude API backend for text generation."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        from anthropic import Anthropic
        from config import ANTHROPIC_KEY_ENV

        api_key = os.getenv(ANTHROPIC_KEY_ENV)
        if not api_key:
            raise RuntimeError(
                f"Environment variable '{ANTHROPIC_KEY_ENV}' is not set. "
                "Provide an Anthropic API key or set LLM_BACKEND='local'."
            )

        self._client = Anthropic(api_key=api_key)
        return self._client

    def generate(self, request: LLMRequest) -> str:
        from config import ANTHROPIC_MODEL

        client = self._get_client()
        messages = []
        for user_msg, asst_msg in request.examples:
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if asst_msg:
                messages.append({"role": "assistant", "content": asst_msg})
        messages.append({"role": "user", "content": request.user_message})

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=request.max_tokens,
            system=request.system,
            messages=messages,
        )
        if _active_stats is not None:
            _active_stats.record_llm_call(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        return response.content[0].text
