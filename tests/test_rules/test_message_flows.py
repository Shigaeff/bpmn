"""Tests for message flow rules (MF-001..002)."""

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.rules.message_flows import (
    MessageFlowNotWithinSamePool,
    MessageFlowBetweenPools,
)


class TestMF001:
    def test_message_flow_within_same_pool(self):
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Pool A" processRef="Process_1"/>
                  <participant id="P2" name="Pool B" processRef="Process_B"/>
                  <messageFlow id="MF1" sourceRef="T1" targetRef="T2"/>
                </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <task id="T1" name="Task1"/>
                <task id="T2" name="Task2"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
                <sequenceFlow id="F2" sourceRef="T1" targetRef="T2"/>
                <sequenceFlow id="F3" sourceRef="T2" targetRef="E1"/>
            """,
            definitions_body="""
                <process id="Process_B" isExecutable="false">
                  <startEvent id="SB1"/>
                  <endEvent id="EB1"/>
                  <sequenceFlow id="FB1" sourceRef="SB1" targetRef="EB1"/>
                </process>
            """,
        )
        issues = MessageFlowNotWithinSamePool().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "same pool" in issues[0].message

    def test_message_flow_between_pools_ok(self):
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Pool A" processRef="Process_1"/>
                  <participant id="P2" name="Pool B" processRef="Process_B"/>
                  <messageFlow id="MF1" sourceRef="T1" targetRef="TB1"/>
                </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <task id="T1" name="Task1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
                <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
            """,
            definitions_body="""
                <process id="Process_B" isExecutable="false">
                  <startEvent id="SB1"/>
                  <task id="TB1" name="TaskB"/>
                  <endEvent id="EB1"/>
                  <sequenceFlow id="FB1" sourceRef="SB1" targetRef="TB1"/>
                  <sequenceFlow id="FB2" sourceRef="TB1" targetRef="EB1"/>
                </process>
            """,
        )
        issues = MessageFlowNotWithinSamePool().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestMF002:
    def test_message_flow_unknown_endpoint(self):
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Pool A" processRef="Process_1"/>
                  <participant id="P2" name="Pool B" processRef="Process_B"/>
                  <messageFlow id="MF1" sourceRef="UNKNOWN_SRC" targetRef="T1"/>
                </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <task id="T1" name="Task1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
                <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
            """,
            definitions_body="""
                <process id="Process_B" isExecutable="false">
                  <startEvent id="SB1"/>
                  <endEvent id="EB1"/>
                  <sequenceFlow id="FB1" sourceRef="SB1" targetRef="EB1"/>
                </process>
            """,
        )
        issues = MessageFlowBetweenPools().check(parse_bpmn(xml))
        assert len(issues) >= 1
        assert any("not associated" in i.message for i in issues)

    def test_single_participant_skip(self):
        """MF-002 skips when collaboration has fewer than 2 participants."""
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Only Pool" processRef="Process_1"/>
                  <messageFlow id="MF1" sourceRef="T1" targetRef="T1"/>
                </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <task id="T1" name="Task1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
                <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
            """,
        )
        issues = MessageFlowBetweenPools().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_pool_level_message_flow(self):
        """MF-002 resolves sourceRef/targetRef that are participant IDs."""
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Pool A" processRef="Process_1"/>
                  <participant id="P2" name="Pool B" processRef="Process_B"/>
                  <messageFlow id="MF1" sourceRef="P1" targetRef="P2"/>
                </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            """,
            definitions_body="""
                <process id="Process_B" isExecutable="false">
                  <startEvent id="SB1"/>
                  <endEvent id="EB1"/>
                  <sequenceFlow id="FB1" sourceRef="SB1" targetRef="EB1"/>
                </process>
            """,
        )
        issues = MessageFlowBetweenPools().check(parse_bpmn(xml))
        assert len(issues) == 0
