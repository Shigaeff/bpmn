"""Shared test fixtures and helpers."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from bpmn_validator.parser import BPMNParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_DIR = FIXTURES_DIR / "valid"
INVALID_DIR = FIXTURES_DIR / "invalid_semantic"

NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"


def make_bpmn_xml(
    *,
    process_body: str = "",
    process_attrs: str = "",
    definitions_body: str = "",
    collaboration: str = "",
    process_id: str = "Process_1",
) -> str:
    """Build a minimal BPMN XML string with the given inner content."""
    return dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <definitions xmlns="{NS}"
                     xmlns:bpmndi="{BPMNDI_NS}"
                     xmlns:dc="{DC_NS}"
                     xmlns:di="{DI_NS}"
                     id="Definitions_1"
                     targetNamespace="http://example.com/bpmn">
          {collaboration}
          {definitions_body}
          <process id="{process_id}" isExecutable="true" {process_attrs}>
            {process_body}
          </process>
        </definitions>
    """)


def parse_bpmn(xml: str):
    """Parse a BPMN XML string and return BPMNDefinitions."""
    return BPMNParser().parse(xml)


@pytest.fixture
def parser():
    return BPMNParser()


@pytest.fixture
def valid_simple_process():
    """Minimal valid process with start → task → end."""
    return make_bpmn_xml(
        process_body="""
        <startEvent id="Start_1" name="Start"/>
        <task id="Task_1" name="Do Something"/>
        <endEvent id="End_1" name="End"/>
        <sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1"/>
        <sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1"/>
    """
    )
