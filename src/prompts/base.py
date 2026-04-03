from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMRequest:
    system: str
    examples: list[tuple[str, str]] = field(default_factory=list)
    user_message: str = ""
    max_tokens: int = 150


class PromptSet(ABC):
    @abstractmethod
    def personality_generation(self, env: str, env_name: str) -> LLMRequest: ...

    @abstractmethod
    def conversation_identity(self, name: str, job: str, personality: str,
                              hobby: str, env: str, env_name: str) -> str: ...

    @abstractmethod
    def npc_greeting(self, name: str, identity: str) -> LLMRequest: ...

    @abstractmethod
    def npc_response(self, identity: str, history: list[dict],
                     npc_name: str, player_input: str) -> LLMRequest: ...

    @abstractmethod
    def image_description(self, personality_doc: dict) -> LLMRequest: ...
