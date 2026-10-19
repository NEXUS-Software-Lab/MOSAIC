"""
HTML report renderer — renders the canonical JSON records produced by
analyze_apk() through a Jinja2 template (templates/report.html).

This module prepares the data (formatting, organizing records) and delegates
presentation entirely to the template, including all chart configurations.
"""

from __future__ import annotations

import math
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

METRIC_ORDER = ("CD", "LL", "IC", "UE", "AB", "PD", "FC")

METRIC_INFO: dict[str, dict[str, str]] = {
    "CD": {
        "name": "Component Density",
        "formula": "N_comp / N_cls",
        "description": (
            "How much of the code in the selected scope is organized into Android components "
            "(Activities, Services, Broadcast Receivers, Content Providers) and Fragments."
        ),
    },
    "LL": {
        "name": "Lifecycle Load",
        "formula": "N_lifecycle / N_comp",
        "description": (
            "How many Android lifecycle callbacks (such as onCreate or onResume) "
            "the average component implements."
        ),
    },
    "IC": {
        "name": "ICC Coupling",
        "formula": "N_icc / N_icc_comp",
        "description": (
            "ICC callsites per manifest endpoint (Activities, Services, Receivers, "
            "Providers, and activity aliases). Fragments are excluded from this denominator."
        ),
    },
    "UE": {
        "name": "UI Entanglement",
        "formula": "N_ui_nonui / N_ui",
        "description": (
            "How much non-UI work (network, database, file I/O, crypto, async) "
            "is embedded inside UI classes such as Activities and Fragments."
        ),
    },
    "AB": {
        "name": "Async Burden",
        "formula": "N_async / N_call",
        "description": (
            "What share of all callsites involves asynchronous or concurrent "
            "execution (threads, handlers, executors, coroutines, Rx chains, "
            "work schedulers)."
        ),
    },
    "PD": {
        "name": "Platform Dependence",
        "formula": "N_res / N_call",
        "description": (
            "What share of all callsites touches resource-sensitive platform APIs "
            "(camera, location, sensors, Bluetooth, media, notifications, etc.)."
        ),
    },
    "FC": {
        "name": "Framework Coupling",
        "formula": "N_fw / N_call",
        "description": (
            "What share of all callsites targets Android framework APIs "
            "(android.* / androidx.*); third-party libraries are excluded."
        ),
    },
}

COUNT_LABELS: dict[str, str] = {
    "components_total_for_cd_ll": "Components and fragments (CD / LL)",
    "manifest_components": "Manifest components",
    "activity_aliases": "Activity aliases",
    "icc_components_for_ic": "ICC endpoints including aliases (IC)",
    "fragment_classes": "Fragment classes",
    "classes_analyzed_total": "Classes analyzed (selected scope)",
    "lifecycle_callbacks": "Lifecycle callbacks",
    "icc_callsites": "ICC callsites",
    "ui_classes": "UI classes",
    "ui_nonui_callsites": "Non-UI callsites in UI classes",
    "async_callsites": "Async callsites",
    "resource_callsites": "Resource callsites",
    "callsites_total": "Total callsites",
    "callsites_framework_android_androidx": "Framework callsites (Android / AndroidX)",
}

COUNT_GROUPS = (
    {"id": "structure", "title": "Structure & Lifecycle", "sections": (
        {"id": "structure-metrics", "title": "Metric inputs", "keys": (
            "classes_analyzed_total", "components_total_for_cd_ll", "lifecycle_callbacks",
        )},
        {"id": "component-breakdown", "title": "Component breakdown", "keys": (
            "manifest_components", "fragment_classes",
        )},
    )},
    {"id": "communication", "title": "Communication & UI", "sections": (
        {"id": "communication-metrics", "title": "Metric inputs", "keys": (
            "icc_components_for_ic", "activity_aliases", "icc_callsites", "ui_classes", "ui_nonui_callsites",
        )},
    )},
    {"id": "platform", "title": "Callsites & Platform", "sections": (
        {"id": "platform-metrics", "title": "Metric inputs", "keys": (
            "callsites_total", "async_callsites", "resource_callsites", "callsites_framework_android_androidx",
        )},
    )},
)

METRIC_INPUTS: dict[str, tuple[str, str]] = {
    "CD": ("components_total_for_cd_ll", "classes_analyzed_total"),
    "LL": ("lifecycle_callbacks", "components_total_for_cd_ll"),
    "IC": ("icc_callsites", "icc_components_for_ic"),
    "UE": ("ui_nonui_callsites", "ui_classes"),
    "AB": ("async_callsites", "callsites_total"),
    "PD": ("resource_callsites", "callsites_total"),
    "FC": ("callsites_framework_android_androidx", "callsites_total"),
}

