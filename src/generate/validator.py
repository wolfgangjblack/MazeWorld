"""Base Validator — rule-based + optional LLM validation for generated content.

Each concrete validator implements ``validate()`` which receives checked data
and returns a ``ValidationResult`` with pass/fail and reasons.

Hard rules (stat ranges, required fields, valid references) are checked
deterministically. Soft rules (theme coherence) can optionally call the LLM.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.models.player import (
    ARCHETYPE_STAT_ROLES, STAT_BUDGET, STAT_NAMES,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Outcome of a validation pass."""
    passed: bool
    reasons: list[str] = field(default_factory=list)
    data: object = None


class BaseValidator(ABC):
    """Abstract validator for generated content."""

    @abstractmethod
    def validate(self, data, context: dict | None = None) -> ValidationResult:
        """Validate *data* and return a ``ValidationResult``."""
        ...


class ClassValidator(BaseValidator):
    """Validates PlayerClass objects against hard stat rules.

    Hard rules:
    - Stat total == 72
    - Primary stats in 14-18
    - Secondary stats in 11-14 (9-13 for jester)
    - Dump stats in 6-10
    - Each archetype has minimum ability/spell counts
    """

    MIN_ABILITIES = {"warrior": 4, "mage": 0, "healer": 0, "jester": 0}
    MIN_SPELLS = {"warrior": 0, "mage": 4, "healer": 4, "jester": 0}

    def validate(self, data, context: dict | None = None) -> ValidationResult:
        reasons: list[str] = []

        # Accept either a PlayerClass object or a dict
        if hasattr(data, "stats"):
            stats = data.stats
            archetype = getattr(data, "archetype", "warrior")
            abilities = getattr(data, "abilities", [])
            spells = getattr(data, "spells", [])
        else:
            stats_raw = data.get("stats", {})
            archetype = data.get("archetype", "warrior")
            abilities = data.get("abilities", [])
            spells = data.get("spells", [])
            # Build a simple object-like accessor
            class _S:
                pass
            stats = _S()
            for s in STAT_NAMES:
                setattr(stats, s, stats_raw.get(s, 10))
            stats.total = lambda: sum(stats_raw.get(s, 10) for s in STAT_NAMES)

        # Stat budget
        total = stats.total() if callable(getattr(stats, "total", None)) else sum(
            getattr(stats, s, 10) for s in STAT_NAMES
        )
        if total != STAT_BUDGET:
            reasons.append(f"Stat total {total} != {STAT_BUDGET}")

        # Role ranges
        roles = ARCHETYPE_STAT_ROLES.get(archetype, {})
        for stat in roles.get("primary", []):
            val = getattr(stats, stat, 10)
            if not (14 <= val <= 18):
                reasons.append(f"{stat}={val} outside primary 14-18")

        for stat in roles.get("secondary", []):
            val = getattr(stats, stat, 10)
            lo, hi = (9, 13) if archetype == "jester" else (11, 14)
            if not (lo <= val <= hi):
                reasons.append(f"{stat}={val} outside secondary {lo}-{hi}")

        for stat in roles.get("dump", []):
            val = getattr(stats, stat, 10)
            if not (6 <= val <= 10):
                reasons.append(f"{stat}={val} outside dump 6-10")

        # Minimum content counts
        min_ab = self.MIN_ABILITIES.get(archetype, 0)
        if len(abilities) < min_ab:
            reasons.append(f"{archetype} has {len(abilities)} abilities, need {min_ab}")
        min_sp = self.MIN_SPELLS.get(archetype, 0)
        if len(spells) < min_sp:
            reasons.append(f"{archetype} has {len(spells)} spells, need {min_sp}")

        return ValidationResult(passed=len(reasons) == 0, reasons=reasons, data=data)


class QuestValidator(BaseValidator):
    """Validates a quest for completability within the current world state."""

    def validate(self, data: dict, context: dict | None = None) -> ValidationResult:
        reasons: list[str] = []
        ctx = context or {}
        npc_ids: set = ctx.get("npc_ids", set())
        item_ids: set = ctx.get("item_ids", set())
        event_ids: set = ctx.get("event_ids", set())
        quest_ids: set = ctx.get("quest_ids", set())

        qtype = data.get("type", "")

        # Giver NPC must exist
        if npc_ids and data.get("giver_npc_id") not in npc_ids:
            reasons.append(f"Giver NPC {data.get('giver_npc_id')} missing")

        # Type-specific validations
        if qtype == "fetch":
            for ti in data.get("target_items", []):
                if item_ids and ti.get("item_id") not in item_ids:
                    reasons.append(f"Fetch item {ti.get('item_id')} not on map")
        elif qtype == "escort":
            if npc_ids and data.get("escort_npc_id") not in npc_ids:
                reasons.append(f"Escort NPC {data.get('escort_npc_id')} missing")
        elif qtype == "delivery":
            if item_ids and data.get("delivery_item_id") not in item_ids:
                reasons.append(f"Delivery item {data.get('delivery_item_id')} missing")
            if npc_ids and data.get("target_npc_id") not in npc_ids:
                reasons.append(f"Target NPC {data.get('target_npc_id')} missing")
        elif qtype == "combat":
            if event_ids and data.get("target_event_id") not in event_ids:
                reasons.append(f"Target event {data.get('target_event_id')} missing")

        # Prerequisite chain depth <= 2
        prereq = data.get("prerequisite_quest_id")
        if prereq and quest_ids and prereq not in quest_ids:
            reasons.append(f"Prerequisite quest {prereq} not found")

        return ValidationResult(passed=len(reasons) == 0, reasons=reasons, data=data)


class EventValidator(BaseValidator):
    """Validates events for solvability and required content."""

    def validate(self, data: dict, context: dict | None = None) -> ValidationResult:
        reasons: list[str] = []
        ctx = context or {}
        tool_attrs: set = ctx.get("tool_attributes", set())

        etype = data.get("type", "")

        if not data.get("name"):
            reasons.append("Missing event name")
        if not data.get("description"):
            reasons.append("Missing event description")

        if etype == "combat":
            if not data.get("monsters"):
                reasons.append("Combat event has no monsters")
        elif etype == "puzzle":
            choices = data.get("choices", [])
            solvable = any(
                c.get("auto_success") or c.get("tool_attribute") in tool_attrs
                for c in choices
            )
            if not solvable and tool_attrs:
                reasons.append("Puzzle has no solvable path with available tools")

        return ValidationResult(passed=len(reasons) == 0, reasons=reasons, data=data)
