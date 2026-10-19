"""Regenerate illustrative reports: python docs/examples/render_examples.py."""

import json
from pathlib import Path

from mosaic.report import METRIC_INPUTS, render_html

ROOT = Path(__file__).resolve().parent


def example(name, classes, components, fragments, lifecycle, icc, ui, nonui, calls, async_calls, resource, framework):
    package = f"org.example.{name}"
    counts = {
        "classes_analyzed_total": classes,
        "components_total_for_cd_ll": components + fragments,
        "manifest_components": components,
        "activity_aliases": 0,
        "fragment_classes": fragments,
        "icc_components_for_ic": components,
        "lifecycle_callbacks": lifecycle,
        "icc_callsites": icc,
        "ui_classes": ui,
        "ui_nonui_callsites": nonui,
        "async_callsites": async_calls,
        "resource_callsites": resource,
        "callsites_total": calls,
        "callsites_framework_android_androidx": framework,
    }
    return {
        "apk_path": f"illustrative-{name}.apk",
        "apk_sha256": "0" * 64,
        "package": package,
        "version_code": "1",
        "analysis_scope": "artifact",
        "sdk": {"min": "23", "target": "35"},
        "metrics": {key: counts[n] / counts[d] if counts[d] else 0 for key, (n, d) in METRIC_INPUTS.items()},
        "counts": counts,
        "provenance": {
            "mosaic_version": "0.4.0",
            "androguard_version": "illustrative; no APK analyzed",
            "taxonomy_version": "illustrative",
            "run_timestamp": "illustrative; no analysis run",
            "analysis_scope": "artifact",
            "scope_definition": "all DEX-defined classes",
            "callsite_definition": "Dalvik invoke instructions in analyzed methods",
            "framework_definition": "target class starts with Landroid/ or Landroidx/",
        },
        "evidence": {
            "manifest_components": [{"name": f"{package}.MainActivity", "dalvik_name": f"Lorg/example/{name}/MainActivity;", "type": "activity"}],
            "activity_aliases": [],
            "fragment_classes": [],
            "ui_classes": [f"Lorg/example/{name}/MainActivity;"],
        },
    }


if __name__ == "__main__":
    # Synthetic values for documentation, not experimental results. Evidence is abbreviated.
    notes = example("notes", 240, 8, 4, 30, 16, 10, 45, 4000, 160, 80, 1800)
    tasks = example("tasks", 360, 12, 6, 54, 36, 14, 84, 6000, 420, 180, 3300)
    (ROOT / "single-app.json").write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")
    (ROOT / "single-app.html").write_text(render_html([notes]), encoding="utf-8")
    (ROOT / "comparison.html").write_text(render_html([notes, tasks]), encoding="utf-8")
