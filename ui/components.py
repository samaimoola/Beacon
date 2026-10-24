"""
ui/components.py
================
Reusable Streamlit rendering components for the StormReady UI.

Owner: Roommate (ui/)
"""

from __future__ import annotations
import streamlit as st


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_RISK_COLOUR = {
    "Low":      "#2e7d32",   # green
    "Moderate": "#f57c00",   # orange
    "High":     "#c62828",   # red
    "Critical": "#6a1b9a",   # purple
}

_EVIDENCE_COLOUR = {
    "High":   "#1565c0",
    "Medium": "#558b2f",
    "Low":    "#757575",
}


def risk_card(result: dict) -> None:
    """Render the outage-risk summary card."""
    band = result["risk_band"]
    colour = _RISK_COLOUR.get(band, "#333")
    eq = result["evidence_quality"]
    eq_colour = _EVIDENCE_COLOUR.get(eq, "#333")

    st.markdown(
        f"""
        <div style="
            border-left: 6px solid {colour};
            background: #fafafa;
            padding: 1rem 1.2rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
        ">
            <span style="font-size:1.6rem; font-weight:700; color:{colour};">
                {band} Risk
            </span>
            &nbsp;&nbsp;
            <span style="
                font-size:0.8rem; color:{eq_colour};
                border:1px solid {eq_colour};
                padding:2px 8px;
                border-radius:10px;
            ">
                Evidence quality: {eq}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Why this risk estimate?", expanded=True):
        for factor in result["risk_factors"]:
            st.markdown(f"- {factor}")


def restoration_card(result: dict) -> None:
    """Render the restoration-duration estimate card."""
    low = result.get("restoration_low_hours")
    high = result.get("restoration_high_hours")

    if low is None or high is None:
        window_text = "Unknown — insufficient data"
    else:
        window_text = f"{low:.1f} – {high:.1f} hours"

    st.markdown(
        f"""
        <div style="
            border-left: 6px solid #1565c0;
            background: #fafafa;
            padding: 1rem 1.2rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
        ">
            <span style="font-size:1.2rem; font-weight:600; color:#1565c0;">
                ⏱ Estimated Restoration Window
            </span><br/>
            <span style="font-size:1.5rem; font-weight:700; color:#0d47a1;">
                {window_text}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Why this estimate?", expanded=True):
        for factor in result["restoration_factors"]:
            st.markdown(f"- {factor}")

    st.caption(
        "⚠️ Scenario estimate only. Actual restoration depends on post-storm damage "
        "assessment, crew routing, and conditions not yet modeled."
    )


def preparation_checklist(result: dict) -> None:
    """Render the preparation action checklist."""
    st.subheader("📋 Preparation Checklist")
    for action in result["preparation_actions"]:
        st.checkbox(action, key=f"prep_{hash(action)}", value=False)


def notification_preview(result: dict, customer_label: str, storm_severity: str) -> None:
    """Render a labeled preview of a customer notification message."""
    low = result.get("restoration_low_hours")
    high = result.get("restoration_high_hours")

    if low is None or high is None:
        window_str = "an estimated timeframe is not yet available"
    else:
        window_str = f"an estimated {low:.0f}–{high:.0f} hours"

    band = result["risk_band"]
    alert_line = ""
    if result["alert_eligible"]:
        alert_line = (
            "\n\nUnder this prototype's notification rules, your scenario would be flagged "
            "to receive outage updates. (Prototype only — this does not enroll you in any "
            "AEP alert service.)"
        )

    message = f"""\
Dear Customer,

A {storm_severity.upper()} storm event is affecting your area. In this prototype \
scenario, your home has an estimated {band} outage-risk level based on the \
inputs provided.

If an outage occurs, this scenario estimates restoration may take {window_str}. \
We recommend taking preparation steps now.{alert_line}

For real-time outage status, use the AEP Ohio outage map (aepohio.com/outagemap) \
or report an outage to AEP Ohio at 1-800-672-2231.

— StormReady Outage Concierge (prototype)"""

    st.subheader("📨 Notification Preview")
    st.info(
        "**Preview only — this is a prototype draft, not a real AEP message and not a confirmed prediction.**",
        icon="ℹ️",
    )
    st.code(message, language=None)


def assumptions_expander(result: dict) -> None:
    """Render the assumptions and caveats section."""
    with st.expander("Assumptions & Caveats"):
        for assumption in result["assumptions"]:
            st.markdown(f"- {assumption}")


def source_banner(result: dict) -> None:
    """Render the data-source warning banner."""
    st.warning(result["source_label"], icon="⚠️")


def alert_badge(result: dict) -> None:
    """Show alert eligibility status under the prototype's documented rules."""
    if result["alert_eligible"]:
        st.success(
            "🔔 Eligible under prototype alert rules — this scenario meets StormReady's "
            "documented notification criteria. This is not AEP enrollment, program "
            "qualification, or guaranteed restoration priority."
        )
    else:
        st.info(
            "🔕 Not eligible under StormReady's prototype alert rules for this scenario. "
            "(Prototype rules only — not an AEP program decision.)"
        )
