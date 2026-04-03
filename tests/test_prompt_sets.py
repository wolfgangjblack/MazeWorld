from src.prompts.base import LLMRequest
from src.prompts.llama_prompts import LlamaPromptSet
from src.prompts.claude_prompts import ClaudePromptSet


SAMPLE_DOC = {
    "name": "Arin",
    "job": "hunter",
    "personality": "cheerful",
    "hobby": "tracking",
    "environment": "forest",
    "environment_name": "Iron Oak",
}

SAMPLE_HISTORY = [
    {"role": "user", "content": "Hello there"},
    {"role": "npc", "content": "Greetings, traveler."},
    {"role": "user", "content": "What do you do here?"},
    {"role": "npc", "content": "I hunt in this forest."},
]


class TestLlamaPromptSet:
    def setup_method(self):
        self.prompts = LlamaPromptSet()

    def test_personality_generation_returns_llm_request(self):
        req = self.prompts.personality_generation("forest", "Iron Oak")
        assert isinstance(req, LLMRequest)
        assert len(req.examples) == 5
        assert "forest" in req.user_message
        assert req.max_tokens == 40

    def test_conversation_identity_returns_str(self):
        identity = self.prompts.conversation_identity(
            "Arin", "hunter", "cheerful", "tracking", "forest", "Iron Oak"
        )
        assert isinstance(identity, str)
        assert "Arin" in identity
        assert "hunter" in identity
        assert "forest" in identity

    def test_npc_greeting_returns_llm_request(self):
        identity = self.prompts.conversation_identity(
            "Arin", "hunter", "cheerful", "tracking", "forest", "Iron Oak"
        )
        req = self.prompts.npc_greeting("Arin", identity)
        assert isinstance(req, LLMRequest)
        assert req.system == identity
        assert req.max_tokens == 50

    def test_npc_response_returns_llm_request(self):
        identity = "test identity"
        req = self.prompts.npc_response(identity, SAMPLE_HISTORY, "Arin", "Nice day")
        assert isinstance(req, LLMRequest)
        assert req.system == identity
        assert req.user_message == "Nice day"
        assert len(req.examples) == 2

    def test_image_description_returns_llm_request(self):
        req = self.prompts.image_description(SAMPLE_DOC)
        assert isinstance(req, LLMRequest)
        assert len(req.examples) == 3
        assert req.max_tokens == 40


class TestClaudePromptSet:
    def setup_method(self):
        self.prompts = ClaudePromptSet()

    def test_personality_generation_returns_llm_request(self):
        req = self.prompts.personality_generation("forest", "Iron Oak")
        assert isinstance(req, LLMRequest)
        assert len(req.examples) == 1
        assert "JSON" in req.system
        assert "forest" in req.user_message

    def test_conversation_identity_returns_str(self):
        identity = self.prompts.conversation_identity(
            "Arin", "hunter", "cheerful", "tracking", "forest", "Iron Oak"
        )
        assert isinstance(identity, str)
        assert "Arin" in identity
        assert "concise" in identity.lower() or "1-3 sentences" in identity

    def test_npc_greeting_returns_llm_request(self):
        req = self.prompts.npc_greeting("Arin", "test identity")
        assert isinstance(req, LLMRequest)
        assert req.max_tokens == 80

    def test_npc_response_returns_llm_request(self):
        req = self.prompts.npc_response("identity", SAMPLE_HISTORY, "Arin", "Hello")
        assert isinstance(req, LLMRequest)
        assert req.user_message == "Hello"
        assert len(req.examples) == 2

    def test_image_description_returns_llm_request(self):
        req = self.prompts.image_description(SAMPLE_DOC)
        assert isinstance(req, LLMRequest)
        assert len(req.examples) == 1
        assert req.max_tokens == 80
