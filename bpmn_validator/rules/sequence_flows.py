"""Sequence flow validation rules (SF-001 through SF-002)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions
from .base import SemanticRule, registry


@registry.register
class SequenceFlowNoCrossBoundary(SemanticRule):
    rule_id = "SF-001"
    description = "Sequence flows cannot cross subprocess boundaries"
    severity = Severity.ERROR
    spec_reference = "Section 10.3.1"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            # Build a map of element_id -> parent subprocess id
            parent_map: dict[str, str | None] = {}
            for eid, elem in proc.elements.items():
                parent_map[eid] = elem.parent_id

            for sf in proc.sequence_flows.values():
                src_parent = parent_map.get(sf.source_ref)
                tgt_parent = parent_map.get(sf.target_ref)
                if src_parent != tgt_parent:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Sequence flow '{sf.id}' crosses subprocess boundary: "
                                f"source in '{src_parent or 'process'}', "
                                f"target in '{tgt_parent or 'process'}'"
                            ),
                            element_id=sf.id,
                            element_type="sequenceFlow",
                            line=sf.line,
                        )
                    )
        return issues


@registry.register
class ConditionalFlowMustHaveCondition(SemanticRule):
    rule_id = "SF-002"
    description = "Conditional sequence flows must have a condition expression"
    severity = Severity.WARNING
    spec_reference = "Section 10.3.1"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for sf in proc.sequence_flows.values():
                src_elem = proc.elements.get(sf.source_ref)
                if not src_elem:
                    continue

                # Flows from gateways with multiple outgoing need conditions
                if src_elem.tag in ("exclusiveGateway", "inclusiveGateway"):
                    outgoing = [
                        f for f in proc.sequence_flows.values() if f.source_ref == sf.source_ref
                    ]
                    if len(outgoing) <= 1:
                        continue

                    default_ref = src_elem.attrib.get("default")
                    if sf.id == default_ref:
                        continue  # Default flow doesn't need condition

                    if not sf.condition_expression:
                        issues.append(
                            self._make_issue(
                                message=(
                                    f"Sequence flow '{sf.name or sf.id}' from "
                                    f"'{src_elem.tag}' has no condition expression"
                                ),
                                element_id=sf.id,
                                element_type="sequenceFlow",
                                line=sf.line,
                            )
                        )
        return issues
