"""Best practice validation rules (BP-001 through BP-004)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions, FLOW_NODE_TAGS, _bpmn_tag
from .base import SemanticRule, registry


@registry.register
class UnnamedElements(SemanticRule):
    rule_id = "BP-001"
    description = "Key flow elements should have a name attribute"
    severity = Severity.WARNING
    spec_reference = "Best practice"

    # Tags where a name is strongly recommended
    _NAMEABLE_TAGS = {
        "task",
        "sendTask",
        "receiveTask",
        "serviceTask",
        "userTask",
        "manualTask",
        "businessRuleTask",
        "scriptTask",
        "subProcess",
        "callActivity",
        "exclusiveGateway",
        "parallelGateway",
        "inclusiveGateway",
        "eventBasedGateway",
    }

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for eid, elem in proc.elements.items():
                if elem.tag in self._NAMEABLE_TAGS and not elem.name:
                    issues.append(
                        self._make_issue(
                            message=f"Element '{eid}' ({elem.tag}) has no name",
                            element_id=eid,
                            element_type=elem.tag,
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class EmptyPools(SemanticRule):
    rule_id = "BP-002"
    description = "Pools (participants) should reference a process"
    severity = Severity.INFO
    spec_reference = "Best practice"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for collab in model.collaborations.values():
            for part_id, part_data in collab.participants.items():
                proc_ref = part_data.get("processRef")
                if not proc_ref:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Participant '{part_data.get('name') or part_id}' "
                                "has no processRef (empty pool)"
                            ),
                            element_id=part_id,
                            element_type="participant",
                        )
                    )
                elif proc_ref not in model.processes:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Participant '{part_data.get('name') or part_id}' "
                                f"references non-existent process '{proc_ref}'"
                            ),
                            element_id=part_id,
                            element_type="participant",
                        )
                    )
        return issues


@registry.register
class OverlyComplexProcess(SemanticRule):
    rule_id = "BP-003"
    description = "Processes with too many elements may be overly complex"
    severity = Severity.INFO
    spec_reference = "Best practice"

    MAX_ELEMENTS = 50

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc_id, proc in model.processes.items():
            flow_count = len([e for e in proc.elements.values() if e.tag in FLOW_NODE_TAGS])
            if flow_count > self.MAX_ELEMENTS:
                issues.append(
                    self._make_issue(
                        message=(
                            f"Process '{proc.name or proc_id}' has {flow_count} "
                            f"flow elements (threshold: {self.MAX_ELEMENTS}). "
                            "Consider decomposing into sub-processes."
                        ),
                        element_id=proc_id,
                        element_type="process",
                        line=proc.line,
                    )
                )
        return issues


@registry.register
class MissingDocumentation(SemanticRule):
    rule_id = "BP-004"
    description = "Processes should have documentation"
    severity = Severity.INFO
    spec_reference = "Best practice"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if model.root is None:
            return issues

        for proc_id, proc in model.processes.items():
            # Check for <documentation> child element
            has_doc = False
            for proc_elem in model.root.findall(_bpmn_tag("process")):
                if proc_elem.get("id") == proc_id:
                    doc_elem = proc_elem.find(_bpmn_tag("documentation"))
                    if doc_elem is not None and doc_elem.text and doc_elem.text.strip():
                        has_doc = True
                    break

            if not has_doc:
                issues.append(
                    self._make_issue(
                        message=f"Process '{proc.name or proc_id}' has no documentation",
                        element_id=proc_id,
                        element_type="process",
                        line=proc.line,
                    )
                )
        return issues
