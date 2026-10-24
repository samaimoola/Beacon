"""
ui/components.py
================
Reusable Streamlit rendering components for the StormReady UI.

This module ONLY renders. All numbers, bands, factors, assumptions, and the
source label come from the engine result dict (engine/api.py). The UI never
computes estimates and never alters the engine's source labels.

Owner: Roommate (ui/)
"""

from __future__ import annotations
import streamlit as st

from engine.formatting import format_window as _format_window


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
    "Medium": "#8d6e00",
    "Low":    "#757575",
}

_EVIDENCE_HELP = {
    "High": "Backed largely by confirmed data.",
    "Medium": "Mix of real inputs and simulated/assumed values.",
    "Low": "Mostly synthetic or rule-based — treat as illustrative.",
}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_window(low, high) -> str:
    """Human-readable restoration window (delegates to the shared engine helper).

    Returns "Unknown" for None, and "No repairs modeled" for a true 0–0 window
    (so a no-damage preset never reads like a guaranteed zero-hour outage).
    """
    return _format_window(low, high)


def _card_open(border: str) -> str:
    return (
        f'<div style="border-left:6px solid {border}; background:#fafafa; '
        f'padding:0.9rem 1.1rem; border-radius:6px; margin-bottom:0.4rem;">'
    )


# ---------------------------------------------------------------------------
# Provenance / source labelling (drives off the engine's source_label)
# ---------------------------------------------------------------------------

def provenance_banner(result: dict, backend_name: str) -> None:
    """
    Show the engine-provided source_label verbatim, with an icon chosen by
    backend. Never rewrites the label — only presents it.
    """
    label = result["source_label"]
    if backend_name == "real":
        st.warning(label, icon="🛰️")
    else:
        st.error(label, icon="🧪")


# ---------------------------------------------------------------------------
# Risk + evidence
# ---------------------------------------------------------------------------

def risk_card(result: dict) -> None:
    """Render the outage-risk summary card with an evidence-quality chip."""
    band = result["risk_band"]
    colour = _RISK_COLOUR.get(band, "#333")
    eq = result["evidence_quality"]
    eq_colour = _EVIDENCE_COLOUR.get(eq, "#333")

    st.markdown(
        _card_open(colour)
        + f'<div style="font-size:0.8rem; color:#555; text-transform:uppercase; '
          f'letter-spacing:0.05em;">Outage risk</div>'
          f'<span style="font-size:1.7rem; font-weight:700; color:{colour};">{band}</span>'
          f'&nbsp;&nbsp;<span style="font-size:0.78rem; color:{eq_colour}; '
          f'border:1px solid {eq_colour}; padding:2px 8px; border-radius:10px; '
          f'white-space:nowrap;">Evidence: {eq}</span>'
          f'<div style="font-size:0.75rem; color:#777; margin-top:0.35rem;">'
          f'{_EVIDENCE_HELP.get(eq, "")}</div>'
        + "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Why this risk level?", expanded=False):
        for factor in result["risk_factors"]:
            st.markdown(f"- {factor}")


def restoration_card(result: dict) -> None:
    """Render the restoration-duration estimate card.

    Three distinct states:
      - Unknown  : engine could not map the damage to labor references (None).
      - No repairs modeled : a 0–0 window from the "No simulated damage" preset.
      - A heuristic hour range.
    """
    low = result.get("restoration_low_hours")
    high = result.get("restoration_high_hours")
    unknown = low is None or high is None
    no_repairs = (not unknown) and low == 0 and high == 0

    if unknown:
        value_html = '<span style="font-size:1.6rem; font-weight:700; color:#8d6e00;">Unknown</span>'
        border = "#8d6e00"
    elif no_repairs:
        value_html = '<span style="font-size:1.4rem; font-weight:700; color:#2e7d32;">No repairs modeled</span>'
        border = "#2e7d32"
    else:
        value_html = (
            f'<span style="font-size:1.6rem; font-weight:700; color:#0d47a1;">{low:.1f}–{high:.1f}</span>'
            f'<span style="font-size:0.95rem; color:#0d47a1;"> hours</span>'
        )
        border = "#1565c0"

    st.markdown(
        _card_open(border)
        + '<div style="font-size:0.8rem; color:#555; text-transform:uppercase; '
          'letter-spacing:0.05em;">Estimated restoration window</div>'
        + value_html
        + "</div>",
        unsafe_allow_html=True,
    )

    if unknown:
        st.info(
            "No restoration estimate is available for this scenario. See the reasons below "
            "rather than assuming a time.",
            icon="❔",
        )
    elif no_repairs:
        st.info(
            "This preset models **no equipment damage**, so there are no repairs to schedule. "
            "This is **not** a guarantee of uninterrupted power — it only means this particular "
            "simulated scenario includes no damage to repair.",
            icon="🛠️",
        )

    with st.expander("Why this estimate?", expanded=False):
        for factor in result["restoration_factors"]:
            st.markdown(f"- {factor}")

    st.caption(
        "Scenario estimate only. Actual restoration depends on post-storm damage "
        "assessment, crew routing, and conditions not modeled here."
    )


def alert_badge(result: dict) -> None:
    """Show alert eligibility status under the prototype's documented rules."""
    if result["alert_eligible"]:
        st.success(
            "🔔 Eligible under prototype alert rules — this scenario meets StormReady's "
            "documented notification criteria. Not AEP enrollment, program qualification, "
            "or guaranteed restoration priority."
        )
    else:
        st.info(
            "🔕 Not eligible under StormReady's prototype alert rules for this scenario. "
            "(Prototype rules only — not an AEP program decision.)"
        )


