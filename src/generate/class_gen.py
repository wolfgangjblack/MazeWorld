"""Class generation pipeline: generate -> check -> validate -> fix.

Generates 4 player classes (warrior, mage, healer, jester) themed to the
current environment. Includes stat guardrail enforcement and fallback defaults.
"""

import logging
import random

from src.models.player import (
    Stats, Ability, Spell, PlayerClass,
    STAT_NAMES, STAT_BUDGET, ARCHETYPE_STAT_ROLES,
)

logger = logging.getLogger(__name__)

REQUIRED_ARCHETYPES = ["warrior", "mage", "healer", "jester"]

ELEMENTS = ["fire", "water", "forest", "light", "dark"]

# Minimum ability/spell counts per archetype
MIN_ABILITIES = {"warrior": 4, "mage": 0, "healer": 0, "jester": 0}
MIN_SPELLS = {"warrior": 0, "mage": 4, "healer": 4, "jester": 0}


def generate_classes(env_type: str, env_name: str) -> list[PlayerClass]:
    """Full generation pipeline: LLM generate -> check -> validate -> fix."""
    raw_classes = _llm_generate(env_type, env_name)
    checked = _check_classes(raw_classes, env_type, env_name)
    validated = _validate_classes(checked, env_type, env_name)
    return validated


def _llm_generate(env_type: str, env_name: str) -> list[dict]:
    """Call LLM to generate 4 class definitions."""
    try:
        from src.generate.generators.llm_primitives import generate_player_classes
        result = generate_player_classes({
            "environment": {"type": env_type, "name": env_name}
        })
        if isinstance(result, list) and len(result) >= 4:
            return result[:4]
        logger.warning("LLM returned %d classes, expected 4. Using fallback.",
                       len(result) if isinstance(result, list) else 0)
    except Exception as e:
        logger.warning("LLM class generation failed: %s. Using fallback.", e)
    return []


def _check_classes(raw: list[dict], env_type: str, env_name: str) -> list[dict]:
    """Ensure we have exactly 4 classes covering all archetypes.

    Fills missing archetypes with fallback defaults.
    """
    archetype_map = {}
    for cls_data in raw:
        arch = cls_data.get("archetype", "").lower()
        if arch in REQUIRED_ARCHETYPES and arch not in archetype_map:
            archetype_map[arch] = cls_data

    for arch in REQUIRED_ARCHETYPES:
        if arch not in archetype_map:
            logger.info("Missing archetype '%s', generating fallback.", arch)
            archetype_map[arch] = _fallback_class(arch, env_type, env_name)

    return [archetype_map[a] for a in REQUIRED_ARCHETYPES]


def _validate_classes(checked: list[dict], env_type: str, env_name: str) -> list[PlayerClass]:
    """Convert raw dicts to PlayerClass models, fixing stats/abilities as needed."""
    classes = []
    for cls_data in checked:
        archetype = cls_data.get("archetype", "warrior").lower()

        # Fix stats
        stats_raw = cls_data.get("stats", {})
        stats = _fix_stats(stats_raw, archetype)

        # Build abilities
        abilities = _parse_abilities(cls_data.get("abilities", []))
        ability_pool = _parse_abilities(cls_data.get("ability_pool", []))

        # Build spells
        spells = _parse_spells(cls_data.get("spells", []))
        spell_pool = _parse_spells(cls_data.get("spell_pool", []))

        # Ensure minimum counts
        if archetype == "warrior" and len(abilities) < MIN_ABILITIES["warrior"]:
            abilities = _pad_abilities(abilities, MIN_ABILITIES["warrior"], archetype)
        if archetype in ("mage", "healer") and len(spells) < MIN_SPELLS[archetype]:
            spells = _pad_spells(spells, MIN_SPELLS[archetype], archetype)

        pc = PlayerClass(
            name=cls_data.get("name", f"Unknown {archetype.title()}"),
            archetype=archetype,
            flavor_text=cls_data.get("flavor_text", ""),
            environment=env_type,
            stats=stats,
            starting_weapon=cls_data.get("starting_weapon", "fists"),
            abilities=abilities,
            spells=spells,
            portrait_path=None,
            portrait_prompt=cls_data.get("portrait_prompt"),
            ability_pool=ability_pool,
            spell_pool=spell_pool,
        )
        classes.append(pc)

    return classes


