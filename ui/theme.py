"""
ui/theme.py
============
StormReady UI design system.

Design goal: A polished, approachable outage-preparation assistant that a residential customer 
can understand immediately.

Color palette: carlet (#C41E3A) and grey with restrained amber accents (#FFB347).
"""

# Color palette
CARLET = "#C41E3A"  # Primary brand color
CARLET_LIGHT = "#F8E8E8"
GREY_DARK = "#333333"
GREY_MEDIUM = "#666666"
GREY_LIGHT = "#F5F5F5"
GREY_BORDER = "#E0E0E0"
AMBER = "#FFB347"  # Accent color
AMBER_LIGHT = "#FFF3E0"

# Semantic colors
PRIMARY = CARLET
SECONDARY = GREY_MEDIUM
ACCENT = AMBER
SUCCESS = "#2E7D32"  # Green
WARNING = "#FF9800"  # Orange
ERROR = "#C62828"    # Red
INFO = "#1565C0"     # Blue

# Typography scale (rem)
TYPOGRAPHY = {
    "h1": "1.8rem",
    "h2": "1.5rem", 
    "h3": "1.2rem",
    "h4": "1.1rem",
    "body": "0.95rem",
    "small": "0.85rem",
    "caption": "0.75rem"
}

# Spacing scale (rem)
SPACING = {
    "xs": "0.25rem",
    "sm": "0.5rem",
    "md": "1rem",
    "lg": "1.5rem",
    "xl": "2rem",
    "xxl": "3rem"
}

# Border radius
BORDER_RADIUS = {
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "pill": "9999px"
}

# Shadows
SHADOWS = {
    "sm": "0 1px 2px rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
}

# Risk band colors (using new palette)
RISK_COLOR = {
    "Low": SUCCESS,
    "Moderate": WARNING,
    "High": ERROR,
    "Critical": CARLET  # Use carlet for critical
}

# Evidence quality colors
EVIDENCE_COLOR = {
    "High": INFO,
    "Medium": AMBER,
    "Low": GREY_MEDIUM
}

# CSS utility classes
def card_style(border_color: str = GREY_BORDER, bg_color: str = "white") -> str:
    """Generate CSS for a card component."""
    return f"""
        border: 1px solid {border_color};
        border-radius: {BORDER_RADIUS['md']};
        background-color: {bg_color};
        padding: {SPACING['lg']};
        box-shadow: {SHADOWS['sm']};
        margin-bottom: {SPACING['md']};
    """

def metric_style(color: str = PRIMARY) -> str:
    """Generate CSS for metric display."""
    return f"""
        font-size: {TYPOGRAPHY['h2']};
        font-weight: 600;
        color: {color};
        line-height: 1.2;
    """

def label_style() -> str:
    """Generate CSS for labels."""
    return f"""
        font-size: {TYPOGRAPHY['small']};
        color: {GREY_MEDIUM};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: {SPACING['xs']};
    """

def badge_style(bg_color: str, text_color: str = "white") -> str:
    """Generate CSS for badges."""
    return f"""
        display: inline-block;
        padding: {SPACING['xs']} {SPACING['sm']};
        background-color: {bg_color};
        color: {text_color};
        border-radius: {BORDER_RADIUS['pill']};
        font-size: {TYPOGRAPHY['caption']};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    """

# Helper functions
def apply_card_styles() -> None:
    """Apply global CSS styles for cards."""
    import streamlit as st
    
    st.markdown(f"""
    <style>
    .stormready-card {{
        {card_style()}
    }}
    
    .stormready-card-primary {{
        {card_style(border_color=PRIMARY, bg_color=CARLET_LIGHT)}
    }}
    
    .stormready-card-warning {{
        {card_style(border_color=WARNING, bg_color=AMBER_LIGHT)}
    }}
    
    .stormready-metric {{
        {metric_style()}
    }}
    
    .stormready-metric-primary {{
        {metric_style(color=PRIMARY)}
    }}
    
    .stormready-label {{
        {label_style()}
    }}
    
    .stormready-badge {{
        {badge_style(bg_color=PRIMARY)}
    }}
    
    .stormready-badge-success {{
        {badge_style(bg_color=SUCCESS)}
    }}
    
    .stormready-badge-warning {{
        {badge_style(bg_color=WARNING)}
    }}
    
    .stormready-badge-error {{
        {badge_style(bg_color=ERROR)}
    }}
    
    /* Improve overall typography */
    .stApp {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        line-height: 1.6;
    }}
    
    /* Improve spacing in Streamlit components */
    .stSelectbox, .stSlider, .stCheckbox {{
        margin-bottom: {SPACING['sm']};
    }}
    
    /* Improve tab styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: {SPACING['sm']};
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: {BORDER_RADIUS['md']} {BORDER_RADIUS['md']} 0 0;
        padding: {SPACING['sm']} {SPACING['lg']};
    }}
    
    /* Responsive improvements */
    @media (max-width: 768px) {{
        .stormready-card {{
            padding: {SPACING['md']};
        }}
        
        .stTabs [data-baseweb="tab"] {{
            padding: {SPACING['xs']} {SPACING['md']};
            font-size: {TYPOGRAPHY['small']};
        }}
    }}
    </style>
    """, unsafe_allow_html=True)