COUNT_SYMBOLS: dict[str, list[str]] = {key: [] for key in COUNT_LABELS}
for _mid, _input_keys in METRIC_INPUTS.items():
    for _key, _symbol in zip(_input_keys, METRIC_INFO[_mid]["formula"].split(" / ")):
        if _symbol not in COUNT_SYMBOLS[_key]:
            COUNT_SYMBOLS[_key].append(_symbol)

_METRIC_REFERENCE_MAX: dict[str, float] = {
    "CD": 1.0,
    "LL": 10.0,
    "IC": 10.0,
    "UE": 20.0,
    "AB": 1.0,
    "PD": 1.0,
    "FC": 1.0,
}

_ENV = Environment(
    loader=PackageLoader("mosaic", "templates"),
    autoescape=select_autoescape(enabled_extensions=("html",)),
    trim_blocks=True,
    lstrip_blocks=True,
)
_TEMPLATE = _ENV.get_template("report.html")


def _fmt_metric(value: Any) -> str:
    try:
        number = float(value)
        return f"{number:.4f}" if math.isfinite(number) else "n/a"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_scalar(value: Any) -> str:
    return "?" if value is None else str(value)


def _metric_calculation(mid: str, counts: dict, value: Any) -> dict:
    numerator_key, denominator_key = METRIC_INPUTS[mid]
    numerator, denominator = counts.get(numerator_key), counts.get(denominator_key)
    result = _fmt_metric(value)
    if numerator is None or denominator is None:
        display = f"Calculation unavailable (missing input). Reported value: {result}"
    elif denominator == 0:
        display = f"Reported value: {result} (MOSAIC uses 0 for a zero denominator)"
    else:
        display = f"{_fmt_scalar(numerator)} / {_fmt_scalar(denominator)} = {result}"
    return {
        "inputs": [
            {"label": COUNT_LABELS[key], "symbol": symbol, "value": _fmt_scalar(counts.get(key))}
            for key, symbol in zip(
                (numerator_key, denominator_key), METRIC_INFO[mid]["formula"].split(" / ")
            )
        ],
        "display": display,
    }


def _scope(record: dict) -> dict:
    provenance = record.get("provenance") or {}
    key = record.get("analysis_scope") or provenance.get("analysis_scope") or "unknown"
    definitions = {
        "artifact": "All DEX-defined classes, including bundled library and generated code.",
        "app-owned": "APK package-prefix classes, excluding R, R$* and BuildConfig. Package-prefix ownership is a heuristic; app code outside that namespace is excluded.",
    }
    return {
        "key": key,
        "label": {"artifact": "Artifact", "app-owned": "App-owned"}.get(key, "Unknown" if key == "unknown" else key),
        "definition": provenance.get("scope_definition") or definitions.get(key, "Scope was not specified in this record."),
        "note": definitions.get(key, "Scope was not specified in this record."),
    }


def _record_name(record: dict) -> str:
    return str(record.get("apk_path", "unknown")).replace("\\", "/").rsplit("/", 1)[-1]


def _prepare_differences(records: list[dict]) -> list[dict]:
    if len(records) != 2:
        return []
    rows = []
    for mid in METRIC_ORDER:
        a, b = [(r.get("metrics") or {}).get(mid) for r in records]
        delta, relative = "n/a", "n/a"
        try:
            av, bv = float(a), float(b)
            if math.isfinite(av) and math.isfinite(bv):
                delta = f"{bv - av:+.4f}"
                relative = f"{(bv - av) / abs(av) * 100:+.1f}%" if av else "n/a (baseline is zero)"
        except (TypeError, ValueError):
            pass
        rows.append({"id": mid, "name": METRIC_INFO[mid]["name"], "a": _fmt_metric(a), "b": _fmt_metric(b), "delta": delta, "relative": relative})
    return rows


def _header_meta(records: list[dict]) -> tuple[str, str, str]:
    """Best-effort (mosaic_version, androguard_version, run_timestamp) for the header."""
    mosaic_version = "unknown"
    androguard_version = "unknown"
    timestamp = ""
    for record in records:
        prov = record.get("provenance") or {}
        if mosaic_version == "unknown":
            mosaic_version = prov.get("mosaic_version") or record.get("mosaic_version") or "unknown"
        if androguard_version == "unknown":
            androguard_version = prov.get("androguard_version") or "unknown"
        if not timestamp:
            timestamp = prov.get("run_timestamp") or record.get("run_timestamp") or ""
        if mosaic_version != "unknown" and androguard_version != "unknown" and timestamp:
            break
    return mosaic_version, androguard_version, timestamp


