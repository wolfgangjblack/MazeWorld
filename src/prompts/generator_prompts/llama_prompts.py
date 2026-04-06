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
                ("environment: 'forest', env_name: 'Iron Oak'",
                 "{'name': 'helena', 'job': 'herbalist', 'personality': 'mysterious', 'hobby': 'collecting herbs'}"),
                ("environment: 'desert', env_name: 'Sandstone'",
                 "{'name': 'khalid', 'job': 'merchant', 'personality': 'charming', 'hobby': 'haggling'}"),
                ("environment: 'mountain', env_name: 'Frostpeak'",
                 "{'name': 'greta', 'job': 'blacksmith', 'personality': 'gruff', 'hobby': 'forging'}"),
                ("environment: 'city', env_name: 'Silverport'",
                 "{'name': 'julius', 'job': 'guard', 'personality': 'stoic', 'hobby': 'training'}"),
                ("environment: 'swamp', env_name: 'Mosswood'",
                 "{'name': 'elara', 'job': 'alchemist', 'personality': 'eccentric', 'hobby': 'experimenting'}"),
            ],
            user_message=f"environment: '{env}', env_name: '{env_name}'",
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
                     npc_name: str, player_input: str,
                     story_context: str = "") -> LLMRequest:
        examples = _history_to_examples(history)
        system = identity
        if story_context:
            system += (
                f"\n\nWorld context you are aware of:\n{story_context}\n"
                "Weave this knowledge naturally into conversation when relevant."
            )
        return LLMRequest(
            system=system,
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


    def environment_name_generation(self, env_type: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are a fantasy location name generator. Given an environment type, "
                "output ONLY a single creative name. No explanation."
            ),
            examples=[
                ("forest", "Shadowleaf"),
                ("cave", "Gloomhollow"),
                ("dungeon", "Dreadkeep"),
                ("castle", "Whitespire"),
                ("city", "Silverport"),
            ],
            user_message=env_type,
            max_tokens=10,
        )

    def event_generation(self, env: str, env_name: str, event_type: str) -> LLMRequest:
        if event_type == "combat":
            return LLMRequest(
                system=(
                    "You generate combat encounters for a fantasy game. "
                    "Output a JSON object with: name, description, difficulty (1-5), "
                    "damage_type (health|hunger|thirst), damage_range ([min,max])."
                ),
                examples=[
                    ("environment: 'forest', env_name: 'Shadowleaf'",
                     '{"name": "Giant Spider", "description": "A massive spider drops from the canopy!", '
                     '"difficulty": 3, "damage_type": "health", "damage_range": [5, 15]}'),
                    ("environment: 'cave', env_name: 'Gloomhollow'",
                     '{"name": "Cave Troll", "description": "A hulking troll emerges from the shadows!", '
                     '"difficulty": 4, "damage_type": "health", "damage_range": [8, 20]}'),
                ],
                user_message=f"environment: '{env}', env_name: '{env_name}'",
                max_tokens=80,
            )
        else:
            return LLMRequest(
                system=(
                    "You generate puzzle encounters for a fantasy game. "
                    "Output a JSON object with: name, description, difficulty (1-5), "
                    "choices (array with: text, stat_check, tool_attribute, dc, auto_success). "
                    "Include 2-3 choices. One should be a safe walk-away option."
                ),
                examples=[
                    ("environment: 'cave', env_name: 'Gloomhollow'",
                     '{"name": "Locked Chest", "description": "A heavy chest with a strange mechanism...", '
                     '"difficulty": 2, "choices": ['
                     '{"text": "Force it open", "stat_check": "health", "tool_attribute": null, "dc": 12, "auto_success": false}, '
                     '{"text": "Walk away", "stat_check": null, "tool_attribute": null, "dc": 0, "auto_success": true}]}'),
                ],
                user_message=f"environment: '{env}', env_name: '{env_name}'",
                max_tokens=200,
            )

    def quest_generation(self, env: str, env_name: str,
                         available_npcs: list[dict], available_items: list[dict],
                         available_events: list[dict], quest_type: str) -> LLMRequest:
        context = str({
            "environment": env, "environment_name": env_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        })
        return LLMRequest(
            system=(
                "You generate quests for a fantasy game. Given context about NPCs, items, events, "
                "output a JSON object with: title, description, giver_npc_id. "
                "For fetch: add target_items [{item_id, count}]. "
                "For escort: add escort_npc_id. "
                "For delivery: add delivery_item_id, target_npc_id. "
                "For combat: add target_event_id. "
                "For dialogue_gated: add dialogue_tree with prompt and choices. "
                "Use ONLY ids from context."
            ),
            examples=[],
            user_message=context,
            max_tokens=200,
        )

    def dialogue_tree_generation(self, npc_personality: dict,
                                 quest_context: dict | None = None) -> LLMRequest:
        context = str({"npc": npc_personality, "quest": quest_context})
        return LLMRequest(
            system=(
                "You generate dialogue trees for fantasy game NPCs. "
                "Output a JSON: {nodes: {start: {prompt, choices: [{text, next_node_id}]}, ...}}. "
                "3-5 nodes. Stay in character."
            ),
            examples=[],
            user_message=context,
            max_tokens=400,
        )

    def item_generation(self, env: str, env_name: str, room_level: int) -> LLMRequest:
        return LLMRequest(
            system=(
                "You generate environment-themed items for a fantasy game. "
                "Output a JSON object with keys: food (4 items), drink (4 items), "
                "tools (3 items), weapons (3 items), spell_scrolls (2 items). "
                "Each food: {name, desc, nutrition_value, health_value}. "
                "Each drink: {name, desc, hydration_value, health_value}. "
                "Each tool: {name, desc, attribute (bludgeon|cutting|digging|climbing)}. "
                "Each weapon: {name, desc, weapon_type (heavy|light|simple), stat_modifier (STR|DEX|INT)}. "
                "Each spell_scroll: {name, desc, spell_effect (heal|damage|shield|reveal|sustain)}. "
                "Items must be thematic to the environment."
            ),
            examples=[
                (
                    "environment: 'forest', name: 'Whisperwood', room_level: 1",
                    '{"food": [{"name": "forest bread", "desc": "Hearty bread baked with acorn flour.", '
                    '"nutrition_value": 20, "health_value": 0}, {"name": "wild berries", '
                    '"desc": "Sweet ripe berries.", "nutrition_value": 10, "health_value": 5}, '
                    '{"name": "roasted rabbit", "desc": "Campfire-roasted rabbit.", '
                    '"nutrition_value": 25, "health_value": 10}, {"name": "honey cake", '
                    '"desc": "Sticky-sweet cake with wild honey.", "nutrition_value": 15, "health_value": 5}], '
                    '"drink": [{"name": "spring water", "desc": "Cool forest spring water.", '
                    '"hydration_value": 15, "health_value": 0}, {"name": "herbal tea", '
                    '"desc": "Soothing forest herb tea.", "hydration_value": 20, "health_value": 10}, '
                    '{"name": "berry juice", "desc": "Fresh wild berry juice.", '
                    '"hydration_value": 10, "health_value": 5}, {"name": "dew drops", '
                    '"desc": "Morning dew from broad leaves.", "hydration_value": 10, "health_value": 0}], '
                    '"tools": [{"name": "hatchet", "desc": "A small hatchet.", "attribute": "cutting"}, '
                    '{"name": "climbing vines", "desc": "Strong woven vines.", "attribute": "climbing"}, '
                    '{"name": "root digger", "desc": "Curved digging tool.", "attribute": "digging"}], '
                    '"weapons": [{"name": "wooden bow", "desc": "A yew short bow.", '
                    '"weapon_type": "light", "stat_modifier": "DEX"}, '
                    '{"name": "oak club", "desc": "Heavy oak club.", '
                    '"weapon_type": "heavy", "stat_modifier": "STR"}, '
                    '{"name": "thorn staff", "desc": "Enchanted thorn staff.", '
                    '"weapon_type": "simple", "stat_modifier": "INT"}], '
                    '"spell_scrolls": [{"name": "scroll of entangle", '
                    '"desc": "Vines ensnare your foes.", "spell_effect": "shield"}, '
                    '{"name": "scroll of regrowth", "desc": "Nature mends wounds.", '
                    '"spell_effect": "heal"}]}'
                ),
            ],
            user_message=f"environment: '{env}', name: '{env_name}', room_level: {room_level}",
            max_tokens=600,
        )

    def item_image_description(self, item_data: dict) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are a stable diffusion prompt generator for game items. "
                "Output a short visual description of the item, high fantasy style."
            ),
            examples=[
                (str({"name": "hammer", "desc": "A craftsman's hammer"}),
                 "A sturdy iron hammer with a worn leather grip, resting on a workbench."),
            ],
            user_message=str(item_data),
            max_tokens=40,
        )

    def event_image_description(self, event_data: dict) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are a stable diffusion prompt generator for game encounters. "
                "Output a short scene illustration description, high fantasy style."
            ),
            examples=[
                (str({"name": "Giant Spider", "type": "combat"}),
                 "A giant spider descending from dark forest canopy, silk threads glistening."),
            ],
            user_message=str(event_data),
            max_tokens=40,
        )

    def player_image_description(self) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are a stable diffusion prompt generator. Generate a visual description "
                "for a default adventurer player character portrait. High fantasy pixel art style."
            ),
            examples=[],
            user_message="Generate a default player character portrait.",
            max_tokens=40,
        )


    def class_generation(self, env: str, env_name: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You generate 4 player classes for a fantasy RPG. Output a JSON array of 4 objects. "
                "Each: name, archetype (warrior|mage|healer|jester), flavor_text, starting_weapon, "
                "stats ({STR,DEX,CON,INT,WIS,CHA,LUCK} totaling 72), "
                "abilities [{name,description,stat,cost_hunger,cost_thirst}], "
                "spells [{name,description,element,damage_dice,spell_type,cost_hunger,cost_thirst}], "
                "portrait_prompt, ability_pool (4 extra abilities), spell_pool (4 extra spells). "
                "Warrior: STR/CON 14-18, 4 abilities, no spells. "
                "Mage: INT 14-18, 4 spells (2 damage, 2 utility). "
                "Healer: WIS 14-18, 4 spells (1 heal, 1 buff, 1 damage, 1 utility). "
                "Jester: LUCK 14-18, random 0-3 from others."
            ),
            examples=[],
            user_message=f"environment: '{env}', env_name: '{env_name}'",
            max_tokens=2000,
        )

    def class_portrait_description(self, class_data: dict) -> LLMRequest:
        return LLMRequest(
            system=(
                "You generate image prompts for fantasy RPG character portraits. "
                "Output a short visual description. High fantasy pixel art style."
            ),
            examples=[
                (str({"name": "Ranger", "archetype": "warrior", "environment": "forest"}),
                 "A rugged ranger in green leather, longbow on back, standing in a forest clearing."),
            ],
            user_message=str(class_data),
            max_tokens=60,
        )


    def story_generation(self, story_seed: str, room_count: int,
                         environments: list[str]) -> LLMRequest:
        context = str({
            "story_seed": story_seed,
            "room_count": room_count,
            "environments": environments,
        })
        return LLMRequest(
            system=(
                "You generate overarching stories for a fantasy game. "
                "Output a JSON: {title, synopsis, faction: {name, description, leader}, "
                "escalation_arc: [per-room strings], climax, final_boss_name, "
                "key_npc_names: [strings], beats: [{room_id, summary, faction_presence, escalation}]}. "
                "One beat per room. escalation 1-5 increasing."
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
        context = str({
            "environment": env, "environment_name": env_name,
            "story_beat": story_beat, "faction_name": faction_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        })
        return LLMRequest(
            system=(
                "You generate story quests for a fantasy game referencing a faction and story beat. "
                "Output JSON: {title, description, giver_npc_id, is_story_quest: true}. "
                "Add type-specific fields. Use ONLY ids from context."
            ),
            examples=[],
            user_message=context,
            max_tokens=300,
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
