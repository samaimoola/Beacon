"""
ui/sidebar.py
=============
Sidebar controls: customer selection and scenario inputs, plus a reliable reset.

Owner: Roommate (ui/)
"""

from __future__ import annotations
import streamlit as st
from engine.api import get_customers, get_damage_scenarios
from engine.contracts import (
    STORM_SEVERITY_OPTIONS,
    AVAILABLE_CREWS_MIN,
    AVAILABLE_CREWS_MAX,
)

from ui.theme import (
    CARLET, GREY_DARK, GREY_MEDIUM, GREY_LIGHT, GREY_BORDER, AMBER,
    SUCCESS, WARNING, ERROR, INFO,
    TYPOGRAPHY, SPACING, BORDER_RADIUS,
)

# Widget state keys and their defaults — single source of truth for reset.
_DEFAULTS = {
    "storm_severity": "medium",
    "available_crews": 4,
    "access_blocked": False,
}
# The damage-scenario default is handled separately (first preset for the
# selected customer), because the options depend on the customer.
# customer_select default is handled separately (first available label).

# Keys that hold per-scenario UI state we also want cleared on reset
# (checkbox state for the preparation list is namespaced "prep_*").
_RESET_PREFIXES = ("prep_",)


def _reset_callback() -> None:
    """Reset all scenario controls to defaults. Runs before the next rerun."""
    for key, default in _DEFAULTS.items():
        st.session_state[key] = default
    # Reset customer selection to the first option.
    customers = get_customers()
    if customers:
        st.session_state["customer_select"] = customers[0]["label"]
    # Reset the damage-scenario selector to the first preset for the first customer.
    scenarios = get_damage_scenarios(customers[0]["id"]) if customers else []
    if scenarios:
        st.session_state["damage_scenario_label"] = scenarios[0]["label"]
    # Clear preparation checkboxes and the what-changed comparison state.
    for key in list(st.session_state.keys()):
        if key.startswith(_RESET_PREFIXES):
            del st.session_state[key]
    for key in ("_prev_result", "_prev_inputs", "_last_result", "_last_inputs"):
        if key in st.session_state:
            del st.session_state[key]
    # Clear the concierge chat history too (preserves existing reset behavior).
    from ui.concierge_panel import clear_history as _clear_chat
    _clear_chat()
    
    # Clear notification preferences
    notification_keys = [
        "notification_lifecycle_state",
        "notification_opted_in",
        "notification_channels",
        "notification_preferred_channel",
    ]
    for key in notification_keys:
        if key in st.session_state:
            del st.session_state[key]


