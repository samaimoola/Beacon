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


def render_sidebar() -> tuple[str, str, int, bool, str | None]:
    """
    Render the sidebar and return
    (customer_id, storm_severity, available_crews, access_blocked, damage_scenario_id).
    """
    st.sidebar.header("⚙️ Scenario controls")
    st.sidebar.caption("Adjust these and the results update instantly.")

    # --- Customer selection ---
    customers = get_customers()
    labels = [c["label"] for c in customers]
    ids = [c["id"] for c in customers]

    # Seed defaults once so widgets have stable state for the reset callback.
    if "customer_select" not in st.session_state and labels:
        st.session_state["customer_select"] = labels[0]
    for key, default in _DEFAULTS.items():
        st.session_state.setdefault(key, default)

    selected_label = st.sidebar.selectbox(
        "Household",
        options=labels,
        help="Choose an anonymized household to evaluate.",
        key="customer_select",
    )
    customer_id = ids[labels.index(selected_label)]

    st.sidebar.markdown("---")
    st.sidebar.subheader("🌩 Storm scenario")

    storm_severity = st.sidebar.select_slider(
        "Storm severity",
        options=STORM_SEVERITY_OPTIONS,
        help="low = minor wind/rain · medium = widespread outages possible · high = major event",
        key="storm_severity",
    )

    # --- Simulated damage scenario (presets depend on the selected customer) ---
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
            "Simulated damage scenario",
            options=scen_labels,
            help="Explicitly simulated damage — which assets are damaged and the repair "
                 "jobs required. Not read from any live or historical data file.",
            key="damage_scenario_label",
        )
        scen = scen_by_label.get(chosen, scenarios[0])
        damage_scenario_id = scen["id"]
        if scen.get("description"):
            st.sidebar.caption(f"🧪 {scen['description']}")

    available_crews = st.sidebar.slider(
        "Available repair crews",
        min_value=AVAILABLE_CREWS_MIN,
        max_value=AVAILABLE_CREWS_MAX,
        step=1,
        help="Field crews available to dispatch (1 = constrained, 10 = full staffing).",
        key="available_crews",
    )

    access_blocked = st.sidebar.checkbox(
        "Access route blocked",
        help="Road damage, flooding, or debris preventing crew access.",
        key="access_blocked",
    )

    st.sidebar.markdown("---")

    # Reliable reset via on_click callback (runs before the rerun).
    st.sidebar.button(
        "🔄 Reset to defaults",
        key="reset_btn",
        on_click=_reset_callback,
        use_container_width=True,
    )

    st.sidebar.caption(
        f"**Scenario:** {storm_severity.capitalize()} storm · "
        f"{available_crews} crew(s) · "
        f"Access {'⛔ blocked' if access_blocked else '✅ clear'}"
    )

    return customer_id, storm_severity, available_crews, access_blocked, damage_scenario_id
