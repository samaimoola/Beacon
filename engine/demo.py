"""
engine/demo.py
==============
⚠️  SYNTHETIC DEMO IMPLEMENTATION — All results are fabricated for demonstration.
    Nothing here represents real AEP network data, real customer records, or
    confirmed outage/restoration predictions.

This module provides:
  - Three fictional demo households with plausible but invented characteristics.
  - Deterministic scenario logic that varies with storm_severity, available_crews,
    and access_blocked so judges can observe meaningful result changes.

Owner: Samai (engine/)
Replace or augment this file in later milestones once real GIS data is processed.
"""

from __future__ import annotations
from typing import Optional

# ---------------------------------------------------------------------------
# Demo households
# ---------------------------------------------------------------------------

_DEMO_CUSTOMERS: list[dict] = [
    {
        "id": "demo-001",
        "label": "Household A — Suburban, overhead lines",
        # Fictional profile attributes used by scenario logic:
        "_profile": {
            "line_type": "overhead",
            "topology": "single_source",   # no backup feed
            "tree_exposure": "high",        # lots of mature trees nearby
            "medical_needs_declared": False,
            "circuits_upstream": 3,         # fictional upstream equipment count
        },
    },
    {
        "id": "demo-002",
        "label": "Household B — Rural, long span lines",
        "_profile": {
            "line_type": "overhead",
            "topology": "single_source",
            "tree_exposure": "medium",
            # DECLARED FICTIONAL PROFILE ATTRIBUTE: this demo household has stated it
            # relies on electric medical equipment. This affects preparation guidance
            # and communication urgency ONLY — it does NOT change the physical
            # likelihood of losing power.
            "medical_needs_declared": True,
            "circuits_upstream": 5,
        },
    },
    {
        "id": "demo-003",
        "label": "Household C — Urban, underground lines",
        "_profile": {
            "line_type": "underground",
            "topology": "looped",           # has a backup feed path
            "tree_exposure": "low",
            "medical_needs_declared": False,
            "circuits_upstream": 2,
        },
    },
]

_CUSTOMER_INDEX: dict[str, dict] = {c["id"]: c for c in _DEMO_CUSTOMERS}

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_customers() -> list[dict]:
    """Return anonymized customer list: [{"id": str, "label": str}, ...]."""
    return [{"id": c["id"], "label": c["label"]} for c in _DEMO_CUSTOMERS]


def get_damage_scenarios(customer_id: str) -> list[dict]:
    """
    Synthetic backend has no preset damage scenarios. Returns a single
    placeholder so the UI can render uniformly across backends.
    """
    if customer_id not in _CUSTOMER_INDEX:
        raise ValueError(f"Unknown customer_id: {customer_id!r}")
    return [{
        "id": "synthetic",
        "label": "Synthetic demo (no damage presets)",
        "description": "The synthetic backend uses rule-based estimates, not simulated damage presets.",
        "damaged_assets": [],
        "jobs": [],
    }]


