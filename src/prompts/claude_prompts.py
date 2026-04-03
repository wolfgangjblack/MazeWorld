import json
from src.prompts.base import PromptSet, LLMRequest


class ClaudePromptSet(PromptSet):

    def personality_generation(self, env: str, env_name: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You generate NPC personalities for a fantasy video game. "
                "Given an environment, respond with ONLY a JSON object with keys: "
                "name, job, personality, hobby. Keep values thematic to the environment. "
                "Do not include any text outside the JSON object."
            ),
            examples=[
                (
                    "environment: 'forest', name: 'Iron Oak'",
                    json.dumps({"name": "helena", "job": "herbalist",
                                "personality": "mysterious", "hobby": "collecting herbs"}),
                ),
            ],
            user_message=f"environment: '{env}', name: '{env_name}'",
            max_tokens=60,
        )

    def conversation_identity(self, name: str, job: str, personality: str,
                              hobby: str, env: str, env_name: str) -> str:
        return (
            f"You are {name}, a {job} in a fantasy {env} called {env_name}. "
            f"Your personality is {personality}. Your hobbies include {hobby}.\n\n"
            "Rules:\n"
            "- Stay in character at all times\n"
            "- Do not speak for the player\n"
            "- Do not break the fourth wall\n"
            "- Keep responses concise (1-3 sentences)\n"
            "- Only discuss topics relevant to your environment, job, and hobbies\n"
            "- Generate exactly one response per turn"
        )

    def npc_greeting(self, name: str, identity: str) -> LLMRequest:
        return LLMRequest(
            system=identity,
            examples=[],
            user_message=(
                "The player approaches you for the first time. "
                "Give a brief, in-character greeting."
            ),
            max_tokens=80,
        )

    def npc_response(self, identity: str, history: list[dict],
                     npc_name: str, player_input: str) -> LLMRequest:
        examples = _history_to_examples(history)
        return LLMRequest(
            system=identity,
            examples=examples,
            user_message=player_input,
            max_tokens=150,
        )

    def image_description(self, personality_doc: dict) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are an image prompt generator for a pixel-art fantasy game. "
                "Given NPC details as JSON, output a short visual description suitable "
                "for an image generator. Focus on appearance, clothing, pose, and setting. "
                "Output ONLY the description, no labels or prefixes."
            ),
            examples=[
                (
                    json.dumps({"name": "Duran", "job": "fighter",
                                "personality": "brooding", "hobby": "swordsplay",
                                "environment": "city", "environment_name": "Capital City"}),
                    "A precocious warrior, clad in steel armor with a great sword over his "
                    "shoulder. He has long red hair, untamed and wild. He stands in a bustling "
                    "city square, scanning the crowd."
                ),
            ],
            user_message=json.dumps(personality_doc),
            max_tokens=80,
        )


def _history_to_examples(history: list[dict]) -> list[tuple[str, str]]:
    """Convert neutral history dicts into (user, npc) turn pairs."""
    examples: list[tuple[str, str]] = []
    i = 0
    while i < len(history):
        turn = history[i]
        if turn["role"] == "user":
            user_msg = turn["content"]
            npc_msg = ""
            if i + 1 < len(history) and history[i + 1]["role"] == "npc":
                npc_msg = history[i + 1]["content"]
                i += 1
            examples.append((user_msg, npc_msg))
        elif turn["role"] == "npc" and not examples:
            examples.append(("", turn["content"]))
        i += 1
    return examples