# ---------------------------------------------------------------------------
# "What changed?" panel
# ---------------------------------------------------------------------------

def _window_midpoint(result: dict):
    low = result.get("restoration_low_hours")
    high = result.get("restoration_high_hours")
    if low is None or high is None:
        return None
    return (low + high) / 2.0


_INPUT_LABELS = {
    "customer_label": "Household",
    "storm_severity": "Storm severity",
    "damage_scenario": "Damage scenario",
    "available_crews": "Crews",
    "access_blocked": "Access blocked",
}


def compute_input_changes(prev_inputs: dict | None, curr_inputs: dict) -> list:
    """
    Return [(field_label, before, after), ...] for inputs that changed.
    Shared by the What-changed panel and the concierge context.
    """
    if not prev_inputs:
        return []
    out = []
    for key, label in _INPUT_LABELS.items():
        before, after = prev_inputs.get(key), curr_inputs.get(key)
        if before != after:
            out.append((label, before, after))
    return out


def what_changed_panel(prev: dict | None, curr: dict, prev_inputs: dict | None,
                       curr_inputs: dict) -> None:
    """
    Compare the previous scenario to the current one and summarize deltas.

    `prev`/`prev_inputs` are None on the first evaluation of a session.
    Pure presentation — all values come from engine results / sidebar inputs.
    """
    st.subheader("🔀 What changed?")

    if prev is None or prev_inputs is None:
        st.caption(
            "This is your first scenario this session. Adjust a control in the sidebar "
            "and this panel will compare the previous result with the new one."
        )
        return

    if prev_inputs == curr_inputs:
        st.caption("No change — inputs are the same as the previous scenario.")
        return

    # --- input changes ---
    input_rows = compute_input_changes(prev_inputs, curr_inputs)

    if input_rows:
        st.markdown("**Inputs you changed**")
        for label, before, after in input_rows:
            st.markdown(f"- {label}: `{before}` → `{after}`")

    # --- output changes ---
    st.markdown("**Resulting changes**")
    changed_any = False

    # risk band
    if prev["risk_band"] != curr["risk_band"]:
        changed_any = True
        st.markdown(f"- Risk band: **{prev['risk_band']} → {curr['risk_band']}**")

    # evidence quality
    if prev["evidence_quality"] != curr["evidence_quality"]:
        changed_any = True
        st.markdown(f"- Evidence quality: {prev['evidence_quality']} → {curr['evidence_quality']}")

    # restoration window
    prev_w = format_window(prev.get("restoration_low_hours"), prev.get("restoration_high_hours"))
    curr_w = format_window(curr.get("restoration_low_hours"), curr.get("restoration_high_hours"))
    if prev_w != curr_w:
        changed_any = True
        pm, cm = _window_midpoint(prev), _window_midpoint(curr)
        arrow = ""
        if pm is not None and cm is not None:
            if cm > pm:
                arrow = "  ⬆️ longer"
            elif cm < pm:
                arrow = "  ⬇️ shorter"
        st.markdown(f"- Restoration window: **{prev_w} → {curr_w}**{arrow}")

    # alert eligibility
    if prev["alert_eligible"] != curr["alert_eligible"]:
        changed_any = True
        was = "eligible" if prev["alert_eligible"] else "not eligible"
        now = "eligible" if curr["alert_eligible"] else "not eligible"
        st.markdown(f"- Alert eligibility: {was} → **{now}**")

    if not changed_any:
        st.caption("Inputs changed, but the risk band, restoration window, and alert "
                   "eligibility stayed the same.")


# ---------------------------------------------------------------------------
# Preparation + notification
# ---------------------------------------------------------------------------

def preparation_checklist(result: dict, customer_id: str) -> None:
    """Render the preparation action checklist (keys namespaced by customer)."""
    st.subheader("📋 Preparation checklist")
    actions = result["preparation_actions"]
    if not actions:
        st.caption("No preparation actions provided for this scenario.")
        return
    for i, action in enumerate(actions):
        # Namespace keys by customer + index so switching households resets boxes cleanly.
        st.checkbox(action, key=f"prep_{customer_id}_{i}", value=False)


def notification_preview(result: dict, storm_severity: str) -> None:
    """Render a labeled PREVIEW of a customer notification message."""
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

This is a SIMULATED scenario for a {storm_severity.upper()} storm — not a report of \
an actual storm or outage. Under these assumed conditions, your home would have an \
estimated {band} outage-risk level based on the inputs provided.

If such an outage occurred, this scenario estimates restoration could take {window_str}. \
Using it as practice, we recommend taking preparation steps now.{alert_line}

For real-time outage status in an actual event, use the AEP Ohio outage map \
(aepohio.com/outagemap) or report an outage to AEP Ohio at 1-800-672-2231.

— StormReady Outage Concierge (prototype · simulated preview)"""

    st.subheader("📨 Notification preview")
    st.info(
        "**Preview only — a prototype draft, not a real AEP message and not a confirmed prediction.**",
        icon="ℹ️",
    )
    st.code(message, language=None)


def assumptions_expander(result: dict) -> None:
    """Render the assumptions and caveats section."""
    with st.expander("Assumptions & caveats", expanded=False):
        for assumption in result["assumptions"]:
            st.markdown(f"- {assumption}")
