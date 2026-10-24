"""
ui/sidebar.py
=============
Sidebar controls: customer selection and scenario inputs.

Owner: Roommate (ui/)
"""

from __future__ import annotations
import streamlit as st
from engine.api import get_customers
from engine.contracts import (
    STORM_SEVERITY_OPTIONS,
    AVAILABLE_CREWS_MIN,
    AVAILABLE_CREWS_MAX,
)


def render_sidebar() -> tuple[str, str, int, bool]:
    """
    Render the sidebar and return (customer_id, storm_severity, available_crews, access_blocked).
    """
    st.sidebar.header("⚙️ Scenario Controls")

    # --- Customer selection ---
    customers = get_customers()
    labels = [c["label"] for c in customers]
    ids = [c["id"] for c in customers]

    selected_label = st.sidebar.selectbox(
        "Select Household",
        options=labels,
        help="Choose an anonymized demo household to evaluate.",
        key="customer_select",
    )
    customer_id = ids[labels.index(selected_label)]

    st.sidebar.markdown("---")
    st.sidebar.subheader("🌩 Storm Scenario")

    storm_severity = st.sidebar.select_slider(
        "Storm Severity",
        options=STORM_SEVERITY_OPTIONS,
        value="medium",
        help="low = minor wind/rain · medium = widespread outages possible · high = major event",
        key="storm_severity",
    )

    available_crews = st.sidebar.slider(
        "Available Repair Crews",
        min_value=AVAILABLE_CREWS_MIN,
        max_value=AVAILABLE_CREWS_MAX,
        value=4,
        step=1,
        help="Number of field crews AEP can dispatch to this area (1 = constrained, 10 = full staffing)",
        key="available_crews",
    )

    access_blocked = st.sidebar.checkbox(
        "Access Route Blocked",
        value=False,
        help="Check if road damage, flooding, or debris prevents crew access.",
        key="access_blocked",
    )

    st.sidebar.markdown("---")

    # Reset button
    if st.sidebar.button("🔄 Reset to Defaults", key="reset_btn"):
        # Clear session state for scenario controls
        for key in ["storm_severity", "available_crews", "access_blocked", "customer_select"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    # Scenario summary
    st.sidebar.caption(
        f"**Current scenario:** {storm_severity.capitalize()} storm · "
        f"{available_crews} crew(s) · "
        f"Access {'⛔ blocked' if access_blocked else '✅ clear'}"
    )

    return customer_id, storm_severity, available_crews, access_blocked
