"""Tests for the SemanticValidator orchestrator."""

from __future__ import annotations

import logging


from bpmn_validator.semantic_validator import SemanticValidator
from bpmn_validator.models import Severity
from tests.conftest import make_bpmn_xml, parse_bpmn


class TestSemanticValidator:
    """Core orchestration tests."""

    def test_basic_validation(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        model = parse_bpmn(xml)
        sv = SemanticValidator()
        issues = sv.validate(model)
        # Should run without errors — no assertions on issue count since
        # warnings/infos from best-practice rules may appear.
        assert isinstance(issues, list)

    def test_exclude_rules(self):
        xml = make_bpmn_xml(
            process_body="""
            <endEvent id="E1"/>
        """
        )
        model = parse_bpmn(xml)

        # Without exclude → should include PROC-001
        sv = SemanticValidator()
        issues = sv.validate(model)
        assert any(i.rule_id == "PROC-001" for i in issues)

        # With exclude → PROC-001 should be absent
        sv2 = SemanticValidator(exclude_rules={"PROC-001"})
        issues2 = sv2.validate(model)
        assert not any(i.rule_id == "PROC-001" for i in issues2)

    def test_severity_filter(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        model = parse_bpmn(xml)

        sv = SemanticValidator(severity_filter=Severity.ERROR)
        issues = sv.validate(model)
        # Only ERROR-severity rules should have run
        for issue in issues:
            assert issue.severity == Severity.ERROR

    def test_unknown_excluded_rule_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="bpmn_validator.semantic_validator"):
            SemanticValidator(exclude_rules={"FAKE-999"})
        assert "FAKE-999" in caplog.text
        assert "does not match" in caplog.text

    def test_rule_exception_handled(self, monkeypatch):
        """If a rule's check() raises, the validator logs and returns an error issue."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        model = parse_bpmn(xml)

        from bpmn_validator.rules import registry

        # Temporarily inject a broken rule
        class _BrokenRule:
            rule_id = "__BROKEN__"
            severity = Severity.ERROR
            description = "I always crash"
            spec_reference = ""

            def check(self, model):
                raise RuntimeError("boom")

        original_rules = registry._rules[:]
        registry._rules.append(_BrokenRule)
        try:
            sv = SemanticValidator()
            issues = sv.validate(model)
            broken = [i for i in issues if i.rule_id == "__BROKEN__"]
            assert len(broken) == 1
            assert "Internal error" in broken[0].message
            assert "boom" in broken[0].message
        finally:
            registry._rules = original_rules
