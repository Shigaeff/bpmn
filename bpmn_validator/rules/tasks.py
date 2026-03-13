"""Task and activity validation rules (TASK-001 through TASK-006)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions, _bpmn_tag
from .base import SemanticRule, registry


@registry.register
class SendTaskMessage(SemanticRule):
    rule_id = "TASK-001"
    description = "Send Task must have a message reference"
    severity = Severity.ERROR
    spec_reference = "Section 10.2.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for eid in proc.tasks:
                elem = proc.elements.get(eid)
                if not elem or elem.tag != "sendTask":
                    continue
                if not elem.attrib.get("messageRef"):
                    issues.append(
                        self._make_issue(
                            message=f"Send Task '{elem.name or eid}' has no messageRef",
                            element_id=eid,
                            element_type="sendTask",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class ReceiveTaskMessage(SemanticRule):
    rule_id = "TASK-002"
    description = "Receive Task must have a message reference"
    severity = Severity.ERROR
    spec_reference = "Section 10.2.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for eid in proc.tasks:
                elem = proc.elements.get(eid)
                if not elem or elem.tag != "receiveTask":
                    continue
                if not elem.attrib.get("messageRef"):
                    issues.append(
                        self._make_issue(
                            message=f"Receive Task '{elem.name or eid}' has no messageRef",
                            element_id=eid,
                            element_type="receiveTask",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class ScriptTaskDefinition(SemanticRule):
    rule_id = "TASK-003"
    description = "Script Task must have a script and scriptFormat"
    severity = Severity.WARNING
    spec_reference = "Section 10.2.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if model.root is None:
            return issues

        for proc in model.processes.values():
            for eid in proc.tasks:
                elem = proc.elements.get(eid)
                if not elem or elem.tag != "scriptTask":
                    continue

                missing = []
                if not elem.attrib.get("scriptFormat"):
                    missing.append("scriptFormat")

                # Check for <script> child element
                for script_task_elem in model.root.iter(_bpmn_tag("scriptTask")):
                    if script_task_elem.get("id") == eid:
                        script_child = script_task_elem.find(_bpmn_tag("script"))
                        if script_child is None or not (
                            script_child.text and script_child.text.strip()
                        ):
                            missing.append("script")
                        break

                if missing:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Script Task '{elem.name or eid}' is missing: {', '.join(missing)}"
                            ),
                            element_id=eid,
                            element_type="scriptTask",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class ServiceTaskImplementation(SemanticRule):
    rule_id = "TASK-004"
    description = "Service Task should have an implementation"
    severity = Severity.WARNING
    spec_reference = "Section 10.2.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for eid in proc.tasks:
                elem = proc.elements.get(eid)
                if not elem or elem.tag != "serviceTask":
                    continue
                if not elem.attrib.get("implementation"):
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Service Task '{elem.name or eid}' has no implementation attribute"
                            ),
                            element_id=eid,
                            element_type="serviceTask",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class SubProcessEvents(SemanticRule):
    rule_id = "TASK-005"
    description = "Sub-processes must have their own start and end events"
    severity = Severity.WARNING
    spec_reference = "Section 10.2.5"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for sp_id in proc.sub_processes:
                sp_elem = proc.elements.get(sp_id)
                if not sp_elem:
                    continue

                children = sp_elem.children_ids
                child_tags = {proc.elements[cid].tag for cid in children if cid in proc.elements}

                missing = []
                if "startEvent" not in child_tags:
                    missing.append("Start Event")
                if "endEvent" not in child_tags:
                    missing.append("End Event")

                if missing:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Sub-process '{sp_elem.name or sp_id}' is missing: "
                                f"{', '.join(missing)}"
                            ),
                            element_id=sp_id,
                            element_type=sp_elem.tag,
                            line=sp_elem.line,
                        )
                    )
        return issues


@registry.register
class CallActivityReference(SemanticRule):
    rule_id = "TASK-006"
    description = "Call Activities must reference a called element"
    severity = Severity.ERROR
    spec_reference = "Section 10.2.5"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        # Collect all known process IDs for reference validation
        known_process_ids = set(model.processes.keys())

        for proc in model.processes.values():
            for eid in proc.tasks:
                elem = proc.elements.get(eid)
                if not elem or elem.tag != "callActivity":
                    continue

                called = elem.attrib.get("calledElement")
                if not called:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Call Activity '{elem.name or eid}' has no calledElement attribute"
                            ),
                            element_id=eid,
                            element_type="callActivity",
                            line=elem.line,
                        )
                    )
                elif called not in known_process_ids and called not in model.all_elements:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Call Activity '{elem.name or eid}' references "
                                f"unknown element '{called}'"
                            ),
                            element_id=eid,
                            element_type="callActivity",
                            line=elem.line,
                            severity=Severity.WARNING,
                        )
                    )
        return issues
