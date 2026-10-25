"""
tests/test_notifications.py
===========================
Offline, deterministic tests for the notification-lifecycle service. No network,
no AI calls — notifications are a pure engine feature.

Runnable standalone:  python -m tests.test_notifications
"""

from __future__ import annotations

from engine import notifications as N
from engine.api import (
    get_customers, get_damage_scenarios, evaluate_scenario,
    build_notification_preview, build_lifecycle_previews, LIFECYCLE_STATES,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def _cid_label():
    c = get_customers()[0]
    return c["id"], c["label"]


def _inputs(label, dmg):
    return {"customer_label": label, "storm_severity": "medium",
            "available_crews": 3, "access_blocked": False, "damage_scenario": dmg}


def _result(cid, dmg, sev="medium", crews=3):
    return evaluate_scenario(cid, sev, crews, False, damage_scenario=dmg)


# --------------------------------------------------------------------------
# Each lifecycle state generates an appropriate preview
# --------------------------------------------------------------------------

def test_all_states_produce_valid_previews():
    cid, label = _cid_label()
    res = _result(cid, "pole_and_span")
    previews = build_lifecycle_previews(inputs=_inputs(label, "pole_and_span"), result=res)
    assert set(previews.keys()) == set(LIFECYCLE_STATES)
    required = {
        "lifecycle_state", "message", "trigger_reason", "recommended_channel",
        "timing", "scenario_eligible", "consent_status", "channel_available",
        "send_recommended", "send_blockers", "estimate_window", "estimate_change",
        "unknowns", "simulation_label", "safety_guidance",
    }
    for state, p in previews.items():
        assert set(p.keys()) == required, (state, set(p.keys()) ^ required)
        assert p["lifecycle_state"] == state
        # Every message is framed as a simulated preview.
        assert "SIMULATED PREVIEW" in p["message"]
        assert "SIMULATED" in p["simulation_label"]
        # Reuses approved safety guidance (same list object contents).
        assert p["safety_guidance"] == list(N.APPROVED_SAFETY_GUIDANCE)


def test_unknown_lifecycle_state_raises():
    cid, label = _cid_label()
    res = _result(cid, "pole_and_span")
    try:
        build_notification_preview(lifecycle_state="party", inputs=_inputs(label, "pole_and_span"), result=res)
        assert False, "should raise"
    except ValueError:
        pass


# --------------------------------------------------------------------------
# Message numbers match the engine
# --------------------------------------------------------------------------

def test_message_numbers_match_engine():
    cid, label = _cid_label()
    res = _result(cid, "pole_and_span")
    lo, hi = res["restoration_low_hours"], res["restoration_high_hours"]
    from engine.formatting import format_window
    expected = format_window(lo, hi)
    p = build_notification_preview(lifecycle_state=N.OUTAGE_CONFIRMED,
                                   inputs=_inputs(label, "pole_and_span"), result=res)
    assert expected in p["message"], (expected, p["message"])
    assert p["estimate_window"] == expected
    # No number appears that isn't the engine's window.
    assert f"{lo:g}" in p["message"] or f"{lo:.1f}" in p["message"]


# --------------------------------------------------------------------------
# Opt-out prevents a send recommendation while preserving the preview
# --------------------------------------------------------------------------

def test_optout_blocks_send_but_keeps_preview():
    cid, label = _cid_label()
    res = _result(cid, "pole_and_span")  # alert_eligible likely True
    prefs = {"opted_in": False}
    p = build_notification_preview(lifecycle_state=N.OUTAGE_CONFIRMED,
                                   inputs=_inputs(label, "pole_and_span"),
                                   result=res, preferences=prefs)
    assert p["send_recommended"] is False
    assert p["consent_status"] == "opted_out"
    assert any("opted out" in b.lower() for b in p["send_blockers"])
    # Preview content is still fully generated.
    assert p["message"] and "SIMULATED PREVIEW" in p["message"]


def test_eligibility_consent_channel_are_separate():
    cid, label = _cid_label()
    res = _result(cid, "pole_and_span")
    # Eligible + opted in + a channel -> send recommended.
    p_ok = build_notification_preview(lifecycle_state=N.OUTAGE_CONFIRMED,
                                      inputs=_inputs(label, "pole_and_span"), result=res,
                                      preferences={"opted_in": True, "available_channels": ["sms"]})
    # No channel available -> blocked on channel, independent of consent/eligibility.
    p_nochan = build_notification_preview(lifecycle_state=N.OUTAGE_CONFIRMED,
                                          inputs=_inputs(label, "pole_and_span"), result=res,
                                          preferences={"opted_in": True, "available_channels": []})
    assert p_ok["scenario_eligible"] == p_nochan["scenario_eligible"]  # eligibility unchanged
    assert p_nochan["channel_available"] is False
    assert p_nochan["send_recommended"] is False
    assert any("channel" in b.lower() for b in p_nochan["send_blockers"])


# --------------------------------------------------------------------------
# Unknown estimates remain unknown
# --------------------------------------------------------------------------

def test_unknown_estimate_stays_unknown():
    cid, label = _cid_label()
    res = _result(cid, "unmapped_asset")  # None/None window
    assert res["restoration_low_hours"] is None

    # With NO previous result there is no legitimate prior number to reference,
    # so the message must not contain any duration at all.
    import re
    duration_re = re.compile(r"\b\d+(?:\.\d+)?\s*(?:hour|hr|h)\b")
    p = build_notification_preview(lifecycle_state=N.RESTORATION_UPDATED,
                                   inputs=_inputs(label, "unmapped_asset"), result=res)
    assert p["estimate_window"] == "Unknown"
    cleaned = p["message"].lower().replace("1-800-672-2231", "")
    assert not duration_re.search(cleaned), p["message"]
    assert any("unknown" in u.lower() for u in p["unknowns"])

    # Outage-confirmed on an unknown estimate: current window is Unknown and the
    # message states the window as Unknown (it may not invent a current number).
    p2 = build_notification_preview(lifecycle_state=N.OUTAGE_CONFIRMED,
                                    inputs=_inputs(label, "unmapped_asset"), result=res)
    assert p2["estimate_window"] == "Unknown"
    assert "Unknown" in p2["message"]


# --------------------------------------------------------------------------
# Material-change threshold: small vs material
# --------------------------------------------------------------------------

def test_small_change_is_not_material():
    # midpoint 10 -> 11 : abs 1.0 (<2.0) and 10% (<25%) => not material
    prev = {"restoration_low_hours": 9.0, "restoration_high_hours": 11.0}   # mid 10
    curr = {"restoration_low_hours": 10.0, "restoration_high_hours": 12.0}  # mid 11
    change = N.classify_estimate_change(prev, curr)
    assert change["kind"] == "changed"
    assert change["material"] is False, change


def test_material_change_by_absolute_hours():
    # midpoint 10 -> 13 : abs 3.0 (>=2.0) => material
    prev = {"restoration_low_hours": 9.0, "restoration_high_hours": 11.0}   # mid 10
    curr = {"restoration_low_hours": 12.0, "restoration_high_hours": 14.0}  # mid 13
    change = N.classify_estimate_change(prev, curr)
    assert change["material"] is True, change


def test_material_change_by_fraction():
    # midpoint 2 -> 2.6 : abs 0.6 (<2.0) but 30% (>=25%) => material
    prev = {"restoration_low_hours": 1.5, "restoration_high_hours": 2.5}    # mid 2.0
    curr = {"restoration_low_hours": 2.1, "restoration_high_hours": 3.1}    # mid 2.6
    change = N.classify_estimate_change(prev, curr)
    assert change["material"] is True, change


def test_change_transitions_to_and_from_unknown_are_material():
    known = {"restoration_low_hours": 4.0, "restoration_high_hours": 8.0}
    unknown = {"restoration_low_hours": None, "restoration_high_hours": None}
    to_unknown = N.classify_estimate_change(known, unknown)
    from_unknown = N.classify_estimate_change(unknown, known)
    both_unknown = N.classify_estimate_change(unknown, unknown)
    assert to_unknown["kind"] == "to_unknown" and to_unknown["material"] is True
    assert from_unknown["kind"] == "from_unknown" and from_unknown["material"] is True
    assert both_unknown["kind"] == "both_unknown" and both_unknown["material"] is False


def test_no_previous_is_handled():
    curr = {"restoration_low_hours": 4.0, "restoration_high_hours": 8.0}
    change = N.classify_estimate_change(None, curr)
    assert change["kind"] == "no_previous"
    assert change["material"] is False


# --------------------------------------------------------------------------
# High risk does NOT imply outage confirmation
# --------------------------------------------------------------------------

def test_high_risk_does_not_imply_outage_confirmation():
    # Premise index 1 (Overhead) reaches a High band with multi_damage.
    c = get_customers()[1]
    cid, label = c["id"], c["label"]
    res = evaluate_scenario(cid, "medium", 3, False, damage_scenario="multi_damage")
    assert res["risk_band"] in ("High", "Critical"), res["risk_band"]

    # pre_storm on a high-risk scenario must NOT ASSERT a confirmed outage.
    # (The disclaimer "...not a confirmed outage" is allowed and expected.)
    p = build_notification_preview(lifecycle_state=N.PRE_STORM,
                                   inputs=_inputs(label, "multi_damage"), result=res)
    msg = p["message"].lower()
    assert "has been marked confirmed" not in msg and "outage confirmed" not in msg
    assert "not a forecast or a confirmed outage" in msg  # negated disclaimer present
    assert p["lifecycle_state"] == N.PRE_STORM

    # When outage_confirmed IS explicitly requested on a high-risk scenario, the
    # reason must clarify confirmation came from the explicit state, not the band.
    p2 = build_notification_preview(lifecycle_state=N.OUTAGE_CONFIRMED,
                                    inputs=_inputs(label, "multi_damage"), result=res)
    assert ("does NOT confirm" in p2["trigger_reason"]
            or "explicit simulated" in p2["trigger_reason"].lower())


# --------------------------------------------------------------------------
# No modeled repairs does NOT imply restoration completion
# --------------------------------------------------------------------------

def test_no_damage_does_not_imply_completion():
    cid, label = _cid_label()
    res = _result(cid, "none")  # zero-duration, no-damage preset
    assert res["restoration_low_hours"] == 0.0 and res["restoration_high_hours"] == 0.0
    # Asking for RESTORATION_COMPLETE on a zero-duration scenario must flag the
    # mismatch: completion is only from the explicit state, not the 0h estimate.
    p = build_notification_preview(lifecycle_state=N.RESTORATION_COMPLETE,
                                   inputs=_inputs(label, "none"), result=res)
    assert any("does NOT by itself mean restoration is complete" in u for u in p["unknowns"]), p["unknowns"]
    assert "explicit simulated lifecycle state" in p["trigger_reason"]


def test_restoration_complete_requires_explicit_state_only():
    """Completion is never produced by any state other than RESTORATION_COMPLETE."""
    cid, label = _cid_label()
    res = _result(cid, "none")
    for state in (N.PRE_STORM, N.OUTAGE_CONFIRMED, N.RESTORATION_UPDATED):
        p = build_notification_preview(lifecycle_state=state,
                                       inputs=_inputs(label, "none"), result=res)
        assert "restored" not in p["message"].lower()


# --------------------------------------------------------------------------
# restoration_updated: a send also requires a MATERIAL estimate change
# --------------------------------------------------------------------------

_ELIGIBLE = {"risk_band": "High", "alert_eligible": True}
_PREFS_OK = {"opted_in": True, "available_channels": ["sms", "email"]}


def _est(lo, hi):
    return dict(_ELIGIBLE, restoration_low_hours=lo, restoration_high_hours=hi)


def _updated(prev, curr, prefs=_PREFS_OK):
    return build_notification_preview(
        lifecycle_state=N.RESTORATION_UPDATED,
        inputs={"customer_label": "Real premise 1", "storm_severity": "medium"},
        result=curr, prev_result=prev, preferences=prefs,
    )


def _assert_preview_kept(p):
    assert p["message"].startswith("[SIMULATED PREVIEW]")
    assert "SIMULATED" in p["simulation_label"]


def test_updated_unchanged_estimate_is_not_sent():
    cid, label = _cid_label()
    res = _result(cid, "pole_and_span")
    assert res["alert_eligible"] is True
    p = build_notification_preview(lifecycle_state=N.RESTORATION_UPDATED,
                                   inputs=_inputs(label, "pole_and_span"), result=res,
                                   prev_result=dict(res), preferences=_PREFS_OK)
    assert p["estimate_change"]["material"] is False
    assert p["send_recommended"] is False, "identical estimates must not recommend a send"
    assert any("did not change" in b for b in p["send_blockers"]), p["send_blockers"]
    assert "has been updated" not in p["message"]
    _assert_preview_kept(p)


def test_updated_below_threshold_is_not_sent():
    p = _updated(_est(9.0, 11.0), _est(10.0, 12.0))   # midpoint 10 -> 11
    assert p["estimate_change"]["kind"] == "changed" and p["estimate_change"]["material"] is False
    assert p["send_recommended"] is False
    assert any("below the material threshold" in b for b in p["send_blockers"]), p["send_blockers"]
    _assert_preview_kept(p)


def test_updated_material_change_is_sent():
    p = _updated(_est(9.0, 11.0), _est(12.0, 14.0))   # midpoint 10 -> 13
    assert p["estimate_change"]["material"] is True
    assert p["send_recommended"] is True and p["send_blockers"] == []
    assert "has been updated" in p["message"]


def test_updated_without_previous_has_no_baseline():
    p = _updated(None, _est(12.0, 14.0))
    assert p["estimate_change"]["kind"] == "no_previous"
    assert p["send_recommended"] is False
    assert any("no baseline" in b for b in p["send_blockers"]), p["send_blockers"]
    assert "not an estimate update" in p["message"]
    _assert_preview_kept(p)


def test_updated_transitions_to_and_from_unknown():
    unknown = _est(None, None)
    to_u = _updated(_est(4.0, 8.0), unknown)
    from_u = _updated(unknown, _est(4.0, 8.0))
    both = _updated(unknown, dict(unknown))
    assert to_u["send_recommended"] is True and to_u["estimate_change"]["kind"] == "to_unknown"
    assert from_u["send_recommended"] is True and from_u["estimate_change"]["kind"] == "from_unknown"
    assert both["send_recommended"] is False
    assert any("still unknown" in b for b in both["send_blockers"]), both["send_blockers"]


def test_updated_material_still_respects_consent_and_channel():
    opted_out = _updated(_est(9.0, 11.0), _est(12.0, 14.0), {"opted_in": False})
    no_channel = _updated(_est(9.0, 11.0), _est(12.0, 14.0), {"opted_in": True, "available_channels": []})
    ineligible = _updated(dict(_est(9.0, 11.0), alert_eligible=False),
                          dict(_est(12.0, 14.0), alert_eligible=False))
    for p in (opted_out, no_channel, ineligible):
        assert p["send_recommended"] is False and p["estimate_change"]["material"] is True
    assert any("opted out" in b.lower() for b in opted_out["send_blockers"])
    assert any("channel" in b.lower() for b in no_channel["send_blockers"])
    assert any("not eligible" in b.lower() for b in ineligible["send_blockers"])


def test_other_states_ignore_estimate_change():
    """The material-change rule applies only to restoration_updated."""
    same = _est(9.0, 11.0)
    for state in (N.PRE_STORM, N.OUTAGE_CONFIRMED, N.RESTORATION_COMPLETE):
        p = build_notification_preview(lifecycle_state=state, inputs={"customer_label": "x",
                                       "storm_severity": "medium"}, result=same,
                                       prev_result=dict(same), preferences=_PREFS_OK)
        assert p["estimate_change"] is None
        assert p["send_recommended"] is True, (state, p["send_blockers"])


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} notification tests passed")
