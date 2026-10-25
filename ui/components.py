"""
ui/components.py
================
Reusable Streamlit rendering components for the Beacon UI.

This module ONLY renders. All numbers, bands, factors, assumptions, and the
source label come from the engine result dict (engine/api.py). The UI never
computes estimates and never alters the engine's source labels.

Owner: Roommate (ui/)
"""

from __future__ import annotations
import streamlit as st

from engine.formatting import format_window as _format_window
from ui.theme import (
    # Colors
    CARLET, GREY_DARK, GREY_MEDIUM, GREY_LIGHT, GREY_BORDER, AMBER,
    SUCCESS, WARNING, ERROR, INFO,
    # Typography
    TYPOGRAPHY, SPACING, BORDER_RADIUS,
    # Risk band colors
    RISK_COLOR as _RISK_COLOUR,
    # Evidence colors  
    EVIDENCE_COLOR as _EVIDENCE_COLOUR,
    # Helper functions
    card_style, metric_style, label_style, badge_style, apply_card_styles
)


# ---------------------------------------------------------------------------
# Evidence quality help text
# ---------------------------------------------------------------------------

_EVIDENCE_HELP = {
    "High": "Based primarily on confirmed data from AEP's anonymized network.",
    "Medium": "Combination of real network data and simulated storm conditions.",
    "Low": "Illustrative scenario using synthetic data — for demonstration only.",
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


def _card_html(title: str, content: str, border_color: str = GREY_BORDER, bg_color: str = "white") -> str:
    """Generate HTML for a card with consistent styling."""
    styles = card_style(border_color, bg_color)
    return f'''
    <div style="{styles}">
        <div style="{label_style()}">{title}</div>
        {content}
    </div>
    '''


def _metric_html(value: str, label: str, color: str = CARLET) -> str:
    """Generate HTML for a metric display."""
    return f'''
    <div style="margin-bottom: {SPACING['md']}">
        <div style="{label_style()}">{label}</div>
        <div style="{metric_style(color)}">{value}</div>
    </div>
    '''


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
        # Real data backend
        st.markdown(f"""
        <div style="
            background-color: #FFF3E0;
            border: 1px solid {AMBER};
            border-left: 6px solid {AMBER};
            border-radius: {BORDER_RADIUS['md']};
            padding: {SPACING['md']};
            margin-bottom: {SPACING['lg']};
            font-size: {TYPOGRAPHY['body']};
            color: {GREY_DARK};
        ">
            <div style="display: flex; align-items: center; gap: {SPACING['sm']}; margin-bottom: {SPACING['xs']};">
                <span style="color: {AMBER}; font-size: 1.2rem;">🛰️</span>
                <span style="font-weight: 600; color: {AMBER};">Data provenance</span>
            </div>
            <div>{label}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Synthetic demo backend
        st.markdown(f"""
        <div style="
            background-color: #FFEBEE;
            border: 1px solid {ERROR};
            border-left: 6px solid {ERROR};
            border-radius: {BORDER_RADIUS['md']};
            padding: {SPACING['md']};
            margin-bottom: {SPACING['lg']};
            font-size: {TYPOGRAPHY['body']};
            color: {GREY_DARK};
        ">
            <div style="display: flex; align-items: center; gap: {SPACING['sm']}; margin-bottom: {SPACING['xs']};">
                <span style="color: {ERROR}; font-size: 1.2rem;">🧪</span>
                <span style="font-weight: 600; color: {ERROR};">Demo mode</span>
            </div>
            <div>{label}</div>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Risk + evidence
# ---------------------------------------------------------------------------

def risk_card(result: dict) -> None:
    """Render the outage-risk summary card with an evidence-quality chip."""
    band = result["risk_band"]
    colour = _RISK_COLOUR.get(band, GREY_DARK)
    eq = result["evidence_quality"]
    eq_colour = _EVIDENCE_COLOUR.get(eq, GREY_MEDIUM)
    
    # Create badge for evidence quality
    eq_badge = f'''
    <span style="{badge_style(eq_colour, 'white')}">Evidence: {eq}</span>
    '''
    
    # Create main content
    content = f'''
    <div style="display: flex; align-items: center; gap: {SPACING['md']}; margin-bottom: {SPACING['xs']}">
        <span style="font-size: {TYPOGRAPHY['h1']}; font-weight: 700; color: {colour};">{band}</span>
        {eq_badge}
    </div>
    <div style="font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">
        {_EVIDENCE_HELP.get(eq, "")}
    </div>
    '''
    
    st.markdown(
        _card_html("Outage risk", content, border_color=colour),
        unsafe_allow_html=True,
    )

    with st.expander("Why this risk level?", expanded=False):
        st.markdown("**Contributing factors:**")
        for factor in result["risk_factors"]:
            st.markdown(f"• {factor}")
        st.caption("These factors contribute to the overall risk assessment for this scenario.")


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
        value_html = f'<span style="{metric_style(WARNING)}">Unknown</span>'
        border = WARNING
        bg_color = "#FFF3E0"
    elif no_repairs:
        value_html = f'<span style="{metric_style(SUCCESS)}">No repairs modeled</span>'
        border = SUCCESS
        bg_color = "#E8F5E9"
    else:
        value_html = f'''
        <div style="display: flex; align-items: baseline; gap: {SPACING['xs']}">
            <span style="{metric_style(INFO)}">{low:.1f}–{high:.1f}</span>
            <span style="font-size: {TYPOGRAPHY['body']}; color: {GREY_MEDIUM};">hours</span>
        </div>
        '''
        border = INFO
        bg_color = "#E3F2FD"

    # Add status indicator
    status_indicator = ""
    if unknown:
        status_indicator = f'''
        <div style="display: flex; align-items: center; gap: {SPACING['xs']}; margin-top: {SPACING['sm']}">
            <div style="width: 8px; height: 8px; border-radius: 50%; background-color: {WARNING};"></div>
            <span style="font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">Estimate unavailable</span>
        </div>
        '''
    elif no_repairs:
        status_indicator = f'''
        <div style="display: flex; align-items: center; gap: {SPACING['xs']}; margin-top: {SPACING['sm']}">
            <div style="width: 8px; height: 8px; border-radius: 50%; background-color: {SUCCESS};"></div>
            <span style="font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">No simulated damage in this preset</span>
        </div>
        '''
    else:
        status_indicator = f'''
        <div style="display: flex; align-items: center; gap: {SPACING['xs']}; margin-top: {SPACING['sm']}">
            <div style="width: 8px; height: 8px; border-radius: 50%; background-color: {INFO};"></div>
            <span style="font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">Heuristic estimate based on simulated conditions</span>
        </div>
        '''

    content = value_html + status_indicator
    
    st.markdown(
        _card_html("Estimated restoration window", content, border_color=border, bg_color=bg_color),
        unsafe_allow_html=True,
    )

    with st.expander("Why this estimate?", expanded=False):
        st.markdown("**Key factors affecting restoration time:**")
        for factor in result["restoration_factors"]:
            st.markdown(f"• {factor}")
        st.caption("These factors influence the estimated repair and restoration timeline.")

    st.caption(
        "⚠️ **Scenario estimate only.** Actual restoration depends on post-storm damage "
        "assessment, crew routing, and conditions not modeled here."
    )


def alert_badge(result: dict) -> None:
    """Show alert eligibility status under the prototype's documented rules."""
    if result["alert_eligible"]:
        st.markdown(
            _card_html(
                "Alert Eligibility",
                f'''
                <div style="display: flex; align-items: center; gap: {SPACING['sm']};">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background-color: {SUCCESS};"></div>
                    <span style="font-weight: 600; color: {SUCCESS};">Eligible for prototype alerts</span>
                </div>
                <div style="margin-top: {SPACING['sm']}; font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">
                    This scenario meets Beacon's documented notification criteria. 
                    <strong>This is not AEP enrollment, program qualification, or guaranteed restoration priority.</strong>
                </div>
                ''',
                border_color=SUCCESS,
                bg_color="#E8F5E9"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            _card_html(
                "Alert Eligibility",
                f'''
                <div style="display: flex; align-items: center; gap: {SPACING['sm']};">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background-color: {GREY_MEDIUM};"></div>
                    <span style="font-weight: 600; color: {GREY_MEDIUM};">Not eligible for prototype alerts</span>
                </div>
                <div style="margin-top: {SPACING['sm']}; font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">
                    This scenario does not meet Beacon's prototype notification criteria. 
                    <strong>Prototype rules only — not an AEP program decision.</strong>
                </div>
                ''',
                border_color=GREY_BORDER
            ),
            unsafe_allow_html=True,
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
    st.markdown(f'<h3 style="margin-bottom: {SPACING["md"]};">🔀 What changed?</h3>', unsafe_allow_html=True)

    if prev is None or prev_inputs is None:
        st.markdown(
            _card_html(
                "First scenario",
                f'''
                <div style="color: {GREY_MEDIUM}; font-size: {TYPOGRAPHY['body']};">
                    This is your first scenario this session. Adjust a control in the sidebar 
                    and this panel will compare the previous result with the new one.
                </div>
                ''',
                border_color=GREY_BORDER
            ),
            unsafe_allow_html=True,
        )
        return

    if prev_inputs == curr_inputs:
        st.markdown(
            _card_html(
                "No changes detected",
                f'''
                <div style="color: {GREY_MEDIUM}; font-size: {TYPOGRAPHY['body']};">
                    No change — inputs are the same as the previous scenario.
                </div>
                ''',
                border_color=GREY_BORDER
            ),
            unsafe_allow_html=True,
        )
        return

    # --- input changes ---
    input_rows = compute_input_changes(prev_inputs, curr_inputs)

    if input_rows:
        _input_rows_html = "".join(
            f'''
                <div style="margin-bottom: {SPACING["sm"]}; padding: {SPACING["xs"]} {SPACING["sm"]}; 
                     background-color: {GREY_LIGHT}; border-radius: {BORDER_RADIUS["sm"]};">
                    <div style="font-weight: 600; color: {GREY_DARK}; margin-bottom: 2px;">{label}</div>
                    <div style="display: flex; align-items: center; gap: {SPACING["xs"]}; color: {GREY_MEDIUM};">
                        <span>{before}</span>
                        <span style="color: {CARLET};">→</span>
                        <span style="font-weight: 600; color: {CARLET};">{after}</span>
                    </div>
                </div>
                '''
            for label, before, after in input_rows
        )
        st.markdown(
            _card_html(
                "Inputs you changed",
                f'''
                <div style="font-size: {TYPOGRAPHY['body']};">
                {_input_rows_html}
                </div>
                ''',
                border_color=AMBER,
                bg_color="#FFF3E0"
            ),
            unsafe_allow_html=True,
        )

    # --- output changes ---
    changed_items = []
    
    # risk band
    if prev["risk_band"] != curr["risk_band"]:
        prev_color = _RISK_COLOUR.get(prev["risk_band"], GREY_DARK)
        curr_color = _RISK_COLOUR.get(curr["risk_band"], GREY_DARK)
        changed_items.append((
            "Risk band",
            f'<span style="color: {prev_color};">{prev["risk_band"]}</span>',
            f'<span style="color: {curr_color}; font-weight: 600;">{curr["risk_band"]}</span>'
        ))

    # evidence quality
    if prev["evidence_quality"] != curr["evidence_quality"]:
        prev_color = _EVIDENCE_COLOUR.get(prev["evidence_quality"], GREY_MEDIUM)
        curr_color = _EVIDENCE_COLOUR.get(curr["evidence_quality"], GREY_MEDIUM)
        changed_items.append((
            "Evidence quality",
            f'<span style="color: {prev_color};">{prev["evidence_quality"]}</span>',
            f'<span style="color: {curr_color}; font-weight: 600;">{curr["evidence_quality"]}</span>'
        ))

    # restoration window
    prev_w = format_window(prev.get("restoration_low_hours"), prev.get("restoration_high_hours"))
    curr_w = format_window(curr.get("restoration_low_hours"), curr.get("restoration_high_hours"))
    if prev_w != curr_w:
        pm, cm = _window_midpoint(prev), _window_midpoint(curr)
        arrow_html = ""
        if pm is not None and cm is not None:
            if cm > pm:
                arrow_html = f'<span style="color: {WARNING}; margin-left: {SPACING["xs"]};">↑ longer</span>'
            elif cm < pm:
                arrow_html = f'<span style="color: {SUCCESS}; margin-left: {SPACING["xs"]};">↓ shorter</span>'
        changed_items.append((
            "Restoration window",
            prev_w,
            f'<span style="font-weight: 600;">{curr_w}</span>{arrow_html}'
        ))

    # alert eligibility
    if prev["alert_eligible"] != curr["alert_eligible"]:
        was = "eligible" if prev["alert_eligible"] else "not eligible"
        now = "eligible" if curr["alert_eligible"] else "not eligible"
        was_color = SUCCESS if prev["alert_eligible"] else GREY_MEDIUM
        now_color = SUCCESS if curr["alert_eligible"] else GREY_MEDIUM
        changed_items.append((
            "Alert eligibility",
            f'<span style="color: {was_color};">{was}</span>',
            f'<span style="color: {now_color}; font-weight: 600;">{now}</span>'
        ))

    if changed_items:
        _changed_items_html = "".join(
            f'''
                <div style="margin-bottom: {SPACING["md"]};">
                    <div style="font-weight: 600; color: {GREY_DARK}; margin-bottom: 4px;">{label}</div>
                    <div style="display: flex; align-items: center; gap: {SPACING["sm"]};">
                        <div style="flex: 1; padding: {SPACING["xs"]}; background-color: {GREY_LIGHT}; 
                             border-radius: {BORDER_RADIUS["sm"]}; text-align: center;">
                            {before}
                        </div>
                        <span style="color: {CARLET}; font-weight: 600;">→</span>
                        <div style="flex: 1; padding: {SPACING["xs"]}; background-color: #E8F5E9; 
                             border: 1px solid {SUCCESS}; border-radius: {BORDER_RADIUS["sm"]}; text-align: center;">
                            {after}
                        </div>
                    </div>
                </div>
                '''
            for label, before, after in changed_items
        )
        st.markdown(
            _card_html(
                "Resulting changes",
                f'''
                <div style="font-size: {TYPOGRAPHY['body']};">
                {_changed_items_html}
                </div>
                ''',
                border_color=SUCCESS,
                bg_color="#F8FFF8"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            _card_html(
                "No output changes",
                f'''
                <div style="color: {GREY_MEDIUM}; font-size: {TYPOGRAPHY['body']};">
                    Inputs changed, but the risk band, restoration window, and alert 
                    eligibility stayed the same.
                </div>
                ''',
                border_color=GREY_BORDER
            ),
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Preparation + notification
# ---------------------------------------------------------------------------

def preparation_checklist(result: dict, customer_id: str) -> None:
    """Render the preparation action checklist (keys namespaced by customer)."""
    st.markdown(f'<h3 style="margin-bottom: {SPACING["md"]};">📋 Preparation checklist</h3>', unsafe_allow_html=True)
    
    actions = result["preparation_actions"]
    if not actions:
        st.markdown(
            _card_html(
                "No preparation actions",
                f'<div style="color: {GREY_MEDIUM}; font-size: {TYPOGRAPHY["body"]};">No specific preparation actions recommended for this scenario.</div>',
                border_color=GREY_BORDER
            ),
            unsafe_allow_html=True,
        )
        return
    
    # Use a container with consistent styling
    with st.container():
        st.markdown(
            _card_html(
                "Recommended actions",
                '<div style="color: #555; font-size: 0.9rem; margin-bottom: 0.5rem;">Check off items as you complete them:</div>',
                border_color=AMBER,
                bg_color="#FFF3E0"
            ),
            unsafe_allow_html=True,
        )
        
        for i, action in enumerate(actions):
            # Namespace keys by customer + index so switching households resets boxes cleanly.
            col1, col2 = st.columns([1, 20])
            with col1:
                st.checkbox("", key=f"prep_{customer_id}_{i}", value=False, label_visibility="collapsed")
            with col2:
                st.markdown(f'<div style="font-size: {TYPOGRAPHY["body"]}; padding: 0.25rem 0;">{action}</div>', unsafe_allow_html=True)
        
        st.caption("Your checklist progress is saved for this session. Switching households will reset the checklist.")


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

— Beacon Outage Concierge (prototype · simulated preview)"""

    st.markdown(f'<h3 style="margin-bottom: {SPACING["md"]};">📨 Notification preview</h3>', unsafe_allow_html=True)
    
    st.markdown(
        _card_html(
            "Prototype notification draft",
            f'''
            <div style="display: flex; align-items: center; gap: {SPACING['sm']}; margin-bottom: {SPACING['md']}">
                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: {WARNING};"></div>
                <span style="font-weight: 600; color: {WARNING};">Preview only</span>
            </div>
            <div style="font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM}; margin-bottom: {SPACING['md']}">
                A prototype draft — not a real AEP message and not a confirmed prediction.
            </div>
            ''',
            border_color=WARNING,
            bg_color="#FFF3E0"
        ),
        unsafe_allow_html=True,
    )
    
    # Style the code block container
    st.markdown(f"""
    <div style="
        background-color: {GREY_LIGHT};
        border: 1px solid {GREY_BORDER};
        border-radius: {BORDER_RADIUS['md']};
        padding: {SPACING['lg']};
        font-family: 'Courier New', monospace;
        font-size: {TYPOGRAPHY['small']};
        line-height: 1.6;
        white-space: pre-wrap;
        margin-top: {SPACING['md']};
    ">
    {message}
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("This is a simulated notification for demonstration purposes only.")


def assumptions_expander(result: dict) -> None:
    """Render the assumptions and caveats section."""
    with st.expander("📝 Assumptions & caveats", expanded=False):
        _assumptions_html = "".join(
            f'''
                <div style="margin-bottom: {SPACING["sm"]}; padding-left: {SPACING["md"]}; position: relative;">
                    <div style="position: absolute; left: 0; top: 0.4rem; width: 6px; height: 6px; 
                         border-radius: 50%; background-color: {WARNING};"></div>
                    <div>{assumption}</div>
                </div>
                '''
            for assumption in result["assumptions"]
        )
        st.markdown(
            _card_html(
                "Important limitations",
                f'''
                <div style="color: {GREY_MEDIUM}; font-size: {TYPOGRAPHY['small']}; margin-bottom: {SPACING['md']};">
                    These assumptions affect the scenario estimates. Review them to understand the limitations.
                </div>
                <div style="font-size: {TYPOGRAPHY['body']};">
                {_assumptions_html}
                </div>
                ''',
                border_color=WARNING,
                bg_color="#FFF3E0"
            ),
            unsafe_allow_html=True,
        )
