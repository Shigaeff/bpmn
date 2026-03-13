"""Message flow validation rules (MF-001 through MF-002)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions
from .base import SemanticRule, registry


def _find_participant_for_element(model: BPMNDefinitions, element_id: str) -> str | None:
    """Find which participant (pool) an element belongs to."""
    for collab in model.collaborations.values():
        for part_id, part_data in collab.participants.items():
            proc_ref = part_data.get("processRef")
            if proc_ref and proc_ref in model.processes:
                proc = model.processes[proc_ref]
                if element_id in proc.elements or element_id == proc_ref:
                    return part_id
    return None


@registry.register
class MessageFlowNotWithinSamePool(SemanticRule):
    rule_id = "MF-001"
    description = "Message flows cannot connect elements within the same pool"
    severity = Severity.ERROR
    spec_reference = "Section 9.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for collab in model.collaborations.values():
            for mf in collab.message_flows.values():
                src_part = _find_participant_for_element(model, mf.source_ref)
                tgt_part = _find_participant_for_element(model, mf.target_ref)

                if src_part and tgt_part and src_part == tgt_part:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Message flow '{mf.name or mf.id}' connects elements "
                                f"within the same pool (participant '{src_part}')"
                            ),
                            element_id=mf.id,
                            element_type="messageFlow",
                            line=mf.line,
                        )
                    )
        return issues


@registry.register
class MessageFlowBetweenPools(SemanticRule):
    rule_id = "MF-002"
    description = "Message flows must connect elements in different pools"
    severity = Severity.ERROR
    spec_reference = "Section 9.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for collab in model.collaborations.values():
            if len(collab.participants) < 2:
                continue

            for mf in collab.message_flows.values():
                src_part = _find_participant_for_element(model, mf.source_ref)
                tgt_part = _find_participant_for_element(model, mf.target_ref)

                # If source or target is a participant itself (pool-level message)
                if mf.source_ref in collab.participants:
                    src_part = mf.source_ref
                if mf.target_ref in collab.participants:
                    tgt_part = mf.target_ref

                if src_part is None or tgt_part is None:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Message flow '{mf.name or mf.id}' has source or target "
                                "not associated with any pool"
                            ),
                            element_id=mf.id,
                            element_type="messageFlow",
                            line=mf.line,
                        )
                    )
        return issues
