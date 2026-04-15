"""Class generation pipeline: generate -> check -> validate -> fix.

Generates 4 player classes (warrior, mage, healer, jester) themed to the
current environment. Includes stat guardrail enforcement and fallback defaults.
"""

import logging
import random

from src.models.player import (
    ABILITY_DISTRIBUTIONS,
    ARCHETYPE_STAT_ROLES,
    STAT_BUDGET,
    STAT_NAMES,
    Ability,
    PlayerClass,
    Stats,
    roll_ability_skeleton,
)
from src.models.spell import (
    SPELL_DISTRIBUTIONS,
    Spell,
    compute_stamina_cost,
    roll_jester_spell_skeletons,
    roll_spell_skeleton,
)

logger = logging.getLogger(__name__)

REQUIRED_ARCHETYPES = ["warrior", "mage", "healer", "jester"]

ELEMENTS = ["fire", "water", "forest", "light", "dark"]

# Minimum ability/spell counts per archetype
MIN_ABILITIES = {"warrior": 4, "mage": 0, "healer": 0, "jester": 0}
MIN_SPELLS = {"warrior": 0, "mage": 4, "healer": 4, "jester": 0}


def _build_archetype_skeletons() -> dict[str, dict]:
    """Pre-roll spell and ability skeletons for all archetypes."""
    class_element_mage = random.choice(ELEMENTS)
    class_element_healer = random.choice(ELEMENTS)

    archetype_skeletons: dict[str, dict] = {}
    for arch in REQUIRED_ARCHETYPES:
        element = class_element_mage if arch == "mage" else class_element_healer if arch == "healer" else "fire"
        spell_skels = [roll_spell_skeleton(arch, slot, 0, element) for slot in SPELL_DISTRIBUTIONS[arch]["starting"]]
        pool_skels = [
            roll_spell_skeleton(arch, slot, i + 1, element) for i, slot in enumerate(SPELL_DISTRIBUTIONS[arch]["pool"])
        ]
        ability_skels = [roll_ability_skeleton(s) for s in ABILITY_DISTRIBUTIONS[arch]["starting"]]
        ability_pool_skels = [roll_ability_skeleton(s) for s in ABILITY_DISTRIBUTIONS[arch]["pool"]]
        archetype_skeletons[arch] = {
            "spells": spell_skels,
            "spell_pool": pool_skels,
            "abilities": ability_skels,
            "ability_pool": ability_pool_skels,
            "element": element,
        }

    # Jester steals 0-3 random spell skeletons from mage+healer pools
    all_caster_pool = archetype_skeletons["mage"]["spell_pool"] + archetype_skeletons["healer"]["spell_pool"]
    jester_stolen = roll_jester_spell_skeletons(all_caster_pool)
    archetype_skeletons["jester"]["spell_pool"] = jester_stolen

    return archetype_skeletons


def generate_classes(env_type: str, env_name: str) -> tuple[list[PlayerClass], dict[str, str]]:
    """Full generation pipeline: pre-roll skeletons -> LLM generate -> check -> validate.

    Returns (player_classes, class_elements) where class_elements maps
    archetype to the chosen element (e.g. {"mage": "fire", "healer": "water"}).
    """
    archetype_skeletons = _build_archetype_skeletons()
    raw_classes = _llm_generate(env_type, env_name, archetype_skeletons)
    checked = _check_classes(raw_classes, env_type, env_name)
    validated = _validate_classes(checked, env_type, env_name, archetype_skeletons)
    class_elements = {arch: skels["element"] for arch, skels in archetype_skeletons.items()}
    return validated, class_elements


def _llm_generate(env_type: str, env_name: str, archetype_skeletons: dict[str, dict] | None = None) -> list[dict]:
    """Call LLM to generate 4 class definitions."""
    try:
        from src.generate.generators.llm_primitives import generate_player_classes

        result = generate_player_classes(
            {"environment": {"type": env_type, "name": env_name}},
            archetype_skeletons=archetype_skeletons,
        )
        if isinstance(result, list) and len(result) >= 4:
            return result[:4]
        logger.warning(
            "LLM returned %d classes, expected 4. Using fallback.", len(result) if isinstance(result, list) else 0
        )
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


