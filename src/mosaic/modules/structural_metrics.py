"""
Structural quality metrics for Android APKs.

Metrics implemented here:
  CD: Component Density
  LL: Lifecycle Load
  IC: ICC Coupling
  UE: UI Entanglement
  AB: Async Burden
  PD: Platform Dependence / Platform Reliance
  FC: Framework Coupling

The extraction layer provides counts; this module applies the formal metric
formulas and returns both normalized values and raw counts for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass

from mosaic.modules.apk_loader import APKModel


def _safe_ratio(numerator: int, denominator: int, ndigits: int = 4) -> float:
    return round(numerator / denominator, ndigits) if denominator > 0 else 0.0


@dataclass(frozen=True)
class CDResult:
    cd: float
    n_comp: int
    n_cls: int
    manifest_component_count: int
    fragment_count: int


@dataclass(frozen=True)
class LLResult:
    ll: float
    n_lifecycle: int
    n_lifecycle_hosts: int


@dataclass(frozen=True)
class ICResult:
    ic: float
    n_icc: int
    n_icc_comp: int


@dataclass(frozen=True)
class UEResult:
    ue: float
    n_ui_nonui: int
    n_ui: int


@dataclass(frozen=True)
class ABResult:
    ab: float
    n_async: int
    n_call: int


@dataclass(frozen=True)
class PDResult:
    pd: float
    n_res: int
    n_call: int


@dataclass(frozen=True)
class FCResult:
    fc: float
    n_fw: int
    n_call: int


def compute_cd(model: APKModel) -> CDResult:
    """Component Density: CD = N_comp / N_cls.

    N_comp includes manifest-declared Android components (Activity, Service,
    Receiver, Provider) plus Fragment subclasses detected in DEX. Activity
    aliases are retained separately as entry aliases and are not counted as
    lifecycle-bearing components for CD.
    """
    n_manifest = len(model.manifest_components)
    n_fragments = len(model.fragment_classes)
    n_comp = n_manifest + n_fragments
    n_cls = model.app_class_count
    return CDResult(
        cd=_safe_ratio(n_comp, n_cls),
        n_comp=n_comp,
        n_cls=n_cls,
        manifest_component_count=n_manifest,
        fragment_count=n_fragments,
    )


def compute_ll(model: APKModel, cd: CDResult) -> LLResult:
    """Lifecycle Load: LL = N_lifecycle / N_lifecycle_hosts.

    N_lifecycle counts lifecycle callbacks declared directly in manifest
    component classes and Fragment subclasses. N_lifecycle_hosts uses the same
    lifecycle-bearing host set as CD: manifest components + Fragments.
    """
    n_lifecycle = model.lifecycle_callback_count
    n_hosts = cd.n_comp
    return LLResult(ll=_safe_ratio(n_lifecycle, n_hosts), n_lifecycle=n_lifecycle, n_lifecycle_hosts=n_hosts)


def compute_ic(model: APKModel) -> ICResult:
    """ICC Coupling: IC = N_icc / N_icc_comp.

    N_icc counts ICC callsites. N_icc_comp counts ICC-capable manifest endpoints
    (Activity, Service, Receiver, Provider) plus activity aliases. Fragments are
    intentionally excluded because they are hosted UI modules, not independent
    ICC endpoints.
    """
    n_icc = model.icc_callsite_count
    n_icc_comp = model.icc_component_count
    return ICResult(ic=_safe_ratio(n_icc, n_icc_comp), n_icc=n_icc, n_icc_comp=n_icc_comp)


def compute_ue(model: APKModel) -> UEResult:
    """UI Entanglement: UE = N_ui_nonui / N_ui.

    N_ui is the number of detected UI classes. N_ui_nonui is the number of
    non-UI operation callsites inside those UI classes.
    """
    n_ui_nonui = model.ui_nonui_callsite_count
    n_ui = len(model.ui_classes)
    return UEResult(ue=_safe_ratio(n_ui_nonui, n_ui), n_ui_nonui=n_ui_nonui, n_ui=n_ui)


def compute_ab(model: APKModel) -> ABResult:
    """Async Burden: AB = N_async / N_call.

    This implementation is intentionally callsite-based: N_async counts invoke
    callsites targeting predefined async/concurrency API families. It does not
    claim to count every type reference or allocation.
    """
    n_async = model.async_callsite_count
    n_call = model.total_callsites
    return ABResult(ab=_safe_ratio(n_async, n_call), n_async=n_async, n_call=n_call)


def compute_pd(model: APKModel) -> PDResult:
    """Platform Dependence: PD = N_res / N_call.

    N_res counts invoke callsites targeting resource-sensitive Android platform
    APIs such as camera, location, sensors, wake locks, Bluetooth, media, jobs,
    alarms, notifications, foreground-service APIs, telephony, NFC, WiFi, USB,
    biometrics, and related AndroidX wrappers.
    """
    n_res = model.resource_callsite_count
    n_call = model.total_callsites
    return PDResult(pd=_safe_ratio(n_res, n_call), n_res=n_res, n_call=n_call)


def compute_fc(model: APKModel) -> FCResult:
    """Framework Coupling: FC = N_fw / N_call.

    N_fw counts callsites targeting Android platform or AndroidX framework APIs.
    Third-party libraries are intentionally excluded from the numerator.
    """
    n_fw = model.framework_callsites
    n_call = model.total_callsites
    return FCResult(fc=_safe_ratio(n_fw, n_call), n_fw=n_fw, n_call=n_call)
