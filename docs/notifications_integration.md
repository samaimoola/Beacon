# Notification Lifecycle — Integration Guide (for the UI)

A deterministic, **preview-only** notification service lives in `engine/notifications.py`
and is exposed additively through `engine/api.py`. It generates structured, explicitly
**simulated** customer-notification previews for four lifecycle states. It makes **no AI
calls**, **sends nothing**, and **enrolls no one**. All numbers come verbatim from an
engine `result`.

Existing public interfaces are unchanged — this is purely additive.

## Helper signature

```python
from engine.api import (
    build_notification_preview,   # one state
    build_lifecycle_previews,     # all four states at once
    LIFECYCLE_STATES,             # ("pre_storm","outage_confirmed","restoration_updated","restoration_complete")
    PRE_STORM, OUTAGE_CONFIRMED, RESTORATION_UPDATED, RESTORATION_COMPLETE,  # string constants
)

build_notification_preview(
    *,
    lifecycle_state: str,          # one of LIFECYCLE_STATES
    inputs: dict,                  # current scenario inputs (see below)
    result: dict,                  # current engine result from evaluate_scenario()
    prev_result: dict | None = None,   # previous engine result (for restoration_updated)
    preferences: dict | None = None,   # customer prefs (SEPARATE from eligibility)
) -> dict

build_lifecycle_previews(
    *, inputs, result, prev_result=None, preferences=None
) -> dict   # {state: preview_dict} for all four states
```

### `inputs` (reuse what the sidebar already produces)
```python
{
  "customer_label": "Real premise 2 — Overhead, circuit CIR3",
  "storm_severity": "medium",      # low | medium | high
  "available_crews": 3,
  "access_blocked": False,
  "damage_scenario": "pole_and_span",
}
```

### `preferences` (opt-in and channels — kept separate from scenario eligibility)
```python
{
  "opted_in": True,                              # default True
  "available_channels": ["sms", "email", "push"],# default all three
  "preferred_channel": None,                     # optional override, e.g. "email"
}
```

## Return fields

| Field | Type | Meaning |
| --- | --- | --- |
| `lifecycle_state` | str | Echo of the requested state |
| `message` | str | The preview text — always prefixed `[SIMULATED PREVIEW]` |
| `trigger_reason` | str | Why this notification fires / what it represents |
| `recommended_channel` | str \| None | Chosen channel (preferred → state default → first available) |
| `timing` | str | When this would be sent (human-readable, prototype convention) |
| `scenario_eligible` | bool | From the engine result's `alert_eligible` (prototype rule) |
| `consent_status` | str | `"opted_in"` or `"opted_out"` |
| `channel_available` | bool | Whether any channel is available |
| `send_recommended` | bool | `scenario_eligible AND opted_in AND channel_available` |
| `send_blockers` | list[str] | Why a send is **not** recommended (if any) |
| `estimate_window` | str | `format_window(result)` — `"Unknown"`, `"No repairs modeled"`, or `"x.x–y.y h"` |
| `estimate_change` | dict \| None | Only for `restoration_updated` (see below) |
| `unknowns` | list[str] | What is missing/unknown — surface these, don't hide them |
| `simulation_label` | str | Standard "SIMULATED PREVIEW …" label to display |
| `safety_guidance` | list[str] | Approved safety lines (reused, not generated) |

`estimate_change` (restoration_updated only):
```python
{"kind": "changed|unchanged|to_unknown|from_unknown|both_unknown|no_previous",
 "material": bool,      # per the documented threshold
 "detail": "human-readable explanation"}
```

## Documented prototype thresholds (NOT verified AEP rules)

- **Material estimate change:** an update is *material* if the restoration-window
  **midpoint** moves by **≥ 2.0 hours** OR **≥ 25%**, whichever is easier to meet.
  Any transition **into or out of `Unknown`** is always material. (Constants:
  `engine.notifications.MATERIAL_CHANGE_ABS_HOURS`, `MATERIAL_CHANGE_FRACTION`.)
- **Scenario eligibility** comes from the engine's `alert_eligible` prototype rule and is
  **separate** from opt-in and channel availability. A send is recommended only when all
  three are satisfied.
- **Default channel / timing** per state are prototype conventions (urgent → SMS,
  informational → email), overridable via `preferences.preferred_channel`.

## Guardrails the UI can rely on

- **High risk ≠ confirmed outage.** `outage_confirmed` is produced **only** when you pass
  that explicit `lifecycle_state`; the service never infers it from a High/Critical band.
- **No-damage / zero-duration ≠ restoration complete.** `restoration_complete` is produced
  **only** when you pass that explicit state. If the scenario models 0 h, the preview adds
  an `unknowns` note that completion is asserted by the explicit state, not the estimate.
- **Unknown stays unknown.** If `result` has a `None` window, the message says `Unknown`
  and never fabricates a duration.
- **Opt-out preserves the preview.** `send_recommended` becomes `False` with a blocker, but
  the `message` is still generated so you can display it.

## Example calls

```python
from engine.api import (
    evaluate_scenario, build_notification_preview,
    PRE_STORM, OUTAGE_CONFIRMED, RESTORATION_UPDATED, RESTORATION_COMPLETE,
)

inputs = {
    "customer_label": label, "storm_severity": "medium",
    "available_crews": 3, "access_blocked": False, "damage_scenario": "pole_and_span",
}
result = evaluate_scenario(cid, "medium", 3, False, damage_scenario="pole_and_span")

# 1) Pre-storm advisory
pre = build_notification_preview(lifecycle_state=PRE_STORM, inputs=inputs, result=result)
st.write(pre["message"]); st.caption(pre["simulation_label"])

# 2) Outage confirmed (requires the explicit state)
oc = build_notification_preview(lifecycle_state=OUTAGE_CONFIRMED, inputs=inputs, result=result)

# 3) Restoration estimate updated (needs prev_result for change classification)
prev = evaluate_scenario(cid, "medium", 1, False, damage_scenario="pole_and_span")
upd = build_notification_preview(
    lifecycle_state=RESTORATION_UPDATED, inputs=inputs, result=result, prev_result=prev,
)
st.write(upd["estimate_change"]["detail"])   # material? direction?

# 4) Restoration complete (explicit state; opt-out example)
done = build_notification_preview(
    lifecycle_state=RESTORATION_COMPLETE, inputs=inputs, result=result,
    preferences={"opted_in": False},
)
assert done["send_recommended"] is False      # opted out, but preview still present

# Or build all four at once:
from engine.api import build_lifecycle_previews
all_previews = build_lifecycle_previews(inputs=inputs, result=result, prev_result=prev)
```

## Suggested UI usage

- Render `message` with the `simulation_label` always visible.
- Show `send_recommended` as a status (e.g. "Would send via SMS" vs "Preview only —
  {send_blockers}").
- When `unknowns` is non-empty, surface it so customers see what's missing rather than an
  invented value.
- These are previews only — do not wire them to any real SMS/email/enrollment.
