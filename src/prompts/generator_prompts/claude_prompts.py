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
                     npc_name: str, player_input: str,
                     story_context: str = "") -> LLMRequest:
        examples = _history_to_examples(history)
        system = identity
        if story_context:
            system += (
                f"\n\nWorld context you are aware of:\n{story_context}\n"
                "Weave this knowledge naturally into conversation when relevant — "
                "gossip, warnings, rumors, or opinions about the faction and events."
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

    def event_generation(self, env: str, env_name: str, event_type: str,
                         story_context: str = "") -> LLMRequest:
        ctx_suffix = (
            f"\n\nWorld Bible context (use for thematic coherence):\n{story_context}"
            if story_context else ""
        )
        if event_type == "combat":
            return LLMRequest(
                system=(
                    "You generate combat encounter descriptions for a fantasy game. "
                    "Given an environment, respond with ONLY a JSON object with keys: "
                    "name, description, difficulty (1-5), damage_type (health|hunger|thirst), "
                    "damage_range ([min, max]). Keep it thematic and reference the world "
                    "lore when provided."
                ),
                examples=[
                    (
                        "environment: 'forest', name: 'Shadowleaf'",
                        json.dumps({"name": "Giant Spider", "description": "A massive spider drops from the canopy!",
                                    "difficulty": 3, "damage_type": "health", "damage_range": [5, 15]}),
                    ),
                ],
                user_message=f"environment: '{env}', name: '{env_name}'{ctx_suffix}",
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
                    "Include 2-3 choices, one should be a safe 'walk away' option. "
                    "Reference the world lore when provided."
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
                user_message=f"environment: '{env}', name: '{env_name}'{ctx_suffix}",
                max_tokens=250,
            )

    def quest_generation(self, env: str, env_name: str,
                         available_npcs: list[dict], available_items: list[dict],
                         available_events: list[dict], quest_type: str,
                         story_context: str = "") -> LLMRequest:
        ctx_data: dict = {
            "environment": env, "environment_name": env_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        }
        if story_context:
            ctx_data["world_bible_context"] = story_context[:500]
        context = json.dumps(ctx_data)
        return LLMRequest(
            system=(
                "You generate quests for a fantasy game. Given context about available NPCs, "
                "items, events, and world lore, respond with ONLY a JSON object with keys: "
                "title, description, giver_npc_id (int from available NPCs). "
                "For fetch quests also include target_items: [{item_id, count}]. "
                "For escort quests include escort_npc_id. "
                "For delivery quests include delivery_item_id and target_npc_id. "
                "For combat quests include target_event_id. "
                "For dialogue_gated quests include a simple dialogue_tree with prompt and choices. "
                "Use ONLY ids from the provided context. "
                "Reference the world lore to make quests narratively coherent."
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

    def item_generation(self, env: str, env_name: str, room_level: int,
                        story_context: str = "") -> LLMRequest:
        return LLMRequest(
            system=(
                "You generate items for a fantasy video game. Given an environment type, "
                "environment name, and room level, generate a JSON object with item pools. "
                "Items MUST be thematic to the environment and world lore.\n\n"
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
            user_message=(
                f"environment: '{env}', name: '{env_name}', room_level: {room_level}"
                + (f"\n\nWorld Bible context (use for flavor text):\n{story_context[:400]}"
                   if story_context else "")
            ),
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
                "- abilities: array of {name, description, stat, hunger_cost, thirst_cost}\n"
                "  Warrior gets 4 utility abilities (break door, intimidate, bash, rally type)\n"
                "  Jester gets 0-3 random abilities from other classes\n"
                "- spells: array of {name, description, element, damage_dice, spell_type, hunger_cost, thirst_cost}\n"
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
                               quest_type: str,
                               story_context: str = "") -> LLMRequest:
        ctx_data: dict = {
            "environment": env, "environment_name": env_name,
            "story_beat": story_beat, "faction_name": faction_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        }
        if story_context:
            ctx_data["world_bible_context"] = story_context[:500]
        context = json.dumps(ctx_data)
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


    def full_story_generation(self, story_seed: str, room_count: int,
                              environments: list[str]) -> LLMRequest:
        context = json.dumps({
            "story_seed": story_seed,
            "room_count": room_count,
            "environments": environments,
        })
        return LLMRequest(
            system=(
                "You generate a COMPLETE world story for a fantasy dungeon-crawling game. "
                "This includes the overarching narrative AND all story-important entities.\n\n"
                "Given a story seed, room count, and environment list, respond with ONLY a JSON object:\n"
                "{\n"
                '  "title": "story title",\n'
                '  "synopsis": "2-3 sentence lore overview — this is the WORLD BIBLE synopsis",\n'
                '  "faction": {"name": "...", "description": "full faction lore paragraph", "history": "how faction came to power", "leader": "leader name"},\n'
                '  "escalation_arc": ["room 1 escalation description", ...],\n'
                '  "climax": "full paragraph describing the final confrontation",\n'
                '  "final_boss_name": "name",\n'
                '  "final_boss_lore": "full paragraph: who they are, why they do this, their powers",\n'
                '  "beats": [{"room_id": "room_0", "summary": "full paragraph story beat", "faction_presence": "...", "escalation": 1, "boss_name": "room boss name or empty", "boss_lore": "why this boss guards this room"}, ...],\n'
                '  "story_npcs": [{"name": "...", "role": "ally|betrayer|quest_giver|faction_leader", "backstory": "full lore paragraph", "room_id": "room_0", "personality": "...", "job": "..."}, ...],\n'
                '  "story_items": [{"name": "...", "description": "...", "lore": "full paragraph: why it matters to the story", "room_id": "room_0"}, ...],\n'
                '  "story_monsters": [{"name": "...", "description": "...", "lore": "full paragraph: its history and role", "room_id": "room_0", "is_boss": true/false, "species": "..."}, ...]\n'
                "}\n\n"
                "REQUIREMENTS:\n"
                "- Generate 2-4 story NPCs (named characters central to the narrative)\n"
                "- Generate 1-2 story items (artifacts or key items)\n"
                "- Generate 1 boss per room + the final boss (story_monsters with is_boss=true)\n"
                "- Every entity needs a FULL LORE PARAGRAPH (3-5 sentences minimum), not just a label\n"
                "- The story should feel like a living world: interconnected characters, motivations, betrayals\n"
                "- Beats array: one entry per room, escalation 1-5 increasing"
            ),
            examples=[],
            user_message=context,
            max_tokens=2500,
        )

    def monster_generation(self, env: str, env_name: str, room_level: int,
                           story_context: str) -> LLMRequest:
        context = json.dumps({
            "environment": env,
            "environment_name": env_name,
            "room_level": room_level,
        })
        return LLMRequest(
            system=(
                "You generate monsters for a fantasy dungeon-crawling game room. "
                "Generate 4-6 monster types themed to the environment.\n\n"
                f"World context:\n{story_context}\n\n"
                "Respond with ONLY a JSON array of monster objects:\n"
                '[{"name": "...", "species": "...", "description": "...", "backstory": "full lore paragraph", '
                '"level": N, "hp": N, "ac": N, "damage_type": "physical|fire|water|forest|light|dark", '
                '"elemental_affinity": "fire|water|forest|light|dark|null", '
                '"time_availability": "always|night_only|day_only", '
                '"abilities": [{"name": "...", "effect_type": "damage|poison|stun", "damage_dice": "1d6", "chance": 0.3}], '
                '"portrait_prompt": "visual description for pixel art"}]\n\n'
                "Some monsters should be faction-related if the story context mentions a faction. "
                "At least 1 monster should be night_only. "
                "Scale stats to room_level (1=easy, 4=hard)."
            ),
            examples=[],
            user_message=context,
            max_tokens=1200,
        )

    def npc_backstory_generation(self, npc_data: dict,
                                 story_context: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You write NPC backstories for a fantasy game. Given NPC details and world context, "
                "generate a rich backstory paragraph (3-5 sentences) that references the world lore.\n\n"
                f"World context:\n{story_context}\n\n"
                "Respond with ONLY the backstory paragraph — no JSON, no labels."
            ),
            examples=[
                (
                    json.dumps({"name": "Greta", "job": "blacksmith", "environment": "cave"}),
                    "Greta has hammered iron in the depths of Gloomhollow for twenty years, "
                    "ever since the Shadow Cult drove her family from the surface. She forges "
                    "weapons for the resistance, hiding them in false walls. Her masterwork — "
                    "a silver-edged blade — was stolen by a cult spy, and she'll pay handsomely "
                    "to get it back."
                ),
            ],
            user_message=json.dumps(npc_data),
            max_tokens=200,
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
