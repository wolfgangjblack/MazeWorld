import json

from config import STORY_CONTEXT_LIMIT
from src.prompts.base import LLMRequest, PromptSet

_NO_FENCES = "\nRespond with raw JSON only. Do not wrap in markdown code fences."


class ClaudePromptSet(PromptSet):
    def personality_generation(self, env: str, env_name: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You generate NPC personalities for a fantasy video game. "
                "Given an environment, respond with ONLY a JSON object with keys: "
                "name, job, personality, hobby. Keep values thematic to the environment. "
                "Do not include any text outside the JSON object." + _NO_FENCES
            ),
            examples=[
                (
                    "environment: 'forest', name: 'Iron Oak'",
                    json.dumps(
                        {"name": "helena", "job": "herbalist", "personality": "mysterious", "hobby": "collecting herbs"}
                    ),
                ),
            ],
            user_message=f"environment: '{env}', name: '{env_name}'",
            max_tokens=60,
        )

    def conversation_identity(self, name: str, job: str, personality: str, hobby: str, env: str, env_name: str) -> str:
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
            user_message=("The player approaches you for the first time. Give a brief, in-character greeting."),
            max_tokens=80,
        )

    def npc_response(
        self,
        identity: str,
        history: list[dict],
        npc_name: str,
        player_input: str,
        story_context: str = "",
        quest_context: dict | None = None,
    ) -> LLMRequest:
        examples = _history_to_examples(history)
        system = identity
        if story_context:
            system += (
                f"\n\nWorld context you are aware of:\n{story_context[:STORY_CONTEXT_LIMIT]}\n"
                "Draw on this knowledge naturally — gossip, warnings, faction opinions, "
                "rumors about events — but keep each response to 1-3 sentences. "
                "Reference specifics (names, places, events) rather than vague allusions."
            )
        max_tokens = 150
        if quest_context:
            dc = quest_context.get("dc", 10)
            title = quest_context.get("title", "unknown")
            desc = quest_context.get("description", "")
            system += (
                "\n\nYou are also evaluating the player's social behavior. "
                "After your in-character response, output a JSON line on a NEW line "
                "in this exact format:\n"
                '{"dc_next": <8-20>, "tone": "<friendly|neutral|rude|threatening|off_topic>"}\n\n'
                f"dc_next: difficulty class for the NEXT interaction. Start at {dc}.\n"
                "- If the player was friendly/charming/on-topic: lower by 1-3\n"
                "- If the player was neutral: keep the same\n"
                "- If the player was rude/aggressive/off-topic: raise by 2-5\n"
                "- Clamp between 8 and 20\n\n"
                "Your personality affects tolerance: a gruff NPC raises DC slower on "
                "rudeness; a shy NPC raises it faster.\n\n"
                f'Active quest: "{title}" — {desc}'
            )
            max_tokens = 200
        return LLMRequest(
            system=system,
            examples=examples,
            user_message=player_input,
            max_tokens=max_tokens,
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
                    json.dumps(
                        {
                            "name": "Duran",
                            "job": "fighter",
                            "personality": "brooding",
                            "hobby": "swordsplay",
                            "environment": "city",
                            "environment_name": "Capital City",
                        }
                    ),
                    "A precocious warrior, clad in steel armor with a great sword over his "
                    "shoulder. He has long red hair, untamed and wild. He stands in a bustling "
                    "city square, scanning the crowd.",
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

    def event_generation(self, env: str, env_name: str, event_type: str, story_context: str = "") -> LLMRequest:
        ctx_suffix = ""
        if story_context:
            ctx_suffix = (
                f"\n\nWorld context (use to name and describe encounters using the world's "
                f"lore — faction creatures, environmental hazards tied to the story):\n"
                f"{story_context[:STORY_CONTEXT_LIMIT]}\n"
                "Be information-dense: every name and description should reinforce "
                "the world's lore and environment. Do not pad or ramble."
            )
        if event_type == "combat":
            return LLMRequest(
                system=(
                    "You generate combat encounter descriptions for a fantasy game. "
                    "Given an environment, respond with ONLY a JSON object with keys: "
                    "name, description, difficulty (1-5), damage_type (health|stamina), "
                    "damage_range ([min, max]). Name and describe encounters using the "
                    "world's lore when provided — faction creatures, story-relevant hazards." + _NO_FENCES
                ),
                examples=[
                    (
                        "environment: 'forest', name: 'Shadowleaf'",
                        json.dumps(
                            {
                                "name": "Giant Spider",
                                "description": "A massive spider drops from the canopy!",
                                "difficulty": 3,
                                "damage_type": "health",
                                "damage_range": [5, 15],
                            }
                        ),
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
                    "text, stat_check (health|stamina|null), tool_attribute "
                    "(bludgeon|cutting|digging|climbing|null), dc (number), auto_success (bool)). "
                    "Include 2-3 choices, one should be a safe 'walk away' option. "
                    "Name and describe puzzles using the world's lore when provided — "
                    "faction mechanisms, story-relevant obstacles." + _NO_FENCES
                ),
                examples=[
                    (
                        "environment: 'cave', name: 'Gloomhollow'",
                        json.dumps(
                            {
                                "name": "Locked Chest",
                                "description": "A heavy chest with a strange mechanism...",
                                "difficulty": 2,
                                "choices": [
                                    {
                                        "text": "Force it open",
                                        "stat_check": "health",
                                        "tool_attribute": None,
                                        "dc": 12,
                                        "auto_success": False,
                                    },
                                    {
                                        "text": "Pick the lock",
                                        "stat_check": None,
                                        "tool_attribute": "cutting",
                                        "dc": 8,
                                        "auto_success": False,
                                    },
                                    {
                                        "text": "Walk away",
                                        "stat_check": None,
                                        "tool_attribute": None,
                                        "dc": 0,
                                        "auto_success": True,
                                    },
                                ],
                            }
                        ),
                    ),
                ],
                user_message=f"environment: '{env}', name: '{env_name}'{ctx_suffix}",
                max_tokens=250,
            )

    def quest_generation(
        self,
        env: str,
        env_name: str,
        available_npcs: list[dict],
        available_items: list[dict],
        available_events: list[dict],
        quest_type: str,
        story_context: str = "",
    ) -> LLMRequest:
        ctx_data: dict = {
            "environment": env,
            "environment_name": env_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        }
        if story_context:
            ctx_data["world_bible_context"] = story_context[:STORY_CONTEXT_LIMIT]
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
                "Use ONLY ids from the provided context.\n\n"
                "Quest titles and descriptions MUST reference the world's faction, environment, "
                "or story from world_bible_context. Make objectives feel like part of the living "
                "world, not generic fetch/kill tasks. Be information-dense: every detail should "
                "add gameplay or lore value. Do not pad or ramble." + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=200,
        )

    def dialogue_tree_generation(self, npc_personality: dict, quest_context: dict | None = None) -> LLMRequest:
        context = json.dumps({"npc": npc_personality, "quest": quest_context})

        if quest_context and quest_context.get("quest_type") == "combat":
            system = (
                "You generate dialogue trees for a HOSTILE NPC in a fantasy game. "
                "This NPC is an enemy the player must defeat in combat. "
                "Respond with ONLY a JSON object containing THREE dialogue trees:\n\n"
                '1. "incomplete" — the NPC\'s taunt/threat before combat (1-2 nodes). '
                "Aggressive, in-character. They challenge the player, explain why "
                "they're hostile, reference their backstory and the faction conflict. "
                "End with a combat declaration.\n\n"
                '2. "complete_success" — shown AFTER the player defeats this NPC (2-3 nodes). '
                "The NPC yields and is no longer hostile. They may share information, "
                "express grudging respect, reveal lore about the faction, or offer a warning. "
                "Use the success_dialogue hint as a tone guide. "
                "The player should feel this NPC is now an ally or neutral.\n\n"
                '3. "complete_failure" — shown if the player fled or failed (1-2 nodes). '
                "The NPC taunts them for running. Still hostile, still dangerous. "
                "Use the failure_dialogue hint as a tone guide.\n\n"
                'Format: {"incomplete": {"nodes": {"start": {"prompt": "...", '
                '"choices": [{"text": "...", "next_node_id": "..."}]}, ..., '
                '"end": {"prompt": "...", "choices": []}}}, '
                '"complete_success": {"nodes": {...}}, '
                '"complete_failure": {"nodes": {...}}}.\n\n'
                "Use the NPC's personality, job, and backstory to shape their voice. "
                "Stay in character. Reference the story context." + _NO_FENCES
            )
            max_tokens = 1000
        elif quest_context:
            system = (
                "You generate dialogue trees for a fantasy game NPC who has a quest. "
                "Respond with ONLY a JSON object containing THREE dialogue trees:\n\n"
                '1. "incomplete" — shown while the quest is active (3-5 nodes). '
                "Introduce the NPC, describe the quest and why it matters to them. "
                "End node: urge the player to complete the quest.\n\n"
                '2. "complete_success" — shown after quest success (2-3 nodes). '
                "Thank the player, explain what changed, give a grateful farewell. "
                "Use the success_dialogue hint from quest context as a tone guide.\n\n"
                '3. "complete_failure" — shown after quest failure (2-3 nodes). '
                "Acknowledge the attempt, reflect with semi-disappointment, give a resigned farewell. "
                "Use the failure_dialogue hint from quest context as a tone guide.\n\n"
                'Format: {"incomplete": {"nodes": {"start": {"prompt": "...", '
                '"choices": [{"text": "...", "next_node_id": "..."}]}, ..., '
                '"end": {"prompt": "...", "choices": []}}}, '
                '"complete_success": {"nodes": {...}}, '
                '"complete_failure": {"nodes": {...}}}.\n\n'
                "Use the NPC's personality, hobby, and personality_notes to shape their voice and word choice. "
                "Stay in character. Reference the quest title and story context." + _NO_FENCES
            )
            max_tokens = 1000
        else:
            system = (
                "You generate dialogue trees for a fantasy game NPC. "
                "Respond with ONLY a JSON object representing a dialogue tree. Format: "
                '{"nodes": {"start": {"prompt": "NPC says...", '
                '"choices": [{"text": "Player option", "next_node_id": "node2"}, ...]}, '
                '"node2": {"prompt": "...", "choices": [...]}, '
                '"end": {"prompt": "Farewell!", "choices": []}}}. '
                "Use the NPC's personality, hobby, and personality_notes to shape their voice and word choice. "
                "Keep it 3-5 nodes deep. Stay in character." + _NO_FENCES
            )
            max_tokens = 400

        return LLMRequest(
            system=system,
            examples=[],
            user_message=context,
            max_tokens=max_tokens,
        )

    def item_generation(self, env: str, env_name: str, room_level: int, story_context: str = "") -> LLMRequest:
        lore_suffix = ""
        if story_context:
            lore_suffix = (
                f"\n\nWorld context (theme items to both the environment AND the world's "
                f"faction/story — reference it, don't repeat it verbatim):\n"
                f"{story_context[:STORY_CONTEXT_LIMIT]}\n"
                "Be information-dense: item names and descriptions should reinforce "
                "the world's lore. Do not pad or ramble."
            )
        return LLMRequest(
            system=(
                "You generate items for a fantasy video game. Given an environment type, "
                "environment name, and room level, generate a JSON object with item pools. "
                "Items MUST be thematic to the environment and world lore.\n\n"
                "Return ONLY a JSON object with these keys:\n"
                "- food: array of 4 items, each {name, desc}\n"
                "- drink: array of 4 items, each {name, desc}\n"
                "- tools: array of 3 items, each {name, desc, attribute (bludgeon|cutting|digging|climbing)}\n"
                "- weapons: array of 3 items, each {name, desc, weapon_type (heavy|light|simple), stat_modifier (STR|DEX|INT)}\n"
                "- spell_scrolls: array of 2 items, each {name, desc, spell_effect (heal|damage|shield|reveal|sustain)}\n\n"
                "Environment theming examples:\n"
                "- forest: berries, spring water, hatchet, wooden bow\n"
                "- desert: dried meat, cactus juice, sandstone chisel, scimitar\n"
                "- cave: mushroom stew, underground spring, pickaxe, stone mace\n"
                "- city: pastries, ale, lockpick, rapier\n"
                "- castle: roast pheasant, fine wine, grappling hook, halberd" + _NO_FENCES
            ),
            examples=[
                (
                    "environment: 'forest', name: 'Whisperwood', room_level: 1",
                    json.dumps(
                        {
                            "food": [
                                {"name": "forest bread", "desc": "Hearty bread baked with acorn flour."},
                                {"name": "wild berries", "desc": "A handful of sweet, ripe berries."},
                                {"name": "roasted rabbit", "desc": "A small rabbit roasted over a campfire."},
                                {"name": "honey cake", "desc": "A sticky-sweet cake drizzled with wild honey."},
                            ],
                            "drink": [
                                {"name": "spring water", "desc": "Cool, clear water from a forest spring."},
                                {"name": "herbal tea", "desc": "A soothing tea brewed from forest herbs."},
                                {"name": "berry juice", "desc": "Freshly squeezed juice from wild berries."},
                                {"name": "dew drops", "desc": "Morning dew collected from broad leaves."},
                            ],
                            "tools": [
                                {
                                    "name": "woodcutter's hatchet",
                                    "desc": "A small hatchet for chopping branches.",
                                    "attribute": "cutting",
                                },
                                {
                                    "name": "climbing vines",
                                    "desc": "Strong vines woven into a makeshift rope.",
                                    "attribute": "climbing",
                                },
                                {
                                    "name": "root digger",
                                    "desc": "A curved tool for digging up roots.",
                                    "attribute": "digging",
                                },
                            ],
                            "weapons": [
                                {
                                    "name": "wooden bow",
                                    "desc": "A short bow carved from yew wood.",
                                    "weapon_type": "light",
                                    "stat_modifier": "DEX",
                                },
                                {
                                    "name": "oak club",
                                    "desc": "A heavy club hewn from solid oak.",
                                    "weapon_type": "heavy",
                                    "stat_modifier": "STR",
                                },
                                {
                                    "name": "thorn staff",
                                    "desc": "A staff wrapped in enchanted thorns.",
                                    "weapon_type": "simple",
                                    "stat_modifier": "INT",
                                },
                            ],
                            "spell_scrolls": [
                                {
                                    "name": "scroll of entangle",
                                    "desc": "Vines erupt from the ground to ensnare.",
                                    "spell_effect": "shield",
                                },
                                {
                                    "name": "scroll of regrowth",
                                    "desc": "Nature's magic mends your wounds.",
                                    "spell_effect": "heal",
                                },
                            ],
                        }
                    ),
                ),
            ],
            user_message=(f"environment: '{env}', name: '{env_name}', room_level: {room_level}" + lore_suffix),
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
                    "A sturdy iron hammer with a worn leather grip, resting on a wooden workbench.",
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
                    json.dumps(
                        {
                            "name": "Giant Spider",
                            "type": "combat",
                            "description": "A massive spider drops from the canopy!",
                        }
                    ),
                    "A giant spider descending from dark forest canopy, silk threads glistening, menacing fangs visible.",
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
                "- abilities: array of {name, description, stat}\n"
                "  Warrior gets 4 utility abilities (break door, intimidate, bash, rally type)\n"
                "  Jester gets 0-3 random abilities from other classes\n"
                "- spells: array of {name, description, element, spell_type, stat, targets (single|multi|self)}\n"
                "  Do NOT include damage_dice, hunger_cost, thirst_cost, or stamina_cost — the system assigns these.\n"
                "  Mage: 1 element + 4 spells (2 damage, 2 utility), elements: fire|water|forest|light|dark\n"
                "  Healer: 1 element + 4 spells (1 heal, 1 buff, 1 damage, 1 utility)\n"
                "  Warrior: no spells. Jester: random 0-3 from other classes\n"
                "- portrait_prompt: visual description for image generation\n"
                "- ability_pool: 4 additional abilities/spells beyond starting set (for level-ups)\n"
                "- spell_pool: 4 additional spells beyond starting set (for level-ups)\n"
                "Output order: warrior, mage, healer, jester." + _NO_FENCES
            ),
            examples=[],
            user_message=f"environment: '{env}', name: '{env_name}'",
            max_tokens=3500,
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
                    json.dumps(
                        {
                            "name": "Ranger",
                            "archetype": "warrior",
                            "starting_weapon": "longbow",
                            "environment": "forest",
                        }
                    ),
                    "A rugged ranger in forest-green leather armor, longbow slung across their back, "
                    "standing in a sun-dappled forest clearing with keen eyes scanning the treeline.",
                ),
            ],
            user_message=json.dumps(class_data),
            max_tokens=80,
        )

    def story_generation(self, story_seed: str, room_count: int, environments: list[str]) -> LLMRequest:
        context = json.dumps(
            {
                "story_seed": story_seed,
                "room_count": room_count,
                "environments": environments,
            }
        )
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
                "escalation is 1-5, increasing per room." + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=800,
        )

    def story_quest_generation(
        self,
        env: str,
        env_name: str,
        story_beat: str,
        faction_name: str,
        available_npcs: list[dict],
        available_items: list[dict],
        available_events: list[dict],
        quest_type: str,
        story_context: str = "",
    ) -> LLMRequest:
        ctx_data: dict = {
            "environment": env,
            "environment_name": env_name,
            "story_beat": story_beat,
            "faction_name": faction_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        }
        if story_context:
            ctx_data["world_bible_context"] = story_context[:STORY_CONTEXT_LIMIT]
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
                "Use ONLY ids from the provided context.\n\n"
                "The quest title and description MUST reference the faction name, story beat, "
                "and world_bible_context. Tie the objective directly to the story's conflict — "
                "not a generic task. Be information-dense: every detail should advance the "
                "narrative. Do not pad or ramble." + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=300,
        )

    def full_story_generation(self, story_seed: str, room_count: int, environments: list[str]) -> LLMRequest:
        context = json.dumps(
            {
                "story_seed": story_seed,
                "room_count": room_count,
                "environments": environments,
            }
        )
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
                "- Beats array: one entry per room, escalation 1-5 increasing" + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=2500,
        )

    def monster_generation(
        self, env: str, env_name: str, room_level: int, story_context: str, total_rooms: int = 1
    ) -> LLMRequest:
        scale_stats_line = (
            f"Scale stats to room_level (1=easy, {total_rooms}=hard).\n"
            if total_rooms > 1
            else "Scale stats so the mix includes easy fodder monsters and one challenging boss for a single-room dungeon.\n"
        )
        context = json.dumps(
            {
                "environment": env,
                "environment_name": env_name,
                "room_level": room_level,
                "story_context": story_context[:STORY_CONTEXT_LIMIT],
            }
        )
        return LLMRequest(
            system=(
                "You generate monsters for a fantasy dungeon-crawling game room. "
                "Generate 4-6 monster types themed to the environment and story_context.\n\n"
                "RULES:\n"
                "- At least 2 monsters must be direct agents or corrupted victims of the faction "
                "named in story_context. Ground them in what that faction does.\n"
                "- Exactly 1 monster must be the room's boss (is_boss: true). The boss must have "
                "a unique proper name and title — NEVER 'Boss', 'Lieutenant', or a generic rank. "
                "Their motivation must connect to the faction's goal in story_context.\n"
                "- At least 1 monster should be night_only.\n"
                "- " + scale_stats_line + "- Use hp_range [min, max] and ac_range [min, max] instead of fixed values — "
                "actual stats will be rolled from these ranges at combat time.\n"
                "- Include a weakness field — the element this monster is vulnerable to "
                "(fire|water|forest|light|dark or null).\n\n"
                "Each monster object:\n"
                "{name, species, description, backstory (story-grounded lore paragraph), "
                "hp_range [min,max], ac_range [min,max], "
                "damage_type (physical|fire|water|forest|light|dark), "
                "physical_type (slashing|piercing|bludgeoning — based on natural attack: "
                "claws/blades=slashing, fangs/spears=piercing, fists/clubs=bludgeoning), "
                "elemental_affinity (fire|water|forest|light|dark|null), "
                "weakness (fire|water|forest|light|dark|null), "
                "time_availability (always|night_only|day_only), "
                "abilities [{name, effect_type (damage|poison|stun), damage_dice, chance}], "
                "is_boss (bool), portrait_prompt}\n\n"
                "Be information-dense. Do not pad or ramble." + _NO_FENCES
            ),
            examples=[
                (
                    json.dumps(
                        {
                            "environment": "cave",
                            "environment_name": "Stonebiter Caverns",
                            "room_level": 1,
                            "story_context": "Faction: The Brackwater Guild, led by Harrowmaster Veln. They use extortion and debt-binding to control trade. Room boss: Shrike, the Guild's Route-Closer.",
                        }
                    ),
                    json.dumps(
                        [
                            {
                                "name": "Debt-Bound Miner",
                                "species": "coerced human",
                                "description": "A miner forced into Guild service through debt contracts. Hollow-eyed and malnourished, they fight with pick-axes and no hope of escape.",
                                "backstory": "These miners signed Brackwater Guild contracts promising fair wages but found the terms adjusted weekly until every shift added to their debt. Now they swing picks at anyone who threatens the Guild's operation, knowing refusal means their family's debts double.",
                                "hp_range": [7, 12],
                                "ac_range": [8, 10],
                                "damage_type": "physical",
                                "physical_type": "piercing",
                                "elemental_affinity": None,
                                "weakness": "light",
                                "time_availability": "always",
                                "abilities": [
                                    {
                                        "name": "Desperate Strike",
                                        "effect_type": "damage",
                                        "damage_dice": "1d6",
                                        "chance": 0.3,
                                    }
                                ],
                                "is_boss": False,
                                "portrait_prompt": "a gaunt miner in worn leather armor, hollow eyes, raising a cracked pickaxe, pixel art fantasy",
                            },
                            {
                                "name": "Shrike, the Guild's Route-Closer",
                                "species": "Guild enforcer",
                                "description": "Compact and precise, Shrike carries a ledger of every debt she has collected. She fights with twin short blades and treats violence as an accounting entry.",
                                "backstory": "Shrike rose through the Brackwater Guild by being the agent Harrowmaster Veln trusted to close problematic operations quietly. She views Stonebiter Caverns as a routine assignment — extract the shipment, eliminate complications, report back. Failure is not something she has ever logged.",
                                "hp_range": [28, 38],
                                "ac_range": [13, 15],
                                "damage_type": "physical",
                                "physical_type": "slashing",
                                "elemental_affinity": None,
                                "weakness": "forest",
                                "time_availability": "always",
                                "abilities": [
                                    {
                                        "name": "Twin Slash",
                                        "effect_type": "damage",
                                        "damage_dice": "1d6",
                                        "chance": 0.4,
                                    },
                                    {"name": "Ledger Mark", "effect_type": "stun", "damage_dice": "0d0", "chance": 0.2},
                                ],
                                "is_boss": True,
                                "portrait_prompt": "a compact woman in dark leather armor with a brass-clasped ledger at her hip and two short blades drawn, pixel art fantasy villain",
                            },
                        ]
                    ),
                )
            ],
            user_message=context,
            max_tokens=2000,
        )

    def npc_backstory_generation(self, npc_data: dict, story_context: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You write NPC backstories for a fantasy game. Given NPC details and world context, "
                "generate a rich backstory paragraph (3-5 sentences) that references the world lore.\n\n"
                "World context (use to ground the backstory in the world's story, faction, "
                "and environment — reference it, don't repeat it verbatim):\n"
                f"{story_context[:STORY_CONTEXT_LIMIT]}\n\n"
                "Respond with ONLY the backstory paragraph — no JSON, no labels. "
                "Reference specific world events, faction names, or locations from the "
                "context. Each sentence should add unique narrative detail — do not pad "
                "or ramble."
            ),
            examples=[
                (
                    json.dumps({"name": "Greta", "job": "blacksmith", "environment": "cave"}),
                    "Greta has hammered iron in the depths of Gloomhollow for twenty years, "
                    "ever since the Shadow Cult drove her family from the surface. She forges "
                    "weapons for the resistance, hiding them in false walls. Her masterwork — "
                    "a silver-edged blade — was stolen by a cult spy, and she'll pay handsomely "
                    "to get it back.",
                ),
            ],
            user_message=json.dumps(npc_data),
            max_tokens=200,
        )

    # ------------------------------------------------------------------
    # Phase 3C: Batched NPC generation
    # ------------------------------------------------------------------

    def npc_batch_generation(
        self,
        room_env: dict,
        room_story: str,
        npc_slots: list[dict],
        story_context: str,
        existing_npc_names: list[str] | None = None,
    ) -> LLMRequest:
        npc_count = len(npc_slots)
        context = json.dumps(
            {
                "environment": room_env,
                "room_story": room_story,
                "npc_slots": npc_slots,
                "world_context": story_context[:STORY_CONTEXT_LIMIT],
            }
        )
        dedup_note = ""
        if existing_npc_names:
            dedup_note = "\n\nALREADY USED NPC NAMES (do NOT reuse any of these):\n" + "\n".join(
                f"- {n}" for n in existing_npc_names
            )
        return LLMRequest(
            system=(
                f"You generate a batch of exactly {npc_count} unique NPCs for a fantasy game room.\n\n"
                "RULES:\n"
                "- Each NPC must be a living witness to the room_story events in the input — "
                "their backstory, job, and personality must directly reflect the SPECIFIC "
                "situation described in room_story, not generic fantasy tropes.\n"
                "- Every name must be culturally specific to the environment type — never "
                "placeholder names. Vary jobs widely: scribes, fishwives, apothecaries, "
                "runaway apprentices, disgraced guards, travelling performers, etc.\n"
                f"- Generate EXACTLY {npc_count} NPCs in the array, one per slot in order.\n"
                "- Match each NPC's content to their assigned role: quest-givers know what "
                "they need help with, merchants know what they sell, regular NPCs know local "
                "gossip and are affected by the room_story events.\n\n"
                "Each NPC object must include:\n"
                "  name, job, personality, hobby,\n"
                "  opening_greeting (1-2 sentences, fully in character, referencing their "
                "specific situation),\n"
                "  backstory (3-5 sentences grounded in the room_story and world_context),\n"
                "  portrait_prompt (vivid visual description for pixel art generation)\n\n"
                "Respond with ONLY a JSON array of NPC objects." + dedup_note + _NO_FENCES
            ),
            examples=[
                (
                    json.dumps(
                        {
                            "environment": {"type": "cave", "name": "Stonebiter Caverns"},
                            "room_story": "The Iron Pact bandit gang has occupied these caves for months, using them as a smuggling hub. Local miners are trapped or working as forced labor. The gang's enforcer, a woman called Shrike, keeps order through fear. One miner has been secretly organizing an escape.",
                            "npc_slots": [
                                {"position": [8, 12], "role": "quest", "quest_type": "solve", "max_exchanges": 5}
                            ],
                            "world_context": "Faction: The Iron Pact, led by Warden Greiss. They control trade routes through extortion and violence.",
                        }
                    ),
                    json.dumps(
                        [
                            {
                                "name": "Torval Duskpick",
                                "job": "lead miner, secretly organizing the escape",
                                "personality": "exhausted but resolute — he has kept hope alive in the others for three months through small acts of defiance",
                                "hobby": "carving small figures from cave stone to pass time and calm his nerves",
                                "opening_greeting": "Keep moving and don't look at me. If Shrike sees us talking she'll put you in the deep shaft with the others.",
                                "backstory": "Torval was the first miner taken when the Iron Pact arrived at Stonebiter Caverns. He watched Warden Greiss shoot his crew foreman for refusing to cooperate and decided then that open resistance was suicide — instead he has spent months memorizing guard rotations, counting weapons, and quietly identifying which fellow captives still have fight left in them. He has a plan to collapse the north tunnel as a distraction while the others escape through the sump passage, but he needs someone to deal with Shrike first or she'll hunt them all down before they reach the surface.",
                                "portrait_prompt": "a stocky middle-aged miner with a cracked leather helmet and coal-dusted hands, haunted but determined eyes, hiding a small carved stone figure in his fist, pixel art fantasy portrait",
                            }
                        ]
                    ),
                )
            ],
            user_message=context,
            max_tokens=max(5000, npc_count * 400),
        )

    # ------------------------------------------------------------------
    # Phase 4A: Batched event generation
    # ------------------------------------------------------------------

    def event_batch_generation(
        self,
        room_env: dict,
        room_story: str,
        event_type: str,
        event_slots: list[dict],
        story_context: str,
        previous_summaries: list[str] | None = None,
        available_abilities: list[str] | None = None,
        available_spells: list[str] | None = None,
        available_tools: list[str] | None = None,
    ) -> LLMRequest:
        type_guidance = {
            "puzzle": (
                "Generate PUZZLE encounters — environmental/physical obstacles.\n"
                "Puzzles are about interacting with the WORLD: mechanisms, hazards, seals, collapses.\n\n"
                "Each event slot has pre_built_choices with mechanics already set (stat, dc, tool_attribute, "
                "ability_name, spell_name). You generate ONLY narrative content for each puzzle:\n"
                "- name: creative encounter name\n"
                "- description: vivid scene description (2-3 sentences, specific to environment)\n"
                "- summary: 1-2 line description of the puzzle\n"
                "- portrait_prompt: scene description for image generation (pixel art style)\n"
                "- choice_texts: array of 4 strings — one per slot (stat, tool, ability, spell). "
                "Each should contextualize that mechanic for THIS specific scene. "
                "E.g. for stat=DEX: 'Leap across the crumbling dock planks' instead of 'Use DEX'. "
                "For tool=climbing: 'Drive pitons into the rock face' instead of 'Use climbing equipment'. "
                "For ability: describe using that ability in context. For spell: describe casting it.\n"
                "- success_texts: array of 4 strings — one per slot, describing what happens on SUCCESS. "
                "E.g. 'Your fingers find every crack and you scramble across safely.'\n\n"
                "If a slot has no value (e.g. no tool_attribute), still include an empty string '' at that index.\n\n"
                "DESCRIPTION RULES:\n"
                "- Each description must be a vivid, specific scene tied to the environment.\n"
                "- Include a narrative hook: who built it, why it exists, what's at stake.\n"
                "- Do NOT write generic text like 'A puzzle blocks your path'.\n"
                "Do NOT output dc, stat_check, tool_attribute, or any mechanical fields — only narrative text."
            ),
            "event": (
                "Generate EVENT encounters — people/narrative-driven social situations.\n"
                "Events are about PEOPLE: faction encounters, moral dilemmas, social confrontations.\n\n"
                "Each event slot has pre_built_choices with mechanics already set (stat, dc, tool_attribute, "
                "ability_name, spell_name). You generate ONLY narrative content for each event:\n"
                "- name: creative encounter name\n"
                "- description: vivid scene with NAMED characters and clear stakes (2-3 sentences)\n"
                "- summary: 1-2 line description of the event and consequences\n"
                "- portrait_prompt: scene description for image generation (pixel art style)\n"
                "- choice_texts: array of 4 strings — one per slot (stat, tool, ability, spell). "
                "Each should contextualize that mechanic for THIS specific scene. "
                "E.g. for stat=CHA: 'Talk the guards down with a convincing story' instead of 'Use CHA'. "
                "For tool=bludgeon: 'Smash the lock with your hammer' instead of 'Use bludgeon equipment'. "
                "For ability/spell: describe using it in context of this social encounter.\n"
                "- success_texts: array of 4 strings — one per slot, describing what happens on SUCCESS.\n\n"
                "If a slot has no value (e.g. no spell_name), still include an empty string '' at that index.\n\n"
                "DESCRIPTION RULES:\n"
                "- Paint a specific scene with NAMED characters or groups and clear stakes.\n"
                "- Do NOT write 'Something unexpected happens' or any generic placeholder.\n"
                "Do NOT output dc, stat_check, tool_attribute, or any mechanical fields — only narrative text."
            ),
        }

        context_data = {
            "environment": room_env,
            "room_story": room_story,
            "event_type": event_type,
            "event_slots": event_slots,
            "world_context": story_context[:STORY_CONTEXT_LIMIT],
        }
        if available_tools:
            context_data["available_tools"] = available_tools
        if available_abilities:
            context_data["available_abilities"] = available_abilities
        if available_spells:
            context_data["available_spells"] = available_spells
        if previous_summaries:
            context_data["existing_encounters"] = previous_summaries

        context = json.dumps(context_data)

        previous_note = ""
        if previous_summaries:
            previous_note = "\n\nExisting encounters in this room (avoid duplicating these):\n" + "\n".join(
                f"- {s}" for s in previous_summaries[-15:]
            )

        max_tokens = max(6000, len(event_slots) * 700)

        return LLMRequest(
            system=(
                f"You generate {event_type} encounters for a fantasy game room.\n\n"
                f"{type_guidance.get(event_type, type_guidance['event'])}\n\n"
                "Story-related events (marked is_story_related) should reference the "
                "faction, room story, or overarching narrative.\n"
                f"Generate EXACTLY {len(event_slots)} events.\n\n"
                "Respond with ONLY a JSON array of event objects." + _NO_FENCES + previous_note
            ),
            examples=[],
            user_message=context,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Phase 4B: Dialogue generation
    # ------------------------------------------------------------------

    def dialogue_context_generation(
        self, room_env: dict, room_story: str, npc_data: list[dict], story_context: str
    ) -> LLMRequest:
        context = json.dumps(
            {
                "environment": room_env,
                "room_story": room_story,
                "npcs": npc_data,
                "world_context": story_context[:STORY_CONTEXT_LIMIT],
            }
        )
        return LLMRequest(
            system=(
                "You generate dialogue context for NPCs in an online fantasy game. "
                "For each NPC, generate: greeting (opening line), exhausted_dialogue "
                "(farewell when conversation limit is reached), and personality_notes "
                "(3-5 bullet points the live conversation AI should know — what they "
                "know about events, monsters, other NPCs, story lore, and their "
                "personal opinions).\n\n"
                "Each NPC object: {npc_name, greeting, exhausted_dialogue, "
                "personality_notes (array of strings)}\n\n"
                "Respond with ONLY a JSON array." + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=max(2000, len(npc_data) * 200),
        )

    # ------------------------------------------------------------------
    # Phase 3A: Weapon, Spell, and Ability database generation
    # ------------------------------------------------------------------

    def weapon_database_generation(self, environments: list[dict], num_rooms: int) -> LLMRequest:
        context = json.dumps(
            {
                "environments": environments,
                "num_rooms": num_rooms,
                "class_archetypes": ["warrior", "mage", "healer", "jester"],
            }
        )
        return LLMRequest(
            system=(
                "You generate a complete weapon database for a fantasy RPG. "
                "Create weapons for each room and class archetype.\n\n"
                "Weapon types: heavy (warrior, STR), light (warrior, DEX), "
                "simple (mage/healer, INT or WIS).\n"
                "Scaling: room 0 = common (1d4-1d6), higher rooms = stronger "
                "(up to legendary 1d10-1d12).\n"
                "Generate ~3 weapons per room (1 heavy, 1 light, 1 simple).\n\n"
                "Each weapon: {name, weapon_type (heavy|light|simple), "
                "rarity (common|uncommon|rare|legendary), attack_dice (e.g. '1d6'), "
                "stat_modifier (STR|DEX|INT|WIS), flavor_text, portrait_prompt}\n\n"
                "Respond with ONLY a JSON array of weapon objects. "
                "Theme weapons to each room's environment." + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=2000,
        )

    def spell_database_generation(self, class_type: str, environments: list[dict], num_rooms: int) -> LLMRequest:
        element_system = "fire > forest > water > fire; light <> dark (mutual weakness)"
        context = json.dumps(
            {
                "class_type": class_type,
                "environments": environments,
                "num_rooms": num_rooms,
                "element_system": element_system,
            }
        )
        spell_guidance = {
            "mage": "4 starting spells (2 damage, 2 utility) + 4 level-up spells. "
            "Pick 1 element for the class. damage_single, damage_multi, buff_stat, buff_sustain.",
            "healer": "4 starting spells (1 heal, 1 buff, 1 damage, 1 utility) + 4 level-up spells. "
            "Pick 1 element. heal, buff_stat, damage_single, buff_sustain.",
        }
        return LLMRequest(
            system=(
                f"You generate a spell list for the {class_type} class in a fantasy RPG.\n\n"
                f"Guidance: {spell_guidance.get(class_type, 'Generate 4 starting + 4 level-up spells.')}\n\n"
                f"Element system: {element_system}\n"
                "Elements: fire, water, forest, light, dark\n"
                "Spell types: damage_single, damage_multi, heal, buff_stat, buff_sustain\n\n"
                "Each spell: {name, description, element, stat (INT|WIS), damage_dice (int, "
                "die sides e.g. 8 for 1d8), spell_type, hunger_cost, thirst_cost, "
                "targets (single|multi|self), heal_amount (for heal spells), "
                "available_at_room (0 = starting, 1+ = level-up)}\n\n"
                "Respond with ONLY a JSON array of spell objects." + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=1500,
        )

    def utility_ability_generation(self, environments: list[dict], num_rooms: int) -> LLMRequest:
        context = json.dumps(
            {
                "environments": environments,
                "num_rooms": num_rooms,
                "tool_attributes": ["bludgeon", "cutting", "digging", "climbing"],
            }
        )
        return LLMRequest(
            system=(
                "You generate utility abilities for a fantasy RPG. These are non-combat "
                "abilities usable by any class for quests and puzzles.\n\n"
                "Generate 4 starting abilities (available_at_room: 0) + 4 level-up abilities "
                "(available_at_room: 1-4).\n\n"
                "Abilities should be useful for solving puzzles: breaking doors, climbing walls, "
                "persuading NPCs, detecting traps, etc.\n\n"
                "Each ability: {name, description, stat (STR|DEX|CON|INT|WIS|CHA), "
                "cost_hunger (int), cost_thirst (int), available_at_room (int)}\n\n"
                "Respond with ONLY a JSON array of ability objects." + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=800,
        )

    # ------------------------------------------------------------------
    # Phase 0 + Phase 1: Environment sequence & two-pass story generation
    # ------------------------------------------------------------------

    def environment_sequence_generation(self, story_seed: str, num_rooms: int, known_types: list[str]) -> LLMRequest:
        return LLMRequest(
            system=(
                "You plan the environment progression for a fantasy dungeon-crawling game. "
                "Given a story seed and number of rooms, generate a sequence of environments "
                "that creates a natural journey supporting the story.\n\n"
                f"Reference environment types (use these or invent similar ones): {known_types}\n\n"
                "Each environment has a type (short label like 'village', 'forest', 'mountain') "
                "and a unique thematic name.\n\n"
                "Respond with ONLY a JSON array of objects:\n"
                '[{"type": "village", "name": "Lilac Village"}, '
                '{"type": "forest", "name": "Thornwood"}, ...]\n'
                "The sequence should feel like a journey — start small and escalate toward "
                "the story's climax." + _NO_FENCES
            ),
            examples=[
                (
                    "story_seed: 'A fire cult plans to infiltrate the castle nobility', num_rooms: 5",
                    json.dumps(
                        [
                            {"type": "village", "name": "Ashen Meadow"},
                            {"type": "forest", "name": "Thornwood"},
                            {"type": "mountain", "name": "Ember Peak"},
                            {"type": "city", "name": "Irongate"},
                            {"type": "castle", "name": "Pyrespire Keep"},
                        ]
                    ),
                ),
            ],
            user_message=f"story_seed: '{story_seed}', num_rooms: {num_rooms}",
            max_tokens=300,
        )

    def overarching_story_generation(self, story_seed: str, environments: list[dict]) -> LLMRequest:
        context = json.dumps(
            {
                "story_seed": story_seed,
                "environments": environments,
            }
        )
        return LLMRequest(
            system=(
                "You generate the overarching story for a fantasy dungeon-crawling game. "
                "Given a story seed and the environment sequence the player will travel "
                "through, create the high-level narrative arc.\n\n"
                "The enemy faction must be CONSISTENT across the entire story — the same "
                "faction threatens every room, though they manifest differently per "
                "environment.\n\n"
                "Respond with ONLY a JSON object:\n"
                "{\n"
                '  "title": "story title",\n'
                '  "synopsis": "2-3 sentence overview of the full story arc",\n'
                '  "faction": {"name": "...", "description": "full faction lore paragraph", '
                '"history": "how they came to power", "leader": "leader name"},\n'
                '  "escalation_arc": ["room 0 tension description", "room 1...", ...],\n'
                '  "climax": "full paragraph describing the final confrontation",\n'
                '  "final_boss_name": "name of the final boss",\n'
                '  "final_boss_lore": "full paragraph about the boss",\n'
                '  "key_npc_names": ["important character 1", "..."]\n'
                "}\n\n"
                "Do NOT include per-room story beats or entity details — those come later. "
                "Focus on the faction, the arc, and the climax." + _NO_FENCES
            ),
            examples=[],
            user_message=context,
            max_tokens=1200,
        )

    def room_story_beat_generation(
        self, overarching_story: dict, room_env: dict, room_index: int, prior_beats: list[dict], num_rooms: int = 5
    ) -> LLMRequest:
        context = json.dumps(
            {
                "overarching_story": overarching_story,
                "room": {"index": room_index, "environment": room_env},
                "prior_beats": prior_beats,
            }
        )
        return LLMRequest(
            system=(
                "You write a detailed story beat for one room in a fantasy dungeon-crawling game.\n\n"
                "The enemy faction is CONSISTENT across all rooms — the same group, the same goal — "
                "but they manifest differently in each environment based on what that place offers them.\n\n"
                "RULES:\n"
                "- `summary`: full narrative paragraph describing what is happening RIGHT NOW in this "
                "room — specific events, specific people, specific stakes. Not atmosphere alone.\n"
                "- `faction_presence`: exactly how this faction operates HERE — what they have taken "
                "over, who they have recruited, what specific activity they are conducting.\n"
                "- `characters`: 2-4 named individuals with proper names (not 'a guard' or 'a merchant'). "
                "Each must have a role AND a specific motivation tied to the room's situation.\n"
                "- `mini_boss`: must have a unique proper name and title within the faction hierarchy — "
                "NEVER 'Lieutenant' or a generic rank. Their motivation must connect to the overarching "
                "faction's goal.\n"
                "- `conflicts`: 2-3 specific, actionable situations the player can intervene in — name "
                "the characters involved and describe what is at stake right now.\n"
                f"- `escalation`: 1-{num_rooms}, increasing each room. For the final room "
                f"(escalation {num_rooms}), the "
                "`summary` MUST reference the climax from overarching_story.\n"
                "- Build on prior_beats: reference named characters or events from earlier rooms when "
                "narratively logical. Show consequence.\n\n"
                "Respond with ONLY a JSON object." + _NO_FENCES
            ),
            examples=[
                (
                    json.dumps(
                        {
                            "overarching_story": {
                                "title": "The Sunken Ledger",
                                "faction_name": "The Brackwater Guild",
                                "leader": "Harrowmaster Veln",
                                "climax": "Harrowmaster Veln completes the debt-binding ritual in the harbor vault, enslaving the entire merchant class",
                                "escalation_arc": [
                                    "Guild enforcers arrive in the fishing district",
                                    "Guild takeover of the cave smuggling routes",
                                ],
                            },
                            "room": {"index": 0, "environment": {"type": "cave", "name": "Stonebiter Caverns"}},
                            "prior_beats": [],
                        }
                    ),
                    json.dumps(
                        {
                            "summary": "The Brackwater Guild has seized Stonebiter Caverns as the cornerstone of their new smuggling operation. Miners who once extracted copper for the city now haul contraband under armed watch, their wages confiscated as 'debt repayment.' The cavern's foreman, a soft-spoken man named Torval Duskpick, has been keeping a quiet count of how many guards patrol each shift — waiting for someone capable of tipping the scales. Guild enforcer Shrike paces the upper gallery with visible impatience, aware that the longer they stay, the more locals learn the Guild's methods.",
                            "faction_presence": "The Brackwater Guild has posted four enforcers at the cavern entrance and converted the ore-sorting hall into a contraband depot. They are extorting the miners' labor as debt repayment while moving goods stolen from surface merchants through the cave's hidden sump passage.",
                            "characters": [
                                {
                                    "name": "Torval Duskpick",
                                    "role": "resistance_leader",
                                    "motivation": "Free his fellow miners and collapse the Guild's route before Shrike ships the next contraband load",
                                },
                                {
                                    "name": "Mira Coalseam",
                                    "role": "betrayer",
                                    "motivation": "Trading information about the escape plan to Shrike in exchange for her family's debts being forgiven",
                                },
                                {
                                    "name": "Old Fenwick",
                                    "role": "ally",
                                    "motivation": "Too broken to fight but knows every tunnel in these caves and will guide anyone who treats him kindly",
                                },
                            ],
                            "mini_boss": {
                                "name": "Shrike, the Guild's Route-Closer",
                                "description": "A compact, precise woman who carries a ledger of every debt she has collected. She fights with two short blades and treats violence as an accounting entry.",
                                "motivation": "Close the Stonebiter route cleanly and return to Harrowmaster Veln with a full shipment — anything less is a failure she refuses to report",
                            },
                            "conflicts": [
                                "Torval needs Shrike eliminated before Mira's betrayal is acted upon — he does not yet know Mira has turned",
                                "Old Fenwick is locked in the deep shaft as punishment for slow work; freeing him would give the resistance a critical guide but requires dealing with the shaft guard",
                                "The contraband shipment is already packed — if it leaves the cave tonight, the Guild gains enough funds to hire twice as many enforcers for the next stage",
                            ],
                            "escalation": 1,
                        }
                    ),
                )
            ],
            user_message=context,
            max_tokens=1500,
        )

    def music_prompt_generation(self, story_summary: dict, environments: list[str]) -> LLMRequest:
        context = json.dumps(
            {
                "story": story_summary,
                "environments": environments,
            }
        )
        return LLMRequest(
            system=(
                "You write music prompts for a synthwave video game soundtrack. "
                "Given a story summary and a list of environment types actually present in the game, "
                "generate Lyra 3 music prompts for the combat track and one maze track per environment.\n\n"
                "STYLE RULES (apply to ALL prompts you write):\n"
                "- Synthwave, retrowave, analog synths, 80s-inspired video game soundtrack\n"
                "- Instrumental only, absolutely no vocals\n"
                "- Loop-friendly: the opening texture must mirror the closing texture for seamless looping\n"
                "- Use timestamped sections [0:00-0:20] ... [1:40-2:00] for structure\n"
                "- All tracks are 2 minutes except game_over (null — handled separately)\n\n"
                "COMBAT: The combat track should reflect the story faction's character — their methods, "
                "tone, and the threat they pose. Tense, urgent, driving.\n\n"
                "MAZE TRACKS: Each maze track should blend the natural feeling of the environment "
                "(peaceful, mysterious, industrial, etc.) with an undercurrent of tension — "
                "the world is dangerous. Example: village music is warm and pastoral with occasional "
                "swells of unease; cave music is deep and atmospheric with lurking dread.\n\n"
                "Respond with ONLY a JSON object. Keys: 'combat', and 'maze_{env}' for each env in the list. "
                "Set puzzle_event, start_screen, victory, game_over to null (handled separately)." + _NO_FENCES
            ),
            examples=[
                (
                    json.dumps(
                        {
                            "story": {
                                "title": "The Sunken Ledger",
                                "faction_name": "The Brackwater Guild",
                                "faction_description": "A criminal guild controlling trade routes through extortion and debt bondage",
                                "climax": "Harrowmaster Veln completes a debt-binding ritual enslaving the merchant class",
                            },
                            "environments": ["cave"],
                        }
                    ),
                    json.dumps(
                        {
                            "combat": (
                                "[0:00-0:20] Tense synthwave bass pulse in a minor key, slow and ominous. "
                                "The cold precision of hired enforcers. "
                                "[0:20-1:10] Driving drum machine at 130 BPM, sharp arpeggiated synth leads, "
                                "dark and business-like — violence as transaction. "
                                "[1:10-1:40] Escalation: dissonant synth stabs, faster arpeggios, relentless momentum. "
                                "[1:40-2:00] Return to opening bass pulse for seamless loop. "
                                "Synthwave, retrowave, instrumental only, no vocals."
                            ),
                            "maze_cave": (
                                "[0:00-0:20] Deep cave drone, low analog bass hum, cavernous reverb. "
                                "[0:20-1:00] Slow atmospheric synthwave pad, dripping echo, minor key. "
                                "Feels like exploring tunnels where something lurks. "
                                "[1:00-1:30] Tension rises: deeper bass pulse, hint of a melody that resolves nowhere. "
                                "[1:30-2:00] Return to opening drone for seamless loop. "
                                "Synthwave, analog synths, instrumental only, no vocals."
                            ),
                            "puzzle_event": None,
                            "start_screen": None,
                            "victory": None,
                            "game_over": None,
                        }
                    ),
                )
            ],
            user_message=context,
            max_tokens=2000,
        )

    def sfx_prompt_generation(
        self, story_summary: dict, environments: list[dict], spell_elements: list[str]
    ) -> LLMRequest:
        context = json.dumps(
            {
                "story": story_summary,
                "environments": environments,
                "spell_elements": spell_elements,
            }
        )
        return LLMRequest(
            system=(
                "You write sound effect prompts for a fantasy video game. "
                "Given the story context, environment list, and active spell elements, "
                "generate short text descriptions that will be sent to an AI SFX generator "
                "(ElevenLabs). Each prompt must describe a specific, short sound.\n\n"
                "OUTPUT FORMAT: Respond with ONLY a JSON object. Each key maps to an object "
                "with 'prompt' (string), 'duration' (float, seconds), and 'loop' (boolean).\n\n"
                "CATEGORIES TO GENERATE:\n\n"
                "1. WEAPON SFX (6 keys) — flavor these with the story's faction/theme:\n"
                "   - weapon_light_swing (1.5s): fast slash of a light blade (dagger, rapier)\n"
                "   - weapon_light_hit (0.5s): light blade impact on flesh/armor\n"
                "   - weapon_heavy_swing (2s): slow heavy weapon arc (maul, axe, hammer)\n"
                "   - weapon_heavy_hit (0.75s): heavy weapon impact, weighty thud\n"
                "   - weapon_simple_swing (1.5s): staff or scepter swing\n"
                "   - weapon_simple_hit (0.5s): staff/mace impact\n\n"
                "2. SPELL SFX (7 keys) — color these with the dominant spell elements:\n"
                "   - spell_heal_cast (2s): healing magic activation\n"
                "   - spell_damage_single_cast (1.5s): single-target attack spell cast\n"
                "   - spell_damage_single_impact (1s): single-target spell hitting\n"
                "   - spell_damage_multi_cast (2s): area-of-effect spell cast\n"
                "   - spell_damage_multi_impact (1.5s): area spell hitting multiple targets\n"
                "   - spell_buff_cast (2s): protective/stat buff activation\n"
                "   - spell_reveal_cast (2s): reveal/sight magic activation\n\n"
                "3. ENVIRONMENT AMBIENCE (one per environment) — key: ambience_{env_type}:\n"
                "   Each is 12-15 seconds, loop=true. Describe the ambient soundscape of that "
                "   specific environment colored by the story's faction presence and tone. "
                "   Use the environment name for specificity.\n\n"
                "PROMPT STYLE RULES:\n"
                "- Be specific and vivid: describe actual sounds, not abstract concepts\n"
                "- Include the faction's thematic flavor in weapons and ambience\n"
                "- Spell sounds should reference the dominant element (fire=crackling, water=rushing, "
                "  forest=rustling, light=chiming, dark=whispering)\n"
                "- Keep prompts concise (1-3 sentences each)\n"
                "- All durations in seconds\n"
                "- Only ambience tracks get loop=true; all others loop=false\n"
                "- No screaming, yelling, or vocal sounds. Chatter/murmurs are OK for ambience only." + _NO_FENCES
            ),
            examples=[
                (
                    json.dumps(
                        {
                            "story": {
                                "title": "The Sunken Ledger",
                                "faction_name": "The Brackwater Guild",
                                "faction_description": "A criminal guild controlling trade routes",
                                "climax": "Harrowmaster Veln enslaves the merchant class",
                            },
                            "environments": [
                                {"type": "cave", "name": "Stonebiter Caverns"},
                            ],
                            "spell_elements": ["water", "dark"],
                        }
                    ),
                    json.dumps(
                        {
                            "weapon_light_swing": {
                                "prompt": "A quick sharp blade cutting through damp air with a wet metallic whoosh. Fast and precise, like a debt collector's razor.",
                                "duration": 1.5,
                                "loop": False,
                            },
                            "weapon_light_hit": {
                                "prompt": "A short wet slap of steel on flesh. Quick blade impact, sharp and clinical.",
                                "duration": 0.5,
                                "loop": False,
                            },
                            "weapon_heavy_swing": {
                                "prompt": "A heavy iron tool swinging through air with a deep whoosh and chain rattle. Slow, brutal, like a dockworker's maul.",
                                "duration": 2.0,
                                "loop": False,
                            },
                            "weapon_heavy_hit": {
                                "prompt": "A crushing impact of heavy metal on bone. Deep thud with a crunch. Devastating.",
                                "duration": 0.75,
                                "loop": False,
                            },
                            "weapon_simple_swing": {
                                "prompt": "A wooden staff cutting through air with a smooth whoosh. Light and swift, with a faint hum of energy.",
                                "duration": 1.5,
                                "loop": False,
                            },
                            "weapon_simple_hit": {
                                "prompt": "A hollow wooden thud of a staff striking armor. Resonant impact.",
                                "duration": 0.5,
                                "loop": False,
                            },
                            "spell_heal_cast": {
                                "prompt": "Rushing water sounds swirling upward, building to a gentle splash and warm shimmer. Healing water magic.",
                                "duration": 2.0,
                                "loop": False,
                            },
                            "spell_damage_single_cast": {
                                "prompt": "A dark water jet pressurizing and firing: building rush then sharp crack of a water lance.",
                                "duration": 1.5,
                                "loop": False,
                            },
                            "spell_damage_single_impact": {
                                "prompt": "A pressurized water blast impacting a surface. Wet explosive hit.",
                                "duration": 1.0,
                                "loop": False,
                            },
                            "spell_damage_multi_cast": {
                                "prompt": "Dark tidal energy swelling outward: rising rush of cursed water, building to a roaring wave burst.",
                                "duration": 2.0,
                                "loop": False,
                            },
                            "spell_damage_multi_impact": {
                                "prompt": "Multiple impacts of dark water bursts hitting stone and metal. Scattered wet explosions.",
                                "duration": 1.5,
                                "loop": False,
                            },
                            "spell_buff_cast": {
                                "prompt": "A protective shell of flowing water encasing something: gentle rush building to a sealed dome of liquid energy.",
                                "duration": 2.0,
                                "loop": False,
                            },
                            "spell_reveal_cast": {
                                "prompt": "Dark whispers dissolving into clarity: shadowy murmur fading as hidden things become visible. Eerie then clear.",
                                "duration": 2.0,
                                "loop": False,
                            },
                            "ambience_cave": {
                                "prompt": "Deep cave ambience in smuggler tunnels: distant water dripping, echoing footsteps, faint clinking of contraband chains, occasional low wind moaning through stone passages. Tense and claustrophobic.",
                                "duration": 15.0,
                                "loop": True,
                            },
                        }
                    ),
                )
            ],
            user_message=context,
            max_tokens=3000,
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