def _fix_stats(raw: dict, archetype: str) -> Stats:
    """Enforce stat guardrails: redistribute to hit the 72-point budget."""
    roles = ARCHETYPE_STAT_ROLES.get(archetype, ARCHETYPE_STAT_ROLES["warrior"])

    values = {}
    for stat in STAT_NAMES:
        val = raw.get(stat, 10)
        if not isinstance(val, (int, float)):
            val = 10
        values[stat] = int(val)

    effective_roles = dict(roles)

    # Clamp to role ranges
    for stat in effective_roles.get("primary", []):
        lo, hi = _range_for_role("primary", archetype)
        values[stat] = max(lo, min(hi, values[stat]))
    for stat in effective_roles.get("secondary", []):
        lo, hi = _range_for_role("secondary", archetype)
        values[stat] = max(lo, min(hi, values[stat]))
    for stat in effective_roles.get("dump", []):
        lo, hi = _range_for_role("dump", archetype)
        values[stat] = max(lo, min(hi, values[stat]))

    # Handle LUCK for non-jester (LUCK is dump range 6-10 unless jester)
    all_assigned = [s for role_stats in effective_roles.values() for s in role_stats]
    unassigned = [s for s in STAT_NAMES if s not in all_assigned]
    for stat in unassigned:
        values[stat] = max(6, min(10, values[stat]))

    # Redistribute to hit budget
    total = sum(values.values())
    diff = total - STAT_BUDGET

    if diff != 0:
        # Adjust secondary, dump, and unassigned stats
        adjustable = (effective_roles.get("secondary", [])
                      + effective_roles.get("dump", [])
                      + unassigned)
        if not adjustable:
            adjustable = [s for s in STAT_NAMES if s not in effective_roles.get("primary", [])]

        idx = 0
        while diff != 0 and idx < len(adjustable) * 30:
            stat = adjustable[idx % len(adjustable)]
            role = _stat_role(stat, effective_roles)
            if stat in unassigned:
                lo, hi = (6, 10)
            else:
                lo, hi = _range_for_role(role, archetype)

            if diff > 0 and values[stat] > lo:
                values[stat] -= 1
                diff -= 1
            elif diff < 0 and values[stat] < hi:
                values[stat] += 1
                diff += 1
            idx += 1

    return Stats(**values)


def _stat_role(stat: str, roles: dict) -> str:
    for role_name, stats in roles.items():
        if stat in stats:
            return role_name
    return "dump"


def _range_for_role(role: str, archetype: str = "") -> tuple[int, int]:
    if role == "primary":
        return (14, 18)
    elif role == "secondary":
        # Jester needs wider secondary range to hit 72 budget
        if archetype == "jester":
            return (9, 13)
        return (11, 14)
    return (6, 10)


def _parse_abilities(raw_list: list) -> list[Ability]:
    abilities = []
    for a in raw_list:
        if isinstance(a, dict):
            try:
                abilities.append(Ability(
                    name=a.get("name", "Unknown"),
                    description=a.get("description", ""),
                    stat=a.get("stat", "STR"),
                    cost_hunger=a.get("cost_hunger", 0),
                    cost_thirst=a.get("cost_thirst", 0),
                ))
            except Exception:
                pass
    return abilities


def _parse_spells(raw_list: list) -> list[Spell]:
    spells = []
    for s in raw_list:
        if isinstance(s, dict):
            try:
                spells.append(Spell(
                    name=s.get("name", "Unknown Spell"),
                    description=s.get("description", ""),
                    element=s.get("element", "fire"),
                    damage_dice=s.get("damage_dice", "1d6"),
                    spell_type=s.get("spell_type", "damage"),
                    cost_hunger=s.get("cost_hunger", 5),
                    cost_thirst=s.get("cost_thirst", 0),
                ))
            except Exception:
                pass
    return spells


def _pad_abilities(existing: list[Ability], target: int, archetype: str) -> list[Ability]:
    """Pad abilities list with generic fallbacks."""
    fallbacks = {
        "warrior": [
            Ability(name="Bash", description="Slam target with your shield.", stat="STR", cost_hunger=5),
            Ability(name="Intimidate", description="Frighten an enemy into hesitation.", stat="CHA", cost_hunger=3),
            Ability(name="Break Door", description="Force open a stuck door.", stat="STR", cost_hunger=8),
            Ability(name="Rally", description="Boost morale, restoring a small amount of party HP.", stat="CHA", cost_hunger=5),
        ],
    }
    defaults = fallbacks.get(archetype, [
        Ability(name="Focus", description="Concentrate to improve next action.", stat="INT"),
    ])
    result = list(existing)
    for fb in defaults:
        if len(result) >= target:
            break
        if fb.name not in {a.name for a in result}:
            result.append(fb)
    return result


