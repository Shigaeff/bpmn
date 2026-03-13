"""Tests for event rules (EVT-001..005)."""

from lxml import etree

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.parser import BPMNDefinitions, BPMNProcess
from bpmn_validator.rules.events import (
    IntermediateCatchEventFlows,
    BoundaryEventConstraints,
    CompensationEventUsage,
    SignalEventDefinition,
    TimerEventDefinition,
)


class TestEVT001:
    def test_catch_event_no_flows(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <intermediateCatchEvent id="ICE1" name="Wait"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = IntermediateCatchEventFlows().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "incoming" in issues[0].message

    def test_catch_event_with_flows(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <intermediateCatchEvent id="ICE1" name="Wait"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="ICE1"/>
            <sequenceFlow id="F2" sourceRef="ICE1" targetRef="E1"/>
        """
        )
        issues = IntermediateCatchEventFlows().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestEVT002:
    def test_boundary_no_attached(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <boundaryEvent id="BE1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = BoundaryEventConstraints().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "attachedToRef" in issues[0].message

    def test_boundary_valid(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <boundaryEvent id="BE1" attachedToRef="T1"/>
            <endEvent id="E1"/>
            <endEvent id="E2"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F3" sourceRef="BE1" targetRef="E2"/>
        """
        )
        issues = BoundaryEventConstraints().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_boundary_attached_to_unknown(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <boundaryEvent id="BE1" attachedToRef="NONEXISTENT"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = BoundaryEventConstraints().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "unknown" in issues[0].message.lower()


class TestEVT003:
    def test_compensation_in_start_event(self):
        """Compensation event definition in startEvent should be flagged."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1">
              <compensateEventDefinition id="CED1"/>
            </startEvent>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = CompensationEventUsage().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "EVT-003"
        assert "startEvent" in issues[0].message

    def test_compensation_in_boundary_event_ok(self):
        """Compensation in boundaryEvent is allowed."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1" name="Work"/>
            <boundaryEvent id="BE1" attachedToRef="T1">
              <compensateEventDefinition id="CED1"/>
            </boundaryEvent>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = CompensationEventUsage().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_compensation_in_end_event_ok(self):
        """Compensation in endEvent is allowed."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1">
              <compensateEventDefinition id="CED1"/>
            </endEvent>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = CompensationEventUsage().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestEVT004:
    def test_signal_no_ref(self):
        """Signal event with no signalRef should be flagged."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1">
              <signalEventDefinition id="SED1"/>
            </startEvent>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = SignalEventDefinition().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "no signalRef" in issues[0].message

    def test_signal_undefined_ref(self):
        """Signal event referencing an undefined signal should be flagged."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1">
              <signalEventDefinition id="SED1" signalRef="SIG_MISSING"/>
            </startEvent>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = SignalEventDefinition().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "undefined signal" in issues[0].message

    def test_signal_valid_ref(self):
        """Signal event with a valid signalRef should pass."""
        xml = make_bpmn_xml(
            definitions_body='<signal id="SIG1" name="MySignal"/>',
            process_body="""
                <startEvent id="S1">
                  <signalEventDefinition id="SED1" signalRef="SIG1"/>
                </startEvent>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            """,
        )
        issues = SignalEventDefinition().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestEVT005:
    def test_timer_no_spec(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1">
              <timerEventDefinition id="TED1"/>
            </startEvent>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = TimerEventDefinition().check(parse_bpmn(xml))
        assert len(issues) == 1

    def test_timer_with_duration(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1">
              <timerEventDefinition id="TED1">
                <timeDuration>PT5M</timeDuration>
              </timerEventDefinition>
            </startEvent>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = TimerEventDefinition().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_timer_with_date(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1">
              <timerEventDefinition id="TED1">
                <timeDate>2026-01-01T00:00:00Z</timeDate>
              </timerEventDefinition>
            </startEvent>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = TimerEventDefinition().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_timer_with_cycle(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1">
              <timerEventDefinition id="TED1">
                <timeCycle>R3/PT10M</timeCycle>
              </timerEventDefinition>
            </startEvent>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = TimerEventDefinition().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestGhostIDGuards:
    """Tests that rules skip gracefully when element IDs are in lists but absent from elements dict."""

    @staticmethod
    def _empty_model() -> BPMNDefinitions:
        root = etree.Element("definitions")
        model = BPMNDefinitions(target_namespace=None, root=root)
        proc = BPMNProcess(id="P1", name="Test", is_executable=True)
        model.processes["P1"] = proc
        return model

    def test_evt001_ghost_intermediate_catch(self):
        """IntermediateCatchEventFlows skips ghost ID in intermediate_catch_events."""
        model = self._empty_model()
        model.processes["P1"].intermediate_catch_events.append("GHOST")
        issues = IntermediateCatchEventFlows().check(model)
        assert issues == []

    def test_evt002_ghost_boundary_event(self):
        """BoundaryEventConstraints skips ghost ID in boundary_events."""
        model = self._empty_model()
        model.processes["P1"].boundary_events.append("GHOST")
        issues = BoundaryEventConstraints().check(model)
        assert issues == []
