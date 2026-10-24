"""
ui/notification_panel.py
========================
Notification lifecycle preview panel using the new notification backend.

Integrates with the existing UI redesign while using the new engine/notifications.py
backend for deterministic, preview-only notification generation.
"""

from __future__ import annotations
import streamlit as st

from engine.api import (
    build_notification_preview,
    build_lifecycle_previews,
    LIFECYCLE_STATES,
    PRE_STORM,
    OUTAGE_CONFIRMED,
    RESTORATION_UPDATED,
    RESTORATION_COMPLETE,
)

from ui.theme import (
    CARLET, GREY_DARK, GREY_MEDIUM, GREY_LIGHT, GREY_BORDER, AMBER,
    SUCCESS, WARNING, ERROR, INFO,
    TYPOGRAPHY, SPACING, BORDER_RADIUS,
    card_style, label_style, apply_card_styles,
)


def _card_html(title: str, content: str, border_color: str = GREY_BORDER, bg_color: str = "white") -> str:
    """Generate HTML for a card with consistent styling."""
    styles = card_style(border_color, bg_color)
    return f'''
    <div style="{styles}">
        <div style="{label_style()}">{title}</div>
        {content}
    </div>
    '''


def _status_indicator(text: str, color: str, icon: str = "●") -> str:
    """Generate a status indicator with icon and text."""
    return f'''
    <div style="display: flex; align-items: center; gap: {SPACING['xs']}; margin-bottom: {SPACING['sm']}">
        <span style="color: {color}; font-size: 1.2rem;">{icon}</span>
        <span style="font-weight: 600; color: {color};">{text}</span>
    </div>
    '''