def _pad_spells(existing: list[Spell], target: int, archetype: str) -> list[Spell]:
    """Pad spells list with generic fallbacks."""
    element = random.choice(ELEMENTS)
    if archetype == "mage":
        defaults = [
            Spell(name=f"{element.title()} Bolt", description=f"A bolt of {element} energy.",
                  element=element, damage_dice="1d8", spell_type="damage", cost_hunger=5),
            Spell(name=f"{element.title()} Blast", description=f"An explosion of {element} force.",
                  element=element, damage_dice="2d6", spell_type="damage", cost_hunger=8),
            Spell(name=f"{element.title()} Shield", description=f"A protective {element} barrier.",
                  element=element, damage_dice="0", spell_type="utility", cost_hunger=5),
            Spell(name=f"{element.title()} Sight", description=f"See hidden things using {element} magic.",
                  element=element, damage_dice="0", spell_type="utility", cost_hunger=3),
        ]
    elif archetype == "healer":
        defaults = [
            Spell(name="Healing Light", description="Restore HP to a target.",
                  element=element, damage_dice="1d8", spell_type="healing", cost_hunger=5),
            Spell(name="Bolster", description="Temporarily boost an ally's defense.",
                  element=element, damage_dice="0", spell_type="buff", cost_hunger=5),
            Spell(name=f"{element.title()} Strike", description=f"A damaging bolt of {element}.",
                  element=element, damage_dice="1d6", spell_type="damage", cost_hunger=5),
            Spell(name="Purify", description="Remove a negative effect.",
                  element=element, damage_dice="0", spell_type="utility", cost_hunger=3),
        ]
    else:
        defaults = []

    result = list(existing)
    for sp in defaults:
        if len(result) >= target:
            break
        if sp.name not in {s.name for s in result}:
            result.append(sp)
    return result


def _fallback_class(archetype: str, env_type: str, env_name: str) -> dict:
    """Generate a complete fallback class definition for an archetype."""
    fallback_names = {
        "warrior": {"forest": "Ranger", "cave": "Berserker", "dungeon": "Knight",
                     "castle": "Guardian", "city": "Soldier", "house": "Brawler"},
        "mage":    {"forest": "Druid", "cave": "Geomancer", "dungeon": "Warlock",
                     "castle": "Court Wizard", "city": "Arcanist", "house": "Hedge Mage"},
        "healer":  {"forest": "Shaman", "cave": "Oracle", "dungeon": "Cleric",
                     "castle": "Priest", "city": "Apothecary", "house": "Herbalist"},
        "jester":  {"forest": "Trickster", "cave": "Gremlin", "dungeon": "Fool",
                     "castle": "Court Jester", "city": "Charlatan", "house": "Prankster"},
    }

    name = fallback_names.get(archetype, {}).get(env_type, archetype.title())

    # Build raw stat targets, then use _fix_stats for budget enforcement
    if archetype == "jester":
        stats = {s: 11 for s in STAT_NAMES if s != "LUCK"}
        stats["LUCK"] = 16
    else:
        roles = ARCHETYPE_STAT_ROLES[archetype]
        stats = {}
        for stat in roles.get("primary", []):
            stats[stat] = 16
        for stat in roles.get("secondary", []):
            stats[stat] = 12
        for stat in roles.get("dump", []):
            stats[stat] = 8
        if "LUCK" not in stats:
            stats["LUCK"] = 8

    # Use _fix_stats for budget-correct redistribution
    fixed = _fix_stats(stats, archetype)
    stats = fixed.as_dict()

    return {
        "name": name,
        "archetype": archetype,
        "flavor_text": f"A {archetype} from {env_name}.",
        "starting_weapon": {"warrior": "sword", "mage": "staff", "healer": "mace", "jester": "dagger"}[archetype],
        "stats": stats,
        "abilities": [],
        "spells": [],
        "ability_pool": [],
        "spell_pool": [],
        "portrait_prompt": f"A {name.lower()} character, {archetype} class, in a {env_type} setting, fantasy pixel art",
    }
