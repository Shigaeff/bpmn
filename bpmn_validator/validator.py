"""Main validation facade — combines schema and semantic validation."""

from __future__ import annotations

from pathlib import Path

from .models import Severity, ValidationIssue, ValidationResult
from .parser import BPMNParser
from .schema_validator import SchemaValidator
from .semantic_validator import SemanticValidator


class BPMNValidator:
    """High-level validator that runs XSD schema + semantic checks."""

    def __init__(
        self,
        specs_dir: str | Path = "specs",
        *,
        skip_schema: bool = False,
        skip_semantic: bool = False,
        exclude_rules: set[str] | None = None,
        severity_filter: Severity | None = None,
    ) -> None:
        self._specs_dir = Path(specs_dir)
        self._skip_schema = skip_schema
        self._skip_semantic = skip_semantic
        self._exclude_rules = exclude_rules or set()
        self._severity_filter = severity_filter

        self._schema_validator: SchemaValidator | None = None
        if not skip_schema and self._specs_dir.exists():
            xsd_path = self._specs_dir / "BPMN20.xsd"
            if xsd_path.exists():
                self._schema_validator = SchemaValidator(self._specs_dir)

        self._semantic_validator = SemanticValidator(
            exclude_rules=self._exclude_rules,
            severity_filter=self._severity_filter,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, bpmn_path: str | Path) -> ValidationResult:
        """Validate a BPMN file (path) and return a *ValidationResult*."""
        bpmn_path = Path(bpmn_path)
        if not bpmn_path.exists():
            raise FileNotFoundError(f"BPMN file not found: {bpmn_path}")
        if not bpmn_path.is_file():
            raise ValueError(f"Path is not a file: {bpmn_path}")
        try:
            xml_content = bpmn_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"File is not valid UTF-8 text (binary file?): {bpmn_path}") from exc
        return self._run(xml_content, file_path=str(bpmn_path))

    def validate_string(self, xml_content: str, *, file_path: str = "<string>") -> ValidationResult:
        """Validate BPMN XML given as a string."""
        return self._run(xml_content, file_path=file_path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self, xml_content: str, *, file_path: str) -> ValidationResult:
        all_issues: list[ValidationIssue] = []
        schema_valid: bool | None = None
        semantic_valid: bool | None = None

        # --- Phase 1: XSD Schema validation ---
        if not self._skip_schema and self._schema_validator is not None:
            _valid, schema_issues = self._schema_validator.validate_string(xml_content)
            all_issues.extend(schema_issues)
            schema_valid = _valid

        # --- Phase 2: Semantic validation ---
        if not self._skip_semantic:
            parser = BPMNParser()
            model = parser.parse(xml_content)
            semantic_issues = self._semantic_validator.validate(model)
            all_issues.extend(semantic_issues)
            semantic_valid = not any(i.severity == Severity.ERROR for i in semantic_issues)

        # --- Build result ---
        errors = [i for i in all_issues if i.severity == Severity.ERROR]
        warnings = [i for i in all_issues if i.severity == Severity.WARNING]
        infos = [i for i in all_issues if i.severity == Severity.INFO]

        return ValidationResult(
            file_path=file_path,
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            infos=infos,
            schema_valid=schema_valid,
            semantic_valid=semantic_valid,
        )
