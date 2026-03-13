"""Data models for BPMN validation results."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationPhase(Enum):
    SCHEMA = "schema"
    SEMANTIC = "semantic"


@dataclass
class ValidationIssue:
    rule_id: str
    severity: Severity
    message: str
    phase: ValidationPhase
    element_id: str | None = None
    element_type: str | None = None
    line: int | None = None
    column: int | None = None
    spec_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "phase": self.phase.value,
        }
        if self.element_id:
            d["element_id"] = self.element_id
        if self.element_type:
            d["element_type"] = self.element_type
        if self.line is not None:
            d["line"] = self.line
        if self.column is not None:
            d["column"] = self.column
        if self.spec_reference:
            d["spec_reference"] = self.spec_reference
        return d


@dataclass
class ValidationResult:
    file_path: str
    is_valid: bool = True
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    infos: list[ValidationIssue] = field(default_factory=list)
    schema_valid: bool | None = None
    semantic_valid: bool | None = None

    @property
    def all_issues(self) -> list[ValidationIssue]:
        return self.errors + self.warnings + self.infos

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "is_valid": self.is_valid,
            "schema_valid": self.schema_valid,
            "semantic_valid": self.semantic_valid,
            "summary": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "infos": len(self.infos),
            },
            "issues": [i.to_dict() for i in self.all_issues],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_text(self) -> str:
        lines = [f"=== {self.file_path} ==="]
        if self.is_valid:
            lines.append("VALID")
        else:
            lines.append("INVALID")

        lines.append(
            f"  {len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s), "
            f"{len(self.infos)} info(s)"
        )

        for issue in self.all_issues:
            severity_tag = issue.severity.value.upper()
            loc = ""
            if issue.line is not None:
                loc = f" (line {issue.line})"
            element = ""
            if issue.element_id:
                element = f" [{issue.element_id}]"
            lines.append(f"  [{severity_tag}] {issue.rule_id}{element}{loc}: {issue.message}")

        return "\n".join(lines)
