"""Tests for gateway rules (GW-001..004)."""

from lxml import etree

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.parser import BPMNDefinitions, BPMNProcess
from bpmn_validator.rules.gateways import (
    ExclusiveGatewayDefaultFlow,
    ParallelGatewayBalanced,
    InclusiveGatewayConditions,
    EventBasedGatewayConstraints,
)


class TestGW001:
    def test_exclusive_no_default(self):
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
        issues = ExclusiveGatewayDefaultFlow().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "GW-001"

    def test_exclusive_with_default(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <exclusiveGateway id="GW1" default="F2"/>
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
        issues = ExclusiveGatewayDefaultFlow().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_exclusive_single_outgoing_no_warning(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <exclusiveGateway id="GW1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="GW1"/>
            <sequenceFlow id="F1" sourceRef="GW1" targetRef="E1"/>
        """
        )
        issues = ExclusiveGatewayDefaultFlow().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestGW002:
    def test_split_without_join(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <parallelGateway id="PGW1"/>
            <task id="T1" name="A"/>
            <task id="T2" name="B"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="PGW1"/>
            <sequenceFlow id="F1" sourceRef="PGW1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="PGW1" targetRef="T2"/>
            <sequenceFlow id="F3" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F4" sourceRef="T2" targetRef="E1"/>
        """
        )
        issues = ParallelGatewayBalanced().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "GW-002"
        assert "join" in issues[0].message.lower()

    def test_split_with_join(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <parallelGateway id="PGW1"/>
            <task id="T1" name="A"/>
            <task id="T2" name="B"/>
            <parallelGateway id="PGW2"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="PGW1"/>
            <sequenceFlow id="F1" sourceRef="PGW1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="PGW1" targetRef="T2"/>
            <sequenceFlow id="F3" sourceRef="T1" targetRef="PGW2"/>
            <sequenceFlow id="F4" sourceRef="T2" targetRef="PGW2"/>
            <sequenceFlow id="F5" sourceRef="PGW2" targetRef="E1"/>
        """
        )
        issues = ParallelGatewayBalanced().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_no_parallel_gateways(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = ParallelGatewayBalanced().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestGW003:
    def test_inclusive_no_conditions(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <inclusiveGateway id="IGW1"/>
            <task id="T1" name="A"/>
            <task id="T2" name="B"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="IGW1"/>
            <sequenceFlow id="F1" sourceRef="IGW1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="IGW1" targetRef="T2"/>
            <sequenceFlow id="F3" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F4" sourceRef="T2" targetRef="E1"/>
        """
        )
        issues = InclusiveGatewayConditions().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "GW-003"
        assert "without conditions" in issues[0].message

    def test_inclusive_with_conditions_and_default(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <inclusiveGateway id="IGW1" default="F2"/>
            <task id="T1" name="A"/>
            <task id="T2" name="B"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="IGW1"/>
            <sequenceFlow id="F1" sourceRef="IGW1" targetRef="T1">
              <conditionExpression>x &gt; 5</conditionExpression>
            </sequenceFlow>
            <sequenceFlow id="F2" sourceRef="IGW1" targetRef="T2"/>
            <sequenceFlow id="F3" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F4" sourceRef="T2" targetRef="E1"/>
        """
        )
        issues = InclusiveGatewayConditions().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_inclusive_single_outgoing_ok(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <inclusiveGateway id="IGW1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="IGW1"/>
            <sequenceFlow id="F1" sourceRef="IGW1" targetRef="E1"/>
        """
        )
        issues = InclusiveGatewayConditions().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestGW004:
    def test_event_based_no_targets(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <eventBasedGateway id="EBG1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="EBG1"/>
            <sequenceFlow id="F1" sourceRef="EBG1" targetRef="E1"/>
        """
        )
        issues = EventBasedGatewayConstraints().check(parse_bpmn(xml))
        assert len(issues) >= 1

    def test_event_based_valid(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <eventBasedGateway id="EBG1"/>
            <intermediateCatchEvent id="ICE1"/>
            <intermediateCatchEvent id="ICE2"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="EBG1"/>
            <sequenceFlow id="F1" sourceRef="EBG1" targetRef="ICE1"/>
            <sequenceFlow id="F2" sourceRef="EBG1" targetRef="ICE2"/>
            <sequenceFlow id="F3" sourceRef="ICE1" targetRef="E1"/>
            <sequenceFlow id="F4" sourceRef="ICE2" targetRef="E1"/>
        """
        )
        issues = EventBasedGatewayConstraints().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_event_based_invalid_target(self):
        """Outgoing flow to a regular task should be flagged."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <eventBasedGateway id="EBG1"/>
            <intermediateCatchEvent id="ICE1"/>
            <task id="T1" name="Bad"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="EBG1"/>
            <sequenceFlow id="F1" sourceRef="EBG1" targetRef="ICE1"/>
            <sequenceFlow id="F2" sourceRef="EBG1" targetRef="T1"/>
            <sequenceFlow id="F3" sourceRef="ICE1" targetRef="E1"/>
            <sequenceFlow id="F4" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = EventBasedGatewayConstraints().check(parse_bpmn(xml))
        assert any("must target catch events" in i.message for i in issues)

    def test_event_based_condition_on_flow(self):
        """Conditions on event-based gateway outgoing flows should be flagged."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <eventBasedGateway id="EBG1"/>
            <intermediateCatchEvent id="ICE1"/>
            <intermediateCatchEvent id="ICE2"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F0" sourceRef="S1" targetRef="EBG1"/>
            <sequenceFlow id="F1" sourceRef="EBG1" targetRef="ICE1">
              <conditionExpression>x == 1</conditionExpression>
            </sequenceFlow>
            <sequenceFlow id="F2" sourceRef="EBG1" targetRef="ICE2"/>
            <sequenceFlow id="F3" sourceRef="ICE1" targetRef="E1"/>
            <sequenceFlow id="F4" sourceRef="ICE2" targetRef="E1"/>
        """
        )
        issues = EventBasedGatewayConstraints().check(parse_bpmn(xml))
        assert any("conditions are not allowed" in i.message for i in issues)


class TestGhostIDGuards:
    """Tests that gateway rules skip gracefully when gateway IDs are absent from elements dict."""

    @staticmethod
    def _empty_model() -> BPMNDefinitions:
        root = etree.Element("definitions")
        model = BPMNDefinitions(target_namespace=None, root=root)
        proc = BPMNProcess(id="P1", name="Test", is_executable=True)
        model.processes["P1"] = proc
        return model

    def test_gw001_ghost_gateway(self):
        """ExclusiveGatewayDefaultFlow skips ghost gateway ID."""
        model = self._empty_model()
        model.processes["P1"].gateways.append("GHOST")
        issues = ExclusiveGatewayDefaultFlow().check(model)
        assert issues == []

    def test_gw003_ghost_gateway(self):
        """InclusiveGatewayConditions skips ghost gateway ID."""
        model = self._empty_model()
        model.processes["P1"].gateways.append("GHOST")
        issues = InclusiveGatewayConditions().check(model)
        assert issues == []

    def test_gw004_ghost_gateway(self):
        """EventBasedGatewayConstraints skips ghost gateway ID."""
        model = self._empty_model()
        model.processes["P1"].gateways.append("GHOST")
        issues = EventBasedGatewayConstraints().check(model)
        assert issues == []
