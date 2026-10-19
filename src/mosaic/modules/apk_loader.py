"""
APK input and normalization for MOSAIC quality metrics.

This module parses an APK with Androguard and converts it into an APKModel
containing only scalar counts and evidence needed by the metric layer.  The
metric formulas are implemented in structural_metrics.py; this loader owns the
static-analysis extraction logic and API-taxonomy matching.
"""

from __future__ import annotations

import gc
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from androguard.misc import AnalyzeAPK

from mosaic.modules.api_taxonomy import (
    ASYNC_EXACT_CLASSES,
    ASYNC_METHODS_BY_CLASS,
    ASYNC_PREFIXES,
    FRAMEWORK_PREFIXES,
    FRAGMENT_BASES,
    ICC_METHODS_BY_CLASS,
    LIFECYCLE_METHODS,
    NONUI_EXACT_CLASSES,
    NONUI_METHODS_BY_CLASS,
    NONUI_PREFIXES,
    RESOURCE_EXACT_CLASSES,
    RESOURCE_METHODS_BY_CLASS,
    RESOURCE_PREFIXES,
    TAXONOMY_VERSION,
    UI_BASES,
)

# Androguard 4.x uses loguru and may emit extensive DEBUG output during XREF
# construction. Suppress it by default; the CLI can re-enable if needed.
try:  # pragma: no cover - optional runtime dependency behavior
    from loguru import logger as _loguru

    _loguru.disable("androguard")
except ImportError:  # pragma: no cover
    pass

ANDROID_NS = "http://schemas.android.com/apk/res/android"
_METHOD_REF_RE = re.compile(r"(?P<class>L[^;]+;)->(?P<method>[^\(\s]+)")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComponentInfo:
    """Manifest-declared Android component."""

    name: str
    component_type: str  # activity | service | receiver | provider
    dalvik_name: str


@dataclass(frozen=True)
class ActivityAliasInfo:
    """Manifest activity-alias entry.

    Activity aliases do not define their own lifecycle-bearing class, so they are
    not included in CD or LL. They are retained as ICC-capable entry aliases.
    """

    name: str
    target_activity: str
    dalvik_name: str
    target_dalvik_name: str


@dataclass(frozen=True)
class CallsiteSummary:
    total_callsites: int
    framework_callsites: int
    icc_callsites: int
    async_callsites: int
    resource_callsites: int
    ui_nonui_callsites: int


@dataclass
class APKModel:
    path: Path
    analysis_scope: str  # artifact | app-owned
    sha256: str
    package: str
    version_code: Optional[int]
    min_sdk: Optional[int]
    target_sdk: Optional[int]

    # Component structure
    manifest_components: list[ComponentInfo]
    activity_aliases: list[ActivityAliasInfo]
    fragment_classes: list[str]
    app_class_count: int
    icc_component_count: int

    # Shared callsite counts
    total_callsites: int
    framework_callsites: int

    # Metric-specific counts
    lifecycle_callback_count: int
    icc_callsite_count: int
    async_callsite_count: int
    resource_callsite_count: int
    ui_classes: list[str]
    ui_nonui_callsite_count: int

    # Provenance
    androguard_version: str
    taxonomy_version: str


# ---------------------------------------------------------------------------
# Manifest and class helpers
# ---------------------------------------------------------------------------


def _attr(element, local_name: str) -> Optional[str]:
    return element.get(f"{{{ANDROID_NS}}}{local_name}")


def _to_dalvik_name(name: str, package: str) -> str:
    """Convert a Java/manifest class name to a Dalvik descriptor.

    Handles short manifest names such as .MainActivity, fully qualified names,
    and already-Dalvik descriptors.
    """
    if not name:
        return ""
    if name.startswith("L") and name.endswith(";"):
        return name
    if name.startswith("."):
        full = package + name
    elif "." not in name and package:
        # Manifest shorthand without a leading dot is uncommon but legal in some
        # generated manifests; interpret it relative to the package.
        full = f"{package}.{name}"
    else:
        full = name
    return "L" + full.replace(".", "/") + ";"


