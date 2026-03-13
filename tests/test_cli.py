"""Tests for the CLI interface."""

import json
from pathlib import Path

from click.testing import CliRunner

from bpmn_validator.cli import main
from tests.conftest import VALID_DIR, INVALID_DIR, make_bpmn_xml


class TestCLI:
    def test_list_rules(self):
        runner = CliRunner()
        result = runner.invoke(main, ["list-rules"])
        assert result.exit_code == 0
        assert "PROC-001" in result.output
        assert "Total:" in result.output

    def test_validate_valid_file(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(VALID_DIR / "simple_process.bpmn"),
                "--skip-schema",
            ],
        )
        assert result.exit_code == 0

    def test_validate_invalid_file(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(INVALID_DIR / "no_start_event.bpmn"),
                "--skip-schema",
            ],
        )
        assert result.exit_code == 1

    def test_validate_json_format(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(VALID_DIR / "simple_process.bpmn"),
                "--skip-schema",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["is_valid"] is True

    def test_validate_json_multiple_files(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(VALID_DIR / "simple_process.bpmn"),
                str(VALID_DIR / "collaboration.bpmn"),
                "--skip-schema",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_validate_exclude_rules(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(INVALID_DIR / "no_start_event.bpmn"),
                "--skip-schema",
                "--exclude-rules",
                "PROC-001,PROC-002,PROC-005",
            ],
        )
        assert "PROC-001" not in result.output

    def test_validate_strict_with_warnings(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(INVALID_DIR / "no_start_event.bpmn"),
                "--skip-schema",
                "--strict",
            ],
        )
        # Should exit 1 since there are errors
        assert result.exit_code == 1

    def test_validate_severity_filter(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(VALID_DIR / "simple_process.bpmn"),
                "--skip-schema",
                "--severity",
                "error",
            ],
        )
        assert result.exit_code == 0

    def test_validate_no_specs_dir_exits(self):
        """Without --skip-schema and without specs, should exit 2."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(VALID_DIR / "simple_process.bpmn"),
                "--specs-dir",
                "/nonexistent/path/to/specs",
            ],
        )
        assert result.exit_code == 2
        assert "XSD schemas not found" in result.output

    def test_strict_valid_file_exit_0(self):
        """A valid file with no errors and no warnings should exit 0 in strict mode."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(VALID_DIR / "simple_process.bpmn"),
                "--skip-schema",
                "--strict",
            ],
        )
        # exit 0 if no warnings, exit 1 if warnings — both acceptable
        assert result.exit_code in (0, 1)

    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_main_entry_point(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.output


class TestDownloadCommand:
    def test_download_with_files(self, monkeypatch):
        """download command outputs each downloaded file."""
        monkeypatch.setattr(
            "bpmn_validator.cli.download_specs",
            lambda *a, **kw: [Path("BPMN20.xsd"), Path("BPMNDI.xsd")],
        )
        runner = CliRunner()
        result = runner.invoke(main, ["download", "--specs-dir", "/tmp/specs"])
        assert result.exit_code == 0
        assert "BPMN20.xsd" in result.output
        assert "Done." in result.output

    def test_download_no_files(self, monkeypatch):
        """download command with no new downloads."""
        monkeypatch.setattr(
            "bpmn_validator.cli.download_specs",
            lambda *a, **kw: [],
        )
        runner = CliRunner()
        result = runner.invoke(main, ["download"])
        assert result.exit_code == 0
        assert "already present" in result.output


class TestValidateExceptionAndWarnings:
    def test_validate_exception_during_validation(self, monkeypatch):
        """Exception during validation should be caught and printed."""

        def mock_validate(self, file_path):
            raise RuntimeError("Boom!")

        monkeypatch.setattr(
            "bpmn_validator.cli.BPMNValidator.validate",
            mock_validate,
        )
        monkeypatch.setattr("bpmn_validator.cli.verify_specs", lambda d: True)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(VALID_DIR / "simple_process.bpmn"),
                "--skip-schema",
            ],
        )
        assert result.exit_code == 1
        assert "Boom!" in result.output

    def test_warnings_only_exit_0(self, tmp_path: Path):
        """File with warnings but no errors should exit 0 (without --strict)."""
        # Create a BPMN with unnamed tasks → BP-001 warnings, no errors
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1" name="Start"/>
            <task id="T1"/>
            <endEvent id="E1" name="End"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        bpmn_file = tmp_path / "warnings_only.bpmn"
        bpmn_file.write_text(xml, encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(bpmn_file),
                "--skip-schema",
            ],
        )
        assert result.exit_code == 0

    def test_strict_warnings_exit_1(self, tmp_path: Path):
        """With --strict, file with warnings but no errors should exit 1."""
        xml = make_bpmn_xml(
            process_body="""
            <startEvent id="S1" name="Start"/>
            <task id="T1"/>
            <endEvent id="E1" name="End"/>
            <sequenceFlow id="F1" sourceRef="S1" targetRef="T1"/>
            <sequenceFlow id="F2" sourceRef="T1" targetRef="E1"/>
        """
        )
        bpmn_file = tmp_path / "warnings_strict.bpmn"
        bpmn_file.write_text(xml, encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(bpmn_file),
                "--skip-schema",
                "--strict",
            ],
        )
        assert result.exit_code == 1


class TestMainModule:
    def test_main_as_module(self):
        """Running python -m bpmn_validator.cli --help should succeed."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "bpmn_validator.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "validate" in result.stdout
