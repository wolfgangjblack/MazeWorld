"""Base Checker/Editor — reviews generated content for theme, coherence, quality.

Each concrete checker implements ``check()`` which receives raw generated data
and returns a ``CheckResult`` with pass/fail plus a list of issues.

Pattern mirrors ``class_gen.py``'s ``_check_classes`` stage.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.models.player import (
    ARCHETYPE_STAT_ROLES, STAT_BUDGET, STAT_NAMES,
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
        for ti in quest.get("target_items", []):
            if item_ids is not None and ti.get("item_id") not in item_ids:
                issues.append(f"{prefix}fetch item {ti.get('item_id')} not on map")
    elif qtype == "escort":
        if npc_ids is not None and quest.get("escort_npc_id") not in npc_ids:
            issues.append(f"{prefix}escort NPC {quest.get('escort_npc_id')} not found")
    elif qtype == "delivery":
        if item_ids is not None and quest.get("delivery_item_id") not in item_ids:
            issues.append(f"{prefix}delivery item {quest.get('delivery_item_id')} not on map")
        if npc_ids is not None and quest.get("target_npc_id") not in npc_ids:
            issues.append(f"{prefix}target NPC {quest.get('target_npc_id')} not found")
    elif qtype == "combat":
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
                lo, hi = (9, 13) if archetype == "jester" else (11, 14)
                if not (lo <= val <= hi):
                    issues.append(f"{label} {stat}={val} outside secondary {lo}-{hi}")
            for stat in roles.get("dump", []):
                val = stats.get(stat, 10)
                if not (6 <= val <= 10):
                    issues.append(f"{label} {stat}={val} outside dump 6-10")

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

        issues.extend(check_quest_references(
            data, npc_ids=npc_ids, item_ids=item_ids, event_ids=event_ids,
        ))

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
            if not data.get("monsters"):
                issues.append("Combat event has no monsters")
        elif etype == "puzzle":
            choices = data.get("choices", [])
            has_walkaway = any(c.get("auto_success") for c in choices)
            if not has_walkaway:
                issues.append("Puzzle has no walk-away option")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)


class ItemChecker(BaseChecker):
    """Checks generated item data for required fields and valid categories."""

    VALID_CATEGORIES = {"food", "drink", "tool", "weapon", "spell_scroll"}

    def check(self, data: dict, context: dict | None = None) -> CheckResult:
        issues: list[str] = []

        if not data.get("name"):
            issues.append("Item missing name")

        category = data.get("category", "")
        if category not in self.VALID_CATEGORIES:
            issues.append(f"Invalid item category '{category}'")

        stats = data.get("item_stats", {})
        if not stats:
            issues.append("Item missing item_stats")

        if category == "weapon":
            if not stats.get("attack_dice"):
                issues.append("Weapon missing attack_dice")
            if not stats.get("stat_modifier"):
                issues.append("Weapon missing stat_modifier")
        elif category == "tool":
            if not stats.get("attribute"):
                issues.append("Tool missing attribute")
        elif category in ("food", "drink"):
            if stats.get("nutrition_value", 0) == 0 and stats.get("hydration_value", 0) == 0:
                if category == "food":
                    issues.append("Food item has no nutrition_value")
                else:
                    issues.append("Drink item has no hydration_value")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)


class NPCChecker(BaseChecker):
    """Checks NPC data for required personality and identity fields."""

    REQUIRED_FIELDS = {"name", "type", "environment"}

    def check(self, data: dict, context: dict | None = None) -> CheckResult:
        issues: list[str] = []

        missing = self.REQUIRED_FIELDS - set(data.keys())
        if missing:
            issues.append(f"NPC missing fields: {', '.join(sorted(missing))}")

        if not data.get("name"):
            issues.append("NPC has empty name")

        npc_type = data.get("type", "")
        valid_types = {"StaticNPC", "RandomNPC", "AggressiveNPC", "MerchantNPC"}
        if npc_type and npc_type not in valid_types:
            issues.append(f"Invalid NPC type '{npc_type}'")

        if not data.get("personality"):
            issues.append("NPC missing personality trait")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)


class MonsterChecker(BaseChecker):
    """Checks monster data for combat-required fields."""

    def check(self, data: dict, context: dict | None = None) -> CheckResult:
        issues: list[str] = []

        if not data.get("name"):
            issues.append("Monster missing name")

        hp = data.get("hp", 0)
        if hp <= 0:
            issues.append(f"Monster has invalid hp: {hp}")

        if not data.get("attack_dice"):
            issues.append("Monster missing attack_dice")

        ac = data.get("ac", 0)
        if ac <= 0:
            issues.append(f"Monster has invalid ac: {ac}")

        return CheckResult(passed=len(issues) == 0, issues=issues, data=data)
