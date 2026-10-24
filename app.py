"""
app.py
======
StormReady — AEP AI Outage Concierge (HackOHI/O 2026)
Milestone 1: Streamlit customer interface over the synthetic demo engine.

Run with:
    streamlit run app.py

Owner: Roommate (app.py + ui/)
"""

from __future__ import annotations
import streamlit as st

from engine.api import evaluate_scenario, get_customers
from ui.sidebar import render_sidebar
from ui.components import (
    risk_card,
    restoration_card,
    preparation_checklist,
    notification_preview,
    assumptions_expander,
    source_banner,
    alert_badge,
)


def main() -> None:
    st.set_page_config(
        page_title="StormReady — Outage Concierge",
        page_icon="⛈️",
        layout="wide",
    )

    # --- Header ---
    st.title("⛈️ StormReady")
    st.markdown("##### AEP AI Outage Concierge — HackOHI/O 2026 prototype")

    st.error(
        "**SYNTHETIC DEMO** — All households, risk bands, and restoration estimates below "
        "are fabricated for demonstration. They are **not** real AEP data or confirmed predictions.",
        icon="🧪",
    )

    # --- Sidebar controls ---
    customer_id, storm_severity, available_crews, access_blocked = render_sidebar()

    # Map id back to label for display / notification
    customer_label = next(
        (c["label"] for c in get_customers() if c["id"] == customer_id),
        customer_id,
    )

    # --- Evaluate scenario ---
    try:
        result = evaluate_scenario(
            customer_id=customer_id,
            storm_severity=storm_severity,
            available_crews=available_crews,
            access_blocked=access_blocked,
        )
    except Exception as exc:  # defensive: keep the UI alive on engine errors
        st.exception(exc)
        st.stop()

    source_banner(result)

    st.markdown(f"### {customer_label}")

    # --- Scenario estimates section (clearly separated) ---
    st.markdown("## 🔮 Scenario Estimates")
    st.caption("The cards below are model estimates for the selected scenario — adjust the controls to see them change.")

    col1, col2 = st.columns(2)
    with col1:
        risk_card(result)
    with col2:
        restoration_card(result)

    alert_badge(result)

    st.markdown("---")

    # --- Preparation + notification ---
    col3, col4 = st.columns(2)
    with col3:
        preparation_checklist(result)
    with col4:
        notification_preview(result, customer_label, storm_severity)

    st.markdown("---")

    # --- Confirmed information section (separated from estimates) ---
    # Only claims verified against official AEP Ohio / Ohio regulator sources,
    # with source links. These do not depend on the scenario estimate.
    st.markdown("## ✅ Confirmed Information")
    st.caption("Verified facts (not scenario estimates), with sources.")
    st.markdown(
        "- **Report an AEP Ohio outage:** call **1-800-672-2231** "
        "([AEP Ohio outages](https://www.aepohio.com/outages/)).\n"
        "- **Live outage map:** [AEP Ohio outage map](https://outagemap.aepohio.com/).\n"
        "- **Medical needs & disconnection:** In Ohio, a medical certificate can help prevent "
        "a utility disconnection for nonpayment; it does **not** guarantee power restoration "
        "priority during storm outages "
        "([PUCO](https://puco.ohio.gov/utilities/electricity/resources/utility-assistance-programs), "
        "[OCC 30-day medical certificate](https://occ.ohio.gov/factsheet/30-day-medical-certificate)).\n"
    )
    st.caption(
        "Phone and map verified against AEP Ohio's official site; medical-certificate details "
        "from the Public Utilities Commission of Ohio and the Ohio Consumers' Counsel. "
        "StormReady is a student prototype and is not affiliated with AEP."
    )

    assumptions_expander(result)

    st.markdown("---")
    st.caption(
        "StormReady prototype · engine/demo.py provides synthetic estimates · "
        "built for HackOHI/O 2026."
    )


if __name__ == "__main__":
    main()
