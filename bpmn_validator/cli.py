"""BPMN Validator CLI — validate BPMN 2.0.2 files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from bpmn_validator import (
    BPMNValidator,
    Severity,
    __version__,
    download_specs,
    verify_specs,
    rule_registry,
)


@click.group()
@click.version_option(version=__version__, prog_name="bpmn-validator")
def main() -> None:
    """BPMN 2.0.2 Validator — schema + semantic validation."""


# ------------------------------------------------------------------
# download
# ------------------------------------------------------------------


@main.command()
@click.option(
    "--specs-dir",
    default="specs",
    show_default=True,
    help="Directory to store downloaded XSD schemas.",
)
@click.option("--include-pdf", is_flag=True, help="Also download the BPMN 2.0.2 PDF spec.")
@click.option("--force", is_flag=True, help="Re-download even if files already exist.")
def download(specs_dir: str, include_pdf: bool, force: bool) -> None:
    """Download BPMN 2.0.2 XSD schemas from OMG."""
    target = Path(specs_dir)
    click.echo(f"Downloading specs to {target.resolve()} ...")
    downloaded = download_specs(target, include_pdf=include_pdf, force=force)
    for f in downloaded:
        click.echo(f"  ✓ {f}")
    if not downloaded:
        click.echo("  (all files already present, use --force to re-download)")
    click.echo("Done.")


# ------------------------------------------------------------------
# validate
# ------------------------------------------------------------------


@main.command()
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format.",
)
@click.option("--skip-schema", is_flag=True, help="Skip XSD schema validation.")
@click.option("--skip-semantic", is_flag=True, help="Skip semantic rule validation.")
@click.option(
    "--specs-dir",
    default="specs",
    show_default=True,
    help="Directory containing XSD schemas.",
)
@click.option(
    "--exclude-rules",
    default="",
    help="Comma-separated rule IDs to skip.",
)
@click.option(
    "--severity",
    type=click.Choice(["error", "warning", "info"]),
    default=None,
    help="Only run rules of this severity.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with code 1 if there are any warnings (not just errors).",
)
def validate(
    files: tuple[str, ...],
    fmt: str,
    skip_schema: bool,
    skip_semantic: bool,
    specs_dir: str,
    exclude_rules: str,
    severity: str | None,
    strict: bool,
) -> None:
    """Validate one or more BPMN files."""
    severity_filter: Severity | None = None
    if severity:
        try:
            severity_filter = Severity[severity.upper()]
        except KeyError:  # pragma: no cover — click.Choice prevents this
            click.echo(
                f"✗ Unknown severity '{severity}'. Valid values: error, warning, info.",
                err=True,
            )
            sys.exit(2)

    excluded = {r.strip() for r in exclude_rules.split(",") if r.strip()}

    if not skip_schema and not verify_specs(specs_dir):
        click.echo(
            "⚠ XSD schemas not found. Run 'bpmn-validator download' first, or use --skip-schema.",
            err=True,
        )
        sys.exit(2)

    validator = BPMNValidator(
        specs_dir=specs_dir,
        skip_schema=skip_schema,
        skip_semantic=skip_semantic,
        exclude_rules=excluded,
        severity_filter=severity_filter,
    )

    any_errors = False
    any_warnings = False
    json_results: list[dict[str, Any]] = []

    for file_path in files:
        try:
            result = validator.validate(file_path)
        except Exception as exc:
            click.echo(f"✗ {file_path}: {exc}", err=True)
            any_errors = True
            continue

        if fmt == "json":
            json_results.append(result.to_dict())
        else:
            click.echo(result.to_text())

        if result.errors:
            any_errors = True
        if result.warnings:
            any_warnings = True

    if fmt == "json":
        if len(json_results) == 1:
            click.echo(json.dumps(json_results[0], indent=2))
        else:
            click.echo(json.dumps(json_results, indent=2))

    if any_errors:
        sys.exit(1)
    if strict and any_warnings:
        sys.exit(1)


# ------------------------------------------------------------------
# list-rules
# ------------------------------------------------------------------


@main.command("list-rules")
def list_rules() -> None:
    """List all available semantic validation rules."""
    rules = sorted(rule_registry.get_all(), key=lambda r: r.rule_id)
    for rule in rules:
        sev = rule.severity.value.upper()
        click.echo(f"  {rule.rule_id:<12} [{sev:<7}]  {rule.description}")
    click.echo(f"\nTotal: {len(rules)} rules")


if __name__ == "__main__":  # pragma: no cover
    main()
