"""Tests for spec_downloader.py — download BPMN XSD schemas from OMG."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from bpmn_validator.spec_downloader import (
    SPEC_URLS,
    _download_file,
    download_specs,
    verify_specs,
)


# ---------------------------------------------------------------------------
# _download_file
# ---------------------------------------------------------------------------


class TestDownloadFile:
    def test_success(self, tmp_path: Path):
        """First attempt succeeds — file is atomically moved to dest."""
        dest = tmp_path / "test.xsd"

        def fake_retrieve(url, filename):
            Path(filename).write_text("xsd-content")

        with patch(
            "bpmn_validator.spec_downloader.urllib.request.urlretrieve", side_effect=fake_retrieve
        ):
            _download_file("https://example.com/test.xsd", dest)

        assert dest.exists()
        assert dest.read_text() == "xsd-content"

    def test_retry_then_success(self, tmp_path: Path):
        """Fails twice, succeeds on third attempt."""
        dest = tmp_path / "retry.xsd"
        attempts = {"count": 0}

        def flaky_retrieve(url, filename):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ConnectionError("timeout")
            Path(filename).write_text("ok")

        with patch(
            "bpmn_validator.spec_downloader.urllib.request.urlretrieve", side_effect=flaky_retrieve
        ):
            _download_file("https://example.com/retry.xsd", dest)

        assert dest.exists()
        assert attempts["count"] == 3

    def test_all_retries_fail(self, tmp_path: Path):
        """All 3 attempts fail — RuntimeError with last exception."""
        dest = tmp_path / "fail.xsd"

        with patch(
            "bpmn_validator.spec_downloader.urllib.request.urlretrieve",
            side_effect=ConnectionError("network down"),
        ):
            with pytest.raises(RuntimeError, match="Failed to download.*after 3 attempts"):
                _download_file("https://example.com/fail.xsd", dest)

        assert not dest.exists()


# ---------------------------------------------------------------------------
# download_specs
# ---------------------------------------------------------------------------


class TestDownloadSpecs:
    def test_skips_existing(self, tmp_path: Path):
        """Files already on disk are skipped when force=False."""
        for fname in SPEC_URLS:
            (tmp_path / fname).write_text("existing")

        with patch("bpmn_validator.spec_downloader._download_file") as mock_dl:
            result = download_specs(tmp_path, force=False)

        assert result == []
        mock_dl.assert_not_called()

    def test_downloads_missing(self, tmp_path: Path):
        """Missing files are downloaded."""
        with patch("bpmn_validator.spec_downloader._download_file") as mock_dl:
            result = download_specs(tmp_path, force=False)

        assert set(result) == set(SPEC_URLS.keys())
        assert mock_dl.call_count == len(SPEC_URLS)

    def test_force_redownloads(self, tmp_path: Path):
        """force=True re-downloads even if files exist."""
        for fname in SPEC_URLS:
            (tmp_path / fname).write_text("old")

        with patch("bpmn_validator.spec_downloader._download_file") as mock_dl:
            result = download_specs(tmp_path, force=True)

        assert set(result) == set(SPEC_URLS.keys())
        assert mock_dl.call_count == len(SPEC_URLS)

    def test_include_pdf(self, tmp_path: Path):
        """include_pdf=True downloads the PDF as well."""
        with patch("bpmn_validator.spec_downloader._download_file") as mock_dl:
            result = download_specs(tmp_path, include_pdf=True)

        assert "BPMN-2.0.2.pdf" in result
        assert mock_dl.call_count == len(SPEC_URLS) + 1

    def test_pdf_skips_existing(self, tmp_path: Path):
        """PDF already on disk is skipped when force=False."""
        for fname in SPEC_URLS:
            (tmp_path / fname).write_text("x")
        (tmp_path / "BPMN-2.0.2.pdf").write_text("pdf-data")

        with patch("bpmn_validator.spec_downloader._download_file") as mock_dl:
            result = download_specs(tmp_path, include_pdf=True, force=False)

        assert "BPMN-2.0.2.pdf" not in result
        mock_dl.assert_not_called()


# ---------------------------------------------------------------------------
# verify_specs
# ---------------------------------------------------------------------------


class TestVerifySpecs:
    def test_all_present(self, tmp_path: Path):
        for fname in SPEC_URLS:
            (tmp_path / fname).write_text("x")
        assert verify_specs(tmp_path) is True

    def test_missing_one(self, tmp_path: Path):
        names = list(SPEC_URLS.keys())
        for fname in names[:-1]:
            (tmp_path / fname).write_text("x")
        assert verify_specs(tmp_path) is False