def _merge_spell_skeletons(llm_list: list[dict], skeletons: list[dict]) -> list[Spell]:
    """Build Spell objects by merging LLM name/desc onto pre-rolled skeletons."""
    results = []
    for i, skel in enumerate(skeletons):
        llm = llm_list[i] if i < len(llm_list) else {}
        skel_copy = dict(skel)
        skel_copy.pop("available_at_room", None)
        try:
            results.append(
                Spell(
                    name=llm.get("name", f"Spell {i + 1}"),
                    description=llm.get("description", ""),
                    **skel_copy,
                )
            )
        except Exception:
            logger.warning("Failed to merge spell skeleton %d, skipping", i, exc_info=True)
    return results


def _merge_ability_skeletons(llm_list: list[dict], skeletons: list[dict]) -> list[Ability]:
    """Build Ability objects by merging LLM name/desc onto pre-rolled skeletons."""
    results = []
    for i, skel in enumerate(skeletons):
        llm = llm_list[i] if i < len(llm_list) else {}
        skel_copy = dict(skel)
        skel_copy.pop("purpose", None)
        try:
            results.append(
                Ability(
                    name=llm.get("name", f"Ability {i + 1}"),
                    description=llm.get("description", ""),
                    **skel_copy,
                )
            )
        except Exception:
            logger.warning("Failed to merge ability skeleton %d, skipping", i, exc_info=True)
    return results


def _sample_jester_starting(classes: list[PlayerClass]) -> tuple[list[Spell], list[Ability]]:
    """Sample starting spells/abilities for jester from already-built classes."""
    mage_spells = []
    healer_spells = []
    warrior_abilities = []
    for pc in classes:
        if pc.archetype == "mage":
            mage_spells = pc.spells
        elif pc.archetype == "healer":
            healer_spells = pc.spells
        elif pc.archetype == "warrior":
            warrior_abilities = pc.abilities

    stolen_spells: list[Spell] = []
    damage_candidates = [s for s in mage_spells if s.spell_type.startswith("damage")]
    if damage_candidates:
        picked = random.choice(damage_candidates)
        stolen_spells.append(picked.model_copy(update={"stat": "LUCK"}))

    support_candidates = [s for s in healer_spells if s.spell_type in ("heal", "buff_stat", "buff_sustain")]
    if support_candidates:
        picked = random.choice(support_candidates)
        stolen_spells.append(picked.model_copy(update={"stat": "LUCK"}))

    stolen_abilities: list[Ability] = []
    if warrior_abilities:
        stolen_abilities.append(random.choice(warrior_abilities).model_copy())

    return stolen_spells, stolen_abilities


def _validate_classes(
    checked: list[dict],
    env_type: str,
    env_name: str,
    archetype_skeletons: dict[str, dict] | None = None,
) -> list[PlayerClass]:
    """Convert raw dicts to PlayerClass models, fixing stats/abilities as needed."""
    classes = []
    jester_data = None
    for cls_data in checked:
        archetype = cls_data.get("archetype", "warrior").lower()
        if archetype == "jester":
            jester_data = cls_data
            continue

        skels = (archetype_skeletons or {}).get(archetype)

        stats_raw = cls_data.get("stats", {})
        stats = _fix_stats(stats_raw, archetype)

        if skels and skels.get("abilities"):
            abilities = _merge_ability_skeletons(cls_data.get("abilities", []), skels["abilities"])
        else:
            abilities = _parse_abilities(cls_data.get("abilities", []))

        if skels and skels.get("ability_pool"):
            ability_pool = _merge_ability_skeletons(cls_data.get("ability_pool", []), skels["ability_pool"])
        else:
            ability_pool = _parse_abilities(cls_data.get("ability_pool", []))

        if skels and skels.get("spells"):
            spells = _merge_spell_skeletons(cls_data.get("spells", []), skels["spells"])
        else:
            spells = _parse_spells(cls_data.get("spells", []))

        if skels and skels.get("spell_pool"):
            spell_pool = _merge_spell_skeletons(cls_data.get("spell_pool", []), skels["spell_pool"])
        else:
            spell_pool = _parse_spells(cls_data.get("spell_pool", []))

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

    # Build jester last so we can sample from the other classes' finished objects
    if jester_data is None:
        jester_data = _fallback_class("jester", env_type, env_name)

    skels = (archetype_skeletons or {}).get("jester")
    stats = _fix_stats(jester_data.get("stats", {}), "jester")

    jester_spells, jester_abilities = _sample_jester_starting(classes)

    if skels and skels.get("spell_pool"):
        spell_pool = _merge_spell_skeletons(jester_data.get("spell_pool", []), skels["spell_pool"])
    else:
        spell_pool = _parse_spells(jester_data.get("spell_pool", []))

    if skels and skels.get("ability_pool"):
        ability_pool = _merge_ability_skeletons(jester_data.get("ability_pool", []), skels["ability_pool"])
    else:
        ability_pool = _parse_abilities(jester_data.get("ability_pool", []))

    jester_pc = PlayerClass(
        name=jester_data.get("name", "Unknown Jester"),
        archetype="jester",
        flavor_text=jester_data.get("flavor_text", ""),
        environment=env_type,
        stats=stats,
        starting_weapon=jester_data.get("starting_weapon", "fists"),
        abilities=jester_abilities,
        spells=jester_spells,
        portrait_path=None,
        portrait_prompt=jester_data.get("portrait_prompt"),
        ability_pool=ability_pool,
        spell_pool=spell_pool,
    )
    classes.append(jester_pc)

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

    all_assigned = [s for role_stats in effective_roles.values() for s in role_stats]
    unassigned = [s for s in STAT_NAMES if s not in all_assigned]
    for stat in unassigned:
        values[stat] = max(8, min(12, values[stat]))

    # Redistribute to hit budget
    total = sum(values.values())
    diff = total - STAT_BUDGET

    if diff != 0:
        adjustable = (
            effective_roles.get("secondary", [])
            + effective_roles.get("dump", [])
            + unassigned
            + effective_roles.get("primary", [])
        )

        idx = 0
        while diff != 0 and idx < len(adjustable) * 30:
            stat = adjustable[idx % len(adjustable)]
            role = _stat_role(stat, effective_roles)
            if stat in unassigned:
                lo, hi = (8, 12)
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
        if archetype == "jester":
            return (11, 15)
        return (12, 16)
    return (8, 12)


