from src.prompts.base import PromptSet, LLMRequest


class LlamaPromptSet(PromptSet):

    def personality_generation(self, env: str, env_name: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are a non-playable character content generator. You create npcs "
                "for video games, generating names, jobs, personalities, hobbies, and "
                "interaction types. You inherit their environment from the map which is "
                "meant to influence their content.\n\n"
                "Follow these rules:\n"
                "1. output a name, job, personality, and hobby related to their environment\n"
                "2. do not create dialogue\n"
                "3. generate in a jsonic format"
            ),
            examples=[
                ("enviroment: 'forest', env_name: 'Iron Oak'",
                 "{'name': 'helena', 'job': 'herbalist', 'personality': 'mysterious', 'hobby': 'collecting herbs'}"),
                ("enviroment: 'desert', env_name: 'Sandstone'",
                 "{'name': 'khalid', 'job': 'merchant', 'personality': 'charming', 'hobby': 'haggling'}"),
                ("enviroment: 'mountain', env_name: 'Frostpeak'",
                 "{'name': 'greta', 'job': 'blacksmith', 'personality': 'gruff', 'hobby': 'forging'}"),
                ("enviroment: 'city', env_name: 'Silverport'",
                 "{'name': 'julius', 'job': 'guard', 'personality': 'stoic', 'hobby': 'training'}"),
                ("enviroment: 'swamp', env_name: 'Mosswood'",
                 "{'name': 'elara', 'job': 'alchemist', 'personality': 'eccentric', 'hobby': 'experimenting'}"),
            ],
            user_message=f"enviroment: '{env}', env_name: '{env_name}'",
            max_tokens=40,
        )

    def conversation_identity(self, name: str, job: str, personality: str,
                              hobby: str, env: str, env_name: str) -> str:
        return (
            f"##sys: You are playing a video game character. You are {name}, a {job} in a "
            f"{env} called {env_name}. This environment is in a fantasy setting, so limit "
            f"discussions to the environment, the npc's job, and the npc's hobbies. The npc's "
            f"personality is {personality}. The npc's hobbies are {hobby}.\n\n"
            "Always follow these rules:\n"
            "1. do not speak for the player\n"
            "2. do not Roleplay heavily\n"
            "3. do not break the fourth wall\n"
            "4. do not hallucinate\n"
            "5. converse with the NPC but maintain conversational context\n"
            "6. Only generate one response at a time"
        )

    def npc_greeting(self, name: str, identity: str) -> LLMRequest:
        return LLMRequest(
            system=identity,
            examples=[],
            user_message=(
                "You see the player approaching you. "
                "Greet them simply based on your personality."
            ),
            max_tokens=50,
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
                "You are a stable diffusion prompt generator. You will be given a brief "
                "description of a person and you will output a prompt for stable diffusion. "
                "The prompt should be short, in the fashion of a high fantasy/snes video game "
                "style and stay on topic based on the persons details."
            ),
            examples=[
                (
                    str({"name": "Duran", "job": "fighter", "personality": "brooding",
                         "hobby": "swordsplay", "environment": "city",
                         "environment_name": "Capital City"}),
                    "A precocious warrior, clad in steel armor with a great sword over his "
                    "shoulder. He has long red hair, untamed and wild. He stands in a bustling "
                    "city square, scanning the crowd."
                ),
                (
                    str({"name": "Angela", "job": "mage", "personality": "princess",
                         "hobby": "naughty", "environment": "city",
                         "environment_name": "Magic Ice Kingdom of Altena"}),
                    "A sexy mage with long flowing blonde hair, naughty and dressed in a "
                    "revealing short purple dress. She looks playful standing alone in a "
                    "snowy town square"
                ),
                (
                    str({"name": "Kevin", "job": "monk", "personality": "mischievous",
                         "hobby": "goofing off", "environment": "forest",
                         "environment_name": "Dark Forest"}),
                    "A mischievous half beast-half man monk with a playful grin, dressed in "
                    "animal skins. Half wolf man, he has shaggy brown fur and is standing in "
                    "a dark forest, surrounded by tall trees and mist."
                ),
            ],
            user_message=str(personality_doc),
            max_tokens=40,
        )


def _history_to_examples(history: list[dict]) -> list[tuple[str, str]]:
    """Convert neutral history dicts into (user, npc) turn pairs for few-shot."""
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
