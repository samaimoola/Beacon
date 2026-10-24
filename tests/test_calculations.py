"""
tests/test_calculations.py
==========================
Calculation and contract tests for the engine backends and the labor math.

Runnable with pytest, or standalone:  python -m tests.test_calculations

Owner: Samai (engine/scripts tests)
"""

from __future__ import annotations

from engine.contracts import EXAMPLE_RESPONSE
from engine import api, demo, realdata

REQUIRED_KEYS = set(EXAMPLE_RESPONSE.keys())


def _check_contract(res: dict) -> None:
    assert set(res.keys()) == REQUIRED_KEYS, set(res.keys()) ^ REQUIRED_KEYS
    assert res["risk_band"] in ["Low", "Moderate", "High", "Critical"]
    assert res["evidence_quality"] in ["High", "Medium", "Low"]
    for k in ("restoration_low_hours", "restoration_high_hours"):
        assert res[k] is None or isinstance(res[k], float), (k, res[k])
    assert isinstance(res["alert_eligible"], bool)
    for k in ("risk_factors", "restoration_factors", "preparation_actions", "assumptions"):
        assert isinstance(res[k], list) and all(isinstance(s, str) for s in res[k])
    assert isinstance(res["source_label"], str) and res["source_label"]


# --------------------------------------------------------------------------
# Demo backend (must keep working as fallback)
# --------------------------------------------------------------------------

def test_demo_contract_and_zero_crews():
    custs = demo.get_customers()
    assert len(custs) == 3
    for c in custs:
        res = demo.evaluate_scenario(c["id"], "high", 3, False)
        _check_contract(res)
    # zero crews -> unknown, no exception
    z = demo.evaluate_scenario("demo-001", "high", 0, False)
    assert z["restoration_low_hours"] is None and z["restoration_high_hours"] is None


# --------------------------------------------------------------------------
# Real-data backend
# --------------------------------------------------------------------------

def test_real_available():
    assert realdata.is_available(), "run `python -m scripts.build_processed` first"


def test_real_contract_all_premises():
    for c in realdata.get_customers():
        for sev in ("low", "medium", "high"):
            res = realdata.evaluate_scenario(c["id"], sev, 3, False)
            _check_contract(res)


def test_real_zero_crews_is_unknown():
    cid = realdata.get_customers()[0]["id"]
    z = realdata.evaluate_scenario(cid, "high", 0, False)
    assert z["restoration_low_hours"] is None
    assert z["restoration_high_hours"] is None
    assert any("no crews" in f.lower() for f in z["restoration_factors"])


def test_real_unknown_customer_raises():
    try:
        realdata.evaluate_scenario("nope", "low", 3, False)
        assert False, "should raise"
    except ValueError:
        pass


def test_crews_affect_duration_not_risk_band():
    cid = realdata.get_customers()[0]["id"]
    # Hold the damage scenario fixed; only crews vary.
    kw = dict(damage_scenario="multi_damage")
    bands = {realdata.evaluate_scenario(cid, "medium", c, False, **kw)["risk_band"] for c in (1, 5, 10)}
    assert len(bands) == 1, ("risk band changed with crews", bands)
    d1 = realdata.evaluate_scenario(cid, "medium", 1, False, **kw)["restoration_high_hours"]
    d10 = realdata.evaluate_scenario(cid, "medium", 10, False, **kw)["restoration_high_hours"]
    assert d1 > d10


def test_severity_and_access_increase_duration():
    cid = realdata.get_customers()[0]["id"]
    kw = dict(damage_scenario="pole_and_span")
    low = realdata.evaluate_scenario(cid, "low", 3, False, **kw)["restoration_high_hours"]
    high = realdata.evaluate_scenario(cid, "high", 3, False, **kw)["restoration_high_hours"]
    assert high > low
    clear = realdata.evaluate_scenario(cid, "medium", 3, False, **kw)["restoration_high_hours"]
    blocked = realdata.evaluate_scenario(cid, "medium", 3, True, **kw)["restoration_high_hours"]
    assert blocked > clear


# --------------------------------------------------------------------------
# Pass 2: defensible restoration — damaged vs healthy equipment, effort,
# concurrency/dependencies, unknown mappings, and the ILM-once rule.
# --------------------------------------------------------------------------

def test_healthy_equipment_generates_no_repair_work():
    """
    The 'none' scenario leaves all equipment healthy: zero repair jobs and a
    zero-length restoration window — we do NOT schedule replacement of the
    upstream path just because devices exist.
    """
    cid = realdata.get_customers()[0]["id"]
    res = realdata.evaluate_scenario(cid, "medium", 3, False, damage_scenario="none")
    assert res["restoration_low_hours"] == 0.0
    assert res["restoration_high_hours"] == 0.0
    assert any("no repair work" in f.lower() or "no damaged" in f.lower()
               for f in res["restoration_factors"])


