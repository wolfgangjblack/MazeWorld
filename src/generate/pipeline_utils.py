"""Reusable helpers extracted from the pipeline module.

Pure logic functions with no orchestration — used by the pipeline,
tests, and other modules.
"""

import logging
import random

from src.generate.validator import ValidationReport

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _retry_with_feedback(generate_fn, validate_fn, fallback, label: str = "content",
                          max_retries: int = MAX_RETRIES):
    """Generate content with retry-on-validation-failure.

    1. Call *generate_fn()* to produce content.
    2. Call *validate_fn(content)* → (passed: bool, reasons: list[str]).
    3. On failure, retry up to *max_retries* times, passing failure reasons back
       to the generator via *generate_fn(feedback=reasons)*.
    4. On exhaustion, return *fallback*.
    """
    feedback: list[str] | None = None
    for attempt in range(1, max_retries + 1):
        try:
            content = generate_fn(feedback=feedback) if feedback else generate_fn()
        except Exception as e:
            logger.warning("[%s] attempt %d generation error: %s", label, attempt, e)
            feedback = [str(e)]
            continue

        passed, reasons = validate_fn(content)
        if passed:
            logger.info("[%s] passed validation on attempt %d.", label, attempt)
            return content

        logger.warning("[%s] attempt %d failed validation: %s", label, attempt, reasons)
        feedback = reasons

    logger.warning("[%s] exhausted %d retries, using fallback.", label, max_retries)
    return fallback


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------

def build_manifest(
    *,
    seed: int,
    story_seed: str,
    game_mode: str,
    num_rooms: int,
    environments: list[str],
    generated_at: str,
    validation: dict,
    active_npc_count: int,
    item_count: int,
    quest_count: int,
    event_list: list[dict],
    npc_pool: list[dict],
    player_portrait_path: str | None,
    env_portrait_path: str | None,
    environment: str,
    env_name: str,
    maze_width: int,
    maze_height: int,
    class_count: int,
    portraits_generated: bool,
    story_title: str,
    faction_name: str,
) -> dict:
    """Build the manifest dict written to data/manifest.json."""
    image_count = sum(1 for p in [player_portrait_path, env_portrait_path] if p)
    image_count += sum(1 for n in npc_pool if n.get("portrait"))

    monster_count = sum(
        len(e.get("monsters", []))
        for e in event_list if e.get("event_type") == "combat"
    )

    return {
        "seed": seed,
        "story_seed": story_seed,
        "game_mode": game_mode,
        "num_rooms": num_rooms,
        "environments": environments,
        "generated_at": generated_at,
        "validation": validation,
        "content_index": {
            "rooms": num_rooms,
            "npcs": active_npc_count,
            "items": item_count,
            "quests": quest_count,
            "encounters": len(event_list),
            "monsters": monster_count,
            "images": image_count,
            "music_tracks": 0,
        },
        "environment": environment,
        "environment_name": env_name,
        "maze_width": maze_width,
        "maze_height": maze_height,
        "npc_pool_size": len(npc_pool),
        "class_count": class_count,
        "portraits_generated": portraits_generated,
        "player_portrait": player_portrait_path,
        "environment_portrait": env_portrait_path,
        "story_title": story_title,
        "faction_name": faction_name,
    }


# ---------------------------------------------------------------------------
# Quest validation
# ---------------------------------------------------------------------------

def _validate_quest(quest: dict, npc_pool: list, item_placements: list,
                     event_list: list, existing_quests: list) -> bool:
    """Check that a quest is completable given the world state."""
    qtype = quest.get("type", "")
    npc_ids = {n["id"] for n in npc_pool if n.get("selected")}
    item_ids_on_map = {p["item_id"] for p in item_placements}
    event_ids = {e["id"] for e in event_list}
    existing_quest_ids = {q["id"] for q in existing_quests}

    if quest.get("giver_npc_id") not in npc_ids:
        return False

    if qtype == "fetch":
        for ti in quest.get("target_items", []):
            if ti.get("item_id") not in item_ids_on_map:
                return False
    elif qtype == "escort":
        if quest.get("escort_npc_id") not in npc_ids:
            return False
    elif qtype == "delivery":
        if quest.get("delivery_item_id") not in item_ids_on_map:
            return False
        if quest.get("target_npc_id") not in npc_ids:
            return False
    elif qtype in ("combat", "solve"):
        target = quest.get("target_event_id")
        if target and target not in event_ids:
            return False
    elif qtype == "dialogue_gated":
        prereq = quest.get("prerequisite_quest_id")
        if prereq and prereq not in existing_quest_ids:
            return False

    prereq = quest.get("prerequisite_quest_id")
    if prereq:
        depth = 1
        check = prereq
        while check and depth <= 2:
            parent = next((q for q in existing_quests if q["id"] == check), None)
            if parent is None:
                return False
            check = parent.get("prerequisite_quest_id")
            depth += 1
        if depth > 2:
            return False

    return True


