import os
from config import LLM_BACKEND, LLM_MODEL_PATH, HF_ENV
from src.prompts.base import LLMRequest

_tokenizer = None
_model = None
_device = None


def _get_device():
    import torch
    global _device
    if _device is None:
        if torch.cuda.is_available():
            _device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            _device = torch.device("mps")
        else:
            _device = torch.device("cpu")
    return _device


def _get_llm():
    global _tokenizer, _model
    if _tokenizer is not None and _model is not None:
        return _model, _tokenizer

    hf_token = os.getenv(HF_ENV)
    if not hf_token:
        raise RuntimeError(
            f"Environment variable '{HF_ENV}' is not set. "
            "Set it to a valid HuggingFace token."
        )

    from transformers import AutoTokenizer, AutoModelForCausalLM

    try:
        _tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_PATH, token=hf_token)
        _model = AutoModelForCausalLM.from_pretrained(LLM_MODEL_PATH, token=hf_token)
        _model.to(_get_device())
    except Exception as e:
        _tokenizer, _model = None, None
        raise RuntimeError(f"Failed to load LLM '{LLM_MODEL_PATH}': {e}") from e

    return _model, _tokenizer


def generate(request: LLMRequest) -> str:
    if LLM_BACKEND == "api":
        return _generate_api(request)
    return _generate_local(request)


def _generate_api(request: LLMRequest) -> str:
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


def _generate_local(request: LLMRequest) -> str:
    import torch
    model, tokenizer = _get_llm()
    device = _get_device()

    parts = [request.system]
    for user_msg, asst_msg in request.examples:
        parts.append(f"##Input: {user_msg}")
        parts.append(f"##Output: {asst_msg}")
    parts.append(f"##Input: {request.user_message}")
    parts.append("##Output:")
    prompt_text = "\n========================================\n".join(parts)

    inputs = tokenizer(prompt_text, return_tensors="pt",
                       truncation=True, max_length=1024)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=request.max_tokens,
            pad_token_id=tokenizer.eos_token_id,
            temperature=1.0,
        )

    return tokenizer.decode(outputs[0], skip_special_tokens=True)
