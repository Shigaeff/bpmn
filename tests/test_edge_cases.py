"""Edge case tests — unusual but valid/semi-valid inputs."""

from __future__ import annotations

import pytest

from bpmn_validator.parser import BPMNParser
from tests.conftest import NS


class TestNonBPMNXML:
    """Valid XML that is not BPMN at all."""

    def test_html_document(self):
        parser = BPMNParser()
        model = parser.parse("<html><body>Hello</body></html>")
        assert len(model.processes) == 0
        assert len(model.collaborations) == 0

    def test_random_xml_namespace(self):
        parser = BPMNParser()
        model = parser.parse('<root xmlns="http://not-bpmn.example.com"><child/></root>')
        assert len(model.processes) == 0

    def test_bpmn_wrong_namespace(self):
        """BPMN-like structure but wrong namespace → no processes found."""
        parser = BPMNParser()
        xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://wrong.namespace.example.com"
             id="D1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true">
    <startEvent id="S1"/>
  </process>
</definitions>"""
        model = parser.parse(xml)
        assert len(model.processes) == 0


class TestWhitespaceAndBOM:
    """Files with unusual whitespace or BOM markers."""

    def test_whitespace_only(self):
        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse("   \n\t\n   ")

    def test_utf8_bom_prefix(self):
        """UTF-8 BOM (\\xef\\xbb\\xbf) should be handled gracefully."""
        bom = b"\xef\xbb\xbf"
        xml = (
            bom
            + f"""\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="{NS}" id="D1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true">
    <startEvent id="S1"/>
    <endEvent id="E1"/>
    <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
  </process>
</definitions>""".encode("utf-8")
        )

        parser = BPMNParser()
        model = parser.parse(xml)
        assert "P1" in model.processes

    def test_utf16_bom_bytes(self):
        """UTF-16 BOM should be handled or rejected gracefully."""
        bom_le = b"\xff\xfe"
        xml_content = f"""\
<?xml version="1.0" encoding="UTF-16"?>
<definitions xmlns="{NS}" id="D1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true">
    <startEvent id="S1"/>
  </process>
</definitions>"""
        encoded = bom_le + xml_content.encode("utf-16-le")
        parser = BPMNParser()
        # UTF-16 may work or may fail depending on lxml — either way, no crash
        try:
            model = parser.parse(encoded)
            assert model is not None
        except ValueError:
            pass  # Graceful rejection is acceptable


class TestDeeplyNested:
    """Deeply nested XML structures."""

    def test_nested_subprocesses(self):
        """Parser should handle nested subprocesses without crashing."""
        inner = '<startEvent id="S_deep"/>'
        for i in range(20):
            inner = f'<subProcess id="Sub_{i}">\n  {inner}\n</subProcess>'
        xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="{NS}" id="D1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true">
    {inner}
  </process>
</definitions>"""

        parser = BPMNParser()
        model = parser.parse(xml)
        assert "P1" in model.processes
        # Should have found the nested subprocesses
        proc = model.processes["P1"]
        assert len(proc.sub_processes) > 0


class TestEmptyProcess:
    """Valid BPMN with edge-case content."""

    def test_process_with_no_elements(self):
        """An empty process is structurally valid XML."""
        xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="{NS}" id="D1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true"/>
</definitions>"""
        parser = BPMNParser()
        model = parser.parse(xml)
        proc = model.processes["P1"]
        assert len(proc.elements) == 0
        assert len(proc.sequence_flows) == 0

    def test_process_no_id(self):
        """A process element without an id attribute."""
        xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="{NS}" id="D1" targetNamespace="http://example.com">
  <process isExecutable="true">
    <startEvent id="S1"/>
  </process>
</definitions>"""
        parser = BPMNParser()
        model = parser.parse(xml)
        # Process should be stored with empty string key
        assert "" in model.processes


class TestFileBasedParsing:
    """Test parsing from actual files on disk."""

    def test_parse_file_path_object(self, tmp_path):
        bpmn = tmp_path / "test.bpmn"
        bpmn.write_text(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="{NS}" id="D1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true">
    <startEvent id="S1"/>
    <endEvent id="E1"/>
    <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
  </process>
</definitions>""")
        parser = BPMNParser()
        model = parser.parse(bpmn)
        assert "P1" in model.processes

    def test_parse_file_string_path(self, tmp_path):
        bpmn = tmp_path / "test.bpmn"
        bpmn.write_text(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="{NS}" id="D1" targetNamespace="http://example.com">
  <process id="P1" isExecutable="true">
    <startEvent id="S1"/>
  </process>
</definitions>""")
        parser = BPMNParser()
        model = parser.parse(str(bpmn))
        assert "P1" in model.processes