def _parse_manifest_components(app_el, package: str) -> list[ComponentInfo]:
    components: list[ComponentInfo] = []
    for ctype in ("activity", "service", "receiver", "provider"):
        for el in app_el.findall(ctype):
            raw_name = _attr(el, "name") or ""
            dalvik_name = _to_dalvik_name(raw_name, package)
            components.append(
                ComponentInfo(name=raw_name, component_type=ctype, dalvik_name=dalvik_name)
            )
    return components


def _parse_activity_aliases(app_el, package: str) -> list[ActivityAliasInfo]:
    aliases: list[ActivityAliasInfo] = []
    for el in app_el.findall("activity-alias"):
        raw_name = _attr(el, "name") or ""
        raw_target = _attr(el, "targetActivity") or ""
        aliases.append(
            ActivityAliasInfo(
                name=raw_name,
                target_activity=raw_target,
                dalvik_name=_to_dalvik_name(raw_name, package),
                target_dalvik_name=_to_dalvik_name(raw_target, package),
            )
        )
    return aliases


def _is_framework_class(class_name: str) -> bool:
    return class_name.startswith(FRAMEWORK_PREFIXES)


def _is_obvious_generated_class(class_name: str) -> bool:
    """Return True for unambiguous Android build-generated classes.

    This intentionally stays conservative: only R, R$*, and BuildConfig are
    excluded in app-owned mode. Other generated code (Room/Hilt/DataBinding,
    Kotlin synthetics, etc.) is retained unless a future classifier handles it.
    """
    simple = class_name.rstrip(";").rsplit("/", 1)[-1]
    return simple == "R" or simple.startswith("R$") or simple == "BuildConfig"


def _is_application_owned_class(class_name: str, package: str) -> bool:
    if not package:
        return False
    prefix = "L" + package.replace(".", "/") + "/"
    return class_name.startswith(prefix) and not _is_obvious_generated_class(class_name)


def _select_included_classes(analysis, package: str, scope: str) -> frozenset[str]:
    if scope not in {"artifact", "app-owned"}:
        raise ValueError(f"Unknown analysis scope: {scope}")

    dex_defined = {ca.name for ca in analysis.get_classes() if not ca.is_external()}
    if scope == "artifact":
        return frozenset(dex_defined)

    return frozenset(name for name in dex_defined if _is_application_owned_class(name, package))


def _build_superclass_map(analysis, included_classes: frozenset[str]) -> dict[str, str]:
    """Build {class_name: superclass_name} for included DEX-defined classes."""
    superclass_map: dict[str, str] = {}
    for ca in analysis.get_classes():
        if ca.is_external() or ca.name not in included_classes:
            continue
        try:
            superclass = ca.get_vm_class().get_superclassname()
        except Exception:
            continue
        if superclass:
            superclass_map[ca.name] = superclass
    return superclass_map


def _find_subclasses(superclass_map: dict[str, str], seed_classes: frozenset[str]) -> list[str]:
    """Return included classes that transitively extend one of seed_classes."""
    found: set[str] = set(seed_classes)
    result: list[str] = []
    changed = True
    while changed:
        changed = False
        for class_name, superclass in superclass_map.items():
            if class_name not in found and superclass in found:
                found.add(class_name)
                result.append(class_name)
                changed = True
    return sorted(result)


def _filter_manifest_components_for_scope(
    components: list[ComponentInfo], included_classes: frozenset[str], scope: str
) -> list[ComponentInfo]:
    if scope == "artifact":
        return components
    return [c for c in components if c.dalvik_name in included_classes]


def _filter_aliases_for_scope(
    aliases: list[ActivityAliasInfo], included_classes: frozenset[str], scope: str
) -> list[ActivityAliasInfo]:
    if scope == "artifact":
        return aliases
    return [a for a in aliases if a.target_dalvik_name in included_classes]


# ---------------------------------------------------------------------------
# Callsite parsing and matching
# ---------------------------------------------------------------------------


