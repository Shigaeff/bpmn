"""Download BPMN 2.0 XSD schemas from OMG."""

from __future__ import annotations

import logging
import os
import shutil
import socket
import tempfile
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

# Network timeout in seconds for all download operations.
_DOWNLOAD_TIMEOUT: int = 30

SPEC_URLS = {
    "BPMN20.xsd": "https://www.omg.org/spec/BPMN/20100501/BPMN20.xsd",
    "Semantic.xsd": "https://www.omg.org/spec/BPMN/20100501/Semantic.xsd",
    "BPMNDI.xsd": "https://www.omg.org/spec/BPMN/20100501/BPMNDI.xsd",
    "DC.xsd": "https://www.omg.org/spec/BPMN/20100501/DC.xsd",
    "DI.xsd": "https://www.omg.org/spec/BPMN/20100501/DI.xsd",
}

PDF_URL = "https://www.omg.org/spec/BPMN/2.0.2/PDF"

_MAX_RETRIES = 3


def _download_file(url: str, dest: Path) -> None:
    """Download *url* to *dest* atomically with retries.

    Uses a temporary file + rename to avoid leaving partial files on disk
    when the download is interrupted.
    """
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        tmp_path: str | None = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dest.parent, suffix=".download")
            os.close(fd)
            # Use urlopen with explicit timeout instead of urlretrieve
            # to prevent hanging indefinitely on unresponsive servers.
            old_timeout = socket.getdefaulttimeout()
            try:
                socket.setdefaulttimeout(_DOWNLOAD_TIMEOUT)
                urllib.request.urlretrieve(url, tmp_path)
            finally:
                socket.setdefaulttimeout(old_timeout)
            shutil.move(tmp_path, dest)
            return
        except Exception as exc:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
            last_exc = exc
            logger.warning(
                "Download attempt %d/%d for %s failed: %s",
                attempt,
                _MAX_RETRIES,
                url,
                exc,
            )

    raise RuntimeError(f"Failed to download {url} after {_MAX_RETRIES} attempts: {last_exc}")


def download_specs(
    target_dir: str | Path,
    include_pdf: bool = False,
    force: bool = False,
) -> list[str]:
    """Download BPMN XSD schemas to target_dir. Returns list of downloaded filenames."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []

    for filename, url in SPEC_URLS.items():
        dest = target_dir / filename
        if dest.exists() and not force:
            continue
        _download_file(url, dest)
        downloaded.append(filename)

    if include_pdf:
        dest = target_dir / "BPMN-2.0.2.pdf"
        if not dest.exists() or force:
            _download_file(PDF_URL, dest)
            downloaded.append("BPMN-2.0.2.pdf")

    return downloaded


def verify_specs(specs_dir: str | Path) -> bool:
    """Check that all required XSD files are present."""
    specs_dir = Path(specs_dir)
    return all((specs_dir / f).exists() for f in SPEC_URLS)
