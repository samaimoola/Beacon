"""
engine/formatting.py
====================
Tiny, dependency-free formatting helpers shared by the UI and the concierge.

Kept in engine/ (not ui/) so non-Streamlit code — the concierge package and its
tests — can import it without pulling in Streamlit.
"""

from __future__ import annotations
from typing import Optional


def format_window(low: Optional[float], high: Optional[float]) -> str:
    """Human-readable restoration window, with graceful handling of None/zero."""
    if low is None or high is None:
        return "Unknown"
    if low == 0 and high == 0:
        return "No repairs modeled"
    return f"{low:.1f}–{high:.1f} h"
