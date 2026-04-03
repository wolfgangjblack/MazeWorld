import os
import pytest
from unittest.mock import patch, MagicMock
from src.generate import llm_client
from src.prompts.base import LLMRequest


@pytest.fixture(autouse=True)
def reset_globals():
    llm_client._tokenizer = None
    llm_client._model = None
    llm_client._device = None
    yield
    llm_client._tokenizer = None
    llm_client._model = None
    llm_client._device = None


SAMPLE_REQUEST = LLMRequest(
    system="You are a test assistant.",
    examples=[("hello", "world")],
    user_message="test input",
    max_tokens=10,
)


def test_get_device_returns_torch_device():
    import torch
    device = llm_client._get_device()
    assert isinstance(device, torch.device)


def test_get_device_caches():
    d1 = llm_client._get_device()
    d2 = llm_client._get_device()
    assert d1 is d2


def test_get_llm_raises_without_hf_token():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="not set"):
            llm_client._get_llm()


def test_get_llm_raises_on_load_failure():
    with patch.dict(os.environ, {"hf_write_read": "fake-token"}):
        with patch(
            "transformers.AutoTokenizer.from_pretrained",
            side_effect=OSError("download failed"),
        ):
            with pytest.raises(RuntimeError, match="Failed to load LLM"):
                llm_client._get_llm()
    assert llm_client._model is None
    assert llm_client._tokenizer is None


def test_get_llm_caches_on_success():
    mock_tok = MagicMock()
    mock_model = MagicMock()
    with patch.dict(os.environ, {"hf_write_read": "fake-token"}):
        with patch("transformers.AutoTokenizer.from_pretrained", return_value=mock_tok):
            with patch("transformers.AutoModelForCausalLM.from_pretrained", return_value=mock_model):
                m1, t1 = llm_client._get_llm()
                m2, t2 = llm_client._get_llm()
    assert m1 is m2
    assert t1 is t2
    assert mock_model.to.call_count == 1


@patch.object(llm_client, "LLM_BACKEND", "local")
@patch.object(llm_client, "_generate_local", return_value="local response")
def test_generate_routes_to_local(mock_local):
    result = llm_client.generate(SAMPLE_REQUEST)
    assert result == "local response"
    mock_local.assert_called_once_with(SAMPLE_REQUEST)


@patch.object(llm_client, "LLM_BACKEND", "api")
@patch.object(llm_client, "_generate_api", return_value="api response")
def test_generate_routes_to_api(mock_api):
    result = llm_client.generate(SAMPLE_REQUEST)
    assert result == "api response"
    mock_api.assert_called_once_with(SAMPLE_REQUEST)


def _mock_anthropic_module():
    """Create a mock anthropic module so tests work without installing it."""
    import sys
    mock_mod = MagicMock()
    sys.modules["anthropic"] = mock_mod
    return mock_mod


def test_generate_api_raises_without_key():
    _mock_anthropic_module()
    try:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                llm_client._generate_api(SAMPLE_REQUEST)
    finally:
        import sys
        sys.modules.pop("anthropic", None)


def test_generate_api_calls_anthropic():
    mock_mod = _mock_anthropic_module()
    try:
        mock_client = MagicMock()
        mock_mod.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="claude says hi")]
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = llm_client._generate_api(SAMPLE_REQUEST)

        assert result == "claude says hi"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "You are a test assistant."
        assert call_kwargs["max_tokens"] == 10
        assert len(call_kwargs["messages"]) == 3
    finally:
        import sys
        sys.modules.pop("anthropic", None)
