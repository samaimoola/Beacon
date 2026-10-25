"""
tests/test_crew_comparison.py
=============================
Regression tests for "Would another crew help?".

  - The comparison is the current count vs EXACTLY one more crew, through the
    engine, within the supported maximum (10). At 10 nothing is evaluated.
  - No-damage and Unknown results are never blamed on a critical path.
  - A critical-path explanation appears only when the engine's scheduler says the
    schedule is dependency-limited.
  - used_counterfactual is True only when an engine comparison was computed.

Provider calls are MOCKED; no AWS access. Runnable: python -m tests.test_crew_comparison
"""

from __future__ import annotations
import asyncio
import json
import re

from concierge import assistant as A
from concierge import grounding as G
from concierge import provider as P
from engine import restoration as R
from engine.api import evaluate_scenario, get_customers, get_damage_scenarios, schedule_summary
from engine.contracts import AVAILABLE_CREWS_MAX

_NOT_READY = P.ProviderStatus(True, False, False, False, False, "no config")
_READY = P.ProviderStatus(True, True, True, True, True, None)
_HOURS = re.compile(r"\b\d+(?:\.\d+)?\s*(?:h|hours?|hrs?)\b")


def _cust():
    c = get_customers()[0]
    return c["id"], c["label"]


def _inputs(label, dmg, crews, sev="medium", access=False):
    return {"customer_label": label, "storm_severity": sev, "available_crews": crews,
            "access_blocked": access, "damage_scenario": dmg}


def _ask(question, dmg, crews, *, sev="medium", access=False, evaluate_fn=evaluate_scenario,
         schedule_fn=None, status=_NOT_READY, converse=None):
    cid, label = _cust()
    inputs = _inputs(label, dmg, crews, sev, access)
    result = evaluate_scenario(cid, sev, crews, access, damage_scenario=dmg)
    orig_status, orig_converse = A._provider.provider_status, A._provider.converse
    A._provider.provider_status = lambda: status
    if converse is not None:
        A._provider.converse = converse
    try:
        reply = A.answer_question(
            question, customer_id=cid, customer_label=label, inputs=inputs, result=result,
            backend_name="real", evaluate_fn=evaluate_fn,
            damage_scenarios=get_damage_scenarios(cid), schedule_fn=schedule_fn,
        )
    finally:
        A._provider.provider_status, A._provider.converse = orig_status, orig_converse
    return reply, inputs, result


def _spy():
    calls = []

    def fn(**kw):
        calls.append(kw)
        return evaluate_scenario(**kw)
    return fn, calls


# --------------------------------------------------------------------------
# Ordinary count: exactly one more crew, same scenario, active inputs untouched
# --------------------------------------------------------------------------

def test_ordinary_count_compares_exactly_one_more():
    spy, calls = _spy()
    reply, inputs, _ = _ask("Would another crew help?", "pole_and_span", 4, access=True, evaluate_fn=spy)
    assert len(calls) == 1, calls
    cf = calls[0]
    assert cf["available_crews"] == 5, "4 crews must be compared with 5, not 10"
    assert cf["storm_severity"] == "medium" and cf["access_blocked"] is True
    assert cf["damage_scenario"] == "pole_and_span"
    assert cf["customer_id"] == _cust()[0]
    assert inputs["available_crews"] == 4, "the active scenario must not be mutated"
    assert reply.used_counterfactual is True
    assert "5 instead of 4" in reply.text


def test_crews_help_when_jobs_can_run_in_parallel():
    reply, _, res = _ask("Would another crew help?", "multi_damage", 1)
    two = evaluate_scenario(_cust()[0], "medium", 2, False, damage_scenario="multi_damage")
    from engine.formatting import format_window as fw
    assert fw(res["restoration_low_hours"], res["restoration_high_hours"]) in reply.text
    assert fw(two["restoration_low_hours"], two["restoration_high_hours"]) in reply.text
    assert "critical path" not in reply.text.lower()
    assert reply.used_counterfactual is True


