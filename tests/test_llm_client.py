import os
import pytest
from unittest.mock import patch, MagicMock
from src.prompts.base import LLMRequest
from src.generate.backends.llm_local import LocalLLMBackend
from src.generate.backends.llm_api import ApiLLMBackend


SAMPLE_REQUEST = LLMRequest(
    system="You are a test assistant.",
    examples=[("hello", "world")],
    user_message="test input",
    max_tokens=10,
)


# -- LocalLLMBackend --------------------------------------------------------

class TestLocalLLMBackend:
    def setup_method(self):
        self.backend = LocalLLMBackend()

    def test_get_device_returns_cpu_fallback(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        mock_device = MagicMock()
        mock_torch.device.return_value = mock_device
        with patch.dict("sys.modules", {"torch": mock_torch}):
            device = self.backend._get_device()
        assert device is mock_device
        mock_torch.device.assert_called_with("cpu")

    def test_get_device_caches(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        mock_device = MagicMock()
        mock_torch.device.return_value = mock_device
        with patch.dict("sys.modules", {"torch": mock_torch}):
            d1 = self.backend._get_device()
            d2 = self.backend._get_device()
        assert d1 is d2

    def test_get_llm_raises_without_hf_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="not set"):
                self.backend._get_llm()

    def test_get_llm_raises_on_load_failure(self):
        mock_transformers = MagicMock()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.device.return_value = MagicMock()
        mock_transformers.AutoTokenizer.from_pretrained.side_effect = OSError("download failed")
        with patch.dict("sys.modules", {"transformers": mock_transformers, "torch": mock_torch}):
            with patch.dict(os.environ, {"hf_write_read": "fake-token"}):
                with pytest.raises(RuntimeError, match="Failed to load LLM"):
                    self.backend._get_llm()
        assert self.backend._model is None
        assert self.backend._tokenizer is None

    def test_get_llm_caches_on_success(self):
        mock_transformers = MagicMock()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.device.return_value = MagicMock()
        mock_tok = MagicMock()
        mock_model = MagicMock()
        mock_transformers.AutoTokenizer.from_pretrained.return_value = mock_tok
        mock_transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model
        with patch.dict("sys.modules", {"transformers": mock_transformers, "torch": mock_torch}):
            with patch.dict(os.environ, {"hf_write_read": "fake-token"}):
                m1, t1 = self.backend._get_llm()
                m2, t2 = self.backend._get_llm()
        assert m1 is m2
        assert t1 is t2
        assert mock_model.to.call_count == 1


# -- ApiLLMBackend ----------------------------------------------------------

class TestApiLLMBackend:
    def setup_method(self):
        self.backend = ApiLLMBackend()

    def test_generate_raises_without_key(self):
        mock_mod = MagicMock()
        import sys
        sys.modules["anthropic"] = mock_mod
        try:
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                    self.backend.generate(SAMPLE_REQUEST)
        finally:
            sys.modules.pop("anthropic", None)

    def test_generate_calls_anthropic(self):
        mock_mod = MagicMock()
        import sys
        sys.modules["anthropic"] = mock_mod
        try:
            mock_client = MagicMock()
            mock_mod.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = MagicMock(
                content=[MagicMock(text="claude says hi")]
            )

            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = self.backend.generate(SAMPLE_REQUEST)

            assert result == "claude says hi"
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["system"] == "You are a test assistant."
            assert call_kwargs["max_tokens"] == 10
            assert len(call_kwargs["messages"]) == 3
        finally:
            sys.modules.pop("anthropic", None)


# -- generate() dispatch via registry ---------------------------------------

def test_generate_delegates_to_registry():
    from src.generate import llm_client
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "mocked response"
    with patch("src.generate.llm_client.get_llm_backend", return_value=mock_backend):
        result = llm_client.generate(SAMPLE_REQUEST)
    assert result == "mocked response"
    mock_backend.generate.assert_called_once_with(SAMPLE_REQUEST)
