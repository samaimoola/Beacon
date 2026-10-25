"""
engine/realdata.py
==================
Real-data backend. Consumes the PII-free processed dataset
(data/processed/premises.json) produced by scripts/build_processed.py and
implements the SAME public contract as engine/demo.py.

Design principles for this milestone:
  - Storm conditions are EXPLICITLY SIMULATED (the datasets contain network,
    labor, and HISTORICAL damage — not a live storm feed).
  - Historical damage evidence is labeled as historical, never presented as a
    current confirmed outage.
  - Restoration effort is grounded in the labor workbook (direct install hours
    x single indirect labor multiplier), then translated to a wall-clock window
    using the simulated crew count.
  - Missing information uses labeled assumptions or `None`, never invented joins.

Owner: Samai (engine/)
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from engine import restoration as _sched

REPO_ROOT = Path(__file__).resolve().parents[1]
PREMISES_PATH = REPO_ROOT / "data" / "processed" / "premises.json"

SOURCE_LABEL = (
    "REAL AEP network + labor data (anonymized) · storm AND damage SIMULATED · "
    "historical damage is context only · restoration is an UNVALIDATED heuristic"
)

# Default damage scenario when a caller does not specify one (keeps the existing
# evaluate_scenario(...) signature working via a sensible default).
DEFAULT_DAMAGE_SCENARIO = "pole_and_span"


def is_available() -> bool:
    """True if the processed real-data file exists and has premises."""
    if not PREMISES_PATH.exists():
        return False
    try:
        data = json.loads(PREMISES_PATH.read_text())
        return bool(data.get("premises"))
    except Exception:
        return False


def _load() -> dict:
    return json.loads(PREMISES_PATH.read_text())


def _index() -> dict[str, dict]:
    return {p["id"]: p for p in _load()["premises"]}


def get_customers() -> list[dict]:
    """Return [{"id", "label"}] for the real anonymized premises."""
    return [{"id": p["id"], "label": p["label"]} for p in _load()["premises"]]


def get_damage_scenarios(customer_id: str) -> list[dict]:
    """
    Return the SIMULATED damage-scenario presets for a premise:
    [{"id", "label", "description", "damaged_assets", "jobs"}, ...].
    """
    idx = _index()
    if customer_id not in idx:
        raise ValueError(f"Unknown customer_id: {customer_id!r}")
    return idx[customer_id].get("damage_scenarios", [])


def _task_catalog() -> dict:
    return _load().get("labor_task_catalog", {})


def _ilm() -> float:
    return _load().get("ilm", 4.5)


def _find_scenario(premise: dict, scenario_id: Optional[str]) -> dict:
    scenarios = premise.get("damage_scenarios", [])
    if not scenarios:
        return {"id": "none", "label": "No scenario", "damaged_assets": [], "jobs": []}
    if scenario_id is None:
        scenario_id = DEFAULT_DAMAGE_SCENARIO
    for s in scenarios:
        if s["id"] == scenario_id:
            return s
    # Unknown scenario id -> fall back to the first preset (defensive).
    return scenarios[0]


def _build_repair_jobs(scenario: dict, catalog: dict) -> tuple[list, list[str]]:
    """Translate a scenario's job list into engine.restoration.RepairJob objects."""
    jobs = []
    notes: list[str] = []
    for spec in scenario.get("jobs", []):
        task_key = spec.get("task")
        entry = catalog.get(task_key)
        if entry is None:
            jobs.append(_sched.RepairJob(
                task=task_key or "unknown task",
                direct_hours=None,
                depends_on=tuple(spec.get("depends_on", ())),
                hours_source="UNKNOWN — task not in labor catalog",
                is_assumption=True,
            ))
            continue
        jobs.append(_sched.RepairJob(
            task=entry["label"],
            direct_hours=entry["direct_hours"],  # may be None (unknown mapping)
            depends_on=tuple(spec.get("depends_on", ())),
            hours_source=entry["hours_source"],
            is_assumption=entry.get("is_assumption", True),
        ))
    return jobs, notes


# severity -> effort multiplier (SIMULATED). Severity scales the per-job effort
# to represent harder/easier field conditions; it does not add phantom jobs.
_SEVERITY_MULT = {"low": 0.8, "medium": 1.0, "high": 1.3}


def _severity_jobs(scenario: dict, catalog: dict, sev_mult: float) -> list:
    """Repair jobs for a scenario with severity applied (None stays None / unknown)."""
    raw_jobs, _notes = _build_repair_jobs(scenario, catalog)
    return [
        _sched.RepairJob(
            task=j.task,
            direct_hours=(None if j.direct_hours is None else round(j.direct_hours * sev_mult, 3)),
            depends_on=j.depends_on,
            hours_source=j.hours_source,
            is_assumption=j.is_assumption,
        )
        for j in raw_jobs
    ]


