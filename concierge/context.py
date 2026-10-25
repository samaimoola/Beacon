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

from engine import needs as _needs

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


def _pick_inputs(inputs: Optional[dict], damage_scenarios) -> dict:
    """Allowlisted scenario inputs plus the two normalized declared-need booleans."""
    picked = _pick(inputs, _INPUT_ALLOWLIST) or {}
    if picked.get("damage_scenario"):
        picked["damage_scenario"] = _scenario_label(picked["damage_scenario"], damage_scenarios)
    # Declarations are explicit customer choices. Only two booleans pass through —
    # never free text — so the context identity reflects the needs the answer used.
    picked["declared_needs"] = _needs.normalize_declared_needs((inputs or {}).get("declared_needs"))
    return picked


def _estimate_notes(result: Optional[dict]) -> dict:
    """
    Grounded flags + required phrasing for special restoration states, so the
    model reflects the correct caveats instead of over-reassuring.

    - no_damage_modeled: a true 0–0 window from a "no damage" preset. The answer
      MUST state this does NOT guarantee uninterrupted power.
    - estimate_unknown: a None window (e.g. unmapped asset). The answer MUST say
      the duration is unknown and MUST NOT invent a number.
    """
    notes = {
        "no_damage_modeled": False,
        "estimate_unknown": False,
        "required_caveats": [],
    }
    if not result:
        return notes
    low = result.get("restoration_low_hours")
    high = result.get("restoration_high_hours")
    if low is None or high is None:
        notes["estimate_unknown"] = True
        notes["required_caveats"].append(
            "The restoration estimate is UNKNOWN for this scenario. State that it is unknown "
            "and do NOT invent or guess a duration."
        )
    elif low == 0 and high == 0:
        notes["no_damage_modeled"] = True
        notes["required_caveats"].append(
            "This scenario models NO equipment damage, so there are 'No repairs modeled' (0 hours "
            "of modeled repair work). You MUST clarify this does NOT guarantee uninterrupted power "
            "in a real storm — it only means this particular simulated scenario includes no damage."
        )
    return notes


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
    # Damage preset ids are replaced by their human labels when we can.
    current_inputs = _pick_inputs(inputs, damage_scenarios)
    needs = current_inputs["declared_needs"]

    picked_result = _pick(result, _RESULT_ALLOWLIST)

    ctx: dict = {
        "household_label": customer_label,
        "backend": backend_name,  # "real" or "demo"
        "current_scenario": {
            "inputs": current_inputs,
            "result": picked_result,
        },
        # Derived, grounded notes about special estimate states. These are facts
        # about the current engine result, phrased so the model MUST reflect the
        # required caveats (no-damage is not a guarantee; unknown is not a number).
        "estimate_notes": _estimate_notes(picked_result),
        # Customer-declared needs (explicit opt-in booleans, never inferred) and the
        # PREWRITTEN guidance they unlock. They never change risk or restoration.
        "declared_needs": needs,
        "declared_needs_guidance": _needs.declared_needs_guidance(needs),
        "declared_needs_note": _needs.DECLARED_NEEDS_NOTE if any(needs.values()) else None,
        "previous_scenario": None,
        "input_changes": None,
        # Approved guidance is injected by the assistant from grounding.py so the
        # model uses pre-approved safety text rather than inventing instructions.
    }

    if prev_result and prev_inputs:
        prev_in = _pick_inputs(prev_inputs, damage_scenarios)
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
