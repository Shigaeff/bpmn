"""Tests for the SchemaValidator (XSD-based validation)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from lxml import etree

from bpmn_validator.schema_validator import SchemaValidator
from bpmn_validator.models import Severity, ValidationPhase


# ---------------------------------------------------------------------------
# Helpers – lightweight XSD that mimics the structure of BPMN20.xsd
# ---------------------------------------------------------------------------

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

VALID_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D1">
      <process id="P1"/>
    </definitions>
""")

INVALID_XML_SCHEMA = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D1">
    </definitions>
""")  # Missing required <process>

MALFORMED_XML = "<not-xml><<<>>>"


@pytest.fixture
def mock_schema_dir(tmp_path: Path) -> Path:
    """Create a temp directory with a mock BPMN20.xsd."""
    xsd_file = tmp_path / "BPMN20.xsd"
    xsd_file.write_text(MOCK_XSD, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests: _load_schema
# ---------------------------------------------------------------------------


class TestLoadSchema:
    def test_missing_xsd_raises(self, tmp_path: Path):
        sv = SchemaValidator(tmp_path)
        with pytest.raises(FileNotFoundError, match="XSD schemas not found"):
            sv._load_schema()

    def test_loads_successfully(self, mock_schema_dir: Path):
        sv = SchemaValidator(mock_schema_dir)
        schema = sv._load_schema()
        assert isinstance(schema, etree.XMLSchema)

    def test_caches_schema(self, mock_schema_dir: Path):
        sv = SchemaValidator(mock_schema_dir)
        s1 = sv._load_schema()
        s2 = sv._load_schema()
        assert s1 is s2


# ---------------------------------------------------------------------------
# Tests: validate (file-based)
# ---------------------------------------------------------------------------


class TestValidateFile:
    def test_valid_xml(self, mock_schema_dir: Path, tmp_path: Path):
        xml_file = tmp_path / "valid.bpmn"
        xml_file.write_text(VALID_XML, encoding="utf-8")

        sv = SchemaValidator(mock_schema_dir)
        is_valid, issues = sv.validate(xml_file)
        assert is_valid is True
        assert len(issues) == 0

    def test_invalid_xml(self, mock_schema_dir: Path, tmp_path: Path):
        xml_file = tmp_path / "invalid.bpmn"
        xml_file.write_text(INVALID_XML_SCHEMA, encoding="utf-8")

        sv = SchemaValidator(mock_schema_dir)
        is_valid, issues = sv.validate(xml_file)
        assert is_valid is False
        assert len(issues) >= 1
        assert issues[0].rule_id == "XSD-001"
        assert issues[0].severity == Severity.ERROR
        assert issues[0].phase == ValidationPhase.SCHEMA

    def test_malformed_xml(self, mock_schema_dir: Path, tmp_path: Path):
        xml_file = tmp_path / "bad.bpmn"
        xml_file.write_text(MALFORMED_XML, encoding="utf-8")

        sv = SchemaValidator(mock_schema_dir)
        is_valid, issues = sv.validate(xml_file)
        assert is_valid is False
        assert len(issues) == 1
        assert issues[0].rule_id == "XSD-000"
        assert "Malformed XML" in issues[0].message


# ---------------------------------------------------------------------------
# Tests: validate_string
# ---------------------------------------------------------------------------


class TestValidateString:
    def test_valid_string(self, mock_schema_dir: Path):
        sv = SchemaValidator(mock_schema_dir)
        is_valid, issues = sv.validate_string(VALID_XML)
        assert is_valid is True
        assert len(issues) == 0

    def test_valid_bytes(self, mock_schema_dir: Path):
        sv = SchemaValidator(mock_schema_dir)
        is_valid, issues = sv.validate_string(VALID_XML.encode("utf-8"))
        assert is_valid is True
        assert len(issues) == 0

    def test_invalid_string(self, mock_schema_dir: Path):
        sv = SchemaValidator(mock_schema_dir)
        is_valid, issues = sv.validate_string(INVALID_XML_SCHEMA)
        assert is_valid is False
        assert any(i.rule_id == "XSD-001" for i in issues)

    def test_malformed_string(self, mock_schema_dir: Path):
        sv = SchemaValidator(mock_schema_dir)
        is_valid, issues = sv.validate_string(MALFORMED_XML)
        assert is_valid is False
        assert issues[0].rule_id == "XSD-000"


# ---------------------------------------------------------------------------
# Tests: _syntax_issue
# ---------------------------------------------------------------------------


class TestSyntaxIssue:
    def test_returns_xsd_000(self):
        try:
            etree.fromstring(b"<bad><<<>>>")
        except etree.XMLSyntaxError as exc:
            issue = SchemaValidator._syntax_issue(exc)
            assert issue.rule_id == "XSD-000"
            assert issue.severity == Severity.ERROR
            assert issue.phase == ValidationPhase.SCHEMA
            assert "Malformed XML" in issue.message
