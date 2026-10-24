"""
tests/test_concierge.py
=======================
Focused tests for the live-AI concierge. Provider calls are MOCKED — no real
AWS access is used. A fallback or mocked answer is never treated as "verified
live AI".

Runnable standalone:  python -m tests.test_concierge
(or discovered by the aggregate runner in tests/test_calculations.py-style loop)
"""

from __future__ import annotations

from concierge import assistant as A
from concierge import context as C
from concierge import grounding as G
from concierge import provider as P
from engine.api import evaluate_scenario, get_customers, get_damage_scenarios, active_backend_name


# --------------------------------------------------------------------------
# Helpers / fixtures
# --------------------------------------------------------------------------

def _scenario():
    cid = get_customers()[0]["id"]
    label = get_customers()[0]["label"]
    scens = get_damage_scenarios(cid)
    inputs = {
        "customer_label": label, "storm_severity": "high",
        "available_crews": 2, "access_blocked": False,
        "damage_scenario": "pole_and_span",
    }
    result = evaluate_scenario(cid, "high", 2, False, damage_scenario="pole_and_span")
    return cid, label, scens, inputs, result


# --------------------------------------------------------------------------
# Context allowlisting
# --------------------------------------------------------------------------

def test_context_allowlists_and_excludes_pii():
    cid, label, scens, inputs, result = _scenario()
    # Inject forbidden fields that MUST be dropped.
    dirty_inputs = dict(inputs, premise_nu="123456789", address="1 Main St", latitude=40.1)
    dirty_result = dict(result, owner_name="J. Doe", global_id="abc-123")
    ctx = C.build_context(
        customer_label=label, inputs=dirty_inputs, result=dirty_result,
        backend_name="real", damage_scenarios=scens,
    )
    # Allowlisted fields present:
    assert ctx["current_scenario"]["inputs"]["storm_severity"] == "high"
    assert ctx["current_scenario"]["result"]["risk_band"] == result["risk_band"]
    # Forbidden fields absent — raises nothing:
    C.assert_no_forbidden_fields(ctx)
    import json
    blob = json.dumps(ctx).lower()
    for frag in ("premise_nu", "address", "latitude", "owner_name", "global_id"):
        assert frag not in blob


def test_context_current_vs_previous():
    cid, label, scens, inputs, result = _scenario()
    prev_inputs = dict(inputs, available_crews=1)
    prev_result = evaluate_scenario(cid, "high", 1, False, damage_scenario="pole_and_span")
    changes = [("Crews", 1, 2)]
    ctx = C.build_context(
        customer_label=label, inputs=inputs, result=result, backend_name="real",
        damage_scenarios=scens, prev_inputs=prev_inputs, prev_result=prev_result,
        input_changes=changes,
    )
    assert ctx["previous_scenario"] is not None
    assert ctx["previous_scenario"]["inputs"]["available_crews"] == 1
    assert ctx["current_scenario"]["inputs"]["available_crews"] == 2
    assert ctx["input_changes"] == [{"field": "Crews", "from": 1, "to": 2}]


# --------------------------------------------------------------------------
# Provider configuration + failure (mocked)
# --------------------------------------------------------------------------

def test_missing_provider_config_uses_fallback(monkeypatch=None):
    """With provider not ready, the answer is fallback and labels the blocker."""
    cid, label, scens, inputs, result = _scenario()
    # Force provider unavailable regardless of local env.
    not_ready = P.ProviderStatus(sdk_installed=True, region_configured=False,
                                 model_configured=False, credentials_resolvable=False,
                                 ready=False, blocker="Missing: region; model id; credentials")
    _orig = P.provider_status
    A._provider.provider_status = lambda: not_ready
    try:
        reply = A.answer_question(
            "What should I do now?", customer_id=cid, customer_label=label,
            inputs=inputs, result=result, backend_name="real",
            evaluate_fn=evaluate_scenario, damage_scenarios=scens,
        )
    finally:
        A._provider.provider_status = _orig
    assert reply.mode == "fallback"
    assert reply.provider_error and "Missing" in reply.provider_error


