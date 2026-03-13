"""Gateway validation rules (GW-001 through GW-004)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions
from .base import SemanticRule, registry


@registry.register
class ExclusiveGatewayDefaultFlow(SemanticRule):
    rule_id = "GW-001"
    description = "Exclusive Gateway with multiple outgoing flows should have a default flow"
    severity = Severity.WARNING
    spec_reference = "Section 10.5.3"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for gw_id in proc.gateways:
                elem = proc.elements.get(gw_id)
                if not elem or elem.tag != "exclusiveGateway":
                    continue

                outgoing = [sf for sf in proc.sequence_flows.values() if sf.source_ref == gw_id]
                if len(outgoing) <= 1:
                    continue

                default_ref = elem.attrib.get("default")
                if not default_ref:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Exclusive Gateway '{elem.name or gw_id}' has "
                                f"{len(outgoing)} outgoing flows but no default flow"
                            ),
                            element_id=gw_id,
                            element_type="exclusiveGateway",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class ParallelGatewayBalanced(SemanticRule):
    rule_id = "GW-002"
    description = "Parallel Gateway used for splitting should have a corresponding join"
    severity = Severity.WARNING
    spec_reference = "Section 10.5.4"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            parallel_gws = [
                gw_id
                for gw_id in proc.gateways
                if proc.elements.get(gw_id) and proc.elements[gw_id].tag == "parallelGateway"
            ]
            if not parallel_gws:
                continue

            splits = []
            joins = []
            for gw_id in parallel_gws:
                outgoing = sum(1 for sf in proc.sequence_flows.values() if sf.source_ref == gw_id)
                incoming = sum(1 for sf in proc.sequence_flows.values() if sf.target_ref == gw_id)
                if outgoing > 1:
                    splits.append(gw_id)
                if incoming > 1:
                    joins.append(gw_id)

            if len(splits) > len(joins):
                for gw_id in splits:
                    elem = proc.elements[gw_id]
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Parallel Gateway '{elem.name or gw_id}' splits flow "
                                "but may not have a corresponding join gateway"
                            ),
                            element_id=gw_id,
                            element_type="parallelGateway",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class InclusiveGatewayConditions(SemanticRule):
    rule_id = "GW-003"
    description = "Inclusive Gateway with multiple outgoing flows should have conditions on flows"
    severity = Severity.WARNING
    spec_reference = "Section 10.5.5"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for gw_id in proc.gateways:
                elem = proc.elements.get(gw_id)
                if not elem or elem.tag != "inclusiveGateway":
                    continue

                outgoing = [sf for sf in proc.sequence_flows.values() if sf.source_ref == gw_id]
                if len(outgoing) <= 1:
                    continue

                default_ref = elem.attrib.get("default")
                unconditional = [
                    sf for sf in outgoing if sf.id != default_ref and not sf.condition_expression
                ]
                if unconditional:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Inclusive Gateway '{elem.name or gw_id}' has "
                                f"{len(unconditional)} outgoing flow(s) without conditions"
                            ),
                            element_id=gw_id,
                            element_type="inclusiveGateway",
                            line=elem.line,
                        )
                    )
        return issues


@registry.register
class EventBasedGatewayConstraints(SemanticRule):
    rule_id = "GW-004"
    description = (
        "Event-Based Gateway must have at least 2 outgoing flows targeting "
        "catch events or receive tasks"
    )
    severity = Severity.ERROR
    spec_reference = "Section 10.5.6"

    _VALID_TARGETS = {"intermediateCatchEvent", "receiveTask"}

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for proc in model.processes.values():
            for gw_id in proc.gateways:
                elem = proc.elements.get(gw_id)
                if not elem or elem.tag != "eventBasedGateway":
                    continue

                outgoing = [sf for sf in proc.sequence_flows.values() if sf.source_ref == gw_id]

                if len(outgoing) < 2:
                    issues.append(
                        self._make_issue(
                            message=(
                                f"Event-Based Gateway '{elem.name or gw_id}' must have "
                                f"at least 2 outgoing flows (has {len(outgoing)})"
                            ),
                            element_id=gw_id,
                            element_type="eventBasedGateway",
                            line=elem.line,
                        )
                    )
                    continue

                for sf in outgoing:
                    target_elem = proc.elements.get(sf.target_ref)
                    if target_elem and target_elem.tag not in self._VALID_TARGETS:
                        issues.append(
                            self._make_issue(
                                message=(
                                    f"Event-Based Gateway '{elem.name or gw_id}' has outgoing "
                                    f"flow to '{target_elem.tag}' ('{sf.target_ref}') — "
                                    "must target catch events or receive tasks"
                                ),
                                element_id=gw_id,
                                element_type="eventBasedGateway",
                                line=elem.line,
                            )
                        )

                    # Per spec: outgoing flows from event-based gateways
                    # must NOT have condition expressions
                    if sf.condition_expression:
                        issues.append(
                            self._make_issue(
                                message=(
                                    f"Event-Based Gateway '{elem.name or gw_id}' has a "
                                    f"condition on outgoing flow '{sf.id}' — "
                                    "conditions are not allowed on event-based gateway flows"
                                ),
                                element_id=gw_id,
                                element_type="eventBasedGateway",
                                line=elem.line,
                            )
                        )
        return issues