def render_notification_panel(
    *,
    inputs: dict,
    result: dict,
    storm_severity: str,
    prev_result: dict | None = None,
) -> None:
    """
    Render the enhanced notification preview panel with lifecycle states.
    
    Parameters
    ----------
    inputs : dict
        Current scenario inputs (customer_label, storm_severity, available_crews, 
        access_blocked, damage_scenario)
    result : dict
        Current engine result from evaluate_scenario()
    storm_severity : str
        Current storm severity (for display)
    prev_result : dict | None
        Previous engine result for restoration_updated comparison
    """
    st.markdown(f'<h3 style="margin-bottom: {SPACING["md"]};">📨 Notification Lifecycle</h3>', unsafe_allow_html=True)
    
    # Section explanation
    st.markdown(f"""
    <div style="
        color: {GREY_MEDIUM};
        font-size: {TYPOGRAPHY['body']};
        margin-bottom: {SPACING['lg']};
    ">
        Preview simulated customer notifications across different outage lifecycle states. 
        These are <strong>previews only</strong> — no messages are sent, and no contact 
        information is collected.
    </div>
    """, unsafe_allow_html=True)
    
    # Lifecycle state selector
    st.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['body']};
        margin-bottom: {SPACING['sm']};
    ">
        Simulated lifecycle state
    </div>
    <div style="
        color: {GREY_MEDIUM};
        font-size: {TYPOGRAPHY['small']};
        margin-bottom: {SPACING['md']};
    ">
        Select which stage of an outage to preview notifications for
    </div>
    """, unsafe_allow_html=True)
    
    # State descriptions for the selector
    STATE_DESCRIPTIONS = {
        PRE_STORM: "Pre-storm advisory: Outage risk and preparation guidance",
        OUTAGE_CONFIRMED: "Outage confirmed: Initial notification when outage is detected",
        RESTORATION_UPDATED: "Estimate updated: Revised restoration time based on field assessment",
        RESTORATION_COMPLETE: "Restoration complete: Power restored confirmation"
    }
    
    # State selector
    selected_state = st.selectbox(
        "Select lifecycle state",
        options=LIFECYCLE_STATES,
        format_func=lambda x: STATE_DESCRIPTIONS[x],
        key="notification_lifecycle_state",
        label_visibility="collapsed"
    )
    
    # Customer preferences (demo only, not stored)
    st.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['body']};
        margin-top: {SPACING['lg']};
        margin-bottom: {SPACING['sm']};
    ">
        Demo notification preferences
    </div>
    <div style="
        color: {GREY_MEDIUM};
        font-size: {TYPOGRAPHY['small']};
        margin-bottom: {SPACING['md']};
    ">
        Simulated opt-in and channel preferences (no real data collected)
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        opted_in = st.checkbox(
            "Opted in to notifications",
            value=True,
            key="notification_opted_in",
            help="Whether the customer has consented to receive notifications"
        )
    
    with col2:
        available_channels = st.multiselect(
            "Available channels",
            options=["sms", "email", "push"],
            default=["sms", "email", "push"],
            key="notification_channels",
            help="Channels available for this customer"
        )
    
    # Preferred channel (optional)
    preferred_channel = st.selectbox(
        "Preferred channel (optional)",
        options=[None, "sms", "email", "push"],
        format_func=lambda x: "Auto-select" if x is None else x.upper(),
        key="notification_preferred_channel",
        help="If specified, overrides the default channel selection"
    )
    
    # Build preferences dict
    preferences = {
        "opted_in": opted_in,
        "available_channels": available_channels if available_channels else ["sms", "email", "push"],
        "preferred_channel": preferred_channel,
    }
    
    # Generate the notification preview
    try:
        preview = build_notification_preview(
            lifecycle_state=selected_state,
            inputs=inputs,
            result=result,
            prev_result=prev_result,
            preferences=preferences,
        )
        
        # Display the preview
        _render_preview_details(preview, selected_state)
        
    except Exception as e:
        st.error(f"Error generating notification preview: {e}")
        st.exception(e)


def _render_preview_details(preview: dict, selected_state: str) -> None:
    """Render the notification preview with all details."""
    
    # Status card showing send recommendation
    send_color = SUCCESS if preview["send_recommended"] else WARNING
    send_status = "Would send" if preview["send_recommended"] else "Preview only"
    send_icon = "✅" if preview["send_recommended"] else "⚠️"
    
    # Channel info
    channel_display = preview["recommended_channel"] or "No channel available"
    
    st.markdown(
        _card_html(
            "Notification status",
            f'''
            <div style="margin-bottom: {SPACING['md']}">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: {SPACING['sm']}">
                        <span style="color: {send_color}; font-size: 1.5rem;">{send_icon}</span>
                        <span style="font-weight: 600; color: {send_color}; font-size: {TYPOGRAPHY['h4']}">
                            {send_status}
                        </span>
                    </div>
                    <div style="font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">
                        via {channel_display.upper()}
                    </div>
                </div>
                
                <div style="margin-top: {SPACING['sm']}; font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">
                    {preview["trigger_reason"]}
                </div>
                
                <div style="margin-top: {SPACING['xs']}; font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">
                    <strong>Timing:</strong> {preview["timing"]}
                </div>
            </div>
            ''',
            border_color=send_color,
            bg_color="#FFF3E0" if not preview["send_recommended"] else "#E8F5E9"
        ),
        unsafe_allow_html=True,
    )
    
    # Show blockers if send is not recommended
    if not preview["send_recommended"] and preview["send_blockers"]:
        blockers_html = "".join([
            f'<div style="margin-bottom: {SPACING["xs"]}">• {blocker}</div>'
            for blocker in preview["send_blockers"]
        ])
        
        st.markdown(
            _card_html(
                "Why notification would not be sent",
                f'''
                <div style="color: {WARNING}; font-size: {TYPOGRAPHY['small']};">
                    {blockers_html}
                </div>
                ''',
                border_color=WARNING,
                bg_color="#FFF3E0"
            ),
            unsafe_allow_html=True,
        )
    
    # Estimate information (especially important for RESTORATION_UPDATED)
    if selected_state == RESTORATION_UPDATED and preview.get("estimate_change"):
        change = preview["estimate_change"]
        change_color = AMBER if change["material"] else GREY_MEDIUM
        change_icon = "📈" if change["material"] else "↔️"
        
        st.markdown(
            _card_html(
                "Estimate change",
                f'''
                <div style="margin-bottom: {SPACING['sm']}">
                    <div style="display: flex; align-items: center; gap: {SPACING['sm']}">
                        <span style="font-size: 1.2rem;">{change_icon}</span>
                        <span style="font-weight: 600; color: {change_color}">
                            {change["kind"].replace("_", " ").title()}
                        </span>
                    </div>
                    <div style="margin-top: {SPACING['xs']}; font-size: {TYPOGRAPHY['small']}; color: {GREY_MEDIUM};">
                        {change["detail"]}
                    </div>
                </div>
                ''',
                border_color=change_color,
                bg_color="#FFF3E0" if change["material"] else GREY_LIGHT
            ),
            unsafe_allow_html=True,
        )
    
    # Unknowns section
    if preview.get("unknowns"):
        unknowns_html = "".join([
            f'<div style="margin-bottom: {SPACING["xs"]}">• {unknown}</div>'
            for unknown in preview["unknowns"]
        ])
        
        st.markdown(
            _card_html(
                "Missing information",
                f'''
                <div style="color: {WARNING}; font-size: {TYPOGRAPHY['small']};">
                    {unknowns_html}
                </div>
                ''',
                border_color=WARNING,
                bg_color="#FFF3E0"
            ),
            unsafe_allow_html=True,
        )
    
    # Safety guidance
    if preview.get("safety_guidance"):
        safety_html = "".join([
            f'<div style="margin-bottom: {SPACING["xs"]}">• {guidance}</div>'
            for guidance in preview["safety_guidance"]
        ])
        
        st.markdown(
            _card_html(
                "Safety information",
                f'''
                <div style="color: {INFO}; font-size: {TYPOGRAPHY['small']};">
                    {safety_html}
                </div>
                ''',
                border_color=INFO,
                bg_color="#E3F2FD"
            ),
            unsafe_allow_html=True,
        )
    
    # The actual message preview
    st.markdown(f"""
    <div style="
        font-weight: 600;
        color: {GREY_DARK};
        font-size: {TYPOGRAPHY['body']};
        margin-top: {SPACING['lg']};
        margin-bottom: {SPACING['sm']};
    ">
        Message preview
    </div>
    """, unsafe_allow_html=True)
    
    # Simulation label
    st.markdown(f"""
    <div style="
        background-color: #FFF3E0;
        border: 1px solid {WARNING};
        border-radius: {BORDER_RADIUS['sm']};
        padding: {SPACING['sm']};
        font-size: {TYPOGRAPHY['small']};
        color: {WARNING};
        font-weight: 600;
        margin-bottom: {SPACING['md']};
    ">
        ⚠️ {preview["simulation_label"]}
    </div>
    """, unsafe_allow_html=True)
    
    # Message content
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
        margin-bottom: {SPACING['xl']};
    ">
    {preview["message"]}
    </div>
    """, unsafe_allow_html=True)
    
    # Final disclaimer
    st.caption(
        "This is a simulated notification preview for demonstration purposes only. "
        "No messages are sent, and no contact information is collected or stored."
    )