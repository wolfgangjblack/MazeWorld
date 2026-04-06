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


    def environment_name_generation(self, env_type: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You name fantasy locations for a video game. Given an environment type, "
                "respond with ONLY a single creative name for that place. "
                "No punctuation, no explanation, just the name."
            ),
            examples=[
                ("forest", "Shadowleaf"),
                ("cave", "Gloomhollow"),
                ("city", "Silverport"),
            ],
            user_message=env_type,
            max_tokens=10,
        )

    def event_generation(self, env: str, env_name: str, event_type: str) -> LLMRequest:
        if event_type == "combat":
            return LLMRequest(
                system=(
                    "You generate combat encounter descriptions for a fantasy game. "
                    "Given an environment, respond with ONLY a JSON object with keys: "
                    "name, description, difficulty (1-5), damage_type (health|hunger|thirst), "
                    "damage_range ([min, max]). Keep it thematic."
                ),
                examples=[
                    (
                        "environment: 'forest', name: 'Shadowleaf'",
                        json.dumps({"name": "Giant Spider", "description": "A massive spider drops from the canopy!",
                                    "difficulty": 3, "damage_type": "health", "damage_range": [5, 15]}),
                    ),
                ],
                user_message=f"environment: '{env}', name: '{env_name}'",
                max_tokens=100,
            )
        else:
            return LLMRequest(
                system=(
                    "You generate puzzle encounter descriptions for a fantasy game. "
                    "Given an environment, respond with ONLY a JSON object with keys: "
                    "name, description, difficulty (1-5), choices (array of objects with: "
                    "text, stat_check (health|hunger|thirst|null), tool_attribute "
                    "(bludgeon|cutting|digging|climbing|null), dc (number), auto_success (bool)). "
                    "Include 2-3 choices, one should be a safe 'walk away' option."
                ),
                examples=[
                    (
                        "environment: 'cave', name: 'Gloomhollow'",
                        json.dumps({
                            "name": "Locked Chest", "description": "A heavy chest with a strange mechanism...",
                            "difficulty": 2,
                            "choices": [
                                {"text": "Force it open", "stat_check": "health", "tool_attribute": None, "dc": 12, "auto_success": False},
                                {"text": "Pick the lock", "stat_check": None, "tool_attribute": "cutting", "dc": 8, "auto_success": False},
                                {"text": "Walk away", "stat_check": None, "tool_attribute": None, "dc": 0, "auto_success": True},
                            ]
                        }),
                    ),
                ],
                user_message=f"environment: '{env}', name: '{env_name}'",
                max_tokens=250,
            )

    def quest_generation(self, env: str, env_name: str,
                         available_npcs: list[dict], available_items: list[dict],
                         available_events: list[dict], quest_type: str) -> LLMRequest:
        context = json.dumps({
            "environment": env, "environment_name": env_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        })
        return LLMRequest(
            system=(
                "You generate quests for a fantasy game. Given context about available NPCs, "
                "items, and events, respond with ONLY a JSON object with keys: "
                "title, description, giver_npc_id (int from available NPCs). "
                "For fetch quests also include target_items: [{item_id, count}]. "
                "For escort quests include escort_npc_id. "
                "For delivery quests include delivery_item_id and target_npc_id. "
                "For combat quests include target_event_id. "
                "For dialogue_gated quests include a simple dialogue_tree with prompt and choices. "
                "Use ONLY ids from the provided context."
            ),
            examples=[],
            user_message=context,
            max_tokens=200,
        )

    def dialogue_tree_generation(self, npc_personality: dict,
                                 quest_context: dict | None = None) -> LLMRequest:
        context = json.dumps({"npc": npc_personality, "quest": quest_context})
        return LLMRequest(
            system=(
                "You generate dialogue trees for a fantasy game NPC. "
                "Respond with ONLY a JSON object representing a dialogue tree. Format: "
                '{"nodes": {"start": {"prompt": "NPC says...", '
                '"choices": [{"text": "Player option", "next_node_id": "node2"}, ...]}, '
                '"node2": {"prompt": "...", "choices": [...]}, '
                '"end": {"prompt": "Farewell!", "choices": []}}}. '
                "Keep it 3-5 nodes deep. Stay in character."
            ),
            examples=[],
            user_message=context,
            max_tokens=400,
        )

    def item_image_description(self, item_data: dict) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are an image prompt generator for a pixel-art fantasy game. "
                "Given item details as JSON, output a short visual description suitable "
                "for an image generator. Focus on the item's appearance and style. "
                "Output ONLY the description."
            ),
            examples=[
                (
                    json.dumps({"name": "hammer", "desc": "A craftsman's hammer", "category": "tool"}),
                    "A sturdy iron hammer with a worn leather grip, resting on a wooden workbench."
                ),
            ],
            user_message=json.dumps(item_data),
            max_tokens=60,
        )

    def event_image_description(self, event_data: dict) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are an image prompt generator for a pixel-art fantasy game. "
                "Given event details as JSON, output a short scene illustration description "
                "suitable for an image generator. Focus on the scene, atmosphere, and danger. "
                "Output ONLY the description."
            ),
            examples=[
                (
                    json.dumps({"name": "Giant Spider", "type": "combat", "description": "A massive spider drops from the canopy!"}),
                    "A giant spider descending from dark forest canopy, silk threads glistening, menacing fangs visible."
                ),
            ],
            user_message=json.dumps(event_data),
            max_tokens=60,
        )

    def player_image_description(self) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are an image prompt generator for a pixel-art fantasy game. "
                "Generate a visual description for a default player character portrait. "
                "The character is a young adventurer. Output ONLY the description."
            ),
            examples=[],
            user_message="Generate a default player character portrait description.",
            max_tokens=60,
        )


    def class_generation(self, env: str, env_name: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You generate 4 player class options for a fantasy RPG themed to an environment. "
                "Respond with ONLY a JSON array of 4 objects. Each object has:\n"
                "- name: thematic class name (e.g., 'Ranger' not 'Warrior')\n"
                "- archetype: one of warrior, mage, healer, jester\n"
                "- flavor_text: 1-2 sentence description\n"
                "- starting_weapon: a weapon name\n"
                "- stats: {STR, DEX, CON, INT, WIS, CHA, LUCK} — integers, total MUST equal 72\n"
                "  Warrior: STR,CON 14-18; DEX,CHA 11-14; INT,WIS 6-10; LUCK 6-10\n"
                "  Mage: INT 14-18; WIS,DEX 11-14; STR,CON,CHA 6-10; LUCK 6-10\n"
                "  Healer: WIS 14-18; CHA,CON 11-14; STR,DEX,INT 6-10; LUCK 6-10\n"
                "  Jester: LUCK 14-18; all others 11-14 except 1 random dump stat 6-10\n"
                "- abilities: array of {name, description, stat, cost_hunger, cost_thirst}\n"
                "  Warrior gets 4 utility abilities (break door, intimidate, bash, rally type)\n"
                "  Jester gets 0-3 random abilities from other classes\n"
                "- spells: array of {name, description, element, damage_dice, spell_type, cost_hunger, cost_thirst}\n"
                "  Mage: 1 element + 4 spells (2 damage, 2 utility), elements: fire|water|forest|light|dark\n"
                "  Healer: 1 element + 4 spells (1 heal, 1 buff, 1 damage, 1 utility)\n"
                "  Warrior: no spells. Jester: random 0-3 from other classes\n"
                "- portrait_prompt: visual description for image generation\n"
                "- ability_pool: 4 additional abilities/spells beyond starting set (for level-ups)\n"
                "- spell_pool: 4 additional spells beyond starting set (for level-ups)\n"
                "Output order: warrior, mage, healer, jester."
            ),
            examples=[],
            user_message=f"environment: '{env}', name: '{env_name}'",
            max_tokens=2000,
        )

    def class_portrait_description(self, class_data: dict) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are an image prompt generator for a pixel-art fantasy game. "
                "Given a player class, output a short visual description for a character portrait. "
                "Focus on appearance, gear, pose, and class identity. Output ONLY the description."
            ),
            examples=[
                (
                    json.dumps({"name": "Ranger", "archetype": "warrior",
                                "starting_weapon": "longbow", "environment": "forest"}),
                    "A rugged ranger in forest-green leather armor, longbow slung across their back, "
                    "standing in a sun-dappled forest clearing with keen eyes scanning the treeline."
                ),
            ],
            user_message=json.dumps(class_data),
            max_tokens=80,
        )


    def story_generation(self, story_seed: str, room_count: int,
                         environments: list[str]) -> LLMRequest:
        context = json.dumps({
            "story_seed": story_seed,
            "room_count": room_count,
            "environments": environments,
        })
        return LLMRequest(
            system=(
                "You generate overarching stories for a fantasy dungeon-crawling game. "
                "Given a story seed, room count, and environment list, respond with ONLY a JSON object:\n"
                "{\n"
                '  "title": "story title",\n'
                '  "synopsis": "2-3 sentence overview",\n'
                '  "faction": {"name": "...", "description": "...", "leader": "..."},\n'
                '  "escalation_arc": ["room 1 escalation description", "room 2...", ...],\n'
                '  "climax": "description of final confrontation",\n'
                '  "final_boss_name": "name of the final boss",\n'
                '  "key_npc_names": ["important NPC name 1", "..."],\n'
                '  "beats": [{"room_id": "room_0", "summary": "...", "faction_presence": "...", "escalation": 1}, ...]\n'
                "}\n"
                "The escalation_arc should have one entry per room, increasing in tension. "
                "Beats array should have one entry per room. "
                "faction_presence describes how the faction manifests in that room. "
                "escalation is 1-5, increasing per room."
            ),
            examples=[],
            user_message=context,
            max_tokens=800,
        )

    def story_quest_generation(self, env: str, env_name: str,
                               story_beat: str, faction_name: str,
                               available_npcs: list[dict],
                               available_items: list[dict],
                               available_events: list[dict],
                               quest_type: str) -> LLMRequest:
        context = json.dumps({
            "environment": env, "environment_name": env_name,
            "story_beat": story_beat, "faction_name": faction_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        })
        return LLMRequest(
            system=(
                "You generate story-connected quests for a fantasy game. The quest MUST reference "
                "the faction and story beat provided. Respond with ONLY a JSON object with keys: "
                "title, description, giver_npc_id (int from available NPCs), is_story_quest (true). "
                "For fetch quests: target_items [{item_id, count}]. "
                "For escort quests: escort_npc_id. "
                "For delivery quests: delivery_item_id, target_npc_id. "
                "For combat quests: target_event_id, target_monster_name. "
                "For dialogue quests: dc (10-18), dialogue_tree. "
                "For multi_step: sub_quest_ids (leave empty, will be filled). "
                "Use ONLY ids from the provided context. "
                "Make the quest title and description reference the faction and story."
            ),
            examples=[],
            user_message=context,
            max_tokens=300,
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