# ---------------------------------------------------------------------------
# Item scaling and building
# ---------------------------------------------------------------------------

WEAPON_PRICE_BY_DICE = {
    "1d4": (8, 15), "1d6": (16, 25), "1d8": (28, 45),
    "1d10": (40, 55), "2d4": (25, 35), "1d12": (55, 70),
}

CONSUMABLE_SCALING = {
    1: 1.0,
    2: 1.3,
    3: 1.6,
    4: 2.0,
}


def _consumable_mult(room_level: int) -> float:
    """Return the consumable scaling multiplier for a given room level."""
    return CONSUMABLE_SCALING.get(room_level, CONSUMABLE_SCALING[4])


def _build_items_list(llm_result: dict, room_level: int) -> list[dict]:
    """Convert LLM-generated item pools into a flat list of item dicts (no IDs).

    The caller assigns XYYY IDs from the global item DB counter.
    """
    items: list[dict] = []
    mult = _consumable_mult(room_level)

    for raw in llm_result.get("food", [])[:4]:
        stam_base = raw.get("stamina_value", raw.get("nutrition_value", 0))
        if not stam_base:
            stam_base = random.randint(1, 10) + random.randint(1, 10)
        hp_base = raw.get("health_value", 0)
        if not hp_base:
            hp_base = random.randint(1, 6)
        items.append({
            "category": "food",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "room_level": room_level,
            "item_stats": {
                "stamina_value": int(stam_base * mult),
                "health_value": int(hp_base * mult),
                "uses": 1,
                "price": int(random.randint(5, 15) * mult),
            },
        })

    for raw in llm_result.get("drink", [])[:4]:
        stam_base = raw.get("stamina_value", raw.get("hydration_value", 0))
        if not stam_base:
            stam_base = random.randint(1, 10) + random.randint(1, 10)
        hp_base = raw.get("health_value", 0)
        if not hp_base:
            hp_base = random.randint(1, 6)
        items.append({
            "category": "drink",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "room_level": room_level,
            "item_stats": {
                "stamina_value": int(stam_base * mult),
                "health_value": int(hp_base * mult),
                "uses": 1,
                "price": int(random.randint(5, 15) * mult),
            },
        })

    for raw in llm_result.get("tools", [])[:3]:
        items.append({
            "category": "tool",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "room_level": room_level,
            "item_stats": {
                "attribute": raw.get("attribute", "bludgeon"),
                "stamina_value": -5,
                "health_value": 0,
                "uses": 3,
                "price": int(random.randint(10, 25) * mult),
            },
        })

    for raw in llm_result.get("weapons", [])[:3]:
        dice = raw.get("attack_dice", "1d4")
        lo, hi = WEAPON_PRICE_BY_DICE.get(dice, (10, 30))
        weapon_entry = {
            "category": "weapon",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "weapon_type": raw.get("weapon_type", "simple"),
            "damage_type": raw.get("damage_type", "physical"),
            "weapon_category": raw.get("weapon_category", "simple"),
            "room_level": room_level,
            "item_stats": {
                "attack_dice": dice,
                "stat_modifier": raw.get("stat_modifier", "STR"),
                "price": random.randint(lo, hi),
            },
        }
        if raw.get("magic_element"):
            weapon_entry["magic_element"] = raw["magic_element"]
        items.append(weapon_entry)

    scroll_mult = 1.0 + (mult - 1.0) * 0.5
    for raw in llm_result.get("spell_scrolls", [])[:2]:
        items.append({
            "category": "spell_scroll",
            "name": raw["name"],
            "desc": raw.get("desc", ""),
            "spell_effect": raw.get("spell_effect", "generic"),
            "room_level": room_level,
            "item_stats": {
                "health_value": int((25 if raw.get("spell_effect") == "heal" else 0) * scroll_mult),
                "stamina_value": int((30 if raw.get("spell_effect") == "sustain" else 0) * scroll_mult),
                "price": int(random.randint(20, 40) * mult),
            },
        })

    return items


# ---------------------------------------------------------------------------
# Puzzle and event helpers
# ---------------------------------------------------------------------------

