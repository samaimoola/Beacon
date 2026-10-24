"""
tests/test_ui_components.py
===========================
Tests for UI components to ensure they work correctly with the new design system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.theme import (
    CARLET, GREY_DARK, GREY_MEDIUM, GREY_LIGHT, GREY_BORDER, AMBER,
    SUCCESS, WARNING, ERROR, INFO,
    TYPOGRAPHY, SPACING, BORDER_RADIUS,
    RISK_COLOR, EVIDENCE_COLOR,
)


def test_theme_constants():
    """Test that theme constants are defined correctly."""
    assert CARLET == "#C41E3A", f"CARLET should be #C41E3A, got {CARLET}"
    assert AMBER == "#FFB347", f"AMBER should be #FFB347, got {AMBER}"
    assert GREY_DARK == "#333333", f"GREY_DARK should be #333333, got {GREY_DARK}"
    
    # Check risk colors
    assert RISK_COLOR["Low"] == SUCCESS
    assert RISK_COLOR["Moderate"] == WARNING
    assert RISK_COLOR["High"] == ERROR
    assert RISK_COLOR["Critical"] == CARLET
    
    # Check evidence colors
    assert EVIDENCE_COLOR["High"] == INFO
    assert EVIDENCE_COLOR["Medium"] == AMBER
    assert EVIDENCE_COLOR["Low"] == GREY_MEDIUM
    
    print("✓ Theme constants test passed")


def test_typography_scale():
    """Test that typography scale is defined."""
    assert "h1" in TYPOGRAPHY
    assert "body" in TYPOGRAPHY
    assert "small" in TYPOGRAPHY
    assert "caption" in TYPOGRAPHY
    
    for key, value in TYPOGRAPHY.items():
        assert "rem" in value, f"Typography value for {key} should include 'rem', got {value}"
    
    print("✓ Typography scale test passed")


def test_spacing_scale():
    """Test that spacing scale is defined."""
    assert "xs" in SPACING
    assert "sm" in SPACING
    assert "md" in SPACING
    assert "lg" in SPACING
    
    for key, value in SPACING.items():
        assert "rem" in value, f"Spacing value for {key} should include 'rem', got {value}"
    
    print("✓ Spacing scale test passed")


def test_border_radius():
    """Test that border radius values are defined."""
    assert "sm" in BORDER_RADIUS
    assert "md" in BORDER_RADIUS
    assert "lg" in BORDER_RADIUS
    assert "pill" in BORDER_RADIUS
    
    for key, value in BORDER_RADIUS.items():
        if key == "pill":
            assert value == "9999px", f"Pill border radius should be 9999px, got {value}"
        else:
            assert "px" in value, f"Border radius value for {key} should include 'px', got {value}"
    
    print("✓ Border radius test passed")


def test_component_helpers():
    """Test that component helper functions are defined."""
    from ui.theme import card_style, metric_style, label_style, badge_style
    
    # Test card_style
    card_css = card_style()
    assert "border:" in card_css
    assert "border-radius:" in card_css
    assert "padding:" in card_css
    assert "background-color:" in card_css
    
    # Test metric_style
    metric_css = metric_style()
    assert "font-size:" in metric_css
    assert "font-weight:" in metric_css
    assert "color:" in metric_css
    
    # Test label_style
    label_css = label_style()
    assert "font-size:" in label_css
    assert "color:" in label_css
    assert "text-transform:" in label_css
    
    # Test badge_style
    badge_css = badge_style(SUCCESS)
    assert "background-color:" in badge_css
    assert "color:" in badge_css
    assert "border-radius:" in badge_css
    
    print("✓ Component helpers test passed")


def test_format_window():
    """Test the format_window function from components."""
    try:
        from ui.components import format_window
        
        # Test with None values (unknown)
        assert format_window(None, None) == "Unknown"
        
        # Test with 0-0 window (no repairs modeled)
        # Note: This depends on engine.formatting implementation
        result = format_window(0, 0)
        assert result == "No repairs modeled" or result == "0.0–0.0 hours"
        
        # Test with normal values
        result = format_window(4.5, 8.5)
        assert "4.5" in result and "8.5" in result
        
        print("✓ Format window test passed")
    except ImportError:
        print("⚠ Skipping format_window test (engine dependencies missing)")


if __name__ == "__main__":
    print("Running UI component tests...\n")
    
    test_theme_constants()
    test_typography_scale()
    test_spacing_scale()
    test_border_radius()
    test_component_helpers()
    test_format_window()
    
    print("\n✅ All UI component tests completed!")