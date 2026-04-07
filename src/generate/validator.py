"""Validation — rule-based + optional LLM validation for generated content.

Contains:
- ``ValidationReport``: accumulates pipeline-level findings (warnings, failures)
- ``BaseValidator`` / concrete validators: Phase 2 per-entity validation
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.models.player import (
    ARCHETYPE_STAT_ROLES, STAT_BUDGET, STAT_NAMES, Stats,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline-level validation report (PR #24)
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    """Accumulates validation findings during world generation.

    Matches the PDR manifest ``validation`` block schema::

        {
            "status": "passed",
            "rooms_validated": 1,
            "critical_failures": 0,
            "major_retries": 0,
            "minor_warnings": 0,
            "details": []
        }
    """

    rooms_validated: int = 0
    critical_failures: int = 0
    major_retries: int = 0
    minor_warnings: int = 0
    details: list[dict] = field(default_factory=list)

    # -- Mutation helpers -----------------------------------------------------

    def add_warning(self, message: str, *, entity_id: str = "", phase: str = "") -> None:
        self.minor_warnings += 1
        self.details.append({
            "severity": "minor",
            "message": message,
            "entity_id": entity_id,
            "phase": phase,
        })

    def add_major(self, message: str, *, entity_id: str = "", phase: str = "") -> None:
        self.major_retries += 1
        self.details.append({
            "severity": "major",
            "message": message,
            "entity_id": entity_id,
            "phase": phase,
        })

    def add_critical(self, message: str, *, entity_id: str = "", phase: str = "") -> None:
        self.critical_failures += 1
        self.details.append({
            "severity": "critical",
            "message": message,
            "entity_id": entity_id,
            "phase": phase,
        })

    # -- Derived status -------------------------------------------------------

    @property
    def status(self) -> str:
        if self.critical_failures > 0:
            return "failed"
        if self.minor_warnings > 0 or self.major_retries > 0:
            return "passed_with_warnings"
        return "passed"

    # -- Serialisation --------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "rooms_validated": self.rooms_validated,
            "critical_failures": self.critical_failures,
            "major_retries": self.major_retries,
            "minor_warnings": self.minor_warnings,
            "details": list(self.details),
        }


# ---------------------------------------------------------------------------
# Phase 2: Per-entity validators
# ---------------------------------------------------------------------------

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
            stats = Stats(**{s: stats_raw.get(s, 10) for s in STAT_NAMES})

        # Stat budget
        if stats.total() != STAT_BUDGET:
            reasons.append(f"Stat total {stats.total()} != {STAT_BUDGET}")

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
        from src.generate.checker import check_quest_references

        ctx = context or {}
        npc_ids = ctx.get("npc_ids", set()) or None
        item_ids = ctx.get("item_ids", set()) or None
        event_ids = ctx.get("event_ids", set()) or None
        quest_ids = ctx.get("quest_ids", set()) or None

        reasons = check_quest_references(
            data,
            npc_ids=npc_ids,
            item_ids=item_ids,
            event_ids=event_ids,
            quest_ids=quest_ids,
        )

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

        # Validate time_gate
        time_gate = data.get("time_gate")
        if time_gate is not None and time_gate not in ("day", "night"):
            reasons.append(f"Invalid time_gate value: {time_gate}")

        return ValidationResult(passed=len(reasons) == 0, reasons=reasons, data=data)


class NPCValidator(BaseValidator):
    """Validates NPC data for completeness and environment coherence."""

    def validate(self, data: dict, context: dict | None = None) -> ValidationResult:
        reasons: list[str] = []
        npc_id = data.get("id", "?")

        if not data.get("name"):
            reasons.append(f"NPC {npc_id}: missing name")

        if data.get("selected"):
            if not data.get("identity"):
                reasons.append(f"NPC {npc_id}: active NPC missing identity")
            if not data.get("opening_greeting"):
                reasons.append(f"NPC {npc_id}: active NPC missing opening_greeting")

        npc_type = data.get("type", "")
        if npc_type == "MerchantNPC":
            shop = data.get("shop_inventory", [])
            if not shop:
                reasons.append(f"NPC {npc_id}: MerchantNPC has empty shop_inventory")
            for i, entry in enumerate(shop):
                if not isinstance(entry, dict):
                    reasons.append(f"NPC {npc_id}: shop_inventory[{i}] is not a dict")
                    continue
                if "item_id" not in entry:
                    reasons.append(f"NPC {npc_id}: shop_inventory[{i}] missing item_id")
                if entry.get("price", 0) <= 0:
                    reasons.append(f"NPC {npc_id}: shop_inventory[{i}] invalid price")

        return ValidationResult(passed=len(reasons) == 0, reasons=reasons, data=data)


class MonsterValidator(BaseValidator):
    """Validates monster data for stat correctness and level scaling."""

    def validate(self, data: dict, context: dict | None = None) -> ValidationResult:
        reasons: list[str] = []
        name = data.get("name") or data.get("species") or "?"

        if not data.get("name") and not data.get("species"):
            reasons.append("Monster missing name/species")

        hp = data.get("hp", 0)
        if hp <= 0:
            reasons.append(f"Monster {name}: HP must be > 0")

        ac = data.get("ac", 0)
        if ac < 5:
            reasons.append(f"Monster {name}: AC {ac} is unreasonably low")

        level = data.get("level", 1)
        if level < 1:
            reasons.append(f"Monster {name}: level must be >= 1")

        # Validate abilities
        for i, ability in enumerate(data.get("abilities", [])):
            if isinstance(ability, dict):
                if not ability.get("name"):
                    reasons.append(f"Monster {name}: ability[{i}] missing name")
                effect = ability.get("effect_type", "")
                if effect not in ("damage", "poison", "stun"):
                    reasons.append(
                        f"Monster {name}: ability[{i}] unknown effect_type '{effect}'"
                    )

        return ValidationResult(passed=len(reasons) == 0, reasons=reasons, data=data)


class ItemValidator(BaseValidator):
    """Validates item data for category correctness and stat integrity."""

    VALID_CATEGORIES = {"food", "drink", "tool", "weapon", "spell_scroll"}

    def validate(self, data: dict, context: dict | None = None) -> ValidationResult:
        reasons: list[str] = []
        name = data.get("name", "?")

        if not data.get("name"):
            reasons.append("Item missing name")

        category = data.get("category", "")
        if category not in self.VALID_CATEGORIES:
            reasons.append(f"Item {name}: invalid category '{category}'")

        stats = data.get("item_stats", {})
        if not stats:
            reasons.append(f"Item {name}: missing item_stats")
            return ValidationResult(passed=False, reasons=reasons, data=data)

        if category == "weapon":
            dice = stats.get("attack_dice", "")
            if not dice:
                reasons.append(f"Item {name}: weapon missing attack_dice")
            elif "d" not in str(dice):
                reasons.append(f"Item {name}: weapon attack_dice '{dice}' invalid format")
            modifier = stats.get("stat_modifier", "")
            valid_mods = {"STR", "DEX", "INT", "WIS", ""}
            if modifier and modifier not in valid_mods:
                reasons.append(f"Item {name}: weapon stat_modifier '{modifier}' invalid")

        elif category == "tool":
            if not stats.get("attribute"):
                reasons.append(f"Item {name}: tool missing attribute")
            uses = stats.get("uses", 0)
            if uses <= 0:
                reasons.append(f"Item {name}: tool must have uses > 0")

        elif category in ("food", "drink"):
            nutrition = stats.get("nutrition_value", 0)
            hydration = stats.get("hydration_value", 0)
            health = stats.get("health_value", 0)
            if nutrition == 0 and hydration == 0 and health == 0:
                reasons.append(
                    f"Item {name}: {category} restores nothing "
                    "(nutrition, hydration, health all 0)"
                )

        return ValidationResult(passed=len(reasons) == 0, reasons=reasons, data=data)
