import os

from src.generate.backends.base import LLMBackend
from src.prompts.base import LLMRequest


class ApiLLMBackend(LLMBackend):
    """Anthropic Claude API backend for text generation."""

    def generate(self, request: LLMRequest) -> str:
        from anthropic import Anthropic
        from config import ANTHROPIC_MODEL, ANTHROPIC_KEY_ENV

        api_key = os.getenv(ANTHROPIC_KEY_ENV)
        if not api_key:
            raise RuntimeError(
                f"Environment variable '{ANTHROPIC_KEY_ENV}' is not set. "
                "Provide an Anthropic API key or set LLM_BACKEND='local'."
            )

        client = Anthropic(api_key=api_key)
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
        return response.content[0].text
