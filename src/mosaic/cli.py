"""
MOSAIC CLI.

Usage examples:
  mosaic analyze app.apk
  mosaic analyze /path/to/apps/
  mosaic analyze a.apk b.apk --output results.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click

from mosaic.analyzer import analyze_apk


def _parse_formats(ctx, param, value) -> tuple[str, ...]:
    formats = []
    for token in value.split(","):
        token = token.strip().lower()
        if token not in {"json", "html"}:
            raise click.BadParameter("Choose json, html, or json,html.")
        if token not in formats:
            formats.append(token)
    return tuple(formats)


def _collect_apks(paths: tuple[str, ...]) -> list[Path]:
    apks: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found = sorted(path.rglob("*.apk"))
            if not found:
                click.echo(f"Warning: no APK files found in {path}", err=True)
            apks.extend(found)
        elif path.is_file() and path.suffix.lower() == ".apk":
            apks.append(path)
        elif path.is_file():
            raise click.BadParameter(f"Not an APK file: {path}")
        else:
            raise click.BadParameter(f"Path does not exist: {path}")
    return apks


def _write_output(records: list[dict], output: Optional[Path], formats: tuple[str, ...]) -> None:
    if output is None and len(formats) > 1:
        raise click.ClickException("Multiple formats require --output FILE")
    for fmt in formats:
        if fmt == "html":
            from mosaic.report import render_html

            payload = render_html(records)
        else:
            payload = json.dumps(records[0] if len(records) == 1 else records, indent=2, ensure_ascii=False)
        if output is None:
            click.echo(payload)
        else:
            path = output
            if len(formats) > 1:
                base = output.with_suffix("") if output.suffix.lower() in {".json", ".html"} else output
                path = Path(str(base) + "." + fmt)
            path.write_text(payload, encoding="utf-8")
            click.echo(f"Results written to {path}", err=True)


@click.group()
def main() -> None:
    """MOSAIC — Android Quality Metrics Tool."""


@main.command()
@click.argument("paths", nargs=-1, required=True, metavar="APK_OR_DIR...")
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write results to FILE. With multiple formats, write FILE.json and FILE.html.",
)
@click.option(
    "--format", "-f", "formats",
    default="json",
    callback=_parse_formats,
    help="Comma-separated output formats: json, html. Default: json.",
)
@click.option(
    "--scope",
    type=click.Choice(["artifact", "app-owned"], case_sensitive=False),
    default="artifact",
    show_default=True,
    help=(
        "Analysis scope: 'artifact' includes all DEX-defined classes; "
        "'app-owned' restricts analysis to the APK package namespace and "
        "excludes obvious R/R$*/BuildConfig generated classes."
    ),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show Androguard debug output.",
)
def analyze(paths: tuple[str, ...], output: Optional[Path], formats: tuple[str, ...], scope: str, verbose: bool) -> None:
    """Analyze one or more APKs and compute quality metrics."""
    if output is None and len(formats) > 1:
        raise click.UsageError("Multiple formats require --output FILE")
    if verbose:
        try:
            from loguru import logger as _loguru

            _loguru.enable("androguard")
        except ImportError:
            pass

    try:
        apks = _collect_apks(paths)
    except click.BadParameter as exc:
        raise click.ClickException(str(exc)) from exc

    if not apks:
        raise click.ClickException("No APK files found.")

    records: list[dict] = []
    for apk_path in apks:
        click.echo(f"Analyzing {apk_path} ...", err=True)
        record = analyze_apk(apk_path, scope=scope)
        records.append(record)
        if "error" in record:
            click.echo(f"  ERROR: {record['error']}", err=True)

    _write_output(records, output, formats)

    if any("error" in record for record in records):
        sys.exit(1)


if __name__ == "__main__":
    main()