def render_sidebar() -> tuple[str, str, int, bool, str | None]:
    """
    Render the sidebar and return
    (customer_id, storm_severity, available_crews, access_blocked, damage_scenario_id).
    """
    # Sidebar header with improved styling
    st.sidebar.markdown(f"""
    <div style="
        background-color: {CARLET};
        color: white;
        padding: {SPACING['md']} {SPACING['lg']};
        border-radius: {BORDER_RADIUS['md']} {BORDER_RADIUS['md']} 0 0;
        margin: -1rem -1rem {SPACING['md']} -1rem;
        font-weight: 600;
        font-size: {TYPOGRAPHY['h3']};
    ">
        ⚙️ Scenario controls
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown(f"""
    <div style="
        color: {GREY_MEDIUM};
        font-size: {TYPOGRAPHY['small']};
        margin-bottom: {SPACING['lg']};
    ">
        Adjust these controls and the results update instantly.
    </div>
    """, unsafe_allow_html=True)

    # --- Customer selection ---
    customers = get_customers()
    labels = [c["label"] for c in customers]
    ids = [c["id"] for c in customers]

    # Seed defaults once so widgets have stable state for the reset callback.
    if "customer_select" not in st.session_state and labels:
        st.session_state["customer_select"] = labels[0]
    for key, default in _DEFAULTS.items():
        st.session_state.setdefault(key, default)

    st.sidebar.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['body']};
        margin-bottom: {SPACING['xs']};
    ">
        Household
    </div>
    """, unsafe_allow_html=True)
    
    selected_label = st.sidebar.selectbox(
        "Choose an anonymized household to evaluate",
        options=labels,
        help="Select a household to analyze outage risk and restoration estimates.",
        key="customer_select",
        label_visibility="collapsed"
    )
    customer_id = ids[labels.index(selected_label)]
    
    st.sidebar.markdown("<hr>", unsafe_allow_html=True)

    # Storm scenario section
    st.sidebar.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['h4']};
        margin-bottom: {SPACING['sm']};
        display: flex;
        align-items: center;
        gap: {SPACING['xs']};
    ">
        <span>🌩</span>
        <span>Storm scenario</span>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['body']};
        margin-bottom: {SPACING['xs']};
    ">
        Storm severity
    </div>
    """, unsafe_allow_html=True)
    
    storm_severity = st.sidebar.select_slider(
        "low = minor wind/rain · medium = widespread outages possible · high = major event",
        options=STORM_SEVERITY_OPTIONS,
        help="",
        key="storm_severity",
        label_visibility="collapsed"
    )
    
    # Show selected severity with color coding
    severity_colors = {"low": SUCCESS, "medium": WARNING, "high": ERROR}
    selected_color = severity_colors.get(storm_severity, GREY_MEDIUM)
    st.sidebar.markdown(f"""
    <div style="
        background-color: {GREY_LIGHT};
        border: 1px solid {selected_color};
        border-radius: {BORDER_RADIUS['sm']};
        padding: {SPACING['xs']} {SPACING['sm']};
        font-size: {TYPOGRAPHY['small']};
        color: {selected_color};
        font-weight: 600;
        text-align: center;
        margin-top: {SPACING['xs']};
        margin-bottom: {SPACING['md']};
    ">
        {storm_severity.upper()}
    </div>
    """, unsafe_allow_html=True)

    # --- Simulated damage scenario (presets depend on the selected customer) ---
    st.sidebar.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['body']};
        margin-bottom: {SPACING['xs']};
        margin-top: {SPACING['md']};
    ">
        Simulated damage scenario
    </div>
    <div style="
        color: {GREY_MEDIUM};
        font-size: {TYPOGRAPHY['caption']};
        margin-bottom: {SPACING['sm']};
    ">
        Which assets are damaged and repair jobs required
    </div>
    """, unsafe_allow_html=True)
    
    scenarios = get_damage_scenarios(customer_id)
    scen_labels = [s["label"] for s in scenarios]
    scen_by_label = {s["label"]: s for s in scenarios}

    damage_scenario_id: str | None = None
    if scen_labels:
        # Keep selection valid when the customer (and thus options) changes.
        current = st.session_state.get("damage_scenario_label")
        if current not in scen_labels:
            st.session_state["damage_scenario_label"] = scen_labels[0]
        chosen = st.sidebar.selectbox(
            "Select damage scenario",
            options=scen_labels,
            help="Explicitly simulated damage — not read from live or historical data.",
            key="damage_scenario_label",
            label_visibility="collapsed"
        )
        scen = scen_by_label.get(chosen, scenarios[0])
        damage_scenario_id = scen["id"]
        if scen.get("description"):
            st.sidebar.markdown(f"""
            <div style="
                background-color: #FFF3E0;
                border: 1px solid {AMBER};
                border-radius: {BORDER_RADIUS['sm']};
                padding: {SPACING['xs']} {SPACING['sm']};
                font-size: {TYPOGRAPHY['caption']};
                color: {GREY_DARK};
                margin-top: {SPACING['xs']};
            ">
                🧪 {scen['description']}
            </div>
            """, unsafe_allow_html=True)

    st.sidebar.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['body']};
        margin-bottom: {SPACING['xs']};
        margin-top: {SPACING['md']};
    ">
        Available repair crews
    </div>
    <div style="
        color: {GREY_MEDIUM};
        font-size: {TYPOGRAPHY['caption']};
        margin-bottom: {SPACING['sm']};
    ">
        1 = constrained, 10 = full staffing
    </div>
    """, unsafe_allow_html=True)
    
    available_crews = st.sidebar.slider(
        "Field crews available to dispatch",
        min_value=AVAILABLE_CREWS_MIN,
        max_value=AVAILABLE_CREWS_MAX,
        step=1,
        help="",
        key="available_crews",
        label_visibility="collapsed"
    )
    
    # Show crew count with visual indicator
    crew_percentage = (available_crews - AVAILABLE_CREWS_MIN) / (AVAILABLE_CREWS_MAX - AVAILABLE_CREWS_MIN)
    crew_color = SUCCESS if crew_percentage > 0.6 else WARNING if crew_percentage > 0.3 else ERROR
    st.sidebar.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: {GREY_LIGHT};
        border: 1px solid {crew_color};
        border-radius: {BORDER_RADIUS['sm']};
        padding: {SPACING['xs']} {SPACING['sm']};
        font-size: {TYPOGRAPHY['small']};
        color: {crew_color};
        font-weight: 600;
        margin-top: {SPACING['xs']};
        margin-bottom: {SPACING['md']};
    ">
        <span>{available_crews} crew(s)</span>
        <span style="font-size: {TYPOGRAPHY['caption']};">
            {"✅ Adequate" if crew_percentage > 0.6 else "⚠️ Limited" if crew_percentage > 0.3 else "⛔ Constrained"}
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['body']};
        margin-bottom: {SPACING['sm']};
        margin-top: {SPACING['md']};
    ">
        Access conditions
    </div>
    """, unsafe_allow_html=True)
    
    access_blocked = st.sidebar.checkbox(
        "Road damage, flooding, or debris preventing crew access",
        help="",
        key="access_blocked",
    )
    
    # Show access status
    access_color = ERROR if access_blocked else SUCCESS
    access_text = "⛔ Blocked" if access_blocked else "✅ Clear"
    st.sidebar.markdown(f"""
    <div style="
        background-color: {GREY_LIGHT};
        border: 1px solid {access_color};
        border-radius: {BORDER_RADIUS['sm']};
        padding: {SPACING['xs']} {SPACING['sm']};
        font-size: {TYPOGRAPHY['small']};
        color: {access_color};
        font-weight: 600;
        text-align: center;
        margin-top: {SPACING['xs']};
        margin-bottom: {SPACING['md']};
    ">
        {access_text}
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<hr>", unsafe_allow_html=True)

    # Reliable reset via on_click callback (runs before the rerun).
    st.sidebar.markdown(f"""
    <div style="margin-bottom: {SPACING['md']};">
        <button onclick="window.location.reload()" style="
            width: 100%;
            background-color: {GREY_LIGHT};
            color: {GREY_DARK};
            border: 1px solid {GREY_BORDER};
            border-radius: {BORDER_RADIUS['md']};
            padding: {SPACING['sm']} {SPACING['lg']};
            font-size: {TYPOGRAPHY['body']};
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: {SPACING['xs']};
        ">
            🔄 Reset to defaults
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    # Add actual reset button (hidden but functional)
    st.sidebar.button(
        "Reset to defaults",
        key="reset_btn",
        on_click=_reset_callback,
        use_container_width=True,
        label_visibility="collapsed"
    )

    # Scenario summary
    severity_colors = {"low": SUCCESS, "medium": WARNING, "high": ERROR}
    severity_color = severity_colors.get(storm_severity, GREY_MEDIUM)
    access_color = ERROR if access_blocked else SUCCESS
    
    st.sidebar.markdown(f"""
    <div style="
        background-color: {GREY_LIGHT};
        border: 1px solid {GREY_BORDER};
        border-radius: {BORDER_RADIUS['md']};
        padding: {SPACING['md']};
        font-size: {TYPOGRAPHY['small']};
        color: {GREY_DARK};
        margin-top: {SPACING['lg']};
    ">
        <div style="font-weight: 600; color: {GREY_DARK}; margin-bottom: {SPACING['sm']};">
            Current scenario
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: {SPACING['xs']};">
            <div style="color: {GREY_MEDIUM};">Severity</div>
            <div style="color: {severity_color}; font-weight: 600; text-align: right;">
                {storm_severity.capitalize()}
            </div>
            <div style="color: {GREY_MEDIUM};">Crews</div>
            <div style="color: {GREY_DARK}; font-weight: 600; text-align: right;">
                {available_crews}
            </div>
            <div style="color: {GREY_MEDIUM};">Access</div>
            <div style="color: {access_color}; font-weight: 600; text-align: right;">
                {'Blocked' if access_blocked else 'Clear'}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    return customer_id, storm_severity, available_crews, access_blocked, damage_scenario_id
