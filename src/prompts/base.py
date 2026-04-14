from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMRequest:
    system: str
    examples: list[tuple[str, str]] = field(default_factory=list)
    user_message: str = ""
    max_tokens: int = 150

    def format_for_completion(self) -> str:
        """Format as a single prompt string for completion-based models."""
        parts = [self.system]
        for user_msg, asst_msg in self.examples:
            parts.append(f"User: {user_msg}")
            parts.append(f"Assistant: {asst_msg}")
        parts.append(f"User: {self.user_message}")
        parts.append("Assistant:")
        return "\n\n".join(parts)


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
                     npc_name: str, player_input: str,
                     story_context: str = "",
                     quest_context: dict | None = None) -> LLMRequest: ...

    @abstractmethod
    def image_description(self, personality_doc: dict) -> LLMRequest: ...

    @abstractmethod
    def environment_name_generation(self, env_type: str) -> LLMRequest: ...

    @abstractmethod
    def event_generation(self, env: str, env_name: str, event_type: str,
                         story_context: str = "") -> LLMRequest: ...

    @abstractmethod
    def quest_generation(self, env: str, env_name: str,
                         available_npcs: list[dict], available_items: list[dict],
                         available_events: list[dict], quest_type: str,
                         story_context: str = "") -> LLMRequest: ...

    @abstractmethod
    def dialogue_tree_generation(self, npc_personality: dict,
                                 quest_context: dict | None = None) -> LLMRequest: ...

    @abstractmethod
    def item_generation(self, env: str, env_name: str, room_level: int,
                        story_context: str = "") -> LLMRequest: ...

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

    @abstractmethod
    def story_generation(self, story_seed: str, room_count: int,
                         environments: list[str]) -> LLMRequest: ...

    @abstractmethod
    def story_quest_generation(self, env: str, env_name: str,
                               story_beat: str, faction_name: str,
                               available_npcs: list[dict],
                               available_items: list[dict],
                               available_events: list[dict],
                               quest_type: str,
                               story_context: str = "") -> LLMRequest: ...

    @abstractmethod
    def full_story_generation(self, story_seed: str, room_count: int,
                              environments: list[str]) -> LLMRequest: ...

    @abstractmethod
    def monster_generation(self, env: str, env_name: str, room_level: int,
                           story_context: str, total_rooms: int = 1) -> LLMRequest: ...

    @abstractmethod
    def npc_backstory_generation(self, npc_data: dict,
                                 story_context: str) -> LLMRequest: ...

    @abstractmethod
    def npc_batch_generation(self, room_env: dict, room_story: str,
                             npc_slots: list[dict],
                             story_context: str) -> LLMRequest: ...

    @abstractmethod
    def event_batch_generation(self, room_env: dict, room_story: str,
                               event_type: str, event_slots: list[dict],
                               story_context: str, **kwargs) -> LLMRequest: ...

    @abstractmethod
    def dialogue_context_generation(self, room_env: dict, room_story: str,
                                    npc_data: list[dict],
                                    story_context: str) -> LLMRequest: ...

    @abstractmethod
    def weapon_database_generation(self, environments: list[dict],
                                   num_rooms: int) -> LLMRequest: ...

    @abstractmethod
    def spell_database_generation(self, class_type: str,
                                  environments: list[dict],
                                  num_rooms: int) -> LLMRequest: ...

    @abstractmethod
    def utility_ability_generation(self, environments: list[dict],
                                   num_rooms: int) -> LLMRequest: ...

    @abstractmethod
    def environment_sequence_generation(self, story_seed: str, num_rooms: int,
                                        known_types: list[str]) -> LLMRequest: ...

    @abstractmethod
    def overarching_story_generation(self, story_seed: str,
                                     environments: list[dict]) -> LLMRequest: ...

    @abstractmethod
    def room_story_beat_generation(self, overarching_story: dict,
                                   room_env: dict, room_index: int,
                                   prior_beats: list[dict],
                                   num_rooms: int = 5) -> LLMRequest: ...

    @abstractmethod
    def music_prompt_generation(self, story_summary: dict,
                                environments: list[str]) -> LLMRequest: ...

    @abstractmethod
    def sfx_prompt_generation(self, story_summary: dict,
                              environments: list[dict],
                              spell_elements: list[str]) -> LLMRequest: ...