def evaluate_scenario(
    customer_id: str,
    storm_severity: str,       # "low" | "medium" | "high"
    available_crews: int,      # 1–10
    access_blocked: bool,
    damage_scenario: str | None = None,  # accepted for API parity; not used here
) -> dict:
    """
    Deterministic synthetic scenario evaluation.

    Returns a ScenarioResult dict as documented in engine/contracts.py.
    All values are invented — clearly labeled as synthetic demo estimates.
    `damage_scenario` is accepted for signature compatibility and ignored.
    """
    if customer_id not in _CUSTOMER_INDEX:
        raise ValueError(f"Unknown customer_id: {customer_id!r}")

    profile = _CUSTOMER_INDEX[customer_id]["_profile"]

    # ------------------------------------------------------------------
    # 1. Risk band (likelihood of losing power)
    #
    # Deliberately independent of available_crews, access_blocked, and of the
    # household's declared medical needs: none of these change how likely an
    # outage is. Crews/access are used later (restoration window) and medical
    # needs only affect prep/alert eligibility — never the risk score here.
    # ------------------------------------------------------------------
    risk_score = 0
    risk_factors: list[str] = []

    # Storm contribution
    storm_contrib = {"low": 1, "medium": 2, "high": 3}[storm_severity]
    risk_score += storm_contrib
    risk_factors.append(
        f"Storm severity is {storm_severity} — "
        + {"low": "isolated outages expected", "medium": "widespread outages possible",
           "high": "significant infrastructure damage expected"}[storm_severity]
    )

    # Line type
    if profile["line_type"] == "overhead":
        risk_score += 2
        risk_factors.append("Overhead primary lines are exposed to wind and falling debris")
    else:
        risk_score += 0
        risk_factors.append("Underground lines have lower wind/debris exposure")

    # Tree exposure
    tree_contrib = {"high": 2, "medium": 1, "low": 0}[profile["tree_exposure"]]
    risk_score += tree_contrib
    if tree_contrib > 0:
        risk_factors.append(
            f"Tree/vegetation exposure is {profile['tree_exposure']} — increases conductor damage risk"
        )

    # Topology
    if profile["topology"] == "single_source":
        risk_score += 1
        risk_factors.append("Single-source feed — no automatic backup circuit available")
    else:
        risk_factors.append("Looped topology provides a potential backup feed path")

    # Access
    # NOTE: blocked access is a delay REACHING repairs, not a driver of whether
    # power is lost. It must NOT change the physical outage-risk score — it only
    # affects the restoration window below.
    if access_blocked:
        risk_factors.append("Access routes reported blocked — affects restoration time only, "
                            "not the likelihood of losing power")

    # Map score → band
    if risk_score <= 2:
        risk_band = "Low"
    elif risk_score <= 4:
        risk_band = "Moderate"
    elif risk_score <= 6:
        risk_band = "High"
    else:
        risk_band = "Critical"

    # ------------------------------------------------------------------
    # 2. Restoration window (hours)
    #
    # Note: crew availability affects HOW LONG restoration takes, not WHETHER
    # power is lost. The risk band above does not depend on available_crews.
    # ------------------------------------------------------------------
    restoration_factors: list[str] = []
    low_h: Optional[float]
    high_h: Optional[float]

    if available_crews < 1:
        # No crews available: we cannot estimate a finite restoration time.
        # Return an explicit "unknown" window rather than inventing a number
        # (and never divide/compute against zero crews).
        low_h = None
        high_h = None
        restoration_factors.append(
            "No repair crews are available for this area, so a restoration time "
            "cannot be estimated. Restoration begins once at least one crew is dispatched."
        )
    else:
        # Base repair time driven by upstream equipment count and storm severity
        base_hours_per_repair = {"low": 1.5, "medium": 2.5, "high": 4.0}[storm_severity]
        upstream_repairs_needed = max(1, profile["circuits_upstream"] - 1)  # fictional
        base_restore = upstream_repairs_needed * base_hours_per_repair

        restoration_factors.append(
            f"Estimated {upstream_repairs_needed} upstream equipment repair(s) at "
            f"~{base_hours_per_repair:.1f} h each under {storm_severity} severity"
        )

        # Crew effect: fewer crews extend the window (1 crew = slowest within 1–10).
        crew_factor = 1.0 + (0.15 * (10 - available_crews))  # 1.0–2.35× for crews 10..1
        base_restore *= crew_factor
        restoration_factors.append(
            f"{available_crews} crew(s) available — "
            + ("limited crews extend estimated window" if available_crews <= 3
               else ("adequate crews" if available_crews <= 6 else "strong crew availability"))
        )

        # Access blocked adds flat delay
        if access_blocked:
            base_restore += 3.0
            restoration_factors.append("Access blockage adds estimated +3 h delay before work can begin")

        # Underground looped can often restore faster via switching
        if profile["line_type"] == "underground" and profile["topology"] == "looped":
            base_restore *= 0.6
            restoration_factors.append(
                "Underground looped topology: switching may restore power before physical repair"
            )

        # Window: ±30% around base estimate
        low_h = round(base_restore * 0.70, 1)
        high_h = round(base_restore * 1.30, 1)

        # Sanity-clamp: min 0.5 h, max 72 h
        low_h = max(0.5, min(low_h, 72.0))
        high_h = max(low_h + 0.5, min(high_h, 72.0))

    # ------------------------------------------------------------------
    # 3. Preparation actions
    # ------------------------------------------------------------------
    prep: list[str] = [
        "Charge all phones, tablets, and portable power banks now.",
        "Keep refrigerator and freezer doors closed to preserve food.",
        "Locate flashlights and battery-powered lanterns, and check their batteries.",
        "Know where your main circuit breaker is located.",
    ]
    if storm_severity in ("medium", "high"):
        prep.append("Fill bathtubs with water for flushing if your pump is electric.")
        prep.append("Have cash on hand — ATMs and card readers may be offline.")
    if storm_severity == "high":
        prep.append("Consider relocating temporarily if heating/cooling is medically necessary.")
        prep.append("Contact neighbors to check on elderly or vulnerable residents.")
    if profile["medical_needs_declared"]:
        prep.append(
            "⚕️  This demo household's fictional profile declares a reliance on electric "
            "medical equipment. If this applies to you: ensure any battery backup is charged, "
            "keep a manual backup plan, and ask your AEP Ohio utility about medical certificate "
            "options. (A medical certificate under Ohio rules helps prevent disconnection for "
            "nonpayment; it does not guarantee restoration priority during storm outages.)"
        )
    if access_blocked:
        prep.append("Report road hazards or flooding to local emergency management.")

    # ------------------------------------------------------------------
    # 4. Alert eligibility — PROTOTYPE RULES ONLY
    # ------------------------------------------------------------------
    # These are StormReady prototype rules for which households the demo would
    # flag for an outage alert. They do NOT represent actual AEP enrollment,
    # verified program qualification, or any guaranteed restoration priority.
    #   Rule A: household declares medical electricity needs → eligible
    #           (drives communication urgency only, not physical outage risk)
    #   Rule B: storm severity HIGH and overhead lines → eligible
    #   Rule C: risk_band Critical → eligible
    #   Rule D: known restoration window lower bound > 8 h → eligible
    alert_eligible = (
        profile["medical_needs_declared"]
        or (storm_severity == "high" and profile["line_type"] == "overhead")
        or risk_band == "Critical"
        or (low_h is not None and low_h > 8.0)
    )

    # ------------------------------------------------------------------
    # 5. Assumptions / caveats
    # ------------------------------------------------------------------
    assumptions = [
        "All estimates are synthetic demo data — they do not reflect real AEP network records.",
        "Restoration window is derived from simplified rules, not live outage management data.",
        "Crew availability and blocked access affect the restoration-duration estimate only, "
        "not the likelihood of losing power.",
        "Crew routing, mutual-aid agreements, and actual storm track are not modeled.",
        "\"Alert eligible\" means the household meets StormReady's prototype notification rules — "
        "it does not mean the customer is enrolled in any AEP program, qualifies for one, or has "
        "guaranteed restoration priority.",
        "A household's declared medical electricity needs affect preparation and communication "
        "urgency only; they do not increase the physical likelihood of an outage.",
        "Risk factors are based on fictional household profiles, not real GIS data.",
    ]

    return {
        "risk_band": risk_band,
        "evidence_quality": "Low",   # always Low until real data is integrated
        "risk_factors": risk_factors,
        "restoration_low_hours": low_h,
        "restoration_high_hours": high_h,
        "restoration_factors": restoration_factors,
        "preparation_actions": prep,
        "alert_eligible": alert_eligible,
        "assumptions": assumptions,
        "source_label": "⚠️ SYNTHETIC DEMO — not AEP predictions",
    }
