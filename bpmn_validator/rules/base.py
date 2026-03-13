"""Base class and registry for semantic validation rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ..models import Severity, ValidationIssue, ValidationPhase

# TYPE_CHECKING import to avoid circular dependency
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parser import BPMNDefinitions


class SemanticRule(ABC):
    """Abstract base class for all semantic validation rules."""

    rule_id: ClassVar[str]
    description: ClassVar[str]
    severity: ClassVar[Severity]
    spec_reference: ClassVar[str] = ""

    @abstractmethod
    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        """Run this rule against a parsed BPMN model. Return issues found."""
        ...

    def _make_issue(
        self,
        message: str,
        element_id: str | None = None,
        element_type: str | None = None,
        line: int | None = None,
        severity: Severity | None = None,
    ) -> ValidationIssue:
        return ValidationIssue(
            rule_id=self.rule_id,
            severity=severity or self.severity,
            message=message,
            phase=ValidationPhase.SEMANTIC,
            element_id=element_id,
            element_type=element_type,
            line=line,
            spec_reference=self.spec_reference or None,
        )


class RuleRegistry:
    """Registry of all semantic rules."""

    def __init__(self) -> None:
        self._rules: list[type[SemanticRule]] = []

    def register(self, rule_cls: type[SemanticRule]) -> type[SemanticRule]:
        """Decorator to register a rule class."""
        if any(c.rule_id == rule_cls.rule_id for c in self._rules):
            raise ValueError(
                f"Duplicate rule_id '{rule_cls.rule_id}' — "
                f"already registered by {next(c.__name__ for c in self._rules if c.rule_id == rule_cls.rule_id)}"
            )
        self._rules.append(rule_cls)
        return rule_cls

    def get_all(self) -> list[SemanticRule]:
        """Instantiate and return all registered rules."""
        return [cls() for cls in self._rules]

    def get_by_severity(self, severity: Severity) -> list[SemanticRule]:
        return [cls() for cls in self._rules if cls.severity == severity]

    def get_by_id(self, rule_id: str) -> SemanticRule | None:
        for cls in self._rules:
            if cls.rule_id == rule_id:
                return cls()
        return None


# Global registry instance
registry = RuleRegistry()
