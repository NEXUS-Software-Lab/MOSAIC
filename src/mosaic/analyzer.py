"""
MOSAIC analyzer orchestration.

Runs all quality metric modules on a single APK and assembles the canonical JSON
record with normalized metrics, raw counts, evidence, and provenance.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mosaic import __version__
from mosaic.modules.apk_loader import load_apk
from mosaic.modules.structural_metrics import (
    compute_ab,
    compute_cd,
    compute_fc,
    compute_ic,
    compute_ll,
    compute_pd,
    compute_ue,
)


def analyze_apk(apk_path: Path, scope: str = "artifact") -> dict[str, Any]:
    """Analyze a single APK and return a JSON-serializable record.

    scope="artifact" analyzes all DEX-defined classes. scope="app-owned"
    restricts analysis to APK package-prefix classes, excluding obvious
    R/R$*/BuildConfig generated classes.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        model = load_apk(apk_path, scope=scope)
    except Exception as exc:
        return {
            "apk_path": str(apk_path),
            "error": f"APK load failed: {exc}",
            "traceback": traceback.format_exc(),
            "run_timestamp": timestamp,
            "mosaic_version": __version__,
        }

    try:
        cd = compute_cd(model)
        ll = compute_ll(model, cd)
        ic = compute_ic(model)
        ue = compute_ue(model)
        ab = compute_ab(model)
        pd = compute_pd(model)
        fc = compute_fc(model)
    except Exception as exc:
        return {
            "apk_path": str(apk_path),
            "apk_sha256": model.sha256,
            "package": model.package,
            "analysis_scope": model.analysis_scope,
            "error": f"Metric computation failed: {exc}",
            "traceback": traceback.format_exc(),
            "run_timestamp": timestamp,
            "mosaic_version": __version__,
        }

    return {
        "apk_path": str(apk_path),
        "apk_sha256": model.sha256,
        "package": model.package,
        "version_code": model.version_code,
        "analysis_scope": model.analysis_scope,
        "sdk": {
            "min": model.min_sdk,
            "target": model.target_sdk,
        },
        "metrics": {
            "CD": cd.cd,
            "LL": ll.ll,
            "IC": ic.ic,
            "UE": ue.ue,
            "AB": ab.ab,
            "PD": pd.pd,
            "FC": fc.fc,
        },
        "counts": {
            "classes_analyzed_total": cd.n_cls,
            "components_total_for_cd_ll": cd.n_comp,
            "manifest_components": cd.manifest_component_count,
            "activity_aliases": len(model.activity_aliases),
            "fragment_classes": cd.fragment_count,
            "icc_components_for_ic": ic.n_icc_comp,
            "lifecycle_callbacks": ll.n_lifecycle,
            "icc_callsites": ic.n_icc,
            "ui_classes": ue.n_ui,
            "ui_nonui_callsites": ue.n_ui_nonui,
            "async_callsites": ab.n_async,
            "resource_callsites": pd.n_res,
            "callsites_total": fc.n_call,
            "callsites_framework_android_androidx": fc.n_fw,
        },
        "provenance": {
            "androguard_version": model.androguard_version,
            "taxonomy_version": model.taxonomy_version,
            "mosaic_version": __version__,
            "run_timestamp": timestamp,
            "analysis_scope": model.analysis_scope,
            "scope_definition": (
                "all DEX-defined classes"
                if model.analysis_scope == "artifact"
                else "APK package-prefix classes excluding R/R$*/BuildConfig"
            ),
            "callsite_definition": "Dalvik invoke instructions in analyzed methods",
            "framework_definition": "target class starts with Landroid/ or Landroidx/",
        },
        "evidence": {
            "manifest_components": [
                {"name": c.name, "dalvik_name": c.dalvik_name, "type": c.component_type}
                for c in model.manifest_components
            ],
            "activity_aliases": [
                {
                    "name": a.name,
                    "dalvik_name": a.dalvik_name,
                    "target_activity": a.target_activity,
                    "target_dalvik_name": a.target_dalvik_name,
                }
                for a in model.activity_aliases
            ],
            "fragment_classes": model.fragment_classes,
            "ui_classes": model.ui_classes,
        },
    }