def _method_name(method_analysis) -> str:
    for attr in ("name", "method_name"):
        value = getattr(method_analysis, attr, None)
        if value:
            return str(value)
    try:
        return str(method_analysis.get_method().get_name())
    except Exception:
        return ""


def _method_class_name(method_analysis) -> str:
    value = getattr(method_analysis, "class_name", None)
    return str(value) if value is not None else ""


def _extract_ref_from_instruction(inst) -> Optional[str]:
    """Extract the target method reference from an invoke instruction."""
    try:
        operands = inst.get_operands()
    except Exception:
        return None
    for operand in reversed(operands or []):
        candidate = operand[-1] if isinstance(operand, (tuple, list)) and operand else operand
        text = str(candidate)
        if "->" in text:
            return text
    return None


def _parse_method_ref(ref: str) -> tuple[str, str]:
    """Return (class_descriptor, method_name) from a Dalvik method reference."""
    match = _METHOD_REF_RE.search(ref)
    if not match:
        return "", ""
    return match.group("class"), match.group("method")


def _iter_callsites(analysis, included_classes: frozenset[str]):
    """Yield (origin_class, target_class, target_method, ref) for invoke callsites."""
    for ma in analysis.get_methods():
        origin_class = _method_class_name(ma)
        if ma.is_external() or origin_class not in included_classes:
            continue
        try:
            instructions = ma.get_method().get_instructions()
        except Exception:
            continue
        for inst in instructions:
            try:
                name = inst.get_name()
            except Exception:
                continue
            if not name.startswith("invoke"):
                continue
            ref = _extract_ref_from_instruction(inst)
            if not ref:
                continue
            target_class, target_method = _parse_method_ref(ref)
            yield origin_class, target_class, target_method, ref


def _matches_methods_by_class(
    class_name: str, method_name: str, table: dict[str, frozenset[str]] | Iterable[tuple[str, frozenset[str]]] | object
) -> bool:
    # Mapping is used at runtime, but keeping this simple/defensive avoids tight
    # assumptions about typing if the taxonomy is generated later.
    items = table.items() if hasattr(table, "items") else table
    for cls, methods in items:
        if class_name == cls and method_name in methods:
            return True
    return False


def _is_icc_call(class_name: str, method_name: str) -> bool:
    return _matches_methods_by_class(class_name, method_name, ICC_METHODS_BY_CLASS)


def _is_async_call(class_name: str, method_name: str) -> bool:
    return (
        class_name in ASYNC_EXACT_CLASSES
        or class_name.startswith(ASYNC_PREFIXES)
        or _matches_methods_by_class(class_name, method_name, ASYNC_METHODS_BY_CLASS)
    )


def _is_resource_call(class_name: str, method_name: str) -> bool:
    return (
        class_name in RESOURCE_EXACT_CLASSES
        or class_name.startswith(RESOURCE_PREFIXES)
        or _matches_methods_by_class(class_name, method_name, RESOURCE_METHODS_BY_CLASS)
    )


def _is_nonui_call(class_name: str, method_name: str) -> bool:
    return (
        class_name in NONUI_EXACT_CLASSES
        or class_name.startswith(NONUI_PREFIXES)
        or _is_icc_call(class_name, method_name)
        or _is_async_call(class_name, method_name)
        or _matches_methods_by_class(class_name, method_name, NONUI_METHODS_BY_CLASS)
    )


def _count_callsites(
    analysis,
    included_classes: frozenset[str],
    ui_class_names: frozenset[str],
) -> CallsiteSummary:
    total = 0
    framework = 0
    icc = 0
    async_count = 0
    resource = 0
    ui_nonui = 0

    for origin_class, target_class, target_method, _ref in _iter_callsites(analysis, included_classes):
        total += 1
        if _is_framework_class(target_class):
            framework += 1
        if _is_icc_call(target_class, target_method):
            icc += 1
        if _is_async_call(target_class, target_method):
            async_count += 1
        if _is_resource_call(target_class, target_method):
            resource += 1
        if origin_class in ui_class_names and _is_nonui_call(target_class, target_method):
            ui_nonui += 1

    return CallsiteSummary(
        total_callsites=total,
        framework_callsites=framework,
        icc_callsites=icc,
        async_callsites=async_count,
        resource_callsites=resource,
        ui_nonui_callsites=ui_nonui,
    )


