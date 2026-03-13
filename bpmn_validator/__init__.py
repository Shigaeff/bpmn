"""bpmn_validator — BPMN 2.0.2 validation library.

Usage::

    from bpmn_validator import BPMNValidator

    v = BPMNValidator(specs_dir="specs")
    result = v.validate("my_process.bpmn")
    print(result.to_text())
"""

from .models import Severity, ValidationIssue, ValidationPhase, ValidationResult
from .validator import BPMNValidator
from .parser import BPMNParser, BPMNDefinitions
from .schema_validator import SchemaValidator
from .semantic_validator import SemanticValidator
from .spec_downloader import download_specs, verify_specs
from .rules import registry as rule_registry

__version__ = "0.1.0"

__all__ = [
    "BPMNValidator",
    "BPMNParser",
    "BPMNDefinitions",
    "SchemaValidator",
    "SemanticValidator",
    "Severity",
    "ValidationIssue",
    "ValidationPhase",
    "ValidationResult",
    "download_specs",
    "verify_specs",
    "rule_registry",
    "__version__",
]
