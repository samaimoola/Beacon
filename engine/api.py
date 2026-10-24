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
# Prefer the real-data backend when its PII-free processed dataset is present
# (built via `python -m scripts.build_processed`). Otherwise fall back to the
# clearly-labeled synthetic demo so the UI always runs.
#
# Override with the STORMREADY_BACKEND environment variable:
#   STORMREADY_BACKEND=demo   -> force synthetic demo
#   STORMREADY_BACKEND=real   -> force real data (errors if unavailable)
#   STORMREADY_BACKEND=auto   -> default: real if available, else demo

import os

from engine import demo
from engine import realdata


def _select_backend():
    choice = os.environ.get("STORMREADY_BACKEND", "auto").strip().lower()
    if choice == "demo":
        return demo
    if choice == "real":
        return realdata  # intentionally no fallback when explicitly requested
    # auto
    return realdata if realdata.is_available() else demo


_backend = _select_backend()


def active_backend_name() -> str:
    """Return 'real' or 'demo' — which backend is currently serving requests."""
    return "real" if _backend is realdata else "demo"

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


def get_damage_scenarios(customer_id: str) -> list[dict]:
    """
    Return the available damage-scenario presets for a customer.

    Each item: {"id", "label", "description", "damaged_assets", "jobs"}.
    Both backends implement this; the synthetic demo returns a single
    placeholder entry.
    """
    return _backend.get_damage_scenarios(customer_id)


def evaluate_scenario(
    customer_id: str,
    storm_severity: str,
    available_crews: int,
    access_blocked: bool,
    damage_scenario: str | None = None,
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
    damage_scenario : str | None, optional
        One of the ids from get_damage_scenarios(customer_id). When None, the
        backend applies a sensible default so existing callers keep working.
        Accepted but ignored by the synthetic demo backend.

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
        damage_scenario=damage_scenario,
    )
