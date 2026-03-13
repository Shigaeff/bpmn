"""Tests for data rules (DATA-001..002)."""

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.rules.data import (
    DataAssociationReferences,
    DataStoreAccessible,
)


class TestDATA001:
    def test_data_association_unknown_ref(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1" name="Task">
              <dataInputAssociation id="DIA1">
                <sourceRef>NONEXISTENT_DATA</sourceRef>
              </dataInputAssociation>
            </task>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = DataAssociationReferences().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "unknown element" in issues[0].message.lower()

    def test_data_association_valid_ref(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <dataObjectReference id="DOR1" name="MyData"/>
            <task id="T1" name="Task">
              <dataInputAssociation id="DIA1">
                <sourceRef>DOR1</sourceRef>
              </dataInputAssociation>
            </task>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = DataAssociationReferences().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestDATA002:
    def test_data_store_ref_unknown(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <dataStoreReference id="DSR1" name="Store" dataStoreRef="DS_UNKNOWN"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = DataStoreAccessible().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "unknown data store" in issues[0].message.lower()

    def test_data_store_ref_valid(self):
        xml = make_bpmn_xml(
            definitions_body='<dataStore id="DS1" name="MyStore"/>',
            process_body="""
                <startEvent id="S1"/>
                <dataStoreReference id="DSR1" name="Store" dataStoreRef="DS1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            """,
        )
        issues = DataStoreAccessible().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_data_store_ref_without_ref_attr_ok(self):
        """dataStoreReference without dataStoreRef is not an error for DATA-002."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <dataStoreReference id="DSR1" name="Store"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = DataStoreAccessible().check(parse_bpmn(xml))
        assert len(issues) == 0
