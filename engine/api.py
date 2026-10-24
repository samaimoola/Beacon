"""
engine/api.py
=============
Public interface that the UI imports.

This is the ONLY engine module the UI should import.
It delegates to the appropriate backend (currently: demo).

Owner: Samai (engine/)
Swap `_backend` to point at a real implementation when GIS data is ready.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------
# In milestone 1 we always use the synthetic demo backend.
# Future milestones can add:
#   from engine import gis_backend as _backend   (real data)
#   from engine import ml_backend as _backend    (trained model)
# and switch based on an environment flag or data availability.

from engine import demo as _backend

# ---------------------------------------------------------------------------
# Public API — shape must match engine/contracts.py
# ---------------------------------------------------------------------------

def get_customers() -> list[dict]:
    """
    Return a list of available demo customers.

    Returns
    -------
    list of dicts, each with keys:
        id    (str)  – opaque identifier, pass back to evaluate_scenario
        label (str)  – human-readable anonymized description shown in the UI
    """
    return _backend.get_customers()


def evaluate_scenario(
    customer_id: str,
    storm_severity: str,
    available_crews: int,
    access_blocked: bool,
) -> dict:
    """
    Evaluate outage risk and restoration estimate for a given scenario.

    Parameters
    ----------
    customer_id : str
        One of the ids returned by get_customers().
    storm_severity : str
        "low" | "medium" | "high"
    available_crews : int
        1–10 — number of field repair crews available for dispatch.
    access_blocked : bool
        True if road damage / flooding blocks crew access.

    Returns
    -------
    dict with keys (all required unless marked optional):
        risk_band            str           "Low" | "Moderate" | "High" | "Critical"
        evidence_quality     str           "High" | "Medium" | "Low"
        risk_factors         list[str]     contributing factors
        restoration_low_hours   float|None  lower bound of restoration window (hours)
        restoration_high_hours  float|None  upper bound (hours); None = unknown
        restoration_factors  list[str]     what drives the window
        preparation_actions  list[str]     actionable steps for the customer
        alert_eligible       bool          meets prototype notification criteria
        assumptions          list[str]     caveats and limitations
        source_label         str           data provenance notice
    """
    return _backend.evaluate_scenario(
        customer_id=customer_id,
        storm_severity=storm_severity,
        available_crews=available_crews,
        access_blocked=access_blocked,
    )
