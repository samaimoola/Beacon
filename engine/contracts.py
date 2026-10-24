"""
engine/contracts.py
===================
Shared data contract between the engine layer and the UI.

This file is the single source of truth for:
  - allowed input values and their types
  - required output fields and their types
  - an example response for documentation and testing

Both engine/api.py and ui/ must conform to this contract.
Changes here require coordination between engine and UI owners.

Owner: shared — changes need agreement from Samai (engine) AND roommate (UI).
"""

from __future__ import annotations
from typing import Optional

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

# Storm severity levels (str)
#   "low"    – minor wind/rain, isolated outages expected
#   "medium" – moderate storm, widespread outages possible
#   "high"   – major event (tornado, ice storm), significant infrastructure damage expected
STORM_SEVERITY_OPTIONS: list[str] = ["low", "medium", "high"]

# Available crews (int, 1–10)
#   Represents the number of field repair crews AEP can dispatch to this area.
#   1 = severely constrained (mutual-aid event or remote area)
#   10 = full staffing
AVAILABLE_CREWS_MIN: int = 1
AVAILABLE_CREWS_MAX: int = 10

# Access blocked (bool)
#   True  = road damage, flooding, or debris blocks crew access
#   False = standard access
ACCESS_BLOCKED_OPTIONS: list[bool] = [False, True]

# damage_scenario (Optional[str]) — OPTIONAL, added in Pass 2.
#   Selects one of the SIMULATED damage-scenario presets for the chosen premise,
#   as returned by get_damage_scenarios(customer_id). When None (the default),
#   the backend applies a sensible default preset, so existing callers that omit
#   this argument keep working unchanged.
#   The synthetic demo backend accepts the argument for signature compatibility
#   but does not use preset-driven damage.

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

# risk_band (str): one of "Low", "Moderate", "High", "Critical"
RISK_BAND_OPTIONS: list[str] = ["Low", "Moderate", "High", "Critical"]

# evidence_quality (str): one of "High", "Medium", "Low"
#   Reflects how much real data backs this estimate (always "Low" in demo).
EVIDENCE_QUALITY_OPTIONS: list[str] = ["High", "Medium", "Low"]

# restoration_low_hours (Optional[float]):
#   Lower bound of the restoration window in hours.
#   May be None if an estimate cannot be made.

# restoration_high_hours (Optional[float]):
#   Upper bound of the restoration window in hours.
#   May be None if an estimate cannot be made.

# source_label (str): human-readable label clarifying data provenance.
#   Always "⚠️ SYNTHETIC DEMO — not AEP predictions" in milestone 1.

# ---------------------------------------------------------------------------
# Type alias for the evaluate_scenario return value
# ---------------------------------------------------------------------------

ScenarioResult = dict  # keys documented below in EXAMPLE_RESPONSE

# ---------------------------------------------------------------------------
# Contract example (also used as a smoke-test fixture)
# ---------------------------------------------------------------------------

EXAMPLE_RESPONSE: ScenarioResult = {
    # --- risk assessment ---
    "risk_band": "High",          # str: Low | Moderate | High | Critical
    "evidence_quality": "Low",    # str: High | Medium | Low
    "risk_factors": [             # list[str]: human-readable contributing factors
        "High storm severity forecast",
        "Overhead primary lines exposed to wind",
        "No backup feed (single-source transformer)",
    ],

    # --- restoration estimate ---
    "restoration_low_hours": 4.0,    # float | None
    "restoration_high_hours": 12.0,  # float | None
    "restoration_factors": [         # list[str]: what drives this window
        "Moderate crew availability (3 crews)",
        "Access route is clear",
        "Estimated 2–3 upstream equipment repairs needed",
    ],

    # --- preparation guidance ---
    "preparation_actions": [         # list[str]: actionable steps for the customer
        "Charge devices and backup batteries now.",
        "Fill prescriptions if medications require refrigeration.",
        "Locate flashlights and candles.",
        "Know the location of your circuit breaker.",
    ],

    # --- alert eligibility ---
    "alert_eligible": True,          # bool: meets prototype notification criteria

    # --- metadata ---
    "assumptions": [                 # list[str]: limitations and caveats
        "Estimate based on synthetic demo data — not real network topology.",
        "Actual restoration time depends on damage assessment after the storm.",
        "Crew routing and mutual-aid availability not modeled in this version.",
    ],
    "source_label": "⚠️ SYNTHETIC DEMO — not AEP predictions",
}
