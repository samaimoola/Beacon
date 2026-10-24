"""
app.py
======
StormReady — AEP AI Outage Concierge (HackOHI/O 2026)
Streamlit customer interface over the engine API.

The UI is presentation-only: every estimate, band, factor, and source label
comes from engine.api. The UI never computes estimates and never rewrites the
engine's source labels.

Run with:
    streamlit run app.py

Owner: Roommate (app.py + ui/)
"""

from __future__ import annotations
import streamlit as st

from engine.api import evaluate_scenario, get_customers, get_damage_scenarios, active_backend_name
from ui.sidebar import render_sidebar
from ui.components import (
    provenance_banner,
    risk_card,
    restoration_card,
    alert_badge,
    what_changed_panel,
    preparation_checklist,
    notification_preview,
    assumptions_expander,
    format_window,
    compute_input_changes,
)
from ui.concierge_panel import render_concierge


def _header() -> None:
    st.title("⛈️ StormReady")
    st.caption("AEP AI Outage Concierge — HackOHI/O 2026 prototype")


def _top_metrics(result: dict) -> None:
    """Compact at-a-glance strip above the detailed cards."""
    low = result.get("restoration_low_hours")
    high = result.get("restoration_high_hours")
    c1, c2, c3 = st.columns(3)
    c1.metric("Outage risk", result["risk_band"])
    c2.metric("Restoration window", format_window(low, high))
    c3.metric("Evidence quality", result["evidence_quality"])


def main() -> None:
    st.set_page_config(
        page_title="StormReady — Outage Concierge",
        page_icon="⛈️",
        layout="wide",
    )

    _header()

    # --- Sidebar controls ---
    customer_id, storm_severity, available_crews, access_blocked, damage_scenario = render_sidebar()
    customer_label = next(
        (c["label"] for c in get_customers() if c["id"] == customer_id),
        customer_id,
    )

    # --- Evaluate scenario (engine owns all calculation) ---
    try:
        result = evaluate_scenario(
            customer_id=customer_id,
            storm_severity=storm_severity,
            available_crews=available_crews,
            access_blocked=access_blocked,
            damage_scenario=damage_scenario,
        )
    except Exception as exc:  # defensive: keep the UI alive on engine errors
        st.error("The engine could not evaluate this scenario.", icon="⚠️")
        st.exception(exc)
        st.stop()

    backend = active_backend_name()

    # --- Provenance banner (uses the engine's source_label verbatim) ---
    provenance_banner(result, backend)

    # Current inputs snapshot for the "What changed?" comparison.
    curr_inputs = {
        "customer_label": customer_label,
        "storm_severity": storm_severity,
        "available_crews": available_crews,
        "access_blocked": access_blocked,
        "damage_scenario": damage_scenario,
    }

    # --- "What changed?" baseline management --------------------------------
    # Bug previously: _prev_* was overwritten on EVERY rerun, so an unrelated
    # interaction (e.g. ticking a preparation checkbox) replaced the last
    # meaningful comparison with an identical one and the panel went blank.
    #
    # Fix: the comparison baseline (_prev_*) only advances when the SCENARIO
    # INPUTS actually change versus the last evaluated scenario (_last_*).
    # Unrelated reruns leave both _last_* and _prev_* untouched.
    last_inputs = st.session_state.get("_last_inputs")
    last_result = st.session_state.get("_last_result")

    if last_inputs is None:
        # First evaluation this session — no baseline yet.
        prev_inputs = None
        prev_result = None
    elif curr_inputs != last_inputs:
        # Scenario inputs changed: the previous evaluation becomes the baseline.
        prev_inputs = last_inputs
        prev_result = last_result
        st.session_state["_prev_inputs"] = prev_inputs
        st.session_state["_prev_result"] = prev_result
    else:
        # Inputs unchanged (an unrelated interaction): keep the existing baseline.
        prev_inputs = st.session_state.get("_prev_inputs")
        prev_result = st.session_state.get("_prev_result")

    st.markdown(f"### {customer_label}")
    _top_metrics(result)

    # Input changes (shared by What-changed panel and the concierge context).
    input_changes = compute_input_changes(prev_inputs, curr_inputs)

    tab_est, tab_changed, tab_prep, tab_notify, tab_ask = st.tabs(
        ["🔮 Estimates", "🔀 What changed?", "📋 Prepare", "📨 Notification", "💬 Ask StormReady"]
    )

    with tab_est:
        st.caption(
            "Model/scenario estimates — adjust the sidebar controls to see them change. "
            "These are separate from the confirmed information at the bottom of the page."
        )
        col1, col2 = st.columns(2)
        with col1:
            risk_card(result)
        with col2:
            restoration_card(result)
        alert_badge(result)
        assumptions_expander(result)

    with tab_changed:
        what_changed_panel(prev_result, result, prev_inputs, curr_inputs)

    with tab_prep:
        preparation_checklist(result, customer_id)

    with tab_notify:
        notification_preview(result, storm_severity)

    with tab_ask:
        render_concierge(
            customer_id=customer_id,
            customer_label=customer_label,
            inputs=curr_inputs,
            result=result,
            backend_name=backend,
            damage_scenarios=get_damage_scenarios(customer_id),
            prev_inputs=prev_inputs,
            prev_result=prev_result,
            input_changes=input_changes,
        )

    # --- Confirmed information (verified facts, separated from estimates) ---
    st.markdown("---")
    with st.container():
        st.markdown("## ✅ Confirmed information")
        st.caption("Verified facts (not scenario estimates), with sources.")
        st.markdown(
            "- **Report an AEP Ohio outage:** call **1-800-672-2231** "
            "([AEP Ohio outages](https://www.aepohio.com/outages/)).\n"
            "- **Live outage map:** [AEP Ohio outage map](https://outagemap.aepohio.com/).\n"
            "- **Medical needs & disconnection:** In Ohio, a medical certificate can help "
            "prevent a utility disconnection for nonpayment; it does **not** guarantee power "
            "restoration priority during storm outages "
            "([PUCO](https://puco.ohio.gov/utilities/electricity/resources/utility-assistance-programs), "
            "[OCC 30-day medical certificate](https://occ.ohio.gov/factsheet/30-day-medical-certificate)).\n"
        )
        st.caption(
            "Phone and map verified against AEP Ohio's official site; medical-certificate "
            "details from the Public Utilities Commission of Ohio and the Ohio Consumers' "
            "Counsel. StormReady is a student prototype and is not affiliated with AEP."
        )

    st.caption(
        f"StormReady prototype · active engine backend: **{backend}** · built for HackOHI/O 2026."
    )

    # --- Remember this evaluation as the "last" scenario ---
    # Only _last_* is updated every run; the comparison baseline (_prev_*) is
    # advanced above, and only when scenario inputs actually change.
    st.session_state["_last_inputs"] = curr_inputs
    st.session_state["_last_result"] = result


if __name__ == "__main__":
    main()
