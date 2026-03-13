"""Tests for process structure rules (PROC-001..005)."""

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.rules.process_structure import (
    ProcessMustHaveStartEvent,
    ProcessMustHaveEndEvent,
    StartEventNoIncomingFlows,
    EndEventNoOutgoingFlows,
    AllElementsReachable,
)


class TestPROC001:
    def test_no_start_event(self):
        xml = make_bpmn_xml(
            process_body="""
            <task id="T1" name="A"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = ProcessMustHaveStartEvent().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "PROC-001"

    def test_with_start_event(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = ProcessMustHaveStartEvent().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestPROC002:
    def test_no_end_event(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
        """
        )
        issues = ProcessMustHaveEndEvent().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "PROC-002"

    def test_with_end_event(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = ProcessMustHaveEndEvent().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestPROC003:
    def test_start_event_with_incoming(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F_bad" sourceRef="T1" targetRef="S1"/>
        """
        )
        issues = StartEventNoIncomingFlows().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "S1" in issues[0].message


class TestPROC004:
    def test_end_event_with_outgoing(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            <sequenceFlow id="F_bad" sourceRef="E1" targetRef="S1"/>
        """
        )
        issues = EndEventNoOutgoingFlows().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "E1" in issues[0].message


class TestPROC005:
    def test_unreachable_element(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1" name="Connected"/>
            <task id="T_orphan" name="Orphan"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = AllElementsReachable().check(parse_bpmn(xml))
        assert len(issues) >= 1
        ids = {i.element_id for i in issues}
        assert "T_orphan" in ids

    def test_all_reachable(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = AllElementsReachable().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_cycle_revisits_node(self):
        """A cycle in the graph should not cause infinite loop (BFS dedup)."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="TA" name="A"/>
            <task id="TB" name="B"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="TA"/>
            <sequenceFlow id="F2" sourceRef="TA" targetRef="TB"/>
            <sequenceFlow id="F3" sourceRef="TB" targetRef="TA"/>
            <sequenceFlow id="F4" sourceRef="TB" targetRef="E1"/>
        """
        )
        issues = AllElementsReachable().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_two_start_events_same_target(self):
        """Two start events both connecting to the same task exercises BFS dedup (line 128)."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <startEvent id="S2"/>
            <task id="T1" name="Shared"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="S2" targetRef="T1"/>
            <sequenceFlow id="F3" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = AllElementsReachable().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_data_object_excluded(self):
        """dataObject elements should not be reported as unreachable."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1" name="Work"/>
            <endEvent id="E1"/>
            <dataObject id="DO1" name="Data"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = AllElementsReachable().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_boundary_event_excluded(self):
        """boundaryEvent should not be reported as unreachable."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1" name="Work"/>
            <boundaryEvent id="BE1" attachedToRef="T1">
              <timerEventDefinition>
                <timeDuration>PT1H</timeDuration>
              </timerEventDefinition>
            </boundaryEvent>
            <endEvent id="E1"/>
            <endEvent id="E2"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F3" sourceRef="BE1" targetRef="E2"/>
        """
        )
        issues = AllElementsReachable().check(parse_bpmn(xml))
        # BE1 should be excluded; E2 is reachable via BE1 in flow
        be_issues = [i for i in issues if i.element_id == "BE1"]
        assert len(be_issues) == 0