def _prepare_summary(records: list[dict]) -> list[dict]:
    """Build one row per record for the summary table."""
    rows: list[dict] = []
    for record in records:
        name = _record_name(record)
        if "error" in record:
            rows.append(
                {
                    "error": True,
                    "name": name,
                    "error_message": record.get("error", "unknown"),
                    "package": "",
                    "sdk_min": "",
                    "sdk_target": "",
                    "metric_values": [],
                    "scope": _scope(record),
                }
            )
            continue
        sdk = record.get("sdk") or {}
        metrics = record.get("metrics") or {}
        rows.append(
            {
                "error": False,
                "name": name,
                "error_message": "",
                "package": record.get("package", "?"),
                "scope": _scope(record),
                "sdk_min": _fmt_scalar(sdk.get("min")),
                "sdk_target": _fmt_scalar(sdk.get("target")),
                "metric_values": [
                    _fmt_metric(metrics.get(mid)) for mid in METRIC_ORDER
                ],
            }
        )
    return rows


def _prepare_records(records: list[dict]) -> list[dict]:
    """Build the per-APK detail card data for the template."""
    prepared: list[dict] = []
    for index, record in enumerate(records, start=1):
        is_error = "error" in record
        sdk = record.get("sdk") or {}
        item = {
            "index": index,
            "apk_name": _record_name(record),
            "scope": _scope(record),
            "apk_path": str(record.get("apk_path", "?")),
            "sha256": record.get("apk_sha256") or None,
            "package": record.get("package") or None,
            "version_code": _fmt_scalar(record.get("version_code")),
            "has_sdk": bool(sdk),
            "sdk_min": _fmt_scalar(sdk.get("min")),
            "sdk_target": _fmt_scalar(sdk.get("target")),
            "is_error": is_error,
            "error": record.get("error") if is_error else None,
            "traceback": record.get("traceback") if is_error else None,
            "metrics": [],
            "counts": [],
            "evidence": {
                "manifest_components": [],
                "activity_aliases": [],
                "fragment_classes": [],
                "ui_classes": [],
            },
            "provenance": {},
        }
        if not is_error:
            metrics = record.get("metrics") or {}
            counts = record.get("counts") or {}
            item["metrics"] = [
                {
                    "id": mid,
                    "name": METRIC_INFO[mid]["name"],
                    "value": _fmt_metric(metrics.get(mid)),
                    "description": METRIC_INFO[mid]["description"],
                    "formula": METRIC_INFO[mid]["formula"],
                    "formula_display": METRIC_INFO[mid]["formula"],
                    "calculation": _metric_calculation(mid, counts, metrics.get(mid)),
                }
                for mid in METRIC_ORDER
            ]
            item["counts"] = [
                {"key": k, "label": COUNT_LABELS[k], "symbols": COUNT_SYMBOLS[k], "value": _fmt_scalar(counts.get(k))}
                for k in COUNT_LABELS
            ]
            evidence = record.get("evidence") or {}
            item["evidence"] = {
                "manifest_components": evidence.get("manifest_components") or [],
                "activity_aliases": evidence.get("activity_aliases") or [],
                "fragment_classes": evidence.get("fragment_classes") or [],
                "ui_classes": evidence.get("ui_classes") or [],
            }
        prov = record.get("provenance") or {}
        item["provenance"] = {
            "mosaic_version": (
                prov.get("mosaic_version")
                or record.get("mosaic_version")
                or "unknown"
            ),
            "androguard_version": prov.get("androguard_version") or "unknown",
            "taxonomy_version": prov.get("taxonomy_version") or "unknown",
            "callsite_definition": prov.get("callsite_definition") or "unknown",
            "framework_definition": prov.get("framework_definition") or "unknown",
            "run_timestamp": (
                prov.get("run_timestamp")
                or record.get("run_timestamp")
                or "unknown"
            ),
        }
        prepared.append(item)
    return prepared


def render_html(records: list[dict]) -> str:
    """Render analysis records as an interactive HTML report with charts."""
    mosaic_version, androguard_version, timestamp = _header_meta(records)
    success = [r for r in records if "error" not in r]

    return _TEMPLATE.render(
        meta={
            "mosaic_version": mosaic_version,
            "androguard_version": androguard_version,
            "run_timestamp": timestamp,
        },
        stats={
            "total": len(records),
            "ok": len(success),
            "failed": len(records) - len(success),
        },
        has_comparison=len(success) > 1,
        scope_mismatch=len({_scope(r)["key"] for r in success}) > 1,
        scope_unknown=any(_scope(r)["key"] not in {"artifact", "app-owned"} for r in success),
        differences=_prepare_differences(success),
        comparison_names=[f"{_record_name(r)} · {_scope(r)['label']}" for r in success],
        metric_order=METRIC_ORDER,
        count_groups=COUNT_GROUPS,
        metric_info=METRIC_INFO,
        metric_reference_max=_METRIC_REFERENCE_MAX,
        summary_rows=_prepare_summary(records),
        records=_prepare_records(records),
        raw_records=records,
    )