def _validate_puzzle_tools(
    event_list: list[dict], reg, report: ValidationReport | None = None,
) -> None:
    """Ensure puzzle events only reference tool attributes that exist in the registry."""
    from src.models.items import Tool
    available_attrs = set()
    for item in reg.item_registry.values():
        if isinstance(item, Tool) and item.item_stats.attribute:
            available_attrs.add(item.item_stats.attribute)

    for event in event_list:
        if event.get("type") != "puzzle":
            continue
        for choice in event.get("choices", []):
            attr = choice.get("tool_attribute")
            if attr and attr not in available_attrs:
                if report:
                    report.add_warning(
                        f"Puzzle choice referenced invalid tool_attribute '{attr}'; replaced",
                        entity_id=event.get("id", ""),
                        phase="events",
                    )
                if available_attrs:
                    choice["tool_attribute"] = random.choice(list(available_attrs))
                else:
                    choice["tool_attribute"] = None


def _validate_puzzle_abilities(
    event_list: list[dict],
    all_ability_names: list[str],
) -> None:
    """Ensure puzzle correct_ability references actual class abilities."""
    name_set = set(all_ability_names)
    for event in event_list:
        if event.get("type") != "puzzle":
            continue
        ability = event.get("correct_ability")
        if ability and ability not in name_set:
            if all_ability_names:
                event["correct_ability"] = random.choice(all_ability_names)
            else:
                event["correct_ability"] = None


_PUZZLE_NAMES = {
    "puzzle": [
        "Ancient Lock", "Runic Seal", "Trapped Passage", "Hidden Mechanism",
        "Collapsed Doorway", "Enchanted Barrier", "Puzzle Box", "Weighted Floor",
        "Crystal Alignment", "Lever Puzzle", "Shifting Walls", "Mystic Ward",
    ],
    "event": [
        "Cry for Help", "Suspicious Merchant", "Collapsed Tunnel", "Ritual Circle",
        "Wounded Traveler", "Abandoned Camp", "Strange Statue", "Whispering Well",
        "Overgrown Shrine", "Eerie Fog", "Crumbling Bridge", "Burning Cart",
    ],
}

_PUZZLE_DESCRIPTIONS = {
    "village": "Gnarled roots have buckled the cobblestones, blocking the narrow lane ahead.",
    "cave": "A jagged rockfall seals the passage; dust still drifts from the fresh collapse.",
    "dungeon": "Iron bars and a corroded mechanism block the archway deeper into the dungeon.",
    "city": "A heavy iron gate, its winch mechanism jammed with rust, bars your path.",
    "castle": "A ward-sealed door pulses with faint arcane light, refusing to budge.",
}

_EVENT_DESCRIPTIONS = {
    "village": "A group of rough-looking strangers have cornered a local shopkeeper in the alley.",
    "cave": "A wounded miner stumbles toward you, clutching a bloodied arm and gasping for help.",
    "dungeon": "Two cloaked figures argue over a locked chest, neither noticing your approach.",
    "city": "A street urchin tugs at your sleeve, pointing frantically toward a burning market stall.",
    "castle": "A noble's attendant approaches you with a sealed letter and a desperate expression.",
}

_STAT_CHECKS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

_STAT_ACTIONS = {
    "STR": "Force your way through with brute strength",
    "DEX": "Carefully navigate around the obstacle",
    "CON": "Endure the hazard and push through",
    "INT": "Study the mechanism and find the trick",
    "WIS": "Sense the pattern and act on instinct",
    "CHA": "Rally your nerve and press forward boldly",
}

_EVENT_STAT_ACTIONS = {
    "STR": "Step forward and physically intervene",
    "DEX": "Move quickly to defuse the situation",
    "CON": "Stand your ground and weather the confrontation",
    "INT": "Analyze the situation and find a clever angle",
    "WIS": "Read the room and appeal to their better nature",
    "CHA": "Talk your way through with persuasion",
}


