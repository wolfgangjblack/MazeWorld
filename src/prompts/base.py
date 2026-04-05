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

    @abstractmethod
    def environment_name_generation(self, env_type: str) -> LLMRequest: ...

    @abstractmethod
    def event_generation(self, env: str, env_name: str, event_type: str) -> LLMRequest: ...

    @abstractmethod
    def quest_generation(self, env: str, env_name: str,
                         available_npcs: list[dict], available_items: list[dict],
                         available_events: list[dict], quest_type: str) -> LLMRequest: ...

    @abstractmethod
    def dialogue_tree_generation(self, npc_personality: dict,
                                 quest_context: dict | None = None) -> LLMRequest: ...

    @abstractmethod
    def item_image_description(self, item_data: dict) -> LLMRequest: ...

    @abstractmethod
    def event_image_description(self, event_data: dict) -> LLMRequest: ...

    @abstractmethod
    def player_image_description(self) -> LLMRequest: ...

    @abstractmethod
    def class_generation(self, env: str, env_name: str) -> LLMRequest: ...

    @abstractmethod
    def class_portrait_description(self, class_data: dict) -> LLMRequest: ...
