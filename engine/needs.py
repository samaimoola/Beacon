"""
engine/needs.py
===============
Optional, customer-DECLARED needs and the prewritten guidance they unlock.

Rules (see README "Declared needs"):
  - Declarations are explicit customer choices. They are never inferred from a
    household, the datasets, or any other field.
  - Only two booleans exist. No diagnoses, device details, addresses, or free text
    are accepted; anything else is dropped by normalize_declared_needs().
  - They tailor preparation guidance and notice wording ONLY. They never change
    outage risk, repair duration, crew scheduling, or alert eligibility, and they
    do not imply AEP program enrollment, eligibility, or restoration priority.
  - All copy here is short, prewritten, general planning guidance. The medical
    line reuses the approved safety guidance verbatim; nothing is generated.
  - Nothing is stored or logged here; callers pass declarations per request.
"""

from __future__ import annotations
from typing import Optional

from engine.safety import APPROVED_SAFETY_GUIDANCE

MEDICAL_EQUIPMENT = "medical_equipment"
ACCESSIBILITY_ASSISTANCE = "accessibility_assistance"

# Allowlisted declaration keys, in display order.
DECLARED_NEED_KEYS: tuple[str, ...] = (MEDICAL_EQUIPMENT, ACCESSIBILITY_ASSISTANCE)

# Customer-facing labels (the exact wording of the optional checkboxes).
DECLARED_NEED_LABELS: dict[str, str] = {
    MEDICAL_EQUIPMENT: "I rely on electricity-dependent medical equipment.",
    ACCESSIBILITY_ASSISTANCE: "I may need accessibility assistance during an outage.",
}

# Short names used in comparisons ("What changed?") and context summaries.
DECLARED_NEED_SHORT: dict[str, str] = {
    MEDICAL_EQUIPMENT: "Medical equipment",
    ACCESSIBILITY_ASSISTANCE: "Accessibility assistance",
}

# Prewritten preparation guidance per declaration (general planning only).
DECLARED_NEED_GUIDANCE: dict[str, list[str]] = {
    MEDICAL_EQUIPMENT: [
        APPROVED_SAFETY_GUIDANCE[2],
        "Keep backup batteries for your equipment charged, and keep your equipment "
        "supplier's and care provider's phone numbers handy.",
    ],
    ACCESSIBILITY_ASSISTANCE: [
        "Ask a friend, neighbor, or family member to check on you during an outage, and "
        "agree on how you will reach each other.",
        "Keep a flashlight, a charged phone, and any mobility or communication aids within "
        "easy reach.",
    ],
}

# Shared escalation line, added once when any need is declared.
ESCALATION_GUIDANCE = "If anyone's health or safety is at immediate risk, call 911."

# Plain statement of what declarations do NOT do.
DECLARED_NEEDS_NOTE = (
    "Your declarations tailor guidance and notice wording only. They do not change outage "
    "risk, repair time, or crew scheduling, and they are not AEP program enrollment, "
    "eligibility, or restoration priority."
)

# Short sentences used inside notification previews.
_NOTICE_LINES: dict[str, str] = {
    MEDICAL_EQUIPMENT: (
        "You told Beacon you rely on electricity-dependent medical equipment. "
        + APPROVED_SAFETY_GUIDANCE[2]
    ),
    ACCESSIBILITY_ASSISTANCE: (
        "You told Beacon you may need accessibility assistance. Ask someone you trust to "
        "check on you during the outage."
    ),
}
_NOTICE_NOT_PRIORITY = (
    "Telling Beacon this does not change restoration priority or enroll you in any AEP program."
)


def normalize_declared_needs(raw: Optional[dict]) -> dict[str, bool]:
    """
    Return exactly the allowlisted keys as strict booleans. Unknown keys, free
    text, and non-boolean values are dropped (a value counts only if it is True).
    """
    raw = raw if isinstance(raw, dict) else {}
    return {k: raw.get(k) is True for k in DECLARED_NEED_KEYS}


def any_declared(needs: Optional[dict]) -> bool:
    return any(normalize_declared_needs(needs).values())


def describe_declared_needs(needs: Optional[dict]) -> str:
    """'None declared' or e.g. 'Medical equipment; Accessibility assistance'."""
    n = normalize_declared_needs(needs)
    names = [DECLARED_NEED_SHORT[k] for k in DECLARED_NEED_KEYS if n[k]]
    return "; ".join(names) if names else "None declared"


def declared_needs_guidance(needs: Optional[dict]) -> list[str]:
    """All prewritten guidance lines for the declared needs (empty if none)."""
    n = normalize_declared_needs(needs)
    lines: list[str] = []
    for k in DECLARED_NEED_KEYS:
        if n[k]:
            lines.extend(DECLARED_NEED_GUIDANCE[k])
    if lines:
        lines.append(ESCALATION_GUIDANCE)
    return lines


def tailor_preparation(preparation_actions: list[str], needs: Optional[dict]) -> list[str]:
    """
    Declared-needs guidance FIRST (so no caller truncation can drop it), then the
    engine's scenario guidance, without duplicates. Returns a new list.
    """
    out: list[str] = []
    for line in declared_needs_guidance(needs) + list(preparation_actions or []):
        if line not in out:
            out.append(line)
    return out


def notice_lines(needs: Optional[dict]) -> list[str]:
    """Sentences appended to a notification preview when needs are declared."""
    n = normalize_declared_needs(needs)
    lines = [_NOTICE_LINES[k] for k in DECLARED_NEED_KEYS if n[k]]
    if lines:
        lines.append(ESCALATION_GUIDANCE)
        lines.append(_NOTICE_NOT_PRIORITY)
    return lines