# --------------------------------------------------------------------------
# Maximum: never evaluate 11; say the maximum is already in use
# --------------------------------------------------------------------------

def test_at_maximum_does_not_evaluate_beyond_supported():
    spy, calls = _spy()
    reply, _, _ = _ask("Would another crew help?", "multi_damage", AVAILABLE_CREWS_MAX, evaluate_fn=spy)
    assert calls == [], f"no engine call beyond the maximum, got {calls}"
    t = reply.text.lower()
    assert "already uses 10 crews" in t and "most" in t
    assert "11" not in reply.text
    assert "critical path" not in t
    assert reply.used_counterfactual is False, "nothing was compared, so the flag must be False"


def test_at_maximum_live_payload_marks_status():
    seen = {}

    def converse(sysp, msg):
        seen["sys"], seen["msg"] = sysp, msg
        return P.ProviderResult(ok=True, text="MOCK", error=None)

    reply, _, _ = _ask("Would another crew help?", "pole_and_span", 10, status=_READY, converse=converse)
    payload = json.loads(seen["msg"].split("\n\n", 1)[1])
    cmp = payload["engine_crew_comparison"]
    assert cmp["status"] == "at_maximum" and cmp["compared_crews"] is None
    assert cmp["max_supported_crews"] == 10
    assert reply.mode == "live" and reply.used_counterfactual is False


# --------------------------------------------------------------------------
# No modeled damage / Unknown: explain the real reason, never a critical path
# --------------------------------------------------------------------------

def test_no_damage_explains_no_jobs_and_keeps_caveat():
    reply, _, _ = _ask("Would another crew help?", "none", 4)
    t = reply.text.lower()
    assert "no repair jobs for another crew to shorten" in t
    assert "not guarantee uninterrupted power" in t
    assert "critical path" not in t and "dependency" not in t
    assert reply.used_counterfactual is True


def test_unknown_estimate_explains_missing_information():
    reply, _, _ = _ask("Would another crew help?", "unmapped_asset", 4)
    t = reply.text.lower()
    assert "unknown" in t and "labor-hour reference" in t
    assert "critical path" not in t and "dependency" not in t
    assert not _HOURS.search(t), f"must not state hours: {reply.text}"


# --------------------------------------------------------------------------
# Genuine dependency limit (engine-backed)
# --------------------------------------------------------------------------

def test_dependency_limited_result_mentions_critical_path():
    cid, _ = _cust()
    # Engine facts: unchanged with one more crew AND the scheduler is at its critical path.
    three = evaluate_scenario(cid, "medium", 3, False, damage_scenario="multi_damage")
    four = evaluate_scenario(cid, "medium", 4, False, damage_scenario="multi_damage")
    assert (three["restoration_low_hours"], three["restoration_high_hours"]) == \
           (four["restoration_low_hours"], four["restoration_high_hours"])
    assert schedule_summary(cid, "medium", 3, False, "multi_damage")["dependency_limited"] is True
    reply, _, _ = _ask("Would more crews help?", "multi_damage", 3)
    assert "critical path" in reply.text.lower()
    assert "does not change" in reply.text.lower()