def _event_fallback(event_type: str, env_type: str = "dungeon",
                    room_level: int = 1, tool_attrs: list | None = None,
                    ability_names: list | None = None,
                    spell_names: list | None = None) -> dict:
    """Fallback event when LLM generation fails, using real DB refs."""
    names = _PUZZLE_NAMES.get(event_type, _PUZZLE_NAMES["event"])
    name = random.choice(names)
    base_dc = 8 + room_level
    stat = random.choice(_STAT_CHECKS)
    difficulty = min(5, max(1, room_level))

    correct_tool = None
    correct_ability = None
    correct_spell = None
    if tool_attrs and random.random() < 0.3:
        correct_tool = random.choice(tool_attrs)
    if ability_names and random.random() < 0.2:
        correct_ability = random.choice(ability_names)
    if spell_names and random.random() < 0.2:
        correct_spell = random.choice(spell_names)

    if event_type == "puzzle":
        action = _STAT_ACTIONS.get(stat, f"Overcome it with {stat}")
        choices = [
            {"text": action, "stat_check": stat,
             "dc": base_dc + random.randint(0, 3), "auto_success": False},
        ]
        alt_stat = random.choice([s for s in _STAT_CHECKS if s != stat])
        alt_action = _STAT_ACTIONS.get(alt_stat, f"Try a different approach")
        choices.append(
            {"text": alt_action, "stat_check": alt_stat,
             "dc": base_dc + random.randint(1, 4), "auto_success": False},
        )
        if correct_tool:
            choices.insert(0, {
                "text": f"Use your {correct_tool} equipment to clear the way",
                "tool_attribute": correct_tool,
                "dc": max(5, base_dc - 3), "auto_success": False,
            })
        choices.append({"text": "Turn back and find another route", "auto_success": True})
        desc = _PUZZLE_DESCRIPTIONS.get(env_type,
                                        f"An ancient obstacle blocks the way in this {env_type}.")
        return {
            "name": name,
            "description": desc,
            "difficulty": difficulty,
            "choices": choices,
            "correct_tool": correct_tool,
            "correct_ability": correct_ability,
            "summary": f"{name}: {stat} check DC {base_dc}, tool={correct_tool}, ability={correct_ability}",
        }

    # event type — 5 structured slots
    dmg_type = random.choice(["health", "stamina"])
    dmg_lo = 3 + room_level
    dmg_hi = 8 + room_level * 2
    stat_action = _EVENT_STAT_ACTIONS.get(stat, "Take action")
    tool_attr = random.choice(tool_attrs) if tool_attrs else None

    choices = [
        {"text": stat_action, "stat_check": stat,
         "dc": base_dc + random.randint(0, 3), "auto_success": False},
        {"text": f"Use your training to handle this",
         "stat_check": None, "dc": 0, "auto_success": False},
        {"text": "Channel your power to resolve things",
         "stat_check": None, "dc": 0, "auto_success": False},
    ]
    if tool_attr:
        choices.append({"text": f"Put your {tool_attr} gear to use",
                        "tool_attribute": tool_attr,
                        "dc": max(5, base_dc - 2), "auto_success": False})
    else:
        choices.append({"text": "Improvise with what you have",
                        "stat_check": "DEX", "dc": base_dc + 2, "auto_success": False})
    choices.append({"text": "Back away before things escalate", "auto_success": True})

    desc = _EVENT_DESCRIPTIONS.get(env_type,
                                   f"A tense encounter unfolds in the {env_type}.")
    return {
        "name": name,
        "description": desc,
        "difficulty": difficulty,
        "choices": choices,
        "correct_ability": correct_ability,
        "correct_spell": correct_spell,
        "failure_damage_type": dmg_type,
        "failure_damage_range": [dmg_lo, dmg_hi],
        "summary": f"{name}: {stat} DC {base_dc}, fail={dmg_type} {dmg_lo}-{dmg_hi}",
    }


# ---------------------------------------------------------------------------
# Shop and loot helpers
# ---------------------------------------------------------------------------

def _generate_shop_inventory(reg) -> list[dict]:
    """Generate a random shop inventory from available items in the registry."""
    shop = []
    all_ids = reg.item_ids()
    num_items = random.randint(4, 8)
    selected_ids = random.sample(all_ids, min(num_items, len(all_ids)))
    for item_id in selected_ids:
        item = reg.get_item(item_id)
        if item:
            price = item.item_stats.price if item.item_stats.price > 0 else random.randint(5, 30)
            shop.append({
                "item_id": item_id,
                "price": price,
                "stock": random.randint(1, 5),
            })
    return shop


def _generate_loot_table(item_ids: list[int], difficulty: int) -> list[dict]:
    """Generate a loot table for a combat event based on difficulty."""
    num_entries = min(random.randint(1, 3), len(item_ids))
    loot = []
    for item_id in random.sample(item_ids, num_entries):
        drop_chance = round(random.uniform(0.1, 0.3 + difficulty * 0.1), 2)
        loot.append({"item_id": item_id, "drop_chance": min(drop_chance, 1.0)})
    return loot
