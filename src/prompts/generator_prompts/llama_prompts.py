from config import STORY_CONTEXT_LIMIT
from src.prompts.base import LLMRequest, PromptSet


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
                (
                    "environment: 'forest', env_name: 'Iron Oak'",
                    "{'name': 'helena', 'job': 'herbalist', 'personality': 'mysterious', 'hobby': 'collecting herbs'}",
                ),
                (
                    "environment: 'desert', env_name: 'Sandstone'",
                    "{'name': 'khalid', 'job': 'merchant', 'personality': 'charming', 'hobby': 'haggling'}",
                ),
                (
                    "environment: 'mountain', env_name: 'Frostpeak'",
                    "{'name': 'greta', 'job': 'blacksmith', 'personality': 'gruff', 'hobby': 'forging'}",
                ),
                (
                    "environment: 'city', env_name: 'Silverport'",
                    "{'name': 'julius', 'job': 'guard', 'personality': 'stoic', 'hobby': 'training'}",
                ),
                (
                    "environment: 'swamp', env_name: 'Mosswood'",
                    "{'name': 'elara', 'job': 'alchemist', 'personality': 'eccentric', 'hobby': 'experimenting'}",
                ),
            ],
            user_message=f"environment: '{env}', env_name: '{env_name}'",
            max_tokens=40,
        )

    def conversation_identity(self, name: str, job: str, personality: str, hobby: str, env: str, env_name: str) -> str:
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
            user_message=("You see the player approaching you. Greet them simply based on your personality."),
            max_tokens=50,
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
                "You are a stable diffusion prompt generator. You will be given a brief "
                "description of a person and you will output a prompt for stable diffusion. "
                "The prompt should be short, in the fashion of a high fantasy/snes video game "
                "style and stay on topic based on the persons details."
            ),
            examples=[
                (
                    str(
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
                (
                    str(
                        {
                            "name": "Angela",
                            "job": "mage",
                            "personality": "princess",
                            "hobby": "naughty",
                            "environment": "city",
                            "environment_name": "Magic Ice Kingdom of Altena",
                        }
                    ),
                    "A sexy mage with long flowing blonde hair, naughty and dressed in a "
                    "revealing short purple dress. She looks playful standing alone in a "
                    "snowy town square",
                ),
                (
                    str(
                        {
                            "name": "Kevin",
                            "job": "monk",
                            "personality": "mischievous",
                            "hobby": "goofing off",
                            "environment": "forest",
                            "environment_name": "Dark Forest",
                        }
                    ),
                    "A mischievous half beast-half man monk with a playful grin, dressed in "
                    "animal skins. Half wolf man, he has shaggy brown fur and is standing in "
                    "a dark forest, surrounded by tall trees and mist.",
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

    def event_generation(self, env: str, env_name: str, event_type: str, story_context: str = "") -> LLMRequest:
        ctx_suffix = ""
        if story_context:
            ctx_suffix = (
                f"\nWorld context (use to name and describe encounters using the world's "
                f"lore — faction creatures, environmental hazards tied to the story):\n"
                f"{story_context[:STORY_CONTEXT_LIMIT]}\n"
                "Be information-dense. Do not pad or ramble."
            )
        if event_type == "combat":
            return LLMRequest(
                system=(
                    "You generate combat encounters for a fantasy game. "
                    "Output a JSON object with: name, description, difficulty (1-5), "
                    "damage_type (health|stamina), damage_range ([min,max]). "
                    "Name and describe encounters using the world's lore when provided — "
                    "faction creatures, story-relevant hazards."
                ),
                examples=[
                    (
                        "environment: 'forest', env_name: 'Shadowleaf'",
                        '{"name": "Giant Spider", "description": "A massive spider drops from the canopy!", '
                        '"difficulty": 3, "damage_type": "health", "damage_range": [5, 15]}',
                    ),
                    (
                        "environment: 'cave', env_name: 'Gloomhollow'",
                        '{"name": "Cave Troll", "description": "A hulking troll emerges from the shadows!", '
                        '"difficulty": 4, "damage_type": "health", "damage_range": [8, 20]}',
                    ),
                ],
                user_message=f"environment: '{env}', env_name: '{env_name}'{ctx_suffix}",
                max_tokens=80,
            )
        else:
            return LLMRequest(
                system=(
                    "You generate puzzle encounters for a fantasy game. "
                    "Puzzles are ENVIRONMENTAL obstacles: ancient mechanisms, natural hazards, magical seals. "
                    "Output a JSON object with: name, description, difficulty (1-5), "
                    "choices (array with: text, stat_check, tool_attribute, dc, auto_success). "
                    "Include 2-3 choices plus a walk-away option. "
                    "Choice text must describe a NARRATIVE ACTION, not a stat label. "
                    "GOOD: 'Shoulder the boulder aside' BAD: 'Attempt a STR check'. "
                    "Descriptions must be vivid scenes, not generic placeholders."
                ),
                examples=[
                    (
                        "environment: 'cave', env_name: 'Gloomhollow'",
                        '{"name": "Collapsed Passage", "description": "Jagged rocks and shattered support beams block the narrow tunnel. '
                        'Dust still settles from a recent cave-in, and faint air currents suggest open space beyond.", '
                        '"difficulty": 2, "choices": ['
                        '{"text": "Heave the largest stones aside with raw strength", "stat_check": "STR", "tool_attribute": null, "dc": 12, "auto_success": false}, '
                        '{"text": "Carefully pick your way through the gaps", "stat_check": "DEX", "tool_attribute": null, "dc": 14, "auto_success": false}, '
                        '{"text": "Turn back and find another route", "stat_check": null, "tool_attribute": null, "dc": 0, "auto_success": true}]}',
                    ),
                ],
                user_message=f"environment: '{env}', env_name: '{env_name}'{ctx_suffix}",
                max_tokens=200,
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
        ctx_data = {
            "environment": env,
            "environment_name": env_name,
            "quest_type": quest_type,
            "npcs": [{"id": n["id"], "name": n.get("name", "NPC")} for n in available_npcs[:5]],
            "items": [{"id": i.get("id"), "name": i.get("name", "item")} for i in available_items[:5]],
            "events": [{"id": e.get("id"), "name": e.get("name", "event")} for e in available_events[:3]],
        }
        if story_context:
            ctx_data["world_bible_context"] = story_context[:STORY_CONTEXT_LIMIT]
        context = str(ctx_data)
        return LLMRequest(
            system=(
                "You generate quests for a fantasy game. Given context about NPCs, items, events, "
                "and world lore, output a JSON object with: title, description, giver_npc_id. "
                "For fetch: add target_items [{item_id, count}]. "
                "For escort: add escort_npc_id. "
                "For delivery: add delivery_item_id, target_npc_id. "
                "For combat: add target_event_id. "
                "For dialogue_gated: add dialogue_tree with prompt and choices. "
                "Use ONLY ids from context.\n\n"
                "Quest titles and descriptions MUST reference the world's faction, environment, "
                "or story from world_bible_context. Make objectives feel like part of the living "
                "world, not generic fetch/kill tasks. Be information-dense: every detail should "
                "add gameplay or lore value. Do not pad or ramble."
            ),
            examples=[],
            user_message=context,
            max_tokens=200,
        )

    def dialogue_tree_generation(self, npc_personality: dict, quest_context: dict | None = None) -> LLMRequest:
        context = str({"npc": npc_personality, "quest": quest_context})

        if quest_context:
            system = (
                "You generate dialogue trees for a quest NPC. Output JSON with THREE trees:\n"
                '1. "incomplete" — while quest is active (3-5 nodes). Introduce NPC, describe quest.\n'
                '2. "complete_success" — after success (2-3 nodes). Thank player, grateful farewell.\n'
                '3. "complete_failure" — after failure (2-3 nodes). Acknowledge attempt, resigned farewell.\n'
                'Format: {"incomplete": {"nodes": {"start": {"prompt": ..., "choices": [...]}, '
                '"end": {"prompt": ..., "choices": []}}}, '
                '"complete_success": {"nodes": {...}}, "complete_failure": {"nodes": {...}}}. '
                "Stay in character."
            )
            max_tokens = 1000
        else:
            system = (
                "You generate dialogue trees for fantasy game NPCs. "
                "Output a JSON: {nodes: {start: {prompt, choices: [{text, next_node_id}]}, ...}}. "
                "3-5 nodes. Stay in character."
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
                f"\nWorld context (theme items to both the environment AND the world's "
                f"faction/story — reference it, don't repeat it verbatim):\n"
                f"{story_context[:STORY_CONTEXT_LIMIT]}\n"
                "Be information-dense: item names and descriptions should reinforce "
                "the world's lore. Do not pad or ramble."
            )
        return LLMRequest(
            system=(
                "You generate environment-themed items for a fantasy game. "
                "Output a JSON object with keys: food (4 items), drink (4 items), "
                "tools (3 items), weapons (3 items), spell_scrolls (2 items). "
                "Each food: {name, desc}. "
                "Each drink: {name, desc}. "
                "Each tool: {name, desc, attribute (bludgeon|cutting|digging|climbing)}. "
                "Each weapon: {name, desc, weapon_type (heavy|light|simple), stat_modifier (STR|DEX|INT)}. "
                "Each spell_scroll: {name, desc, spell_effect (heal|damage|shield|reveal|sustain)}. "
                "Items must be thematic to the environment and world lore."
            ),
            examples=[
                (
                    "environment: 'forest', name: 'Whisperwood', room_level: 1",
                    '{"food": [{"name": "forest bread", "desc": "Hearty bread baked with acorn flour."}, '
                    '{"name": "wild berries", "desc": "Sweet ripe berries."}, '
                    '{"name": "roasted rabbit", "desc": "Campfire-roasted rabbit."}, '
                    '{"name": "honey cake", "desc": "Sticky-sweet cake with wild honey."}], '
                    '"drink": [{"name": "spring water", "desc": "Cool forest spring water."}, '
                    '{"name": "herbal tea", "desc": "Soothing forest herb tea."}, '
                    '{"name": "berry juice", "desc": "Fresh wild berry juice."}, '
                    '{"name": "dew drops", "desc": "Morning dew from broad leaves."}], '
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
                    '"spell_effect": "heal"}]}',
                ),
            ],
            user_message=(f"environment: '{env}', name: '{env_name}', room_level: {room_level}" + lore_suffix),
            max_tokens=600,
        )

    def item_image_description(self, item_data: dict) -> LLMRequest:
        return LLMRequest(
            system=(
                "You are a stable diffusion prompt generator for game items. "
                "Output a short visual description of the item, high fantasy style."
            ),
            examples=[
                (
                    str({"name": "hammer", "desc": "A craftsman's hammer"}),
                    "A sturdy iron hammer with a worn leather grip, resting on a workbench.",
                ),
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
                (
                    str({"name": "Giant Spider", "type": "combat"}),
                    "A giant spider descending from dark forest canopy, silk threads glistening.",
                ),
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
                "abilities [{name,description,stat}], "
                "spells [{name,description,element,spell_type,stat,targets (single|multi|self)}]. "
                "Do NOT include damage_dice, hunger_cost, thirst_cost, or stamina_cost — the system assigns these. "
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
                (
                    str({"name": "Ranger", "archetype": "warrior", "environment": "forest"}),
                    "A rugged ranger in green leather, longbow on back, standing in a forest clearing.",
                ),
            ],
            user_message=str(class_data),
            max_tokens=60,
        )

    def story_generation(self, story_seed: str, room_count: int, environments: list[str]) -> LLMRequest:
        context = str(
            {
                "story_seed": story_seed,
                "room_count": room_count,
                "environments": environments,
            }
        )
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
        ctx_data = {
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
        context = str(ctx_data)
        return LLMRequest(
            system=(
                "You generate story quests for a fantasy game referencing a faction and story beat. "
                "Output JSON: {title, description, giver_npc_id, is_story_quest: true}. "
                "Add type-specific fields. Use ONLY ids from context.\n\n"
                "The quest title and description MUST reference the faction name, story beat, "
                "and world_bible_context. Tie the objective directly to the story's conflict — "
                "not a generic task. Be information-dense: every detail should advance the "
                "narrative. Do not pad or ramble."
            ),
            examples=[],
            user_message=context,
            max_tokens=300,
        )

    def full_story_generation(self, story_seed: str, room_count: int, environments: list[str]) -> LLMRequest:
        context = str(
            {
                "story_seed": story_seed,
                "room_count": room_count,
                "environments": environments,
            }
        )
        return LLMRequest(
            system=(
                "You generate a complete world story for a fantasy game. "
                "Output JSON: {title, synopsis, faction: {name, description, history, leader}, "
                "escalation_arc, climax, final_boss_name, final_boss_lore, "
                "beats: [{room_id, summary, faction_presence, escalation, boss_name, boss_lore}], "
                "story_npcs: [{name, role, backstory, room_id, personality, job}], "
                "story_items: [{name, description, lore, room_id}], "
                "story_monsters: [{name, description, lore, room_id, is_boss, species}]}. "
                "2-4 NPCs, 1-2 items, 1 boss per room. Full lore paragraphs."
            ),
            examples=[],
            user_message=context,
            max_tokens=2000,
        )

    def monster_generation(
        self, env: str, env_name: str, room_level: int, story_context: str, total_rooms: int = 1
    ) -> LLMRequest:
        scale_stats_line = (
            f"Scale stats to room_level (1=easy, {total_rooms}=hard). "
            if total_rooms > 1
            else "Scale stats so the mix includes easy fodder monsters and one challenging boss for a single-room dungeon. "
        )
        context = str(
            {
                "environment": env,
                "environment_name": env_name,
                "room_level": room_level,
            }
        )
        return LLMRequest(
            system=(
                "You generate monsters for a fantasy game.\n\n"
                "World context (use to ground monsters in the world's story, faction, "
                "and environment — reference it, don't repeat it verbatim):\n"
                f"{story_context[:STORY_CONTEXT_LIMIT]}\n\n"
                "Output a JSON array of 4-6 monster objects: "
                "[{name, species, description, backstory, level, hp, ac, "
                "damage_type, elemental_affinity, time_availability (always|night_only|day_only), "
                "abilities: [{name, effect_type, damage_dice, chance}], portrait_prompt}]\n\n"
                "Each monster's description and backstory should tie to the faction or "
                "environment. Scale lore depth to room_level. At least 1 monster should be "
                "night_only. "
                + scale_stats_line
                + "Be information-dense: every name and backstory should reinforce the world's "
                "lore. Do not pad or ramble."
            ),
            examples=[],
            user_message=context,
            max_tokens=800,
        )

    def npc_backstory_generation(self, npc_data: dict, story_context: str) -> LLMRequest:
        return LLMRequest(
            system=(
                "You write NPC backstories for a fantasy game.\n\n"
                "World context (use to ground the backstory in the world's story, faction, "
                "and environment — reference it, don't repeat it verbatim):\n"
                f"{story_context[:STORY_CONTEXT_LIMIT]}\n\n"
                "Output ONLY a backstory paragraph (3-5 sentences). Reference specific "
                "world events, faction names, or locations from the context. Each sentence "
                "should add unique narrative detail — do not pad or ramble."
            ),
            examples=[
                (
                    str({"name": "Greta", "job": "blacksmith"}),
                    "Greta has hammered iron in Gloomhollow for twenty years, ever since "
                    "the cult drove her family from the surface.",
                ),
            ],
            user_message=str(npc_data),
            max_tokens=150,
        )

    # Stubs for new prompts — local model delegates to Claude prompt set
    def npc_batch_generation(
        self, room_env: dict, room_story: str, npc_slots: list[dict], story_context: str
    ) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().npc_batch_generation(room_env, room_story, npc_slots, story_context)

    def event_batch_generation(
        self, room_env: dict, room_story: str, event_type: str, event_slots: list[dict], story_context: str, **kwargs
    ) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().event_batch_generation(
            room_env, room_story, event_type, event_slots, story_context, **kwargs
        )

    def dialogue_context_generation(
        self, room_env: dict, room_story: str, npc_data: list[dict], story_context: str
    ) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().dialogue_context_generation(room_env, room_story, npc_data, story_context)

    def weapon_database_generation(self, environments: list[dict], num_rooms: int) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().weapon_database_generation(environments, num_rooms)

    def spell_database_generation(self, class_type: str, environments: list[dict], num_rooms: int) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().spell_database_generation(class_type, environments, num_rooms)

    def utility_ability_generation(self, environments: list[dict], num_rooms: int) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().utility_ability_generation(environments, num_rooms)

    def environment_sequence_generation(self, story_seed: str, num_rooms: int, known_types: list[str]) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().environment_sequence_generation(story_seed, num_rooms, known_types)

    def overarching_story_generation(self, story_seed: str, environments: list[dict]) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().overarching_story_generation(story_seed, environments)

    def room_story_beat_generation(
        self, overarching_story: dict, room_env: dict, room_index: int, prior_beats: list[dict], num_rooms: int = 5
    ) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().room_story_beat_generation(
            overarching_story, room_env, room_index, prior_beats, num_rooms
        )

    def music_prompt_generation(self, story_summary: dict, environments: list[str]) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().music_prompt_generation(story_summary, environments)

    def sfx_prompt_generation(
        self, story_summary: dict, environments: list[dict], spell_elements: list[str]
    ) -> LLMRequest:
        from src.prompts.generator_prompts.claude_prompts import ClaudePromptSet

        return ClaudePromptSet().sfx_prompt_generation(story_summary, environments, spell_elements)


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
