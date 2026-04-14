import os

from src.generate.backends.base import LLMBackend
from src.prompts.base import LLMRequest

_active_stats = None


def set_stats(stats) -> None:
    """Wire a GenerationStats instance to count LLM calls from this backend."""
    global _active_stats
    _active_stats = stats


class LocalLLMBackend(LLMBackend):
    """HuggingFace transformers backend for local text generation."""

    def __init__(self):
        self._tokenizer = None
        self._model = None
        self._device = None

    def _get_device(self):
        if self._device is None:
            import torch
            if torch.cuda.is_available():
                self._device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self._device = torch.device("mps")
            else:
                self._device = torch.device("cpu")
        return self._device

    def _get_llm(self):
        if self._tokenizer is not None and self._model is not None:
            return self._model, self._tokenizer

        from config import HF_ENV, LLM_MODEL_PATH
        hf_token = os.getenv(HF_ENV)
        if not hf_token:
            raise RuntimeError(
                f"Environment variable '{HF_ENV}' is not set. "
                "Set it to a valid HuggingFace token."
            )

        from transformers import AutoModelForCausalLM, AutoTokenizer

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                LLM_MODEL_PATH, token=hf_token
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                LLM_MODEL_PATH, token=hf_token
            )
            self._model.to(self._get_device())
        except Exception as e:
            self._tokenizer, self._model = None, None
            raise RuntimeError(
                f"Failed to load LLM '{LLM_MODEL_PATH}': {e}"
            ) from e

        return self._model, self._tokenizer

    def generate(self, request: LLMRequest) -> str:
        import torch
        model, tokenizer = self._get_llm()
        device = self._get_device()

        prompt_text = request.format_for_completion()

        inputs = tokenizer(
            prompt_text, return_tensors="pt", truncation=True, max_length=1024
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                pad_token_id=tokenizer.eos_token_id,
                temperature=1.0,
            )

        if _active_stats is not None:
            _active_stats.record_llm_call()  # no token counts available for local inference
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