def _parse_abilities(raw_list: list) -> list[Ability]:
    abilities = []
    for a in raw_list:
        if isinstance(a, dict):
            try:
                abilities.append(
                    Ability(
                        name=a.get("name", "Unknown"),
                        description=a.get("description", ""),
                        stat=a.get("stat", "STR"),
                        stamina_cost=a.get("stamina_cost", a.get("hunger_cost", 0) + a.get("thirst_cost", 0)),
                    )
                )
            except Exception:
                logger.warning("Skipping malformed ability: %s", a, exc_info=True)
    return abilities


_SPELL_TYPE_MAP = {
    "damage": "damage_single",
    "healing": "heal",
    "buff": "buff_stat",
    "utility": "buff_sustain",
}


def _parse_dice_fields(s: dict) -> tuple[int, int]:
    """Extract num_dice and die_sides from a spell dict, handling legacy damage_dice."""
    if "num_dice" in s and "die_sides" in s:
        return s["num_dice"], s["die_sides"]
    dd = s.get("damage_dice", 0)
    if isinstance(dd, str) and "d" in dd:
        parts = dd.split("d")
        return int(parts[0]), int(parts[1])
    if isinstance(dd, int) and dd > 0:
        return 1, dd
    return 0, 0


def _parse_spells(raw_list: list) -> list[Spell]:
    spells = []
    for s in raw_list:
        if isinstance(s, dict):
            try:
                raw_type = s.get("spell_type", "damage")
                spell_type = _SPELL_TYPE_MAP.get(raw_type, raw_type)
                num_dice, die_sides = _parse_dice_fields(s)
                targets = s.get("targets", "single")
                spells.append(
                    Spell(
                        name=s.get("name", "Unknown Spell"),
                        description=s.get("description", ""),
                        element=s.get("element", "fire"),
                        stat=s.get("stat", "INT"),
                        num_dice=num_dice,
                        die_sides=die_sides,
                        spell_type=spell_type,
                        stamina_cost=s.get(
                            "stamina_cost",
                            compute_stamina_cost(die_sides, num_dice, targets, spell_type),
                        ),
                        targets=targets,
                        heal_amount=s.get("heal_amount", 0),
                        buff_stat=s.get("buff_stat"),
                        buff_value=s.get("buff_value", 2),
                    )
                )
            except Exception:
                logger.warning("Skipping malformed spell: %s", s, exc_info=True)
    return spells


