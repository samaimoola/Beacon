# AGENTS.md — Beacon

Guidance for humans and AI agents working in this repository.

## Product scope

Beacon is a prototype **AI Outage Concierge** built for the AEP HackOHI/O 2026
challenge. A residential customer selects an anonymized household and receives:

- An **outage-risk band** with contributing factors and an evidence-quality rating.
- A **restoration-duration range** with the assumptions behind it.
- **Preparation guidance** tailored to the scenario.
- **Alert eligibility** under documented prototype rules.
- A **preview of a customer notification**.

Judges must be able to change scenario inputs (household, storm severity, crew
availability, access conditions) and see the results update.

### Data reality (current state — supersedes the old "synthetic-only" statement)
The default backend now uses **real, anonymized** AEP network topology and labor
references. What is and isn't real:
- **Real (anonymized):** topology (customer→transformer→upstream devices), equipment
  types, anonymized circuit names, historical damage counts, labor install/removal
  references, and the single indirect labor multiplier (ILM 4.5).
- **Simulated:** the storm severity AND the specific damage scenario (which assets are
  damaged, quantities, and repair tasks). Chosen via user presets, not a live feed.
- **Historical context, not current damage:** prior circuit damage is background only; it
  does not prove current damage and does not generate repair work.
- **Unvalidated heuristic:** the restoration estimate is a transparent effort calculation,
  never checked against real outcomes. Its low–high range is an ASSUMED uncertainty band,
  NOT a statistically validated interval.
- **Evidence quality** reflects how much real data backs the inputs — it must NOT be read
  as measured prediction accuracy.
- A clearly-labeled **synthetic demo** backend remains as a fallback.

### Live AI concierge (milestone 3 — present)
- The **Ask Beacon AI** chat explains engine results via Amazon Bedrock (Converse API,
  `boto3`). The ENGINE is always the source of numbers; the model never computes or
  overrides the active scenario. "Another crew?" questions compare the current count with
  exactly one more crew (never above 10) through the engine, and the explanation comes
  from engine schedule facts (`engine.api.schedule_summary`): critical path only when the
  scheduler says so; no-damage and Unknown results get their own explanations.
- The context sent to the model is **allowlisted and PII-free** (see `concierge/context.py`);
  raw premise numbers, addresses, meters, employee fields, coordinates, and datasets are
  excluded by construction.
- AWS config (region + model id) is **external** (env vars); credentials use the normal
  chain. Nothing secret is stored in code, Git, output, or logs. If AWS is unavailable,
  a **clearly-labeled rule-based fallback** answers instead — never shown as live AI.

### What this milestone is NOT
- No model training, real messaging, or AWS *deployment* yet (runtime invocation only).
- No claim of confirmed/accurate outage or restoration predictions.

### Temporary ownership arrangement (solo)
> **Temporary:** while the team is operating solo, a single maintainer is authorized to
> edit across `engine/`, `scripts/`, `app.py`, `ui/`, `tests/`, and shared docs
> (`README.md`, `AGENTS.md`), including the shared contract — taking care to keep the UI
> and `engine/contracts.py` consistent in the same change. The split ownership below
> resumes when the second maintainer returns, and shared-contract/dependency changes go
> back to requiring coordination.

### Declared needs (optional)
- Two explicit customer booleans (`engine/needs.py`): electricity-dependent medical
  equipment, and accessibility assistance. Never inferred; session memory only; reset
  clears them. They tailor guidance and notice wording only — never risk, restoration,
  crews, alert eligibility, or any implied AEP program/priority.

## Architecture

```
frontend/              React/Next.js UI (primary): console, reading, concierge, notices
api_server.py          FastAPI bridge for the React UI (recomputes results server-side)
app.py                 Streamlit entry point (alternative UI)
ui/
  sidebar.py           Customer selection + scenario input controls + reset
  components.py        Reusable cards, checklist, notification preview
ui/
  concierge_panel.py   "Ask Beacon AI" chat (explicit-action calls only; live/fallback badge)
engine/
  contracts.py         Shared inputs/outputs contract + example response (source of truth)
  api.py               Public interface the UI imports (get_customers, evaluate_scenario, ...)
  demo.py              Synthetic demo backend (fictional households + deterministic logic)
  realdata.py          Real anonymized backend + simulated damage scenarios
  restoration.py       Crew/dependency-aware restoration scheduler (+ dependency_limited flag)
  notifications.py     Simulated lifecycle notice previews and send decision
  needs.py             Optional declared needs: allowlist + prewritten guidance
  safety.py            Approved safety guidance (single source)
  formatting.py        Shared window formatting (incl. "No repairs modeled")
concierge/
  context.py           Allowlisted, PII-free context builder
  grounding.py         System/grounding instructions, approved safety guidance, fallback
  provider.py          Amazon Bedrock Converse call + external config/availability
  assistant.py         Orchestration: context -> provider-or-fallback, engine counterfactuals
data/                  Challenge datasets (raw zips) + extraction instructions
docs/                  Challenge brief and structure diagrams
```

Data flow: `app.py` / `ui/` import **only** from `engine/api.py` for engine results and
from `concierge/` for chat. `api.py` delegates to a backend. The concierge is called ONLY
on an explicit user question/suggested-click, never on ordinary reruns, and uses the
engine as the sole source of numbers.

## Shared contract

Defined in `engine/contracts.py`. Both engine and UI must conform.

### Inputs to `evaluate_scenario`
| Param | Type | Allowed values |
| --- | --- | --- |
| `customer_id` | `str` | an id from `get_customers()` |
| `storm_severity` | `str` | `"low"`, `"medium"`, `"high"` |
| `available_crews` | `int` | `1`–`10` |
| `access_blocked` | `bool` | `True` / `False` |
| `damage_scenario` | `str \| None` | optional preset id from `get_damage_scenarios()` |
| `declared_needs` | `dict \| None` | optional `{"medical_equipment": bool, "accessibility_assistance": bool}`; changes `preparation_actions` (+1 assumption) only |

### `get_customers()` output
List of dicts: `{"id": str, "label": str}`.

### `evaluate_scenario()` output
| Field | Type | Notes |
| --- | --- | --- |
| `risk_band` | `str` | `Low` / `Moderate` / `High` / `Critical` |
| `evidence_quality` | `str` | `High` / `Medium` / `Low` — how much real data backs the inputs, NOT prediction accuracy (`Low` in the synthetic demo, `Medium` in the real-data backend) |
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

Parallel-development split (both maintainers active):

| Area | Owner |
| --- | --- |
| `engine/`, `concierge/`, `scripts/`, and backend tests (`tests/test_calculations.py`, `tests/test_concierge.py`) | **Samai** |
| `app.py`, `ui/`, styling, and dedicated UI tests | **Roommate** |
| `engine/contracts.py` (public interface), `requirements.txt`, and processed-data schemas (`data/processed/*` shape produced by `scripts/build_processed.py` and consumed by `engine/`) | **Shared — coordinate before changing** |

Coordinate before changing any **public interface** (`engine/api.py` / `engine/contracts.py`
signatures and output fields), `requirements.txt`, or the **processed-data schema**, because
each affects code on the other side of the boundary. Everything else can proceed in parallel
within the owner's area.

> Note: the earlier "temporary solo arrangement" section above is superseded by this split now
> that both maintainers are active again.

## Integrity rules for agents

- Never present invented probabilities or imply results are confirmed AEP predictions.
- Keep the `source_label` and synthetic-demo warnings visible in the UI.
- Separate scenario estimates from confirmed information in the UI.
- Preserve existing work; extend rather than replace.
