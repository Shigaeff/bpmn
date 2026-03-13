"""BPMN XML parser — converts XML into an internal model for semantic validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

# Maximum file size we accept for parsing (50 MB).
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024

# Secure XML parser — defends against XXE, billion-laughs, and network access.
SAFE_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    huge_tree=False,
    recover=False,
)

# BPMN 2.0 namespaces
NS_BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
NS_BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
NS_DC = "http://www.omg.org/spec/DD/20100524/DC"
NS_DI = "http://www.omg.org/spec/DD/20100524/DI"

NSMAP = {
    "bpmn": NS_BPMN,
    "bpmndi": NS_BPMNDI,
    "dc": NS_DC,
    "di": NS_DI,
}

# Tags that are sequence flow nodes (not artifacts or data)
FLOW_NODE_TAGS = {
    "task",
    "sendTask",
    "receiveTask",
    "serviceTask",
    "userTask",
    "manualTask",
    "businessRuleTask",
    "scriptTask",
    "subProcess",
    "adHocSubProcess",
    "transaction",
    "callActivity",
    "startEvent",
    "endEvent",
    "intermediateCatchEvent",
    "intermediateThrowEvent",
    "boundaryEvent",
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
    "complexGateway",
}

GATEWAY_TAGS = {
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
    "complexGateway",
}

TASK_TAGS = {
    "task",
    "sendTask",
    "receiveTask",
    "serviceTask",
    "userTask",
    "manualTask",
    "businessRuleTask",
    "scriptTask",
}

SUBPROCESS_TAGS = {"subProcess", "adHocSubProcess", "transaction"}

EVENT_TAGS = {
    "startEvent",
    "endEvent",
    "intermediateCatchEvent",
    "intermediateThrowEvent",
    "boundaryEvent",
}


def _local_tag(elem: etree._Element) -> str:
    """Get the local tag name stripping namespace."""
    tag = elem.tag
    if isinstance(tag, str) and "}" in tag:
        return tag.split("}", 1)[1]
    return str(tag)


def _bpmn_tag(local: str) -> str:
    """Build a fully qualified BPMN tag."""
    return f"{{{NS_BPMN}}}{local}"


def _srcline(elem: etree._Element) -> int | None:
    """Get sourceline as ``int | None`` (lxml stubs type it as Ellipsis-able)."""
    line = elem.sourceline
    return int(line) if isinstance(line, int) else None


@dataclass
class BPMNElement:
    id: str | None
    name: str | None
    tag: str
    attrib: dict[str, str]
    line: int | None
    children_ids: list[str] = field(default_factory=list)
    parent_id: str | None = None


@dataclass
class SequenceFlow:
    id: str
    source_ref: str
    target_ref: str
    condition_expression: str | None = None
    name: str | None = None
    line: int | None = None


@dataclass
class MessageFlow:
    id: str
    source_ref: str
    target_ref: str
    name: str | None = None
    line: int | None = None


@dataclass
class BPMNProcess:
    id: str
    name: str | None
    is_executable: bool
    elements: dict[str, BPMNElement] = field(default_factory=dict)
    sequence_flows: dict[str, SequenceFlow] = field(default_factory=dict)
    start_events: list[str] = field(default_factory=list)
    end_events: list[str] = field(default_factory=list)
    gateways: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    sub_processes: list[str] = field(default_factory=list)
    boundary_events: list[str] = field(default_factory=list)
    intermediate_catch_events: list[str] = field(default_factory=list)
    intermediate_throw_events: list[str] = field(default_factory=list)
    line: int | None = None


@dataclass
class BPMNCollaboration:
    id: str
    participants: dict[str, dict[str, str | None]] = field(default_factory=dict)
    message_flows: dict[str, MessageFlow] = field(default_factory=dict)


@dataclass
class BPMNDefinitions:
    """Top-level parsed model representing a <definitions> document."""

    target_namespace: str | None
    processes: dict[str, BPMNProcess] = field(default_factory=dict)
    collaborations: dict[str, BPMNCollaboration] = field(default_factory=dict)
    all_elements: dict[str, BPMNElement] = field(default_factory=dict)
    root: etree._Element | None = field(default=None, repr=False)


class BPMNParser:
    """Parses BPMN XML into BPMNDefinitions model."""

    def parse(
        self,
        source: str | Path | bytes,
        *,
        max_size: int = MAX_FILE_SIZE_BYTES,
    ) -> BPMNDefinitions:
        """Parse BPMN XML from file path, string, or bytes.

        Uses a hardened XML parser that blocks XXE, entity expansion,
        network access, and files exceeding *max_size* bytes.
        """
        if isinstance(source, (str, Path)) and Path(source).exists():
            path = Path(source)
            file_size = path.stat().st_size
            if file_size == 0:
                raise ValueError(f"File is empty: {path}")
            if file_size > max_size:
                raise ValueError(
                    f"File too large ({file_size:,} bytes, limit {max_size:,}): {path}"
                )
            try:
                tree = etree.parse(str(path), parser=SAFE_PARSER)
            except etree.XMLSyntaxError as exc:
                raise ValueError(f"Malformed XML in {path}: {exc}") from exc
            root = tree.getroot()
        elif isinstance(source, bytes):
            if len(source) > max_size:
                raise ValueError(
                    f"XML content too large ({len(source):,} bytes, limit {max_size:,})"
                )
            try:
                root = etree.fromstring(source, parser=SAFE_PARSER)
            except etree.XMLSyntaxError as exc:
                raise ValueError(f"Malformed XML: {exc}") from exc
        elif isinstance(source, str):
            encoded = source.encode("utf-8")
            if len(encoded) > max_size:
                raise ValueError(
                    f"XML content too large ({len(encoded):,} bytes, limit {max_size:,})"
                )
            try:
                root = etree.fromstring(encoded, parser=SAFE_PARSER)
            except etree.XMLSyntaxError as exc:
                raise ValueError(f"Malformed XML: {exc}") from exc
        else:
            raise ValueError(f"Cannot parse source: {type(source)}")

        definitions = BPMNDefinitions(
            target_namespace=root.get("targetNamespace"),
            root=root,
        )

        # Parse collaborations
        for collab_elem in root.findall(_bpmn_tag("collaboration")):
            collab = self._parse_collaboration(collab_elem)
            definitions.collaborations[collab.id] = collab

        # Parse processes
        for proc_elem in root.findall(_bpmn_tag("process")):
            proc = self._parse_process(proc_elem)
            definitions.processes[proc.id] = proc
            definitions.all_elements.update(proc.elements)

        return definitions

    def _parse_collaboration(self, elem: etree._Element) -> BPMNCollaboration:
        collab_id = elem.get("id", "")
        collab = BPMNCollaboration(id=collab_id)

        for part in elem.findall(_bpmn_tag("participant")):
            pid = part.get("id", "")
            collab.participants[pid] = {
                "name": part.get("name"),
                "processRef": part.get("processRef"),
            }

        for mf in elem.findall(_bpmn_tag("messageFlow")):
            mf_id = mf.get("id", "")
            collab.message_flows[mf_id] = MessageFlow(
                id=mf_id,
                source_ref=mf.get("sourceRef", ""),
                target_ref=mf.get("targetRef", ""),
                name=mf.get("name"),
                line=_srcline(mf),
            )

        return collab

    def _parse_process(self, proc_elem: etree._Element) -> BPMNProcess:
        proc = BPMNProcess(
            id=proc_elem.get("id", ""),
            name=proc_elem.get("name"),
            is_executable=proc_elem.get("isExecutable", "false").lower() == "true",
            line=_srcline(proc_elem),
        )

        self._collect_elements(proc_elem, proc, parent_id=None)
        return proc

    def _collect_elements(
        self,
        container: etree._Element,
        proc: BPMNProcess,
        parent_id: str | None,
    ) -> None:
        """Recursively collect flow elements from a process or subprocess."""
        for child in container:
            tag = _local_tag(child)
            eid = child.get("id")

            if tag == "sequenceFlow":
                if eid:
                    cond_elem = child.find(_bpmn_tag("conditionExpression"))
                    cond_text = None
                    if cond_elem is not None and cond_elem.text:
                        cond_text = cond_elem.text.strip()
                    proc.sequence_flows[eid] = SequenceFlow(
                        id=eid,
                        source_ref=child.get("sourceRef", ""),
                        target_ref=child.get("targetRef", ""),
                        condition_expression=cond_text,
                        name=child.get("name"),
                        line=_srcline(child),
                    )
                continue

            if tag not in FLOW_NODE_TAGS and tag not in (
                "dataObject",
                "dataObjectReference",
                "dataStoreReference",
                "textAnnotation",
                "association",
                "group",
                "laneSet",
                "lane",
            ):
                continue

            elem = BPMNElement(
                id=eid,
                name=child.get("name"),
                tag=tag,
                attrib={str(k): str(v) for k, v in child.attrib.items()},
                line=_srcline(child),
                parent_id=parent_id,
            )

            if eid:
                proc.elements[eid] = elem

                if tag == "startEvent":
                    proc.start_events.append(eid)
                elif tag == "endEvent":
                    proc.end_events.append(eid)
                elif tag in GATEWAY_TAGS:
                    proc.gateways.append(eid)
                elif tag in TASK_TAGS:
                    proc.tasks.append(eid)
                elif tag in SUBPROCESS_TAGS:
                    proc.sub_processes.append(eid)
                    # Recurse into subprocess
                    self._collect_elements(child, proc, parent_id=eid)
                elif tag == "boundaryEvent":
                    proc.boundary_events.append(eid)
                elif tag == "intermediateCatchEvent":
                    proc.intermediate_catch_events.append(eid)
                elif tag == "intermediateThrowEvent":
                    proc.intermediate_throw_events.append(eid)
                elif tag == "callActivity":
                    proc.tasks.append(eid)

                if parent_id and parent_id in proc.elements:
                    proc.elements[parent_id].children_ids.append(eid)