def test_provider_failure_falls_back(monkeypatch=None):
    """If the provider is 'ready' but the call raises, we fall back gracefully."""
    cid, label, scens, inputs, result = _scenario()
    ready = P.ProviderStatus(True, True, True, True, True, None)
    _orig_status = A._provider.provider_status
    _orig_converse = A._provider.converse
    A._provider.provider_status = lambda: ready
    A._provider.converse = lambda sysp, msg: P.ProviderResult(ok=False, text=None,
                                                              error="AccessDeniedException: denied")
    try:
        reply = A.answer_question(
            "Will I lose power?", customer_id=cid, customer_label=label,
            inputs=inputs, result=result, backend_name="real",
            evaluate_fn=evaluate_scenario, damage_scenarios=scens,
        )
    finally:
        A._provider.provider_status = _orig_status
        A._provider.converse = _orig_converse
    assert reply.mode == "fallback"
    assert "AccessDenied" in (reply.provider_error or "")
    assert reply.text  # still produced a grounded answer


def test_live_mode_uses_mocked_provider(monkeypatch=None):
    """A mocked successful provider yields mode='live' (but this is NOT a real live call)."""
    cid, label, scens, inputs, result = _scenario()
    ready = P.ProviderStatus(True, True, True, True, True, None)
    _orig_status = A._provider.provider_status
    _orig_converse = A._provider.converse
    A._provider.provider_status = lambda: ready
    A._provider.converse = lambda sysp, msg: P.ProviderResult(ok=True, text="MOCK ANSWER", error=None)
    try:
        reply = A.answer_question(
            "Why did my estimate change?", customer_id=cid, customer_label=label,
            inputs=inputs, result=result, backend_name="real",
            evaluate_fn=evaluate_scenario, damage_scenarios=scens,
        )
    finally:
        A._provider.provider_status = _orig_status
        A._provider.converse = _orig_converse
    assert reply.mode == "live"
    assert reply.text == "MOCK ANSWER"


# --------------------------------------------------------------------------
# No duplicate provider calls during unrelated reruns (panel-level behavior)
# --------------------------------------------------------------------------

def test_no_provider_call_on_unrelated_rerun():
    """
    The panel only calls the concierge on an explicit action. Simulated via
    AppTest: an initial render (no action) must make zero provider calls; a
    second render with no interaction must also make zero.
    """
    from streamlit.testing.v1 import AppTest
    calls = {"n": 0}

    # Patch the concierge entry point used by the panel to count invocations.
    import ui.concierge_panel as panel
    orig = panel.answer_question
    panel.answer_question = lambda *a, **k: (_bump(calls) or
                                             A.AssistantReply(text="x", mode="fallback"))
    try:
        at = AppTest.from_file("app.py", default_timeout=30).run()
        assert not at.exception, at.exception
        assert calls["n"] == 0, "no provider/answer call should happen on first render"
        at.run()  # unrelated rerun, no interaction
        assert calls["n"] == 0, "no provider/answer call should happen on an unrelated rerun"
    finally:
        panel.answer_question = orig


def _bump(d):
    d["n"] += 1


# --------------------------------------------------------------------------
# Counterfactual ("more crews") comes from the engine, not the model
# --------------------------------------------------------------------------

def test_counterfactual_uses_engine_not_model():
    """
    For a crew counterfactual, the assistant must call evaluate_fn with the SAME
    scenario inputs but more crews, and must NOT mutate the active scenario.
    """
    cid, label, scens, inputs, result = _scenario()
    calls = []

    def spy_eval(**kw):
        calls.append(kw)
        return evaluate_scenario(**kw)

    # Force fallback so we exercise the counterfactual path deterministically.
    not_ready = P.ProviderStatus(True, False, False, False, False, "no config")
    _orig = A._provider.provider_status
    A._provider.provider_status = lambda: not_ready
    try:
        reply = A.answer_question(
            "Would another crew help?", customer_id=cid, customer_label=label,
            inputs=inputs, result=result, backend_name="real",
            evaluate_fn=spy_eval, damage_scenarios=scens,
        )
    finally:
        A._provider.provider_status = _orig

    assert reply.used_counterfactual is True
    assert calls, "engine must be called for the counterfactual"
    cf = calls[-1]
    # Same scenario inputs, only crews increased.
    assert cf["storm_severity"] == inputs["storm_severity"]
    assert cf["access_blocked"] == inputs["access_blocked"]
    assert cf["damage_scenario"] == inputs["damage_scenario"]
    assert cf["available_crews"] > inputs["available_crews"]
    # The active scenario inputs dict is untouched.
    assert inputs["available_crews"] == 2


