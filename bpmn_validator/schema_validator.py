"""XSD-based validation of BPMN XML files using lxml."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from .models import Severity, ValidationIssue, ValidationPhase
from .parser import SAFE_PARSER


class SchemaValidator:
    """Validates BPMN XML against the official BPMN 2.0 XSD schemas."""

    def __init__(self, schema_dir: Path) -> None:
        self._schema_dir = schema_dir
        self._schema: etree.XMLSchema | None = None

    def _load_schema(self) -> etree.XMLSchema:
        if self._schema is None:
            schema_path = self._schema_dir / "BPMN20.xsd"
            if not schema_path.exists():
                raise FileNotFoundError(
                    f"XSD schemas not found in {self._schema_dir}. "
                    "Run 'bpmn-validator download' first."
                )
            try:
                schema_doc = etree.parse(str(schema_path), parser=SAFE_PARSER)
                self._schema = etree.XMLSchema(schema_doc)
            except (etree.XMLSyntaxError, etree.XMLSchemaParseError) as exc:
                raise RuntimeError(
                    f"Corrupted or unreadable XSD schema in {self._schema_dir}: {exc}"
                ) from exc
        return self._schema

    def validate(self, xml_path: str | Path) -> tuple[bool, list[ValidationIssue]]:
        """Validate an XML file against the BPMN 2.0 XSD schema."""
        try:
            doc = etree.parse(str(xml_path), parser=SAFE_PARSER)
        except etree.XMLSyntaxError as e:
            return False, [self._syntax_issue(e)]
        return self._validate_doc(doc)

    def validate_string(self, xml_content: str | bytes) -> tuple[bool, list[ValidationIssue]]:
        """Validate XML string/bytes against the BPMN 2.0 XSD schema."""
        try:
            if isinstance(xml_content, str):
                xml_content = xml_content.encode("utf-8")
            element = etree.fromstring(xml_content, parser=SAFE_PARSER)
        except etree.XMLSyntaxError as e:
            return False, [self._syntax_issue(e)]
        return self._validate_doc(element.getroottree())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_doc(self, doc: etree._ElementTree) -> tuple[bool, list[ValidationIssue]]:
        """Run schema validation on a parsed document tree."""
        schema = self._load_schema()
        is_valid = schema.validate(doc)
        issues: list[ValidationIssue] = []
        for error in schema.error_log:  # type: ignore[attr-defined]
            issues.append(
                ValidationIssue(
                    rule_id="XSD-001",
                    severity=Severity.ERROR,
                    message=str(error.message),
                    phase=ValidationPhase.SCHEMA,
                    line=error.line,
                    column=error.column,
                )
            )
        return is_valid, issues

    @staticmethod
    def _syntax_issue(exc: etree.XMLSyntaxError) -> ValidationIssue:
        return ValidationIssue(
            rule_id="XSD-000",
            severity=Severity.ERROR,
            message=f"Malformed XML: {exc}",
            phase=ValidationPhase.SCHEMA,
            line=getattr(exc, "lineno", None),
            column=getattr(exc, "offset", None),
        )