def test_added_damaged_quantity_increases_effort():
    """More damaged assets => more total effort (ILM-applied)."""
    from engine import restoration as sched
    small = [sched.RepairJob("pole", 3.0)]
    big = [sched.RepairJob("pole", 3.0), sched.RepairJob("pole", 3.0),
           sched.RepairJob("span", 2.0)]
    r_small = sched.schedule(small, crews=5, ilm=4.5, access_blocked=False)
    r_big = sched.schedule(big, crews=5, ilm=4.5, access_blocked=False)
    assert r_big.effective_effort_hours > r_small.effective_effort_hours


def test_crews_respect_concurrency_and_dependencies():
    """
    - Independent jobs parallelize (more crews -> shorter), but
    - a dependency chain (critical path) cannot be shortened below its length,
    - and a single job cannot be sped up by adding crews.
    """
    from engine import restoration as sched

    # Dependency chain: span depends on pole -> fully serial, crew-insensitive.
    chain = [sched.RepairJob("pole", 3.0), sched.RepairJob("span", 2.0, depends_on=(0,))]
    c1 = sched.schedule(chain, crews=1, ilm=1.0, access_blocked=False)
    c9 = sched.schedule(chain, crews=9, ilm=1.0, access_blocked=False)
    assert c1.elapsed_hours == c9.elapsed_hours == c1.critical_path_hours

    # Independent jobs: more crews shorten elapsed time.
    indep = [sched.RepairJob("a", 3.0), sched.RepairJob("b", 3.0), sched.RepairJob("c", 3.0)]
    one = sched.schedule(indep, crews=1, ilm=1.0, access_blocked=False)
    three = sched.schedule(indep, crews=3, ilm=1.0, access_blocked=False)
    assert three.elapsed_hours < one.elapsed_hours
    # But never below a single job's duration (can't split one job).
    assert three.elapsed_hours >= 3.0

    # A single job is crew-insensitive.
    solo = [sched.RepairJob("big", 5.0)]
    s1 = sched.schedule(solo, crews=1, ilm=1.0, access_blocked=False)
    s8 = sched.schedule(solo, crews=8, ilm=1.0, access_blocked=False)
    assert s1.elapsed_hours == s8.elapsed_hours == 5.0


def test_more_crews_never_shorten_a_required_job_in_backend():
    """Backend-level: extra crews cannot push elapsed below the critical path."""
    cid = realdata.get_customers()[0]["id"]
    # pole_and_span is a serial chain: window must be crew-invariant.
    w3 = realdata.evaluate_scenario(cid, "medium", 3, False, damage_scenario="pole_and_span")
    w10 = realdata.evaluate_scenario(cid, "medium", 10, False, damage_scenario="pole_and_span")
    assert w3["restoration_high_hours"] == w10["restoration_high_hours"]


def test_unmapped_asset_yields_unknown_not_invented():
    """An unmapped damaged asset must produce an explicit UNKNOWN estimate."""
    cid = realdata.get_customers()[0]["id"]
    res = realdata.evaluate_scenario(cid, "medium", 3, False, damage_scenario="unmapped_asset")
    assert res["restoration_low_hours"] is None
    assert res["restoration_high_hours"] is None
    assert any("unknown" in f.lower() for f in res["restoration_factors"])


def test_ilm_applied_once_in_scheduler():
    """effective effort == sum(direct) * ILM exactly (no double counting)."""
    from engine import restoration as sched
    jobs = [sched.RepairJob("a", 2.0), sched.RepairJob("b", 1.5)]
    r = sched.schedule(jobs, crews=2, ilm=4.5, access_blocked=False)
    assert abs(r.total_direct_hours - 3.5) < 1e-6
    assert abs(r.effective_effort_hours - 3.5 * 4.5) < 1e-6


def test_transformer_hours_from_workbook_size_assumed():
    """
    The transformer repair task's hour VALUE comes from the workbook, while the
    SIZE is an assumption — the catalog must record both precisely.
    """
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parents[1] / "data" / "processed" / "premises.json").read_text())
    cat = data["labor_task_catalog"]
    xf = cat["replace_transformer"]
    assert xf["direct_hours"] is not None
    assert xf["is_assumption"] is False  # hour value is from the workbook
    assert "assumed" in xf["hours_source"].lower()  # size is assumed
    # Unmapped task stays unknown.
    assert cat["assess_unknown_asset"]["direct_hours"] is None


# --------------------------------------------------------------------------
# API routing + labeling
# --------------------------------------------------------------------------

def test_api_prefers_real_and_labels_source():
    assert api.active_backend_name() == "real"
    cid = api.get_customers()[0]["id"]
    res = api.evaluate_scenario(cid, "medium", 3, False)
    _check_contract(res)
    label = res["source_label"].upper()
    assert "SIMULATED" in label
    assert "HISTORICAL" in label        # historical damage is context only
    assert "UNVALIDATED" in label       # model is an unvalidated heuristic


