"""Base Checker/Editor — reviews generated content for theme, coherence, quality.

Each concrete checker implements ``check()`` which receives raw generated data
and returns a ``CheckResult`` with pass/fail plus a list of issues.

Pattern mirrors ``class_gen.py``'s ``_check_classes`` stage.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.models.player import (
    ARCHETYPE_STAT_ROLES, STAT_BUDGET, STAT_NAMES, PlayerClass,
)

logger = logging.getLogger(__name__)


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
        npc_ids = ctx.get("npc_ids", set())
        item_ids = ctx.get("item_ids", set())
        event_ids = ctx.get("event_ids", set())

        missing = self.REQUIRED_FIELDS - set(data.keys())
        if missing:
            issues.append(f"Missing fields: {', '.join(sorted(missing))}")

        if npc_ids and data.get("giver_npc_id") not in npc_ids:
            issues.append(f"giver_npc_id {data.get('giver_npc_id')} not in NPC pool")

        qtype = data.get("type", "")
        if qtype == "fetch":
            for ti in data.get("target_items", []):
                if item_ids and ti.get("item_id") not in item_ids:
                    issues.append(f"fetch target item {ti.get('item_id')} not on map")
        elif qtype == "combat":
            if event_ids and data.get("target_event_id") not in event_ids:
                issues.append(f"combat target event {data.get('target_event_id')} not found")
        elif qtype == "escort":
            if npc_ids and data.get("escort_npc_id") not in npc_ids:
                issues.append(f"escort NPC {data.get('escort_npc_id')} not found")
        elif qtype == "delivery":
            if item_ids and data.get("delivery_item_id") not in item_ids:
                issues.append(f"delivery item {data.get('delivery_item_id')} not on map")
            if npc_ids and data.get("target_npc_id") not in npc_ids:
                issues.append(f"delivery target NPC {data.get('target_npc_id')} not found")

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
