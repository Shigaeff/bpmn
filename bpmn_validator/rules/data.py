"""Data validation rules (DATA-001 through DATA-002)."""

from __future__ import annotations

from ..models import Severity, ValidationIssue
from ..parser import BPMNDefinitions, _bpmn_tag, _srcline
from .base import SemanticRule, registry


@registry.register
class DataAssociationReferences(SemanticRule):
    rule_id = "DATA-001"
    description = "Data associations must reference valid data objects"
    severity = Severity.ERROR
    spec_reference = "Section 10.3.2"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        data_ids: set[str] = set()

        # Collect all data object/store IDs
        for proc in model.processes.values():
            for eid, elem in proc.elements.items():
                if elem.tag in ("dataObject", "dataObjectReference", "dataStoreReference"):
                    data_ids.add(eid)

        # Check dataInputAssociation and dataOutputAssociation elements
        if model.root is not None:
            for assoc_tag in ("dataInputAssociation", "dataOutputAssociation"):
                for assoc in model.root.iter(_bpmn_tag(assoc_tag)):
                    source_refs = assoc.findall(_bpmn_tag("sourceRef"))
                    target_refs = assoc.findall(_bpmn_tag("targetRef"))
                    for ref_elem in source_refs + target_refs:
                        if ref_elem.text and ref_elem.text.strip():
                            ref_id = ref_elem.text.strip()
                            if ref_id not in data_ids and ref_id not in model.all_elements:
                                issues.append(
                                    self._make_issue(
                                        message=(
                                            f"Data association references unknown element '{ref_id}'"
                                        ),
                                        element_id=assoc.get("id"),
                                        element_type=assoc_tag,
                                        line=_srcline(assoc),
                                    )
                                )
        return issues


@registry.register
class DataStoreAccessible(SemanticRule):
    rule_id = "DATA-002"
    description = "Data store references must point to accessible data stores"
    severity = Severity.WARNING
    spec_reference = "Section 10.2.1"

    def check(self, model: BPMNDefinitions) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if model.root is None:
            return issues

        # Collect dataStore definitions at definitions level
        data_store_ids: set[str] = set()
        for ds in model.root.findall(_bpmn_tag("dataStore")):
            ds_id = ds.get("id")
            if ds_id:
                data_store_ids.add(ds_id)

        # Check dataStoreReference elements reference existing dataStores
        for proc in model.processes.values():
            for eid, elem in proc.elements.items():
                if elem.tag == "dataStoreReference":
                    ds_ref = elem.attrib.get("dataStoreRef")
                    if ds_ref and ds_ref not in data_store_ids:
                        issues.append(
                            self._make_issue(
                                message=(
                                    f"Data store reference '{elem.name or eid}' points to "
                                    f"unknown data store '{ds_ref}'"
                                ),
                                element_id=eid,
                                element_type="dataStoreReference",
                                line=elem.line,
                            )
                        )
        return issues