def test_api_damage_scenario_passthrough_and_default():
    """API exposes get_damage_scenarios and passes damage_scenario through."""
    cid = api.get_customers()[0]["id"]
    scen = api.get_damage_scenarios(cid)
    assert isinstance(scen, list) and scen
    # Explicit 'none' scenario => zero window; default (omitted) => some work.
    none_res = api.evaluate_scenario(cid, "medium", 3, False, damage_scenario="none")
    assert none_res["restoration_high_hours"] == 0.0
    default_res = api.evaluate_scenario(cid, "medium", 3, False)  # uses default preset
    assert default_res["restoration_high_hours"] not in (None, 0.0)


def test_demo_backend_accepts_damage_scenario_arg():
    """Synthetic backend accepts (and ignores) the optional damage_scenario arg."""
    res = demo.evaluate_scenario("demo-001", "medium", 3, False, damage_scenario="anything")
    _check_contract(res)


# --------------------------------------------------------------------------
# No-damage presentation fix: 0–0 reads as "No repairs modeled", not "0 h".
# --------------------------------------------------------------------------

def test_format_window_states():
    from engine.formatting import format_window
    assert format_window(None, None) == "Unknown"
    assert format_window(0.0, 0.0) == "No repairs modeled"
    assert format_window(1.0, 3.0) == "1.0–3.0 h"


def test_no_damage_preset_renders_no_repairs_modeled():
    """
    Backend-driven check: the 'none' preset yields a 0–0 engine window, which the
    UI presents as 'No repairs modeled' (never a positive duration).

    NOTE: the exact wording of the accompanying 'does not guarantee uninterrupted
    power' caveat is UI copy owned by app.py/ui/, so it is intentionally NOT
    asserted here (that belongs in a dedicated UI test). This test only verifies
    the backend value surfaces as 'No repairs modeled'.
    """
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception, at.exception
    # Default sidebar selection is the first preset ("No damage ...").
    txt = "\n".join(
        str(getattr(e, "value", ""))
        for name in ("markdown", "info", "caption", "metric")
        for e in getattr(at, name, [])
    )
    metric_vals = [str(m.value) for m in at.metric]
    assert "No repairs modeled" in (txt + " " + " ".join(metric_vals))


# --------------------------------------------------------------------------
# Streamlit interaction regressions (what-changed persistence + reset)
# --------------------------------------------------------------------------

def _wc_text(at):
    """Text rendered inside the 'What changed?' tab (index 1)."""
    wc = at.tabs[1]
    return "\n".join(
        str(getattr(e, "value", ""))
        for name in ("markdown", "subheader", "caption")
        for e in getattr(wc, name, [])
    )


def _has_comparison(text: str) -> bool:
    return (
        "Inputs you changed" in text
        or "Restoration window:" in text
        or "Risk band:" in text
        or "Alert eligibility:" in text
    )


def test_what_changed_survives_unrelated_checkbox_interaction():
    """
    Regression: ticking a preparation checkbox must NOT wipe the last
    meaningful scenario comparison. The comparison baseline only advances
    when scenario INPUTS change.
    """
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception, at.exception

    # Change a scenario input so a comparison exists.
    at.slider[0].set_value(1).run()  # crews -> 1
    assert not at.exception
    assert _has_comparison(_wc_text(at)), "comparison should populate after input change"

    # Unrelated interaction: tick a preparation checkbox.
    boxes = [c for c in at.checkbox if str(c.key).startswith("prep_")]
    assert boxes, "expected preparation checkboxes"
    boxes[0].set_value(True).run()
    assert not at.exception

    assert _has_comparison(_wc_text(at)), "comparison must survive a checkbox interaction"


def test_reset_clears_comparison_and_controls():
    """Reset returns controls to defaults and clears the what-changed comparison."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception, at.exception

    # Match controls by their stable session key, not UI label text (labels are
    # UI copy owned by app.py/ui/ and may change; keys are the shared contract).
    def _access_cb(a):
        return next(c for c in a.checkbox if str(c.key) == "access_blocked")

    # Move controls away from defaults and create a comparison.
    at.select_slider[0].set_value("high").run()
    at.slider[0].set_value(1).run()
    _access_cb(at).set_value(True).run()
    assert _has_comparison(_wc_text(at))

    # Reset.
    [b for b in at.button if "Reset" in str(b.label)][0].click().run()
    assert not at.exception

    # Controls back to defaults.
    assert at.select_slider[0].value == "medium"
    assert at.slider[0].value == 4
    assert _access_cb(at).value is False

    # Comparison cleared (first-scenario message, no deltas).
    wc = _wc_text(at)
    assert not _has_comparison(wc), "reset should clear the comparison"
    assert "first scenario" in wc.lower()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} calculation tests passed")
