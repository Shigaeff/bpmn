"""Event validation rules (EVT-001 through EVT-005)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions, _bpmn_tag, _local_tag, _srcline
from .base import SemanticRule, registry


@registry.register
class IntermediateCatchEventFlows(SemanticRule):
    rule_id = "EVT-001"
    description = "Intermediate catch events must have incoming AND outgoing sequence flows"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            incoming_targets = {sf.target_ref for sf in proc.sequence_flows.values()}
            outgoing_sources = {sf.source_ref for sf in proc.sequence_flows.values()}

            for eid in proc.intermediate_catch_events:
                elem = proc.elements.get(eid)
                if not elem:
                    continue

                missing = []
                if eid not in incoming_targets:
                    missing.append("incoming")
                if eid not in outgoing_sources:
                    missing.append("outgoing")

                if missing:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Intermediate catch event '{elem.name or eid}' "
                                f"is missing {' and '.join(missing)} sequence flow(s)"
                            ),
                            element_id=eid,
                            element_type="intermediateCatchEvent",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class BoundaryEventConstraints(SemanticRule):
    rule_id = "EVT-002"
    description = "Boundary events must be attached to an activity"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.5"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for eid in proc.boundary_events:
                elem = proc.elements.get(eid)
                if not elem:
                    continue

                attached_to = elem.attrib.get("attachedToRef")
                if not attached_to:
                    issues.append(
                        self._make_issue(
                            message=(f"Boundary event '{elem.name or eid}' has no attachedToRef"),
                            element_id=eid,
                            element_type="boundaryEvent",
                            line=elem.line,
                        )
                    )
                elif attached_to not in proc.elements:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Boundary event '{elem.name or eid}' attached to "
                                f"unknown element '{attached_to}'"
                            ),
                            element_id=eid,
                            element_type="boundaryEvent",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class CompensationEventUsage(SemanticRule):
    rule_id = "EVT-003"
    description = "Compensation events can only be used as boundary events or end events"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if model.root is None:
            return issues

        for event_elem in model.root.iter():
            local = _local_tag(event_elem)

            # Find compensation event definitions
            comp_def = event_elem.find(_bpmn_tag("compensateEventDefinition"))
            if comp_def is None:
                continue

            if local not in ("boundaryEvent", "endEvent", "intermediateThrowEvent"):
                issues.append(
                    self._make_issue(
                        message=(
                            f"Compensation event definition found in '{local}' "
                            f"('{event_elem.get('id')}') — only allowed in "
                            "boundary events, end events, or intermediate throw events"
                        ),
                        element_id=event_elem.get("id"),
                        element_type=local,
                        line=_srcline(event_elem),
                    )
                )
        return issues


@registry.register
class SignalEventDefinition(SemanticRule):
    rule_id = "EVT-004"
    description = "Signal events must reference a signal definition"
    severity = Severity.WARNING
    spec_reference = "Section 10.4.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if model.root is None:
            return issues

        # Collect all defined <signal> ids at the definitions level
        defined_signals = {
            sig.get("id") for sig in model.root.findall(_bpmn_tag("signal")) if sig.get("id")
        }

        for event_elem in model.root.iter():
            signal_def = event_elem.find(_bpmn_tag("signalEventDefinition"))
            if signal_def is None:
                continue

            local = _local_tag(event_elem)
            signal_ref = signal_def.get("signalRef")

            if not signal_ref:
                issues.append(
                    self._make_issue(
                        message=(
                            f"Signal event definition in '{event_elem.get('id')}' has no signalRef"
                        ),
                        element_id=event_elem.get("id"),
                        element_type=local,
                        line=_srcline(event_elem),
                    )
                )
            elif signal_ref not in defined_signals:
                issues.append(
                    self._make_issue(
                        message=(
                            f"Signal event definition in '{event_elem.get('id')}' "
                            f"references undefined signal '{signal_ref}'"
                        ),
                        element_id=event_elem.get("id"),
                        element_type=local,
                        line=_srcline(event_elem),
                    )
                )
        return issues


@registry.register
class TimerEventDefinition(SemanticRule):
    rule_id = "EVT-005"
    description = "Timer events must have a timer definition (timeDate, timeDuration, or timeCycle)"
    severity = Severity.ERROR
    spec_reference = "Section 10.4.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if model.root is None:
            return issues

        for event_elem in model.root.iter():
            timer_def = event_elem.find(_bpmn_tag("timerEventDefinition"))
            if timer_def is None:
                continue

            has_spec = (
                timer_def.find(_bpmn_tag("timeDate")) is not None
                or timer_def.find(_bpmn_tag("timeDuration")) is not None
                or timer_def.find(_bpmn_tag("timeCycle")) is not None
            )

            if not has_spec:
                local = _local_tag(event_elem)
                issues.append(
                    self._make_issue(
                        message=(
                            f"Timer event definition in '{event_elem.get('id')}' "
                            "has no timeDate, timeDuration, or timeCycle"
                        ),
                        element_id=event_elem.get("id"),
                        element_type=local,
                        line=_srcline(event_elem),
                    )
                )
        return issues