def test_counterfactual_critical_path_message_when_no_help():
    """pole_and_span is a serial chain -> more crews don't change the window."""
    cid = get_customers()[0]["id"]
    label = get_customers()[0]["label"]
    scens = get_damage_scenarios(cid)
    inputs = {"customer_label": label, "storm_severity": "medium",
              "available_crews": 3, "access_blocked": False,
              "damage_scenario": "pole_and_span"}
    result = evaluate_scenario(cid, "medium", 3, False, damage_scenario="pole_and_span")
    not_ready = P.ProviderStatus(True, False, False, False, False, "no config")
    _orig = A._provider.provider_status
    A._provider.provider_status = lambda: not_ready
    try:
        reply = A.answer_question(
            "Would more crews help?", customer_id=cid, customer_label=label,
            inputs=inputs, result=result, backend_name="real",
            evaluate_fn=evaluate_scenario, damage_scenarios=scens,
        )
    finally:
        A._provider.provider_status = _orig
    assert "does not change" in reply.text.lower() or "critical path" in reply.text.lower()


# --------------------------------------------------------------------------
# Grounding of special estimate states (no-damage, unknown) — MOCKED.
# These guard the live-validation fixes without any network call.
# --------------------------------------------------------------------------

def test_context_flags_no_damage_with_required_caveat():
    cid = get_customers()[0]["id"]
    label = get_customers()[0]["label"]
    inputs = {"customer_label": label, "storm_severity": "medium",
              "available_crews": 3, "access_blocked": False, "damage_scenario": "none"}
    result = evaluate_scenario(cid, "medium", 3, False, damage_scenario="none")
    ctx = C.build_context(customer_label=label, inputs=inputs, result=result,
                          backend_name="real", damage_scenarios=get_damage_scenarios(cid))
    notes = ctx["estimate_notes"]
    assert notes["no_damage_modeled"] is True
    assert notes["estimate_unknown"] is False
    caveat = " ".join(notes["required_caveats"]).lower()
    assert "not guarantee" in caveat and "uninterrupted power" in caveat


def test_context_flags_unknown_estimate():
    cid = get_customers()[0]["id"]
    label = get_customers()[0]["label"]
    inputs = {"customer_label": label, "storm_severity": "medium",
              "available_crews": 3, "access_blocked": False, "damage_scenario": "unmapped_asset"}
    result = evaluate_scenario(cid, "medium", 3, False, damage_scenario="unmapped_asset")
    ctx = C.build_context(customer_label=label, inputs=inputs, result=result,
                          backend_name="real", damage_scenarios=get_damage_scenarios(cid))
    notes = ctx["estimate_notes"]
    assert notes["estimate_unknown"] is True
    assert notes["no_damage_modeled"] is False
    caveat = " ".join(notes["required_caveats"]).lower()
    assert "unknown" in caveat and "not invent" in caveat


def test_fallback_no_damage_does_not_promise_power():
    """Rule-based fallback must also carry the no-guarantee caveat for 0–0 windows."""
    cid = get_customers()[0]["id"]
    label = get_customers()[0]["label"]
    inputs = {"customer_label": label, "storm_severity": "medium",
              "available_crews": 3, "access_blocked": False, "damage_scenario": "none"}
    result = evaluate_scenario(cid, "medium", 3, False, damage_scenario="none")
    ctx = C.build_context(customer_label=label, inputs=inputs, result=result,
                          backend_name="real", damage_scenarios=get_damage_scenarios(cid))
    text = G.fallback_answer("what does my estimate mean right now?", ctx).lower()
    assert "no repair" in text
    assert "guarantee" in text and "uninterrupted power" in text


def test_fallback_unknown_does_not_invent_duration():
    cid = get_customers()[0]["id"]
    label = get_customers()[0]["label"]
    inputs = {"customer_label": label, "storm_severity": "medium",
              "available_crews": 3, "access_blocked": False, "damage_scenario": "unmapped_asset"}
    result = evaluate_scenario(cid, "medium", 3, False, damage_scenario="unmapped_asset")
    ctx = C.build_context(customer_label=label, inputs=inputs, result=result,
                          backend_name="real", damage_scenarios=get_damage_scenarios(cid))
    text = G.fallback_answer("how long will restoration take?", ctx).lower()
    assert "unknown" in text
    import re
    assert not re.search(r"\b\d+(\.\d+)?\s*(hour|hr)\b", text), "must not invent a duration"


def test_system_prompt_mentions_special_state_rules():
    """The live system prompt must instruct the model on no-damage/unknown states."""
    sp = G.SYSTEM_INSTRUCTIONS.lower()
    assert "no_damage_modeled" in sp or "no repairs modeled" in sp
    assert "uninterrupted power" in sp
    assert "estimate_unknown" in sp or "unknown" in sp


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} concierge tests passed")
