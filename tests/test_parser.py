"""Tests for the BPMN XML parser."""

import pytest
from lxml import etree

from bpmn_validator.parser import BPMNParser, _local_tag
from tests.conftest import make_bpmn_xml, parse_bpmn


class TestBPMNParser:
    def test_parse_simple_process(self, valid_simple_process):
        model = parse_bpmn(valid_simple_process)
        assert "Process_1" in model.processes
        proc = model.processes["Process_1"]
        assert len(proc.start_events) == 1
        assert len(proc.end_events) == 1
        assert "Task_1" in proc.tasks
        assert len(proc.sequence_flows) == 2

    def test_parse_collaboration(self):
        xml = make_bpmn_xml(
            collaboration="""
            <collaboration id="C1">
              <participant id="P1" name="Pool" processRef="Process_1"/>
            </collaboration>
            """,
            process_body="""
                <startEvent id="S1" name="Start"/>
                <endEvent id="E1" name="End"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            """,
        )
        model = parse_bpmn(xml)
        assert len(model.collaborations) == 1
        collab = list(model.collaborations.values())[0]
        assert "P1" in collab.participants

    def test_parse_gateways(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <exclusiveGateway id="GW1" name="Decision"/>
            <task id="T1" name="A"/>
            <task id="T2" name="B"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="GW1"/>
            <sequenceFlow id="F2" sourceRef="GW1" targetRef="T1"/>
            <sequenceFlow id="F3" sourceRef="GW1" targetRef="T2"/>
            <sequenceFlow id="F4" sourceRef="T1" targetRef="E1"/>
            <sequenceFlow id="F5" sourceRef="T2" targetRef="E1"/>
        """
        )
        model = parse_bpmn(xml)
        proc = model.processes["Process_1"]
        assert "GW1" in proc.gateways

    def test_parse_subprocess(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <subProcess id="SP1" name="Sub">
              <startEvent id="SP_S1"/>
              <task id="SP_T1" name="Inner"/>
              <endEvent id="SP_E1"/>
              <sequenceFlow id="SP_F1" sourceRef="SP_S1" targetRef="SP_T1"/>
              <sequenceFlow id="SP_F2" sourceRef="SP_T1" targetRef="SP_E1"/>
            </subProcess>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SP1"/>
            <sequenceFlow id="F2" sourceRef="SP1" targetRef="E1"/>
        """
        )
        model = parse_bpmn(xml)
        proc = model.processes["Process_1"]
        assert "SP1" in proc.sub_processes
        # Sub-process children are collected into the process elements
        assert "SP_T1" in proc.elements

    def test_parse_from_file(self, parser, tmp_path):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        f = tmp_path / "test.bpmn"
        f.write_text(xml, encoding="utf-8")
        model = parser.parse(f)
        assert "Process_1" in model.processes

    def test_all_elements_property(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1" name="Work"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        model = parse_bpmn(xml)
        # all_elements should contain elements from all processes
        assert "S1" in model.all_elements
        assert "T1" in model.all_elements
        assert "E1" in model.all_elements

    def test_parse_bytes_input(self):
        """Parser accepts raw bytes."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        model = BPMNParser().parse(xml.encode("utf-8"))
        assert "Process_1" in model.processes

    def test_parse_invalid_type_raises(self):
        """Passing an unsupported type raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse source"):
            BPMNParser().parse(12345)  # type: ignore[arg-type]

    def test_parse_intermediate_throw_event(self):
        """intermediateThrowEvent is collected into proc.intermediate_throw_events."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <intermediateThrowEvent id="ITE1" name="Signal"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="ITE1"/>
            <sequenceFlow id="F2" sourceRef="ITE1" targetRef="E1"/>
        """
        )
        model = parse_bpmn(xml)
        proc = model.processes["Process_1"]
        assert "ITE1" in proc.intermediate_throw_events

    def test_local_tag_no_namespace(self):
        """_local_tag returns the tag as-is when there's no namespace."""
        elem = etree.Element("plain")
        assert _local_tag(elem) == "plain"