def test_unchanged_but_not_dependency_limited_is_not_blamed_on_critical_path():
    # Four equal independent jobs: 2 and 3 crews both need two "rounds", but the
    # critical path is a single job — the limit is packing, not dependencies.
    jobs = [R.RepairJob(task=f"j{i}", direct_hours=1.0) for i in range(4)]
    s2 = R.schedule(jobs, crews=2, ilm=1.0, access_blocked=False)
    s3 = R.schedule(jobs, crews=3, ilm=1.0, access_blocked=False)
    assert s2.elapsed_hours == s3.elapsed_hours == 2.0
    assert s2.critical_path_hours == 1.0 and s2.dependency_limited is False

    # Same situation through the classifier: stubbed engine returns the same window
    # for 2 and 3 crews, and the stubbed scheduler reports it is NOT dependency-limited.
    fixed = {"risk_band": "Moderate", "restoration_low_hours": 1.6, "restoration_high_hours": 2.7,
             "alert_eligible": False}
    cmp = A._crew_comparison(
        lambda **kw: dict(fixed),
        lambda **kw: {"repair_jobs": 4, "unknown_jobs": 0, "dependency_limited": False,
                      "critical_path_hours": 1.0, "access_delay_hours": 0.0},
        "x", _inputs("x", "multi_damage", 2), dict(fixed),
    )
    assert cmp["basis"] == "not_dependency_limited"
    text = G.fallback_answer("Would another crew help?", {"current_scenario": {}}, cmp).lower()
    assert "does not change" in text
    assert "not at its critical-path limit" in text
    assert "already at its critical path" not in text and "cannot shorten" not in text


def test_no_schedule_facts_never_claims_critical_path():
    fixed = {"risk_band": "Moderate", "restoration_low_hours": 4.0, "restoration_high_hours": 6.0}
    cmp = A._crew_comparison(lambda **kw: dict(fixed), None, "x",
                             _inputs("x", None, 5), dict(fixed))
    assert cmp["basis"] == "unexplained_no_change"
    text = G.fallback_answer("Would another crew help?", {"current_scenario": {}}, cmp).lower()
    assert "critical path" not in text and "cannot say which limit applies" in text


def test_comparison_failure_is_truthful():
    def boom(**kw):
        raise RuntimeError("engine down")
    reply, _, _ = _ask("Would another crew help?", "pole_and_span", 4, evaluate_fn=boom)
    assert reply.used_counterfactual is False
    assert "could not compute" in reply.text.lower()


# --------------------------------------------------------------------------
# Distinctions reach the live model
# --------------------------------------------------------------------------

def test_live_payload_carries_basis_and_facts():
    seen = {}

    def converse(sysp, msg):
        seen["sys"], seen["msg"] = sysp, msg
        return P.ProviderResult(ok=True, text="MOCK", error=None)

    for dmg, crews, basis in (("none", 4, "no_repairs_modeled"),
                              ("unmapped_asset", 4, "estimate_unknown"),
                              ("multi_damage", 3, "dependency_limited"),
                              ("multi_damage", 1, "crew_limited")):
        reply, _, _ = _ask("Would another crew help?", dmg, crews, status=_READY, converse=converse)
        cmp = json.loads(seen["msg"].split("\n\n", 1)[1])["engine_crew_comparison"]
        assert cmp["status"] == "compared" and cmp["basis"] == basis, (dmg, cmp["basis"])
        assert cmp["compared_crews"] == crews + 1
        assert cmp["engine_facts"], "facts must be supplied to the model"
        if basis != "dependency_limited":
            assert any("critical path" in m for m in cmp["must_not"]), cmp["must_not"]
        assert reply.mode == "live" and reply.used_counterfactual is True
    sp = seen["sys"]
    assert "dependency_limited" in sp and "at_maximum" in sp and "EXACTLY ONE more crew" in sp


def test_api_route_crew_question_at_maximum():
    """The FastAPI bridge (called directly, no HTTP client needed) honors the maximum."""
    import api_server
    cid, label = _cust()
    orig = A._provider.provider_status
    A._provider.provider_status = lambda: _NOT_READY
    try:
        req = api_server.ConciergeRequest(
            question="Would another crew help?", customer_id=cid, customer_label=label,
            inputs={"storm_severity": "medium", "available_crews": 10, "access_blocked": False,
                    "damage_scenario": "pole_and_span"},
        )
        out = asyncio.run(api_server.api_concierge_ask(req))
    finally:
        A._provider.provider_status = orig
    assert out["mode"] == "fallback" and out["used_counterfactual"] is False
    assert "already uses 10 crews" in out["text"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} crew-comparison tests passed")
