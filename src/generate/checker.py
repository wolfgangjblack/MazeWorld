"""Base Checker/Editor — reviews generated content for theme, coherence, quality.

Each concrete checker implements ``check()`` which receives raw generated data
and returns a ``CheckResult`` with pass/fail plus a list of issues.

Pattern mirrors ``class_gen.py``'s ``_check_classes`` stage.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.models.player import (
    ARCHETYPE_STAT_ROLES,
    STAT_BUDGET,
    STAT_NAMES,
)

logger = logging.getLogger(__name__)


def check_quest_references(
    quest: dict,
    *,
    npc_ids: set | None = None,
    item_ids: set | None = None,
    event_ids: set | None = None,
    quest_ids: set | None = None,
    label: str = "",
) -> list[str]:
    """Check that a quest's entity references resolve to known IDs.

    Callers are responsible for ensuring ID types are consistent
    (e.g. all strings or all ints) between *quest* fields and the
    provided sets.
    """
    issues: list[str] = []
    prefix = f"{label}: " if label else ""
    qtype = quest.get("type", "")

    if npc_ids is not None and quest.get("giver_npc_id") not in npc_ids:
        issues.append(f"{prefix}giver NPC {quest.get('giver_npc_id')} not found")

    if qtype == "fetch":
        target_items = quest.get("target_items", [])
        if target_items:
            for ti in target_items:
                if item_ids is not None and ti.get("item_id") not in item_ids:
                    issues.append(f"{prefix}fetch item {ti.get('item_id')} not on map")
        elif not quest.get("target_tile") and not quest.get("item_category"):
            issues.append(f"{prefix}fetch quest has no target_items, target_tile, or item_category")
    elif qtype == "escort":
        if npc_ids is not None and quest.get("escort_npc_id") not in npc_ids:
            issues.append(f"{prefix}escort NPC {quest.get('escort_npc_id')} not found")
    elif qtype == "delivery":
        if item_ids is not None and quest.get("delivery_item_id") not in item_ids:
            issues.append(f"{prefix}delivery item {quest.get('delivery_item_id')} not on map")
        if npc_ids is not None and quest.get("target_npc_id") not in npc_ids:
            issues.append(f"{prefix}target NPC {quest.get('target_npc_id')} not found")
    elif qtype in ("combat", "solve"):
        if event_ids is not None and quest.get("target_event_id") not in event_ids:
            issues.append(f"{prefix}target event {quest.get('target_event_id')} not found")

    if quest_ids is not None:
        prereq = quest.get("prerequisite_quest_id")
        if prereq and prereq not in quest_ids:
            issues.append(f"{prefix}Prerequisite quest {prereq} not found")

    return issues


@dataclass
class CheckResult:
    """Outcome of a check pass."""

    passed: bool
    issues: list[str] = field(default_factory=list)
    data: object = None  # Optionally return corrected data


class BaseChecker(ABC):
    """Abstract checker that reviews generated content."""

    @abstractmethod
    def check(self, data, context: dict | None = None) -> CheckResult:
        """Check *data* and return a ``CheckResult``."""
        ...


class ClassChecker(BaseChecker):
    """Validates player-class generation output.

    Checks:
    - Exactly 4 classes covering all required archetypes
    - Each class has a name, archetype, and stats dict
    - Stat budget totals 72
    - Stat values fall within archetype role ranges
    """

    REQUIRED_ARCHETYPES = {"warrior", "mage", "healer", "jester"}

    def check(self, data: list[dict], context: dict | None = None) -> CheckResult:
        issues: list[str] = []
        if not isinstance(data, list):
            return CheckResult(passed=False, issues=["Expected a list of class dicts"])

        # Archetype coverage
        archetypes_found = {d.get("archetype", "").lower() for d in data}
        missing = self.REQUIRED_ARCHETYPES - archetypes_found
        if missing:
            issues.append(f"Missing archetypes: {', '.join(sorted(missing))}")

        if len(data) != 4:
            issues.append(f"Expected 4 classes, got {len(data)}")

        for idx, cls in enumerate(data):
            label = cls.get("name", f"class[{idx}]")
            archetype = cls.get("archetype", "").lower()

            if not cls.get("name"):
                issues.append(f"class[{idx}] missing name")

            stats = cls.get("stats", {})
            if not stats:
                issues.append(f"{label} missing stats")
                continue

            total = sum(stats.get(s, 0) for s in STAT_NAMES)
            if total != STAT_BUDGET:
                issues.append(f"{label} stat total {total} != {STAT_BUDGET}")

            roles = ARCHETYPE_STAT_ROLES.get(archetype, {})
            for stat in roles.get("primary", []):
                val = stats.get(stat, 10)
                if not (14 <= val <= 18):
                    issues.append(f"{label} {stat}={val} outside primary 14-18")
            for stat in roles.get("secondary", []):
                val = stats.get(stat, 10)
                lo, hi = (11, 15) if archetype == "jester" else (12, 16)
                if not (lo <= val <= hi):
                    issues.append(f"{label} {stat}={val} outside secondary {lo}-{hi}")
            for stat in roles.get("dump", []):
                val = stats.get(stat, 10)
                if not (8 <= val <= 12):
                    issues.append(f"{label} {stat}={val} outside dump 8-12")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)


class QuestChecker(BaseChecker):
    """Checks quest data for required fields and reference validity."""

    REQUIRED_FIELDS = {"id", "type", "title", "description", "giver_npc_id"}

    def check(self, data: dict, context: dict | None = None) -> CheckResult:
        issues: list[str] = []
        ctx = context or {}
        npc_ids = ctx.get("npc_ids", set()) or None
        item_ids = ctx.get("item_ids", set()) or None
        event_ids = ctx.get("event_ids", set()) or None

        missing = self.REQUIRED_FIELDS - set(data.keys())
        if missing:
            issues.append(f"Missing fields: {', '.join(sorted(missing))}")

        issues.extend(
            check_quest_references(
                data,
                npc_ids=npc_ids,
                item_ids=item_ids,
                event_ids=event_ids,
            )
        )

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)


class EventChecker(BaseChecker):
    """Checks event data for required fields and solvability."""

    def check(self, data: dict, context: dict | None = None) -> CheckResult:
        issues: list[str] = []

        if not data.get("name"):
            issues.append("Event missing name")
        if not data.get("type"):
            issues.append("Event missing type")

        etype = data.get("type", "")
        if etype == "combat":
            if not data.get("monster_ids"):
                issues.append("Combat event has no monster_ids")
        elif etype == "puzzle":
            choices = data.get("choices", [])
            has_walkaway = any(c.get("auto_success") for c in choices)
            if not has_walkaway:
                issues.append("Puzzle has no walk-away option")

        # Validate time_gate if present
        time_gate = data.get("time_gate")
        if time_gate is not None and time_gate not in ("day", "night"):
            issues.append(f"Invalid time_gate value: {time_gate}")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)


class NPCChecker(BaseChecker):
    """Checks NPC data for required fields and theme coherence."""

    REQUIRED_FIELDS = {"id", "name"}

    def check(self, data: dict, context: dict | None = None) -> CheckResult:
        issues: list[str] = []
        npc_id = data.get("id", "?")

        missing = self.REQUIRED_FIELDS - set(data.keys())
        if missing:
            issues.append(f"NPC {npc_id}: missing fields: {', '.join(sorted(missing))}")

        if not data.get("name"):
            issues.append(f"NPC {npc_id}: empty name")

        if data.get("selected") and not data.get("opening_greeting"):
            issues.append(f"NPC {npc_id}: active NPC missing opening_greeting")

        npc_type = data.get("type", "")
        valid_types = {"StaticNPC", "RandomNPC", "AggressiveNPC", "MerchantNPC"}
        if npc_type and npc_type not in valid_types:
            issues.append(f"NPC {npc_id}: unknown type '{npc_type}'")

        if npc_type == "MerchantNPC" and not data.get("shop_inventory"):
            issues.append(f"NPC {npc_id}: MerchantNPC missing shop_inventory")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)


class MonsterChecker(BaseChecker):
    """Checks monster data for required stats and level scaling."""

    def check(self, data: dict, context: dict | None = None) -> CheckResult:
        from src.models.monster import LEVEL_SCALING

        issues: list[str] = []
        name = data.get("name") or data.get("species") or "?"

        if not data.get("name") and not data.get("species"):
            issues.append("Monster missing name/species")

        hp = data.get("hp", 0)
        level = data.get("level", 1)
        level_key = min(level, max(LEVEL_SCALING.keys()))
        scaling = LEVEL_SCALING.get(level_key, LEVEL_SCALING[1])

        if hp < scaling["hp"][0] or hp > scaling["hp"][1] * 3:
            # Allow up to 3x for bosses
            issues.append(
                f"Monster {name}: HP {hp} outside expected range "
                f"{scaling['hp'][0]}-{scaling['hp'][1] * 3} for level {level}"
            )

        ac = data.get("ac", 10)
        if ac < scaling["ac"][0] or ac > scaling["ac"][1] + 5:
            issues.append(
                f"Monster {name}: AC {ac} outside expected range "
                f"{scaling['ac'][0]}-{scaling['ac'][1] + 5} for level {level}"
            )

        if hp <= 0:
            issues.append(f"Monster {name}: HP must be > 0")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)


class ItemChecker(BaseChecker):
    """Checks item data for required fields and category consistency."""

    VALID_CATEGORIES = {"food", "drink", "tool", "weapon", "spell_scroll"}

    def check(self, data: dict, context: dict | None = None) -> CheckResult:
        issues: list[str] = []
        name = data.get("name", "?")

        if not data.get("name"):
            issues.append("Item missing name")

        category = data.get("category", "")
        if category not in self.VALID_CATEGORIES:
            issues.append(f"Item {name}: invalid category '{category}'")

        stats = data.get("item_stats", {})
        if not stats:
            issues.append(f"Item {name}: missing item_stats")

        if category == "weapon":
            if not stats.get("attack_dice"):
                issues.append(f"Item {name}: weapon missing attack_dice")
        elif category == "tool":
            if not stats.get("attribute"):
                issues.append(f"Item {name}: tool missing attribute")
            uses = stats.get("uses", 0)
            if uses <= 0:
                issues.append(f"Item {name}: tool must have uses > 0")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)
