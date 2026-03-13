"""Tests for best practice rules (BP-001..004)."""

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.rules.best_practices import (
    UnnamedElements,
    EmptyPools,
    OverlyComplexProcess,
    MissingDocumentation,
)


class TestBP001:
    def test_unnamed_task(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = UnnamedElements().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "T1" in issues[0].message

    def test_named_task(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1" name="My Task"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = UnnamedElements().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestBP002:
    def test_empty_pool(self):
        xml = make_bpmn_xml(
            collaboration="""
            <collaboration id="C1">
              <participant id="P1" name="Empty Pool"/>
            </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            """,
        )
        issues = EmptyPools().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "Empty Pool" in issues[0].message


class TestBP003:
    def test_simple_process_ok(self):
        """A process with few elements should not be flagged."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <task id="T1" name="Work"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        issues = OverlyComplexProcess().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_overly_complex_process(self):
        """A process exceeding MAX_ELEMENTS should be flagged."""
        # Generate 51 tasks + start + end = 53 flow nodes (above threshold of 50)
        tasks = "\n".join(f'            <task id="T{i}" name="Task {i}"/>' for i in range(51))
        flows_to_tasks = "\n".join(
            f'            <sequenceFlow id="F_to_{i}" sourceRef="S1" targetRef="T{i}"/>'
            for i in range(51)
        )
        flows_from_tasks = "\n".join(
            f'            <sequenceFlow id="F_from_{i}" sourceRef="T{i}" targetRef="E1"/>'
            for i in range(51)
        )

        xml = make_bpmn_xml(
            process_body=f"""
            <startEvent id="S1"/>
            {tasks}
            <endEvent id="E1"/>
            {flows_to_tasks}
            {flows_from_tasks}
        """
        )
        issues = OverlyComplexProcess().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "BP-003"
        assert "threshold" in issues[0].message.lower()


class TestBP004:
    def test_no_documentation(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
        """
        )
        issues = MissingDocumentation().check(parse_bpmn(xml))
        assert len(issues) == 1

    def test_with_documentation(self):
        xml = make_bpmn_xml(
            process_body="""
                <documentation>This process does things.</documentation>
                <startEvent id="S1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            """,
        )
        issues = MissingDocumentation().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestBP002NonexistentProcessRef:
    def test_participant_references_nonexistent_process(self):
        """Participant with processRef pointing to a process not in the model."""
        xml = make_bpmn_xml(
            collaboration="""
            <collaboration id="C1">
              <participant id="P1" name="Pool A" processRef="Process_1"/>
              <participant id="P2" name="Pool B" processRef="NONEXISTENT"/>
            </collaboration>
            """,
            process_body="""
                <startEvent id="S1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="E1"/>
            """,
        )
        issues = EmptyPools().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "non-existent" in issues[0].message.lower() or "NONEXISTENT" in issues[0].message
