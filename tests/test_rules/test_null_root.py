"""Tests for rules that guard against model.root being None.

These rules use XPath on model.root, so they must return early when root is None.
"""

import pytest

from bpmn_validator.parser import BPMNDefinitions
from bpmn_validator.rules.best_practices import MissingDocumentation
from bpmn_validator.rules.data import DataStoreAccessible
from bpmn_validator.rules.events import (
    CompensationEventUsage,
    SignalEventDefinition,
    TimerEventDefinition,
)
from bpmn_validator.rules.tasks import ScriptTaskDefinition


@pytest.mark.parametrize(
    "rule_cls",
    [
        MissingDocumentation,
        DataStoreAccessible,
        CompensationEventUsage,
        SignalEventDefinition,
        TimerEventDefinition,
        ScriptTaskDefinition,
    ],
    ids=lambda c: c.rule_id,
)
def test_rule_returns_empty_on_null_root(rule_cls):
    """Rules that use XPath should return [] when model.root is None."""
    model = BPMNDefinitions(target_namespace=None, root=None)
    issues = rule_cls().check(model)
    assert issues == []
