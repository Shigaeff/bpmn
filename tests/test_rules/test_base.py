"""Tests for rule registry (base.py)."""

import pytest

from bpmn_validator.models import Severity
from bpmn_validator.rules import registry
from bpmn_validator.rules.base import RuleRegistry, SemanticRule


class TestRuleRegistry:
    def test_get_all_returns_instances(self):
        rules = registry.get_all()
        assert len(rules) > 0
        for rule in rules:
            assert hasattr(rule, "rule_id")
            assert hasattr(rule, "check")

    def test_get_by_severity_error(self):
        error_rules = registry.get_by_severity(Severity.ERROR)
        for rule in error_rules:
            assert rule.severity == Severity.ERROR
        assert len(error_rules) > 0

    def test_get_by_severity_warning(self):
        warn_rules = registry.get_by_severity(Severity.WARNING)
        for rule in warn_rules:
            assert rule.severity == Severity.WARNING

    def test_get_by_severity_info(self):
        info_rules = registry.get_by_severity(Severity.INFO)
        for rule in info_rules:
            assert rule.severity == Severity.INFO

    def test_get_by_id_found(self):
        rule = registry.get_by_id("PROC-001")
        assert rule is not None
        assert rule.rule_id == "PROC-001"

    def test_get_by_id_not_found(self):
        rule = registry.get_by_id("NONEXISTENT-999")
        assert rule is None

    def test_duplicate_registration_raises(self):
        """Registering two rules with the same rule_id should raise ValueError."""
        reg = RuleRegistry()

        class _RuleA(SemanticRule):
            rule_id = "DUP-001"
            description = "First"
            severity = Severity.ERROR

            def check(self, model):
                return []

        class _RuleB(SemanticRule):
            rule_id = "DUP-001"
            description = "Second"
            severity = Severity.WARNING

            def check(self, model):
                return []

        reg.register(_RuleA)
        with pytest.raises(ValueError, match="Duplicate rule_id 'DUP-001'"):
            reg.register(_RuleB)
