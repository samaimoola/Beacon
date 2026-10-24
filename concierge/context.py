"""
concierge/context.py
====================
Builds the ALLOWLISTED context object handed to the assistant.

Only an explicit allowlist of fields is ever included. Everything else — raw
premise numbers, addresses, meter identifiers, employee fields, precise
coordinates, and the original datasets — is excluded by construction (we copy
named fields in, rather than passing engine/UI dicts through).

The context is plain JSON-serialisable data so it can be logged/inspected
safely and sent to the provider without leaking PII.
"""

from __future__ import annotations
from typing import Optional

# Fields copied verbatim from an engine result. Anything not listed here is
# dropped. (The engine result is already PII-free, but we allowlist anyway so a
# future engine field cannot silently leak into the prompt.)
_RESULT_ALLOWLIST = (
    "risk_band",
    "evidence_quality",
    "risk_factors",
    "restoration_low_hours",
    "restoration_high_hours",
    "restoration_factors",
    "preparation_actions",
    "alert_eligible",
    "assumptions",
    "source_label",
)

# Scenario-input fields copied verbatim. Note: customer_label is an anonymized
# household label (e.g. "Real premise 2 — Overhead, circuit CIR3"); we pass the
# label, never the underlying premise id/number.
_INPUT_ALLOWLIST = (
    "customer_label",
    "storm_severity",
    "available_crews",
    "access_blocked",
    "damage_scenario",
)

# Belt-and-braces: field-name fragments that must NEVER appear in the context.
# Used by a self-check (and the tests) to catch accidental leakage.
FORBIDDEN_FIELD_FRAGMENTS = (
    "premise_nu", "premise_number", "address", "street", "road_name",
    "meter", "macss", "latitude", "longitude", "coord", "owner_name",
    "employee", "customer_c", "aep_xfmr_l", "aep_locati", "global_id",
)


def _pick(d: Optional[dict], allowlist) -> Optional[dict]:
    if not d:
        return None
    return {k: d.get(k) for k in allowlist if k in d}


def _scenario_label(scenario_id, scenarios) -> Optional[str]:
    if not scenario_id or not scenarios:
        return scenario_id
    for s in scenarios:
        if s.get("id") == scenario_id:
            return s.get("label", scenario_id)
    return scenario_id


def build_context(
    *,
    customer_label: str,
    inputs: dict,
    result: dict,
    backend_name: str,
    damage_scenarios: Optional[list] = None,
    prev_inputs: Optional[dict] = None,
    prev_result: Optional[dict] = None,
    input_changes: Optional[list] = None,
) -> dict:
    """
    Construct the allowlisted context object.

    Parameters mirror what app.py already computes. `input_changes` is a list of
    (field_label, before, after) tuples describing the most recent meaningful
    change, if any.
    """
    current_inputs = _pick(inputs, _INPUT_ALLOWLIST) or {}
    # Replace the raw damage_scenario id with its human label when we can.
    if current_inputs.get("damage_scenario"):
        current_inputs["damage_scenario"] = _scenario_label(
            current_inputs["damage_scenario"], damage_scenarios
        )

    ctx: dict = {
        "household_label": customer_label,
        "backend": backend_name,  # "real" or "demo"
        "current_scenario": {
            "inputs": current_inputs,
            "result": _pick(result, _RESULT_ALLOWLIST),
        },
        "previous_scenario": None,
        "input_changes": None,
        # Approved guidance is injected by the assistant from grounding.py so the
        # model uses pre-approved safety text rather than inventing instructions.
    }

    if prev_result and prev_inputs:
        prev_in = _pick(prev_inputs, _INPUT_ALLOWLIST) or {}
        if prev_in.get("damage_scenario"):
            prev_in["damage_scenario"] = _scenario_label(
                prev_in["damage_scenario"], damage_scenarios
            )
        ctx["previous_scenario"] = {
            "inputs": prev_in,
            "result": _pick(prev_result, _RESULT_ALLOWLIST),
        }

    if input_changes:
        # Normalise to simple serialisable dicts.
        ctx["input_changes"] = [
            {"field": f, "from": before, "to": after}
            for (f, before, after) in input_changes
        ]

    return ctx


def assert_no_forbidden_fields(ctx: dict) -> None:
    """
    Defensive self-check: raise if any forbidden field fragment appears anywhere
    in the context (keys or stringified values). Used by tests and callable in
    production as a cheap guard.
    """
    import json
    blob = json.dumps(ctx, default=str).lower()
    hits = [frag for frag in FORBIDDEN_FIELD_FRAGMENTS if frag in blob]
    if hits:
        raise ValueError(f"Context contains forbidden field fragment(s): {hits}")
