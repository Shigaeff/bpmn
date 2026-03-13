"""Semantic validation orchestrator.

Runs all registered semantic rules against a parsed BPMN model.
"""

from __future__ import annotations

import logging

from .models import Severity, ValidationIssue, ValidationPhase
from .parser import BPMNDefinitions
from .rules import registry

logger = logging.getLogger(__name__)


class SemanticValidator:
    """Orchestrates semantic validation rules against a BPMN model."""

    def __init__(
        self,
        *,
        exclude_rules: set[str] | None = None,
        severity_filter: Severity | None = None,
    ) -> None:
        self._exclude_rules = exclude_rules or set()
        self._severity_filter = severity_filter
        self._validate_excluded_rules()

    def _validate_excluded_rules(self) -> None:
        """Warn about excluded rule IDs that don't match any registered rule."""
        if not self._exclude_rules:
            return
        known_ids = {r.rule_id for r in registry.get_all()}
        unknown = self._exclude_rules - known_ids
        for rule_id in sorted(unknown):
            logger.warning(
                "Excluded rule '%s' does not match any registered rule. Known rules: %s",
                rule_id,
                ", ".join(sorted(known_ids)),
            )

    def validate(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        """Run all applicable rules and return the collected issues."""
        issues: list[ValidationIssue] = []

        for rule in registry.get_all():
            if rule.rule_id in self._exclude_rules:
                continue
            if self._severity_filter and rule.severity != self._severity_filter:
                continue

            try:
                rule_issues = rule.check(model)
                issues.extend(rule_issues)
            except Exception as exc:
                logger.exception(
                    "Rule %s (%s) raised an unexpected error: %s",
                    rule.rule_id,
                    type(rule).__name__,
                    exc,
                )
                issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=Severity.ERROR,
                        message=f"Internal error in rule {rule.rule_id}: {exc}",
                        phase=ValidationPhase.SEMANTIC,
                    )
                )

        return issues