def _count_lifecycle_callbacks(
    analysis, lifecycle_host_classes: frozenset[str], included_classes: frozenset[str]
) -> int:
    """Count lifecycle methods declared directly in component/fragment classes."""
    count = 0
    for ca in analysis.get_classes():
        if ca.is_external() or ca.name not in included_classes:
            continue
        if ca.name not in lifecycle_host_classes:
            continue
        try:
            for method in ca.get_vm_class().get_methods():
                if method.get_name() in LIFECYCLE_METHODS:
                    count += 1
        except Exception:
            continue
    return count


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_apk(apk_path: Path, scope: str = "artifact") -> APKModel:
    """Parse an APK and return the normalized APKModel used by metric code.

    scope="artifact" analyzes all DEX-defined classes. scope="app-owned"
    restricts analysis to classes under the APK package namespace and excludes
    obvious R/R$*/BuildConfig generated classes.
    """
    import androguard

    apk, dex, analysis = AnalyzeAPK(str(apk_path))

    manifest = apk.get_android_manifest_xml()
    app_el = manifest.find("application")
    package = apk.get_package() or ""

    manifest_components: list[ComponentInfo] = []
    activity_aliases: list[ActivityAliasInfo] = []
    if app_el is not None:
        manifest_components = _parse_manifest_components(app_el, package)
        activity_aliases = _parse_activity_aliases(app_el, package)

    included_classes = _select_included_classes(analysis, package, scope)
    manifest_components = _filter_manifest_components_for_scope(manifest_components, included_classes, scope)
    activity_aliases = _filter_aliases_for_scope(activity_aliases, included_classes, scope)

    superclass_map = _build_superclass_map(analysis, included_classes)
    fragment_classes = _find_subclasses(superclass_map, FRAGMENT_BASES)
    ui_classes = _find_subclasses(superclass_map, UI_BASES)

    app_class_count = len(included_classes)

    lifecycle_host_classes = frozenset({c.dalvik_name for c in manifest_components} | set(fragment_classes))
    lifecycle_callback_count = _count_lifecycle_callbacks(
        analysis, lifecycle_host_classes, included_classes
    )

    callsites = _count_callsites(analysis, included_classes, frozenset(ui_classes))

    # IC denominator: ICC-capable manifest endpoints plus activity aliases.
    # Fragments are not independent ICC endpoints, so they are intentionally
    # excluded from this denominator even though they are counted in CD/LL.
    icc_component_count = len(manifest_components) + len(activity_aliases)

    model = APKModel(
        path=apk_path,
        analysis_scope=scope,
        sha256=_sha256(apk_path),
        package=package,
        version_code=_safe_int(apk.get_androidversion_code()),
        min_sdk=_safe_int(apk.get_min_sdk_version()),
        target_sdk=_safe_int(apk.get_target_sdk_version()),
        manifest_components=manifest_components,
        activity_aliases=activity_aliases,
        fragment_classes=fragment_classes,
        app_class_count=app_class_count,
        icc_component_count=icc_component_count,
        total_callsites=callsites.total_callsites,
        framework_callsites=callsites.framework_callsites,
        lifecycle_callback_count=lifecycle_callback_count,
        icc_callsite_count=callsites.icc_callsites,
        async_callsite_count=callsites.async_callsites,
        resource_callsite_count=callsites.resource_callsites,
        ui_classes=ui_classes,
        ui_nonui_callsite_count=callsites.ui_nonui_callsites,
        androguard_version=str(androguard.__version__),
        taxonomy_version=TAXONOMY_VERSION,
    )

    del apk, dex, analysis, manifest, app_el
    gc.collect()
    return model