def _pad_abilities(existing: list[Ability], target: int, archetype: str) -> list[Ability]:
    """Pad abilities list with generic fallbacks."""
    fallbacks = {
        "warrior": [
            Ability(name="Bash", description="Slam target with your shield.", stat="STR", stamina_cost=5),
            Ability(name="Intimidate", description="Frighten an enemy into hesitation.", stat="CHA", stamina_cost=3),
            Ability(name="Break Door", description="Force open a stuck door.", stat="STR", stamina_cost=8),
            Ability(
                name="Rally",
                description="Boost morale, restoring a small amount of party HP.",
                stat="CHA",
                stamina_cost=5,
            ),
        ],
    }
    defaults = fallbacks.get(
        archetype,
        [
            Ability(name="Focus", description="Concentrate to improve next action.", stat="INT"),
        ],
    )
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
            Spell(
                name=f"{element.title()} Bolt",
                description=f"A bolt of {element} energy.",
                element=element,
                stat="INT",
                num_dice=1,
                die_sides=8,
                spell_type="damage_single",
                stamina_cost=compute_stamina_cost(8, 1, "single", "damage_single"),
                targets="single",
            ),
            Spell(
                name=f"{element.title()} Blast",
                description=f"An explosion of {element} force.",
                element=element,
                stat="INT",
                num_dice=1,
                die_sides=6,
                spell_type="damage_multi",
                stamina_cost=compute_stamina_cost(6, 1, "multi", "damage_multi"),
                targets="multi",
            ),
            Spell(
                name=f"{element.title()} Shield",
                description=f"A protective {element} barrier.",
                element=element,
                stat="INT",
                spell_type="buff_stat",
                buff_stat="CON",
                stamina_cost=compute_stamina_cost(0, 0, "self", "buff_stat"),
                targets="self",
            ),
            Spell(
                name=f"{element.title()} Sight",
                description=f"See hidden things using {element} magic.",
                element=element,
                stat="INT",
                spell_type="buff_sustain",
                stamina_cost=compute_stamina_cost(0, 0, "self", "buff_sustain"),
                targets="self",
            ),
        ]
    elif archetype == "healer":
        defaults = [
            Spell(
                name="Healing Light",
                description="Restore HP to a target.",
                element=element,
                stat="WIS",
                spell_type="heal",
                num_dice=1,
                die_sides=6,
                stamina_cost=compute_stamina_cost(6, 1, "self", "heal"),
                targets="self",
            ),
            Spell(
                name="Bolster",
                description="Temporarily boost an ally's defense.",
                element=element,
                stat="WIS",
                spell_type="buff_stat",
                buff_stat="CON",
                stamina_cost=compute_stamina_cost(0, 0, "self", "buff_stat"),
                targets="self",
            ),
            Spell(
                name=f"{element.title()} Strike",
                description=f"A damaging bolt of {element}.",
                element=element,
                stat="WIS",
                num_dice=1,
                die_sides=6,
                spell_type="damage_single",
                stamina_cost=compute_stamina_cost(6, 1, "single", "damage_single"),
                targets="single",
            ),
            Spell(
                name="Purify",
                description="Remove a negative effect.",
                element=element,
                stat="WIS",
                spell_type="buff_sustain",
                stamina_cost=compute_stamina_cost(0, 0, "self", "buff_sustain"),
                targets="self",
            ),
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
        "warrior": {
            "forest": "Ranger",
            "cave": "Berserker",
            "dungeon": "Knight",
            "castle": "Guardian",
            "city": "Soldier",
            "house": "Brawler",
        },
        "mage": {
            "forest": "Druid",
            "cave": "Geomancer",
            "dungeon": "Warlock",
            "castle": "Court Wizard",
            "city": "Arcanist",
            "house": "Hedge Mage",
        },
        "healer": {
            "forest": "Shaman",
            "cave": "Oracle",
            "dungeon": "Cleric",
            "castle": "Priest",
            "city": "Apothecary",
            "house": "Herbalist",
        },
        "jester": {
            "forest": "Trickster",
            "cave": "Gremlin",
            "dungeon": "Fool",
            "castle": "Court Jester",
            "city": "Charlatan",
            "house": "Prankster",
        },
    }

    name = fallback_names.get(archetype, {}).get(env_type, archetype.title())

    # Build raw stat targets, then use _fix_stats for budget enforcement
    if archetype == "jester":
        stats = {s: 13 for s in STAT_NAMES if s != "LUCK"}
        stats["LUCK"] = 16
    else:
        roles = ARCHETYPE_STAT_ROLES[archetype]
        stats = {}
        for stat in roles.get("primary", []):
            stats[stat] = 16
        for stat in roles.get("secondary", []):
            stats[stat] = 14
        for stat in roles.get("dump", []):
            stats[stat] = 10
        if "LUCK" not in stats:
            stats["LUCK"] = 10

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
