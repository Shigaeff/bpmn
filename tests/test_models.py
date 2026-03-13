"""Tests for data models (models.py)."""

import json

from bpmn_validator.models import (
    Severity,
    ValidationIssue,
    ValidationPhase,
    ValidationResult,
)


class TestValidationIssue:
    def test_to_dict_minimal(self):
        issue = ValidationIssue(
            rule_id="X-001",
            severity=Severity.ERROR,
            message="problem",
            phase=ValidationPhase.SCHEMA,
        )
        d = issue.to_dict()
        assert d["rule_id"] == "X-001"
        assert d["severity"] == "error"
        assert d["phase"] == "schema"
        assert "element_id" not in d
        assert "line" not in d

    def test_to_dict_full(self):
        issue = ValidationIssue(
            rule_id="Y-002",
            severity=Severity.WARNING,
            message="warn",
            phase=ValidationPhase.SEMANTIC,
            element_id="T1",
            element_type="task",
            line=42,
            column=10,
            spec_reference="§10.3",
        )
        d = issue.to_dict()
        assert d["element_id"] == "T1"
        assert d["element_type"] == "task"
        assert d["line"] == 42
        assert d["column"] == 10
        assert d["spec_reference"] == "§10.3"


class TestValidationResult:
    def _make_result(self, *, errors=0, warnings=0, infos=0) -> ValidationResult:
        def _issue(sev):
            return ValidationIssue(
                rule_id="T-001",
                severity=sev,
                message="msg",
                phase=ValidationPhase.SEMANTIC,
            )

        return ValidationResult(
            file_path="test.bpmn",
            is_valid=errors == 0,
            errors=[_issue(Severity.ERROR) for _ in range(errors)],
            warnings=[_issue(Severity.WARNING) for _ in range(warnings)],
            infos=[_issue(Severity.INFO) for _ in range(infos)],
            schema_valid=True,
            semantic_valid=errors == 0,
        )

    def test_all_issues_combined(self):
        r = self._make_result(errors=1, warnings=2, infos=3)
        assert len(r.all_issues) == 6

    def test_to_dict(self):
        r = self._make_result(errors=1, warnings=1, infos=1)
        d = r.to_dict()
        assert d["file_path"] == "test.bpmn"
        assert d["is_valid"] is False
        assert d["schema_valid"] is True
        assert d["semantic_valid"] is False
        assert d["summary"]["errors"] == 1
        assert d["summary"]["warnings"] == 1
        assert d["summary"]["infos"] == 1
        assert len(d["issues"]) == 3

    def test_to_json(self):
        r = self._make_result(errors=0, warnings=1)
        j = r.to_json()
        data = json.loads(j)
        assert data["is_valid"] is True

    def test_to_text_valid(self):
        r = self._make_result()
        text = r.to_text()
        assert "VALID" in text
        assert "0 error" in text

    def test_to_text_invalid_with_details(self):
        r = ValidationResult(
            file_path="bad.bpmn",
            is_valid=False,
            errors=[
                ValidationIssue(
                    rule_id="P-001",
                    severity=Severity.ERROR,
                    message="no start",
                    phase=ValidationPhase.SEMANTIC,
                    element_id="proc1",
                    line=5,
                ),
            ],
        )
        text = r.to_text()
        assert "INVALID" in text
        assert "[ERROR]" in text
        assert "P-001" in text
        assert "[proc1]" in text
        assert "(line 5)" in text