def schedule_summary(
    customer_id: str,
    storm_severity: str,
    available_crews: int,
    access_blocked: bool,
    damage_scenario: Optional[str] = None,
) -> dict:
    """
    Structured scheduling facts for a scenario, computed by the SAME scheduler
    call evaluate_scenario uses. Lets explainers state *why* a crew change does
    or does not move the window without parsing factor text. Additive helper:
    evaluate_scenario's result shape is unchanged.
    """
    idx = _index()
    if customer_id not in idx:
        raise ValueError(f"Unknown customer_id: {customer_id!r}")
    scenario = _find_scenario(idx[customer_id], damage_scenario)
    jobs = _severity_jobs(scenario, _task_catalog(), _SEVERITY_MULT[storm_severity])
    sched = _sched.schedule(jobs, crews=available_crews, ilm=_ilm(), access_blocked=access_blocked)
    return {
        "repair_jobs": len(jobs),
        "unknown_jobs": sched.unknown_jobs,
        "crews": available_crews,
        "elapsed_hours": sched.elapsed_hours,
        "critical_path_hours": sched.critical_path_hours,
        "dependency_limited": sched.dependency_limited,
        "access_delay_hours": sched.access_delay_hours,
    }


def evaluate_scenario(
    customer_id: str,
    storm_severity: str,
    available_crews: int,
    access_blocked: bool,
    damage_scenario: Optional[str] = None,
) -> dict:
    """
    Evaluate a scenario for a real premise. Matches engine/contracts.py.

    `damage_scenario` (optional) selects one of the simulated damage presets from
    get_damage_scenarios(customer_id). When omitted, a sensible default preset is
    used so existing callers keep working unchanged.
    """
    idx = _index()
    if customer_id not in idx:
        raise ValueError(f"Unknown customer_id: {customer_id!r}")
    p = idx[customer_id]

    service_kind = p.get("service_kind", "Unknown")
    chain = p.get("upstream_chain", [])
    iso_count = p.get("upstream_isolating_device_count", 0)
    hist = p.get("historical_damage")

    scenario = _find_scenario(p, damage_scenario)
    catalog = _task_catalog()
    ilm = _ilm()

    # ------------------------------------------------------------------
    # Risk band (likelihood of losing power) — SIMULATED storm applied to
    # real network characteristics. Crews and medical needs do NOT enter here.
    # ------------------------------------------------------------------
    risk_score = {"low": 1, "medium": 2, "high": 3}[storm_severity]
    risk_factors: list[str] = [
        f"Simulated storm severity: {storm_severity}.",
    ]

    if service_kind == "Overhead":
        risk_score += 2
        risk_factors.append("Real data: service is OVERHEAD — more exposed to wind/tree damage.")
    elif service_kind == "Underground":
        risk_factors.append("Real data: service is UNDERGROUND — lower wind/debris exposure.")
    else:
        risk_factors.append("Service type unknown in source data (labeled assumption: treat as average).")

    if iso_count == 0:
        risk_score += 1
        risk_factors.append("Real topology: no isolating device between transformer and breaker — "
                            "a fault upstream affects this premise directly.")
    else:
        risk_factors.append(f"Real topology: {iso_count} upstream isolating device(s) can localize faults.")

    # Historical damage is CONTEXT ONLY. It does not prove current damage and
    # does not change the physical outage-risk score here.
    if hist and hist.get("total", 0) > 0:
        risk_factors.append(
            f"CONTEXT: this circuit had {hist['total']} damage record(s) in a prior assessment "
            f"(e.g. {', '.join(f'{k}×{v}' for k, v in list(hist.get('by_asset_type', {}).items())[:3])}). "
            "Historical only — not evidence of current damage, and not used to score risk."
        )
    else:
        risk_factors.append("No historical damage recorded on this circuit (context only).")

    # The chosen SIMULATED damage scenario informs risk framing (not scored from history).
    n_damaged = sum(a.get("quantity", 0) for a in scenario.get("damaged_assets", []))
    if n_damaged > 0:
        risk_score += 1
        risk_factors.append(
            f"Simulated damage scenario '{scenario.get('label', scenario.get('id'))}' "
            f"assumes {n_damaged} damaged asset(s) on the path."
        )
    else:
        risk_factors.append("Simulated scenario assumes no equipment damage on the path.")

    if access_blocked:
        risk_factors.append("Simulated access blockage affects restoration time only, not outage likelihood.")

    if risk_score <= 2:
        risk_band = "Low"
    elif risk_score <= 4:
        risk_band = "Moderate"
    elif risk_score <= 6:
        risk_band = "High"
    else:
        risk_band = "Critical"

    # ------------------------------------------------------------------
    # Restoration from the SELECTED repair jobs (not the whole chain).
    #
    # - Only damaged assets in the chosen scenario create work.
    # - Severity scales per-job effort (field difficulty), it does not add jobs.
    # - engine.restoration schedules jobs with crew limits + dependencies, so more
    #   crews cannot shorten a single job or bypass the critical path.
    # - The ILM is applied once inside the scheduler.
    # ------------------------------------------------------------------
    restoration_factors: list[str] = []

    sev_mult = _SEVERITY_MULT[storm_severity]
    jobs = _severity_jobs(scenario, catalog, sev_mult)
    sched = _sched.schedule(jobs, crews=available_crews, ilm=ilm, access_blocked=access_blocked)
    low_h: Optional[float] = sched.low_hours
    high_h: Optional[float] = sched.high_hours

    restoration_factors.append(
        f"Simulated damage scenario: '{scenario.get('label', scenario.get('id'))}' — "
        f"{len(jobs)} repair job(s)."
    )
    if jobs:
        restoration_factors.append(
            "Repair jobs: " + "; ".join(
                f"{j.task}"
                + ("" if j.direct_hours is None else f" (~{j.direct_hours:g} effort-h)")
                + ("" if not j.depends_on else f" [after job {', '.join(str(d) for d in j.depends_on)}]")
                for j in jobs
            )
        )
    if sched.effective_effort_hours is not None and sched.effective_effort_hours > 0:
        restoration_factors.append(
            f"Total effort: {sched.total_direct_hours} direct effort-h × ILM {ilm} = "
            f"{sched.effective_effort_hours} effort-h (ILM applied once; includes travel/setup/safety)."
        )
        restoration_factors.append(
            f"Scheduled elapsed with {available_crews} crew(s): ~{sched.elapsed_hours:g} h "
            f"(critical path ≈ {sched.critical_path_hours:g} effort-h)."
        )
    restoration_factors.append(
        f"Simulated {storm_severity} severity scales per-job effort ×{sev_mult:g}."
    )
    if any(j.is_assumption for j in jobs):
        restoration_factors.append(
            "Some repair-hour values are LABELED ASSUMPTIONS (not itemized in the workbook)."
        )
    restoration_factors.extend(sched.notes)
    restoration_factors.append(
        "Labor hours are treated as effort in the workbook's own (UNRESOLVED) unit — "
        "worker-, crew-, or elapsed-hours is an open question; crew size assumed = 1 per job."
    )

    # ------------------------------------------------------------------
    # Preparation actions
    # ------------------------------------------------------------------
    prep = [
        "Charge phones and backup batteries now.",
        "Keep refrigerator/freezer doors closed to preserve food.",
        "Locate flashlights and battery-powered lanterns; check their batteries.",
        "Know a manual way to open electric garage doors.",
    ]
    if service_kind == "Overhead":
        prep.append("Overhead service: report downed wires to AEP Ohio and stay clear of them.")
    if storm_severity in ("medium", "high"):
        prep.append("Have cash on hand; card readers and ATMs may be offline.")
    if storm_severity == "high":
        prep.append("Plan for an extended outage; arrange a backup location if power is medically necessary.")

    # ------------------------------------------------------------------
    # Alert eligibility — PROTOTYPE RULES ONLY (not AEP enrollment/priority).
    # ------------------------------------------------------------------
    alert_eligible = (
        risk_band in ("High", "Critical")
        or (low_h is not None and low_h > 8.0)
    )

    # ------------------------------------------------------------------
    # Evidence quality — Medium: real network/labor/topology, but storm is
    # simulated and damage is historical, so not "High".
    # ------------------------------------------------------------------
    evidence_quality = "Medium"

    assumptions = [
        "Storm severity AND the specific damage scenario are SIMULATED (user-selected presets); "
        "the data has no live storm or damage feed.",
        "Historical circuit damage is CONTEXT ONLY — it does not prove current damage and does "
        "not generate repair work.",
        "Restoration is computed from the selected repair jobs only. Healthy equipment on the "
        "path generates no work.",
        "Labor effort uses the workbook's install/removal references × a single indirect labor "
        "multiplier (ILM 4.5), applied once (it already includes travel/setup/safety).",
        "Pole and transformer hours come from workbook tables (transformer kVA ASSUMED at 100 kVA); "
        "fuse/recloser/line-span hours are LABELED ASSUMPTIONS; unmapped assets yield an UNKNOWN estimate.",
        "Elapsed time respects crew limits and task dependencies: more crews cannot shorten a single "
        "job or bypass the critical path. Crew size is ASSUMED to be 1 per job.",
        "The low–high range is an ASSUMED uncertainty band, NOT a statistically validated interval. "
        "The model is an UNVALIDATED heuristic.",
        "Labor-hour unit is UNRESOLVED (worker-, crew-, or elapsed-hours) — open question for AEP mentors.",
        "Evidence quality describes how much real data backs the inputs, NOT prediction accuracy.",
        "\"Alert eligible\" reflects Beacon prototype rules only — not AEP enrollment, program "
        "qualification, or guaranteed restoration priority.",
        f"Topology join verified on premise number; this premise's customer transformer key "
        f"{'agrees with' if p.get('topology_key_agreement') else 'DISAGREES with'} the topology file.",
    ]

    return {
        "risk_band": risk_band,
        "evidence_quality": evidence_quality,
        "risk_factors": risk_factors,
        "restoration_low_hours": low_h,
        "restoration_high_hours": high_h,
        "restoration_factors": restoration_factors,
        "preparation_actions": prep,
        "alert_eligible": alert_eligible,
        "assumptions": assumptions,
        "source_label": SOURCE_LABEL,
    }
