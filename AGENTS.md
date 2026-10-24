# AGENTS.md — StormReady

Guidance for humans and AI agents working in this repository.

## Product scope

StormReady is a prototype **AI Outage Concierge** built for the AEP HackOHI/O 2026
challenge. A residential customer selects an anonymized household and receives:

- An **outage-risk band** with contributing factors and an evidence-quality rating.
- A **restoration-duration range** with the assumptions behind it.
- **Preparation guidance** tailored to the scenario.
- **Alert eligibility** under documented prototype rules.
- A **preview of a customer notification**.

Judges must be able to change scenario inputs (household, storm severity, crew
availability, access conditions) and see the results update.

### What this milestone is NOT
- Not using real AEP network topology, real customer records, or confirmed predictions.
- No GIS processing, model training, live AI, real messaging, or AWS deployment yet.
- All outputs are **synthetic demo estimates** and are labeled as such everywhere.

## Architecture

```
app.py                 Streamlit entry point (UI)
ui/
  sidebar.py           Customer selection + scenario input controls + reset
  components.py        Reusable cards, checklist, notification preview
engine/
  contracts.py         Shared inputs/outputs contract + example response (source of truth)
  api.py               Public interface the UI imports (get_customers, evaluate_scenario)
  demo.py              Synthetic demo backend (fictional households + deterministic logic)
data/                  Challenge datasets (raw zips) + extraction instructions
docs/                  Challenge brief and structure diagrams
```

Data flow: `app.py` / `ui/` import **only** from `engine/api.py`. `api.py` delegates to a
backend (currently `engine/demo.py`). The UI never imports `demo.py` directly.

## Shared contract

Defined in `engine/contracts.py`. Both engine and UI must conform.

### Inputs to `evaluate_scenario`
| Param | Type | Allowed values |
| --- | --- | --- |
| `customer_id` | `str` | an id from `get_customers()` |
| `storm_severity` | `str` | `"low"`, `"medium"`, `"high"` |
| `available_crews` | `int` | `1`–`10` |
| `access_blocked` | `bool` | `True` / `False` |

### `get_customers()` output
List of dicts: `{"id": str, "label": str}`.

### `evaluate_scenario()` output
| Field | Type | Notes |
| --- | --- | --- |
| `risk_band` | `str` | `Low` / `Moderate` / `High` / `Critical` |
| `evidence_quality` | `str` | `High` / `Medium` / `Low` (always `Low` in demo) |
| `risk_factors` | `list[str]` | contributing factors |
| `restoration_low_hours` | `float \| None` | lower bound; `None` = unknown |
| `restoration_high_hours` | `float \| None` | upper bound; `None` = unknown |
| `restoration_factors` | `list[str]` | drivers of the window |
| `preparation_actions` | `list[str]` | actionable steps |
| `alert_eligible` | `bool` | meets prototype notification rules |
| `assumptions` | `list[str]` | caveats and limitations |
| `source_label` | `str` | data provenance notice |

**Unknown restoration estimates** (`None`) must be handled gracefully by the UI — show
"Unknown" rather than crashing or inventing a number.

## Ownership rules

| Area | Owner |
| --- | --- |
| `engine/`, `scripts/`, processed data | **Samai** |
| `app.py`, `ui/` | **Roommate** |
| `engine/contracts.py`, `requirements.txt` | **Shared — coordinate before changing** |

Any change to the shared contract or dependencies requires agreement between both owners,
because it affects code on the other side of the boundary.

## Integrity rules for agents

- Never present invented probabilities or imply results are confirmed AEP predictions.
- Keep the `source_label` and synthetic-demo warnings visible in the UI.
- Separate scenario estimates from confirmed information in the UI.
- Preserve existing work; extend rather than replace.
