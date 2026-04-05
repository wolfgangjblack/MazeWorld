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

    def item_generation(self, env: str, env_name: str, room_level: int) -> LLMRequest:
        return LLMRequest(
            system=(
                "You generate items for a fantasy video game. Given an environment type, "
                "environment name, and room level, generate a JSON object with item pools. "
                "Items MUST be thematic to the environment.\n\n"
                "Return ONLY a JSON object with these keys:\n"
                "- food: array of 4 items, each {name, desc, nutrition_value (10-30), health_value (0-15)}\n"
                "- drink: array of 4 items, each {name, desc, hydration_value (10-30), health_value (0-15)}\n"
                "- tools: array of 3 items, each {name, desc, attribute (bludgeon|cutting|digging|climbing)}\n"
                "- weapons: array of 3 items, each {name, desc, weapon_type (heavy|light|simple), stat_modifier (STR|DEX|INT)}\n"
                "- spell_scrolls: array of 2 items, each {name, desc, spell_effect (heal|damage|shield|reveal|sustain)}\n\n"
                "Environment theming examples:\n"
                "- forest: berries, spring water, hatchet, wooden bow\n"
                "- desert: dried meat, cactus juice, sandstone chisel, scimitar\n"
                "- cave: mushroom stew, underground spring, pickaxe, stone mace\n"
                "- city: pastries, ale, lockpick, rapier\n"
                "- castle: roast pheasant, fine wine, grappling hook, halberd"
            ),
            examples=[
                (
                    "environment: 'forest', name: 'Whisperwood', room_level: 1",
                    json.dumps({
                        "food": [
                            {"name": "forest bread", "desc": "Hearty bread baked with acorn flour.", "nutrition_value": 20, "health_value": 0},
                            {"name": "wild berries", "desc": "A handful of sweet, ripe berries.", "nutrition_value": 10, "health_value": 5},
                            {"name": "roasted rabbit", "desc": "A small rabbit roasted over a campfire.", "nutrition_value": 25, "health_value": 10},
                            {"name": "honey cake", "desc": "A sticky-sweet cake drizzled with wild honey.", "nutrition_value": 15, "health_value": 5},
                        ],
                        "drink": [
                            {"name": "spring water", "desc": "Cool, clear water from a forest spring.", "hydration_value": 15, "health_value": 0},
                            {"name": "herbal tea", "desc": "A soothing tea brewed from forest herbs.", "hydration_value": 20, "health_value": 10},
                            {"name": "berry juice", "desc": "Freshly squeezed juice from wild berries.", "hydration_value": 10, "health_value": 5},
                            {"name": "dew drops", "desc": "Morning dew collected from broad leaves.", "hydration_value": 10, "health_value": 0},
                        ],
                        "tools": [
                            {"name": "woodcutter's hatchet", "desc": "A small hatchet for chopping branches.", "attribute": "cutting"},
                            {"name": "climbing vines", "desc": "Strong vines woven into a makeshift rope.", "attribute": "climbing"},
                            {"name": "root digger", "desc": "A curved tool for digging up roots.", "attribute": "digging"},
                        ],
                        "weapons": [
                            {"name": "wooden bow", "desc": "A short bow carved from yew wood.", "weapon_type": "light", "stat_modifier": "DEX"},
                            {"name": "oak club", "desc": "A heavy club hewn from solid oak.", "weapon_type": "heavy", "stat_modifier": "STR"},
                            {"name": "thorn staff", "desc": "A staff wrapped in enchanted thorns.", "weapon_type": "simple", "stat_modifier": "INT"},
                        ],
                        "spell_scrolls": [
                            {"name": "scroll of entangle", "desc": "Vines erupt from the ground to ensnare.", "spell_effect": "shield"},
                            {"name": "scroll of regrowth", "desc": "Nature's magic mends your wounds.", "spell_effect": "heal"},
                        ],
                    }),
                ),
            ],
            user_message=f"environment: '{env}', name: '{env_name}', room_level: {room_level}",
            max_tokens=800,
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
