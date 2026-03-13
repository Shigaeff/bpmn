"""Semantic validation rules for BPMN 2.0.2.

Importing this package auto-registers all rule classes via the
``@registry.register`` decorator used in each sub-module.
"""

from .base import SemanticRule, RuleRegistry, registry  # noqa: F401

__all__ = ["SemanticRule", "RuleRegistry", "registry"]

# Import every rule module so that @registry.register decorators fire.
from . import (  # noqa: F401
    process_structure,
    gateways,
    sequence_flows,
    message_flows,
    data,
    events,
    tasks,
    collaboration,
    best_practices,
)
