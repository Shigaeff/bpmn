"""Tests for task rules (TASK-001..006)."""

from lxml import etree

from tests.conftest import make_bpmn_xml, parse_bpmn
from bpmn_validator.parser import BPMNDefinitions, BPMNProcess
from bpmn_validator.rules.tasks import (
    SendTaskMessage,
    ReceiveTaskMessage,
    ScriptTaskDefinition,
    ServiceTaskImplementation,
    CallActivityReference,
    SubProcessEvents,
)


class TestTASK001:
    def test_send_task_no_message(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <sendTask id="ST1" name="Send"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="ST1"/>
            <sequenceFlow id="F2" sourceRef="ST1" targetRef="E1"/>
        """
        )
        issues = SendTaskMessage().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "TASK-001"

    def test_send_task_with_message(self):
        xml = make_bpmn_xml(
            definitions_body='<message id="M1" name="Msg"/>',
            process_body="""
                <startEvent id="S1"/>
                <sendTask id="ST1" name="Send" messageRef="M1"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="ST1"/>
                <sequenceFlow id="F2" sourceRef="ST1" targetRef="E1"/>
            """,
        )
        issues = SendTaskMessage().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestTASK002:
    def test_receive_task_no_message(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <receiveTask id="RT1" name="Receive"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="RT1"/>
            <sequenceFlow id="F2" sourceRef="RT1" targetRef="E1"/>
        """
        )
        issues = ReceiveTaskMessage().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "TASK-002"


class TestTASK003:
    def test_script_task_no_script(self):
        """Script task with no scriptFormat and no script child should be flagged."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <scriptTask id="SCT1" name="Run Script"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SCT1"/>
            <sequenceFlow id="F2" sourceRef="SCT1" targetRef="E1"/>
        """
        )
        issues = ScriptTaskDefinition().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "TASK-003"
        assert "scriptFormat" in issues[0].message
        assert "script" in issues[0].message

    def test_script_task_with_script(self):
        """Script task with scriptFormat and script child should pass."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <scriptTask id="SCT1" name="Run Script" scriptFormat="groovy">
              <script>println("hello")</script>
            </scriptTask>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SCT1"/>
            <sequenceFlow id="F2" sourceRef="SCT1" targetRef="E1"/>
        """
        )
        issues = ScriptTaskDefinition().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_script_task_missing_format_only(self):
        """Script task with script child but no scriptFormat."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <scriptTask id="SCT1" name="Run Script">
              <script>println("hello")</script>
            </scriptTask>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SCT1"/>
            <sequenceFlow id="F2" sourceRef="SCT1" targetRef="E1"/>
        """
        )
        issues = ScriptTaskDefinition().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "scriptFormat" in issues[0].message


class TestTASK004:
    def test_service_task_no_implementation(self):
        """Service task with no implementation should be flagged."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <serviceTask id="SVT1" name="Call Service"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SVT1"/>
            <sequenceFlow id="F2" sourceRef="SVT1" targetRef="E1"/>
        """
        )
        issues = ServiceTaskImplementation().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "TASK-004"
        assert "no implementation" in issues[0].message

    def test_service_task_with_implementation(self):
        """Service task with implementation should pass."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <serviceTask id="SVT1" name="Call Service" implementation="##WebService"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SVT1"/>
            <sequenceFlow id="F2" sourceRef="SVT1" targetRef="E1"/>
        """
        )
        issues = ServiceTaskImplementation().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestTASK005:
    def test_subprocess_no_events(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <subProcess id="SP1" name="Sub">
              <task id="T1" name="Inner"/>
            </subProcess>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SP1"/>
            <sequenceFlow id="F2" sourceRef="SP1" targetRef="E1"/>
        """
        )
        issues = SubProcessEvents().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "Start Event" in issues[0].message
        assert "End Event" in issues[0].message

    def test_subprocess_with_events(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <subProcess id="SP1" name="Sub">
              <startEvent id="SP_S1"/>
              <task id="T1" name="Inner"/>
              <endEvent id="SP_E1"/>
              <sequenceFlow id="SP_F1" sourceRef="SP_S1" targetRef="T1"/>
              <sequenceFlow id="SP_F2" sourceRef="T1" targetRef="SP_E1"/>
            </subProcess>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="SP1"/>
            <sequenceFlow id="F2" sourceRef="SP1" targetRef="E1"/>
        """
        )
        issues = SubProcessEvents().check(parse_bpmn(xml))
        assert len(issues) == 0


class TestTASK006:
    def test_call_activity_no_ref(self):
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <callActivity id="CA1" name="Call"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="CA1"/>
            <sequenceFlow id="F2" sourceRef="CA1" targetRef="E1"/>
        """
        )
        issues = CallActivityReference().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert issues[0].rule_id == "TASK-006"

    def test_call_activity_valid_ref(self):
        """Call activity referencing an existing process should pass."""
        xml = make_bpmn_xml(
            definitions_body="""
                <process id="CalledProcess" isExecutable="false">
                  <startEvent id="CS1"/>
                  <endEvent id="CE1"/>
                  <sequenceFlow id="CF1" sourceRef="CS1" targetRef="CE1"/>
                </process>
            """,
            process_body="""
                <startEvent id="S1"/>
                <callActivity id="CA1" name="Call" calledElement="CalledProcess"/>
                <endEvent id="E1"/>
                <sequenceFlow id="F1" sourceRef="S1" targetRef="CA1"/>
                <sequenceFlow id="F2" sourceRef="CA1" targetRef="E1"/>
            """,
        )
        issues = CallActivityReference().check(parse_bpmn(xml))
        assert len(issues) == 0

    def test_call_activity_unknown_ref(self):
        """Call activity referencing an unknown process should produce a warning."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1"/>
            <callActivity id="CA1" name="Call" calledElement="NONEXISTENT"/>
            <endEvent id="E1"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="CA1"/>
            <sequenceFlow id="F2" sourceRef="CA1" targetRef="E1"/>
        """
        )
        issues = CallActivityReference().check(parse_bpmn(xml))
        assert len(issues) == 1
        assert "unknown" in issues[0].message.lower()


class TestGhostIDGuards:
    """Tests that task rules skip gracefully when element IDs are absent from elements dict."""

    def test_task005_ghost_subprocess(self):
        """SubProcessEvents skips ghost sub-process ID."""
        root = etree.Element("definitions")
        model = BPMNDefinitions(target_namespace=None, root=root)
        proc = BPMNProcess(id="P1", name="Test", is_executable=True)
        proc.sub_processes.append("GHOST")
        model.processes["P1"] = proc
        issues = SubProcessEvents().check(model)
        assert issues == []
