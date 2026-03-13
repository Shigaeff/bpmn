"""Integration tests for the main BPMNValidator facade."""

import textwrap
from pathlib import Path

from bpmn_validator import BPMNValidator
from tests.conftest import VALID_DIR, INVALID_DIR, make_bpmn_xml

# Lightweight mock XSD (same as in test_schema_validator.py)
MOCK_XSD = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
               targetNamespace="http://www.omg.org/spec/BPMN/20100524/MODEL"
               elementFormDefault="qualified">
      <xs:element name="definitions">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="process" minOccurs="1" maxOccurs="unbounded">
              <xs:complexType>
                <xs:sequence>
                  <xs:any minOccurs="0" maxOccurs="unbounded" processContents="skip"/>
                </xs:sequence>
                <xs:attribute name="id" type="xs:string" use="required"/>
              </xs:complexType>
            </xs:element>
          </xs:sequence>
          <xs:attribute name="id" type="xs:string" use="required"/>
        </xs:complexType>
      </xs:element>
    </xs:schema>
""")

VALID_XML_FOR_SCHEMA = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D1">
      <process id="P1"/>
    </definitions>
""")

INVALID_XML_FOR_SCHEMA = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D1">
    </definitions>
""")  # Missing required <process>


class TestBPMNValidatorIntegration:
    def test_valid_simple_process(self):
        v = BPMNValidator(skip_schema=True)
        result = v.validate(VALID_DIR / "simple_process.bpmn")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_invalid_no_start(self):
        v = BPMNValidator(skip_schema=True)
        result = v.validate(INVALID_DIR / "no_start_event.bpmn")
        assert not result.is_valid
        rule_ids = {e.rule_id for e in result.errors}
        assert "PROC-001" in rule_ids

    def test_invalid_no_end(self):
        v = BPMNValidator(skip_schema=True)
        result = v.validate(INVALID_DIR / "no_end_event.bpmn")
        assert not result.is_valid
        rule_ids = {e.rule_id for e in result.errors}
        assert "PROC-002" in rule_ids

    def test_validate_string(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1" name="Start"/>
            <task id="T1" name="Work"/>
            <endEvent id="E1" name="End"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        v = BPMNValidator(skip_schema=True)
        result = v.validate_string(xml)
        assert result.is_valid

    def test_exclude_rules(self):
        v = BPMNValidator(skip_schema=True, exclude_rules={"PROC-001", "PROC-002"})
        result = v.validate(INVALID_DIR / "no_start_event.bpmn")
        proc_ids = {e.rule_id for e in result.errors}
        assert "PROC-001" not in proc_ids
        assert "PROC-002" not in proc_ids

    def test_to_json(self):
        v = BPMNValidator(skip_schema=True)
        result = v.validate(VALID_DIR / "simple_process.bpmn")
        import json

        data = json.loads(result.to_json())
        assert data["is_valid"] is True
        assert "summary" in data
        assert "errors" in data["summary"]

    def test_to_text(self):
        v = BPMNValidator(skip_schema=True)
        result = v.validate(VALID_DIR / "simple_process.bpmn")
        text = result.to_text()
        assert "VALID" in text.upper() or "valid" in text.lower() or "0 error" in text.lower()

    def test_collaboration_file(self):
        v = BPMNValidator(skip_schema=True)
        result = v.validate(VALID_DIR / "collaboration.bpmn")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_skip_semantic(self):
        """With skip_semantic, no semantic issues should be raised."""
        v = BPMNValidator(skip_schema=True, skip_semantic=True)
        result = v.validate(INVALID_DIR / "no_start_event.bpmn")
        assert result.is_valid  # No checks ran
        assert result.schema_valid is None
        assert result.semantic_valid is None

    def test_severity_filter(self):
        from bpmn_validator import Severity

        v = BPMNValidator(skip_schema=True, severity_filter=Severity.ERROR)
        result = v.validate(VALID_DIR / "simple_process.bpmn")
        # Only ERROR-level rules ran; no errors expected on valid file
        assert result.is_valid

    def test_schema_and_semantic_valid_fields(self):
        """schema_valid and semantic_valid should be set after validation."""
        v = BPMNValidator(skip_schema=True)
        result = v.validate(VALID_DIR / "simple_process.bpmn")
        assert result.schema_valid is None  # schema was skipped
        assert result.semantic_valid is True

    def test_semantic_valid_false_on_errors(self):
        v = BPMNValidator(skip_schema=True)
        result = v.validate(INVALID_DIR / "no_start_event.bpmn")
        assert result.semantic_valid is False


class TestSchemaValidationInValidator:
    """Tests that exercise the schema-validation path inside BPMNValidator."""

    def test_schema_validator_loaded_when_xsd_exists(self, tmp_path: Path):
        """If BPMN20.xsd exists in specs_dir, _schema_validator is created."""
        xsd_file = tmp_path / "BPMN20.xsd"
        xsd_file.write_text(MOCK_XSD, encoding="utf-8")
        v = BPMNValidator(specs_dir=tmp_path, skip_semantic=True)
        assert v._schema_validator is not None

    def test_schema_validation_passes_in_run(self, tmp_path: Path):
        """validate_string with valid XML against mock XSD passes."""
        xsd_file = tmp_path / "BPMN20.xsd"
        xsd_file.write_text(MOCK_XSD, encoding="utf-8")
        v = BPMNValidator(specs_dir=tmp_path, skip_semantic=True)
        result = v.validate_string(VALID_XML_FOR_SCHEMA)
        assert result.schema_valid is True
        assert result.is_valid

    def test_schema_validation_fails_in_run(self, tmp_path: Path):
        """validate_string with invalid XML against mock XSD fails."""
        xsd_file = tmp_path / "BPMN20.xsd"
        xsd_file.write_text(MOCK_XSD, encoding="utf-8")
        v = BPMNValidator(specs_dir=tmp_path, skip_semantic=True)
        result = v.validate_string(INVALID_XML_FOR_SCHEMA)
        assert result.schema_valid is False
        assert not result.is_valid
        assert any(i.rule_id == "XSD-001" for i in result.errors)
