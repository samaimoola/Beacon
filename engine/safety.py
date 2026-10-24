"""
engine/safety.py
================
Single source of the APPROVED safety guidance strings.

Pre-written, pre-approved customer-safety lines. They are reused verbatim by the
concierge (grounding) and the notification service so no component invents novel
electrical or medical instructions. Kept in engine/ (dependency-free) so both
the concierge package and the notification service can import it without a cycle.
"""

from __future__ import annotations

# Approved, non-novel safety guidance. Do not generate alternatives at runtime.
APPROVED_SAFETY_GUIDANCE: list[str] = [
    "Stay far away from any downed power line and assume it is energized; report it to AEP Ohio at 1-800-672-2231.",
    "Do not run a generator indoors or in a garage; follow the manufacturer's instructions.",
    "If you rely on electrically powered medical equipment, have a backup plan and know where to go if power is out.",
    "Use flashlights and battery-powered lanterns rather than open flames.",
]
