"""Process structure validation rules (PROC-001 through PROC-005)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions
from .base import SemanticRule, registry


@registry.register
class ProcessMustHaveStartEvent(SemanticRule):
    rule_id = "PROC-001"
    description = "A Process must contain at least one Start Event"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.1"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc_id, proc in model.processes.items():
            if not proc.start_events:
                issues.append(
                    self._make_issue(
                        message=f"Process '{proc.name or proc_id}' has no Start Event",
                        element_id=proc_id,
                        element_type="process",
                        line=proc.line,
                    )
                )
        return issues


@registry.register
class ProcessMustHaveEndEvent(SemanticRule):
    rule_id = "PROC-002"
    description = "A Process must contain at least one End Event"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.1"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc_id, proc in model.processes.items():
            if not proc.end_events:
                issues.append(
                    self._make_issue(
                        message=f"Process '{proc.name or proc_id}' has no End Event",
                        element_id=proc_id,
                        element_type="process",
                        line=proc.line,
                    )
                )
        return issues


@registry.register
class StartEventNoIncomingFlows(SemanticRule):
    rule_id = "PROC-003"
    description = "Start Events in top-level processes cannot have incoming sequence flows"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.2"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            incoming_targets = {sf.target_ref for sf in proc.sequence_flows.values()}
            for se_id in proc.start_events:
                elem = proc.elements.get(se_id)
                # Only top-level start events (not inside subprocesses)
                if elem and elem.parent_id is None and se_id in incoming_targets:
                    issues.append(
                        self._make_issue(
                            message=f"Start Event '{se_id}' has incoming sequence flows",
                            element_id=se_id,
                            element_type="startEvent",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class EndEventNoOutgoingFlows(SemanticRule):
    rule_id = "PROC-004"
    description = "End Events cannot have outgoing sequence flows"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.2"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            outgoing_sources = {sf.source_ref for sf in proc.sequence_flows.values()}
            for ee_id in proc.end_events:
                if ee_id in outgoing_sources:
                    elem = proc.elements.get(ee_id)
                    issues.append(
                        self._make_issue(
                            message=f"End Event '{ee_id}' has outgoing sequence flows",
                            element_id=ee_id,
                            element_type="endEvent",
                            line=elem.line if elem else None,
                        )
                    )
        return issues


@registry.register
class AllElementsReachable(SemanticRule):
    rule_id = "PROC-005"
    description = "Every flow element must be reachable from a Start Event"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.1"

    # Tags that are not flow nodes and should be excluded from reachability checks
    _EXCLUDED_TAGS = {
        "dataObject",
        "dataObjectReference",
        "dataStoreReference",
        "textAnnotation",
        "association",
        "group",
        "laneSet",
        "lane",
    }

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            if not proc.start_events:
                continue  # PROC-001 will catch this

            # Build adjacency list
            adjacency: dict[str, set[str]] = {}
            for sf in proc.sequence_flows.values():
                adjacency.setdefault(sf.source_ref, set()).add(sf.target_ref)

            # BFS from all start events
            reachable: set[str] = set()
            queue = list(proc.start_events)
            while queue:
                node = queue.pop(0)
                if node in reachable:
                    continue
                reachable.add(node)
                for neighbor in adjacency.get(node, set()):
                    if neighbor not in reachable:
                        queue.append(neighbor)

            # Check all elements
            for eid, elem in proc.elements.items():
                if elem.tag in self._EXCLUDED_TAGS:
                    continue
                if elem.tag == "boundaryEvent":
                    continue  # Boundary events are attached, not in flow
                if eid not in reachable:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Element '{elem.name or eid}' ({elem.tag}) "
                                "is not reachable from any Start Event"
                            ),
                            element_id=eid,
                            element_type=elem.tag,
                            line=elem.line,
                        )
                    )
        return issues
