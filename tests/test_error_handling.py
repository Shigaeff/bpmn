"""Error handling tests — file not found, empty, binary, oversized, encoding."""

from __future__ import annotations

import pytest

from bpmn_validator.parser import BPMNParser
from bpmn_validator.validator import BPMNValidator
from bpmn_validator.schema_validator import SchemaValidator


class TestParserFileErrors:
    """Test parser behaviour with problematic file inputs."""

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.bpmn"
        f.write_text("")
        parser = BPMNParser()
        with pytest.raises(ValueError, match="File is empty"):
            parser.parse(f)

    def test_file_too_large(self, tmp_path):
        f = tmp_path / "huge.bpmn"
        # Use a very small limit to avoid writing a real huge file
        f.write_text("<x/>")
        parser = BPMNParser()
        with pytest.raises(ValueError, match="File too large"):
            parser.parse(f, max_size=2)

    def test_binary_file_rejected(self, tmp_path):
        f = tmp_path / "binary.bpmn"
        f.write_bytes(b"\x00\x01\x02\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(f)

    def test_malformed_xml_file(self, tmp_path):
        f = tmp_path / "bad.bpmn"
        f.write_text("<not-closed>")
        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(f)


class TestParserStringErrors:
    """Test parser behaviour with problematic string/bytes inputs."""

    def test_string_too_large(self):
        parser = BPMNParser()
        with pytest.raises(ValueError, match="XML content too large"):
            parser.parse("<x/>", max_size=2)

    def test_bytes_too_large(self):
        parser = BPMNParser()
        with pytest.raises(ValueError, match="XML content too large"):
            parser.parse(b"<x/>", max_size=2)

    def test_malformed_string(self):
        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse("<bad>>><<</oops>")

    def test_malformed_bytes(self):
        parser = BPMNParser()
        with pytest.raises(ValueError, match="Malformed XML"):
            parser.parse(b"\xff\xfe<bad")

    def test_invalid_source_type(self):
        parser = BPMNParser()
        with pytest.raises(ValueError, match="Cannot parse source"):
            parser.parse(12345)  # type: ignore[arg-type]


class TestValidatorFileErrors:
    """Test BPMNValidator.validate() with file edge cases."""

    def test_file_not_found(self):
        v = BPMNValidator(specs_dir="nonexistent", skip_schema=True)
        with pytest.raises(FileNotFoundError, match="BPMN file not found"):
            v.validate("this_file_does_not_exist.bpmn")

    def test_path_is_directory(self, tmp_path):
        v = BPMNValidator(specs_dir="nonexistent", skip_schema=True)
        with pytest.raises(ValueError, match="not a file"):
            v.validate(tmp_path)

    def test_binary_file_rejected(self, tmp_path):
        f = tmp_path / "binary.bpmn"
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
        v = BPMNValidator(specs_dir="nonexistent", skip_schema=True)
        with pytest.raises(ValueError, match="not valid UTF-8"):
            v.validate(f)


class TestSchemaValidatorErrors:
    """Test SchemaValidator with corrupted/missing schemas."""

    def test_corrupted_xsd(self, tmp_path):
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        (schema_dir / "BPMN20.xsd").write_text("THIS IS NOT VALID XSD CONTENT!!!")
        sv = SchemaValidator(schema_dir)
        with pytest.raises(RuntimeError, match="Corrupted or unreadable XSD"):
            sv._load_schema()

    def test_missing_xsd(self, tmp_path):
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        sv = SchemaValidator(schema_dir)
        with pytest.raises(FileNotFoundError, match="XSD schemas not found"):
            sv._load_schema()
