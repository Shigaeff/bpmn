"""Collaboration validation rules (COLLAB-001 through COLLAB-002)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions
from .base import SemanticRule, registry


@registry.register
class OneProcessPerPool(SemanticRule):
    rule_id = "COLLAB-001"
    description = "Each pool (participant) must reference at most one process"
    severity = Severity.ERROR
    spec_reference = "Section 9.2"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for collab in model.collaborations.values():
            process_refs: dict[str, list[str]] = {}
            for part_id, part_data in collab.participants.items():
                proc_ref = part_data.get("processRef")
                if proc_ref:
                    process_refs.setdefault(proc_ref, []).append(part_id)

            for proc_ref, participants in process_refs.items():
                if len(participants) > 1:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Process '{proc_ref}' is referenced by multiple "
                                f"participants: {', '.join(participants)}"
                            ),
                            element_id=proc_ref,
                            element_type="process",
                        )
                    )
        return issues


@registry.register
class MessageFlowValidEndpoints(SemanticRule):
    rule_id = "COLLAB-002"
    description = "Message flows between pools must have valid source and target"
    severity = Severity.ERROR
    spec_reference = "Section 9.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        # Collect all known element IDs
        known_ids: set[str] = set()
        for proc in model.processes.values():
            known_ids.add(proc.id)
            known_ids.update(proc.elements.keys())
        for collab in model.collaborations.values():
            known_ids.update(collab.participants.keys())

        for collab in model.collaborations.values():
            for mf in collab.message_flows.values():
                if mf.source_ref not in known_ids:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Message flow '{mf.name or mf.id}' has unknown "
                                f"source '{mf.source_ref}'"
                            ),
                            element_id=mf.id,
                            element_type="messageFlow",
                            line=mf.line,
                        )
                    )
                if mf.target_ref not in known_ids:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Message flow '{mf.name or mf.id}' has unknown "
                                f"target '{mf.target_ref}'"
                            ),
                            element_id=mf.id,
                            element_type="messageFlow",
                            line=mf.line,
                        )
                    )
        return issues
