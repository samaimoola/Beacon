"""
tests/test_declared_needs.py
============================
Optional customer-declared needs ("I rely on electricity-dependent medical
equipment", "I may need accessibility assistance during an outage").

Verifies that declarations:
  - are allowlisted booleans only (no free text / unknown keys pass through);
  - change preparation guidance, notice wording, and concierge context/fallback;
  - leave risk, restoration hours, factors, crews, and alert eligibility unchanged;
  - are part of the concierge context identity and "What changed?" comparison;
  - keep existing callers working (default None == previous behavior).

Provider calls are MOCKED; no AWS access. Runnable: python -m tests.test_declared_needs
"""

from __future__ import annotations
import asyncio
import json

from concierge import assistant as A
from concierge import context as C
from concierge import grounding as G
from concierge import provider as P
from engine import api, demo, needs as ND
from engine import notifications as N
from engine.contracts import STORM_SEVERITY_OPTIONS

MED = {"medical_equipment": True, "accessibility_assistance": False}
ACC = {"medical_equipment": False, "accessibility_assistance": True}
BOTH = {"medical_equipment": True, "accessibility_assistance": True}
NONE = {"medical_equipment": False, "accessibility_assistance": False}

# Every field that describes the PHYSICAL scenario. Declarations must not touch these.
_PHYSICAL = ("risk_band", "evidence_quality", "risk_factors", "restoration_low_hours",
             "restoration_high_hours", "restoration_factors", "alert_eligible", "source_label")


def _cust(i=0):
    c = api.get_customers()[i]
    return c["id"], c["label"]


# --------------------------------------------------------------------------
# Allowlisting
# --------------------------------------------------------------------------

def test_normalize_keeps_only_two_strict_booleans():
    raw = {"medical_equipment": "true", "accessibility_assistance": True,
           "diagnosis": "something private", "device": "model X", "address": "1 Main St"}
    assert ND.normalize_declared_needs(raw) == {"medical_equipment": False,
                                                "accessibility_assistance": True}
    assert ND.normalize_declared_needs(None) == NONE
    assert ND.normalize_declared_needs("medical") == NONE


# --------------------------------------------------------------------------
# Engine: guidance changes, numbers do not
# --------------------------------------------------------------------------

def test_declarations_change_guidance_not_numbers():
    checked = 0
    for c in api.get_customers():
        for s in api.get_damage_scenarios(c["id"]):
            for sev in STORM_SEVERITY_OPTIONS:
                for crews in (1, 4, 10):
                    for access in (False, True):
                        args = (c["id"], sev, crews, access, s["id"])
                        base = api.evaluate_scenario(*args)
                        for needs in (MED, ACC, BOTH):
                            got = api.evaluate_scenario(*args, declared_needs=needs)
                            for k in _PHYSICAL:
                                assert got[k] == base[k], (k, args, needs)
                            for line in ND.declared_needs_guidance(needs):
                                assert line in got["preparation_actions"], line
                            assert got["preparation_actions"] != base["preparation_actions"]
                            checked += 1
    assert checked > 0


def test_needs_guidance_is_listed_first_and_complete():
    cid, _ = _cust()
    got = api.evaluate_scenario(cid, "high", 4, False, "pole_and_span", declared_needs=BOTH)
    g = ND.declared_needs_guidance(BOTH)
    assert got["preparation_actions"][:len(g)] == g, "declared-needs guidance must come first"
    assert ND.ESCALATION_GUIDANCE in got["preparation_actions"]
    assert got["preparation_actions"].count(ND.ESCALATION_GUIDANCE) == 1
    assert ND.DECLARED_NEEDS_NOTE in got["assumptions"]


def test_default_and_all_false_match_previous_behavior():
    cid, _ = _cust()
    base = api.evaluate_scenario(cid, "medium", 3, False, "multi_damage")
    assert api.evaluate_scenario(cid, "medium", 3, False, "multi_damage", declared_needs=None) == base
    assert api.evaluate_scenario(cid, "medium", 3, False, "multi_damage", declared_needs=NONE) == base


def test_demo_backend_also_unchanged_numerically():
    orig = api._backend
    api._backend = demo
    try:
        cid = demo.get_customers()[1]["id"]  # fictional household with a declared profile
        base = api.evaluate_scenario(cid, "high", 2, True)
        got = api.evaluate_scenario(cid, "high", 2, True, declared_needs=ACC)
        for k in _PHYSICAL:
            assert got[k] == base[k], k
        assert ND.DECLARED_NEED_GUIDANCE["accessibility_assistance"][0] in got["preparation_actions"]
    finally:
        api._backend = orig


# --------------------------------------------------------------------------
# Notification previews: wording changes, decision does not
# --------------------------------------------------------------------------

def test_notice_wording_tailored_but_decision_unchanged():
    cid, label = _cust()
    res = api.evaluate_scenario(cid, "medium", 3, False, "pole_and_span")
    base_in = {"customer_label": label, "storm_severity": "medium"}
    for state in N.LIFECYCLE_STATES:
        base = N.build_notification_preview(lifecycle_state=state, inputs=base_in, result=res,
                                            prev_result=dict(res))
        got = N.build_notification_preview(lifecycle_state=state,
                                           inputs=dict(base_in, declared_needs=BOTH),
                                           result=res, prev_result=dict(res))
        for k in ("send_recommended", "send_blockers", "scenario_eligible", "recommended_channel",
                  "estimate_window", "estimate_change", "timing", "consent_status"):
            assert got[k] == base[k], (state, k)
        msg = got["message"]
        assert msg.startswith(base["message"]), "base preview text must be kept intact"
        assert "electricity-dependent medical equipment" in msg
        assert "accessibility assistance" in msg
        assert "call 911" in msg
        assert "does not change restoration priority" in msg
        assert "electricity-dependent" not in base["message"]


