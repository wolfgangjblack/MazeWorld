"""Validation report used by the generation pipeline.

The full agentic checker/validator pattern (generator -> checker -> validator ->
world editor) described in the PDR is deferred to a later phase.  This module
provides the ``ValidationReport`` dataclass so the pipeline can accumulate
warnings and failures from existing rule-based checks and surface them in the
manifest instead of hardcoding ``{"status": "passed"}``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
