"""Tests for collaboration rules (COLLAB-001..002)."""

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.rules.collaboration import (
    OneProcessPerPool,
    MessageFlowValidEndpoints,
)


class TestCOLLAB001:
    def test_multiple_pools_same_process(self):
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Pool A" processRef="Process_1"/>
                  <participant id="P2" name="Pool B" processRef="Process_1"/>
                </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            """,
        )
        issues = OneProcessPerPool().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "multiple" in issues[0].message.lower()

    def test_one_pool_per_process(self):
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Pool A" processRef="Process_1"/>
                  <participant id="P2" name="Pool B" processRef="Process_B"/>
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
        issues = OneProcessPerPool().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestCOLLAB002:
    def test_message_flow_unknown_source(self):
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Pool A" processRef="Process_1"/>
                  <participant id="P2" name="Pool B" processRef="Process_B"/>
                  <messageFlow id="MF1" sourceRef="UNKNOWN" targetRef="T1"/>
                </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <task id="T1"/>
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
        issues = MessageFlowValidEndpoints().check(parse_bpmn(xml))
        assert len(issues) >= 1
        assert any("unknown" in i.message.lower() for i in issues)

    def test_message_flow_valid_endpoints(self):
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
                <task id="T1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
                <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
            """,
            definitions_body="""
                <process id="Process_B" isExecutable="false">
                  <startEvent id="SB1"/>
                  <task id="TB1"/>
                  <endEvent id="EB1"/>
                  <sequenceFlow id="FB1" sourceRef="SB1" targetRef="TB1"/>
                  <sequenceFlow id="FB2" sourceRef="TB1" targetRef="EB1"/>
                </process>
            """,
        )
        issues = MessageFlowValidEndpoints().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_message_flow_unknown_target(self):
        """Message flow with unknown target should be flagged."""
        xml = make_bpmn_xml(
            collaboration="""
                <collaboration id="C1">
                  <participant id="P1" name="Pool A" processRef="Process_1"/>
                  <participant id="P2" name="Pool B" processRef="Process_B"/>
                  <messageFlow id="MF1" sourceRef="T1" targetRef="UNKNOWN_TGT"/>
                </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <task id="T1"/>
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
        issues = MessageFlowValidEndpoints().check(parse_bpmn(xml))
        assert len(issues) >= 1
        assert any("unknown" in i.message.lower() and "target" in i.message.lower() for i in issues)