# --------------------------------------------------------------------------
# Concierge: allowlisted context, identity, fallback without truncation
# --------------------------------------------------------------------------

def _ctx(needs, prev_needs=None, crews=3):
    cid, label = _cust()
    inputs = {"customer_label": label, "storm_severity": "high", "available_crews": crews,
              "access_blocked": False, "damage_scenario": "pole_and_span",
              "declared_needs": needs}
    res = api.evaluate_scenario(cid, "high", crews, False, "pole_and_span", declared_needs=needs)
    kw = {}
    if prev_needs is not None:
        kw = dict(prev_inputs=dict(inputs, declared_needs=prev_needs),
                  prev_result=api.evaluate_scenario(cid, "high", crews, False, "pole_and_span",
                                                    declared_needs=prev_needs))
    return C.build_context(customer_label=label, inputs=inputs, result=res, backend_name="real",
                           damage_scenarios=api.get_damage_scenarios(cid), **kw)


def test_context_carries_only_booleans_and_prewritten_guidance():
    dirty = dict(MED, diagnosis="private condition", device_model="XYZ-1")
    ctx = _ctx(dirty)
    assert ctx["declared_needs"] == MED
    assert ctx["current_scenario"]["inputs"]["declared_needs"] == MED
    assert ctx["declared_needs_guidance"] == ND.declared_needs_guidance(MED)
    assert ctx["declared_needs_note"] == ND.DECLARED_NEEDS_NOTE
    blob = json.dumps(ctx).lower()
    assert "private condition" not in blob and "xyz-1" not in blob and "diagnosis" not in blob
    C.assert_no_forbidden_fields(ctx)
    plain = _ctx(None)
    assert plain["declared_needs"] == NONE and plain["declared_needs_guidance"] == []
    assert plain["declared_needs_note"] is None


def test_context_identity_reflects_changed_needs():
    ctx = _ctx(BOTH, prev_needs=NONE)
    assert ctx["previous_scenario"]["inputs"]["declared_needs"] == NONE
    assert ctx["current_scenario"]["inputs"]["declared_needs"] == BOTH
    # Physical numbers identical across the two readings.
    cur, prev = ctx["current_scenario"]["result"], ctx["previous_scenario"]["result"]
    for k in ("risk_band", "restoration_low_hours", "restoration_high_hours", "alert_eligible"):
        assert cur[k] == prev[k], k


def test_api_change_list_reports_declared_needs():
    import api_server
    cid, _ = _cust()
    base = {"storm_severity": "medium", "available_crews": 4, "access_blocked": False,
            "damage_scenario": "none"}
    changes = api_server.compute_input_changes(cid, dict(base), cid, dict(base, declared_needs=MED))
    assert changes == [("Declared needs", "None declared", "Medical equipment")], changes
    # Free-text noise in the payload is ignored, so no spurious change appears.
    same = api_server.compute_input_changes(cid, dict(base, declared_needs=NONE), cid,
                                            dict(base, declared_needs={"note": "hello"}))
    assert same == []


def test_fallback_prepare_answer_includes_all_needs_guidance():
    ctx = _ctx(BOTH)
    text = G.fallback_answer("What should I do now?", ctx)
    for line in ND.declared_needs_guidance(BOTH):
        assert line in text, f"missing (truncated?): {line}"
    for line in ctx["current_scenario"]["result"]["preparation_actions"]:
        assert line in text, f"engine guidance dropped: {line}"
    assert ND.DECLARED_NEEDS_NOTE in text
    assert text.index(ND.DECLARED_NEED_GUIDANCE["medical_equipment"][0]) < text.index("For this scenario:")


def test_live_payload_includes_declarations_and_rules():
    cid, label = _cust()
    inputs = {"customer_label": label, "storm_severity": "medium", "available_crews": 4,
              "access_blocked": False, "damage_scenario": "pole_and_span", "declared_needs": ACC}
    res = api.evaluate_scenario(cid, "medium", 4, False, "pole_and_span", declared_needs=ACC)
    seen = {}
    o_status, o_conv = A._provider.provider_status, A._provider.converse
    A._provider.provider_status = lambda: P.ProviderStatus(True, True, True, True, True, None)
    A._provider.converse = lambda s, m: (seen.update(sys=s, msg=m)
                                         or P.ProviderResult(ok=True, text="MOCK", error=None))
    try:
        reply = A.answer_question("What should I do now?", customer_id=cid, customer_label=label,
                                  inputs=inputs, result=res, backend_name="real",
                                  evaluate_fn=api.evaluate_scenario)
    finally:
        A._provider.provider_status, A._provider.converse = o_status, o_conv
    payload = json.loads(seen["msg"].split("\n\n", 1)[1])
    assert payload["context"]["declared_needs"] == ACC
    assert payload["context"]["declared_needs_guidance"] == ND.declared_needs_guidance(ACC)
    assert "restoration priority" in seen["sys"] and "declared_needs" in seen["sys"]
    assert reply.mode == "live"


def test_api_evaluate_route_accepts_declarations():
    import api_server
    cid, _ = _cust()
    req = dict(customer_id=cid, storm_severity="medium", available_crews=4, access_blocked=False,
               damage_scenario="pole_and_span")
    base = asyncio.run(api_server.api_evaluate_scenario(api_server.ScenarioRequest(**req)))
    got = asyncio.run(api_server.api_evaluate_scenario(
        api_server.ScenarioRequest(**req, declared_needs=MED)))
    for k in _PHYSICAL:
        assert got[k] == base[k], k
    assert got["preparation_actions"][0] == ND.DECLARED_NEED_GUIDANCE["medical_equipment"][0]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} declared-needs tests passed")
