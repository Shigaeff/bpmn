"""Tests for sequence flow rules (SF-001..002)."""

from lxml import etree

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.parser import BPMNDefinitions, BPMNProcess, SequenceFlow
from bpmn_validator.rules.sequence_flows import (
    SequenceFlowNoCrossBoundary,
    ConditionalFlowMustHaveCondition,
)


class TestSF001:
    def test_cross_boundary(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <subProcess id="SP1">
              <startEvent id="SP_S1"/>
              <task id="T_INNER"/>
              <endEvent id="SP_E1"/>
              <sequenceFlow id="SF_SP1" sourceRef="SP_S1" targetRef="T_INNER"/>
              <sequenceFlow id="SF_SP2" sourceRef="T_INNER" targetRef="SP_E1"/>
            </subProcess>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SP1"/>
            <sequenceFlow id="F2" sourceRef="SP1" targetRef="E1"/>
            <sequenceFlow id="F_BAD" sourceRef="T_INNER" targetRef="E1"/>
        """
        )
        issues = SequenceFlowNoCrossBoundary().check(parse_bpmn(xml))
        assert len(issues) >= 1
        assert any("crosses subprocess boundary" in i.message for i in issues)

    def test_no_cross_boundary(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = SequenceFlowNoCrossBoundary().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestSF002:
    def test_unconditional_flow_from_exclusive_gw(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <exclusiveGateway id="GW1"/>
            <task id="T1"/>
            <task id="T2"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="GW1"/>
            <sequenceFlow id="F1" sourceRef="GW1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="GW1" targetRef="T2"/>
            <sequenceFlow id="F3" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F4" sourceRef="T2" targetRef="E1"/>
        """
        )
        issues = ConditionalFlowMustHaveCondition().check(parse_bpmn(xml))
        assert len(issues) >= 1
        assert issues[0].rule_id == "SF-002"

    def test_conditional_flows_ok(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <exclusiveGateway id="GW1" default="F2"/>
            <task id="T1"/>
            <task id="T2"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="GW1"/>
            <sequenceFlow id="F1" sourceRef="GW1" targetRef="T1">
              <conditionExpression>x &gt; 5</conditionExpression>
            </sequenceFlow>
            <sequenceFlow id="F2" sourceRef="GW1" targetRef="T2"/>
            <sequenceFlow id="F3" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F4" sourceRef="T2" targetRef="E1"/>
        """
        )
        issues = ConditionalFlowMustHaveCondition().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_single_outgoing_no_warning(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <exclusiveGateway id="GW1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="GW1"/>
            <sequenceFlow id="F1" sourceRef="GW1" targetRef="E1"/>
        """
        )
        issues = ConditionalFlowMustHaveCondition().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestGhostIDGuards:
    """Tests that SF rules skip gracefully when source element is absent from elements dict."""

    def test_sf002_ghost_source_ref(self):
        """ConditionalFlowMustHaveCondition skips when sourceRef element is missing."""
        root = etree.Element("definitions")
        model = BPMNDefinitions(target_namespace=None, root=root)
        proc = BPMNProcess(id="P1", name="Test", is_executable=True)
        # Sequence flow with a source_ref that has no matching element
        proc.sequence_flows["F1"] = SequenceFlow(
            id="F1",
            source_ref="GHOST_GW",
            target_ref="T1",
        )
        model.processes["P1"] = proc
        issues = ConditionalFlowMustHaveCondition().check(model)
        assert issues == []
