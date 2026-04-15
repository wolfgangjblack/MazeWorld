"""Spell pool generation: batch-generate named spell pools via LLM.

Produces 4 pools (mage_damage, healer_damage, heal, buff) of 10 spells each.
The LLM provides only name + description; all mechanics come from skeletons.
"""

import logging
import random

from src.generate.generators.llm_primitives import _parse_json_array
from src.generate.llm_executor import generate_batch
from src.models.spell import (
    roll_spell_skeleton,
)
from src.prompts import get_prompt_set

logger = logging.getLogger(__name__)

ELEMENTS = ["fire", "water", "forest", "light", "dark"]

POOL_CONFIGS = {
    "mage_damage": {
        "archetype": "mage",
        "slots": [
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_multi", "targets": "multi"},
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_multi", "targets": "multi"},
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_multi", "targets": "multi"},
            {"spell_type": "damage_single", "targets": "single"},
            {"spell_type": "damage_single", "targets": "single"},
        ],
    },
    "healer_damage": {
        "archetype": "healer",
        "slots": [{"spell_type": "damage_single", "targets": "single"}] * 10,
    },
    "heal": {
        "archetype": "healer",
        "slots": [{"spell_type": "heal", "targets": "self"}] * 10,
    },
    "buff": {
        "archetype": "healer",
        "slots": [
            {"spell_type": "buff_stat", "targets": "self"},
            {"spell_type": "buff_sustain", "targets": "self"},
            {"spell_type": "buff_stat", "targets": "self"},
            {"spell_type": "buff_sustain", "targets": "self"},
            {"spell_type": "buff_stat", "targets": "self"},
            {"spell_type": "buff_sustain", "targets": "self"},
            {"spell_type": "buff_stat", "targets": "self"},
            {"spell_type": "buff_sustain", "targets": "self"},
            {"spell_type": "buff_stat", "targets": "self"},
            {"spell_type": "buff_sustain", "targets": "self"},
        ],
    },
}


def _build_pool_skeletons(pool_type: str, element: str) -> list[dict]:
    """Build skeletons for a pool. Dice are set to room-0 baseline (will be
    overridden at acquisition time via compute_spell_dice)."""
    cfg = POOL_CONFIGS[pool_type]
    archetype = cfg["archetype"]
    return [roll_spell_skeleton(archetype, slot, available_at_room=0, class_element=element) for slot in cfg["slots"]]


def _merge_pool_results(
    raw_list: list[dict],
    skeletons: list[dict],
    pool_type: str,
) -> list[dict]:
    """Merge LLM name/desc onto skeletons, returning serializable dicts."""
    results = []
    for i, skel in enumerate(skeletons):
        llm = raw_list[i] if i < len(raw_list) else {}
        entry = dict(skel)
        entry["name"] = llm.get("name", f"{pool_type.replace('_', ' ').title()} {i + 1}")
        entry["description"] = llm.get("description", "")
        entry.pop("available_at_room", None)
        results.append(entry)
    return results


def generate_spell_pools(
    mage_element: str,
    healer_element: str,
    existing_spell_names: list[str],
    env_context: str = "",
) -> dict[str, list[dict]]:
    """Generate all 4 spell pools via batched LLM calls.

    Returns a dict keyed by pool type with lists of spell dicts (serializable).
    Each dict has all Spell fields except num_dice/die_sides which are set to
    room-0 baseline and should be overridden at acquisition time.
    """
    prompts = get_prompt_set()

    pool_types = ["mage_damage", "healer_damage", "heal", "buff"]
    element_map = {
        "mage_damage": mage_element,
        "healer_damage": healer_element,
        "heal": healer_element,
        "buff": random.choice(ELEMENTS),
    }

    requests = []
    for pt in pool_types:
        req = prompts.spell_pool_generation(
            pool_type=pt,
            element=element_map[pt],
            count=10,
            existing_names=existing_spell_names,
            env_context=env_context,
        )
        requests.append(req)

    logger.info("Generating spell pools: 4 batched LLM calls...")
    raw_responses = generate_batch(requests)

    skeleton_map = {pt: _build_pool_skeletons(pt, element_map[pt]) for pt in pool_types}

    pools: dict[str, list[dict]] = {}
    for idx, pt in enumerate(pool_types):
        raw = raw_responses[idx]
        if raw is None:
            logger.warning("Spell pool '%s' LLM call failed, using generic names", pt)
            parsed = []
        else:
            parsed = _parse_json_array(raw)

        pools[pt] = _merge_pool_results(parsed, skeleton_map[pt], pt)
        logger.info("Spell pool '%s': %d spells", pt, len(pools[pt]))

    return pools
