# Beacon
*When the lights go out, your plan doesn't.*

HackOHI/O 2026 — AEP AI Outage Concierge

> **Naming note.** This project was formerly called Beacon. The product name is
> now **Beacon**. The repository, local folder, `Beacon_*` environment variables,
> API routes, and internal module names are intentionally unchanged so existing
> setups keep working.

A prototype that lets a residential customer select an anonymized household and see an
outage-risk band, a restoration-time estimate, preparation guidance, alert eligibility,
and a notification preview — with controls judges can change to see results update.

> ⚠️ **What this is.** The default backend uses **real, anonymized** AEP network
> topology and labor references, but the **storm and the specific damage are
> SIMULATED**, and the restoration model is an **unvalidated heuristic** — not a
> measured or statistically validated prediction. Historical circuit damage is shown
> as *context*, never as proof of current damage. A clearly-labeled synthetic demo
> backend is also available as a fallback. See `AGENTS.md` for full scope.

## Run the app (React UI — recommended)

```bash
# Terminal 1 — Python API (repository root)
python3 -m venv .venv && source .venv/bin/activate     # first time only
pip install -r requirements.txt                        # first time only
python api_server.py                                   # http://localhost:8000

# Terminal 2 — frontend
cd frontend && npm install && npm run dev              # http://localhost:3000
```

Or run `./start-react-demo.sh` (macOS/Linux) / `.\start-react-demo.ps1` (Windows).

The page is a single "Storm Observatory": a scenario console (household, simulated storm
severity, damage preset, crews 1–10, access, optional declared needs, reset), the engine's
reading, **Ask Beacon AI**, and notice previews. If the API is unreachable it shows
"Engine disconnected" and no estimates; **Retry** makes a real request and clears the
warning only when the engine answers. See `frontend/README.md` for details.

## Streamlit alternative UI

The original Streamlit UI still works and uses the same engine and concierge:

From the repository root (`Beacon/`):

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows (PowerShell)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Streamlit prints a local URL (default **http://localhost:8501**). Open it in a browser.

## Real-data pipeline (milestone 2)

The engine prefers a **real-data backend** built from the supplied archives, and falls
back to the synthetic demo if the processed file is absent — so the app always runs.

```bash
source .venv/bin/activate
python -m scripts.extract_data       # unzip into data/extracted/ (git-ignored)
python -m scripts.inspect_data       # verify joins; writes data/processed/inspection_report.json
python -m scripts.build_processed    # writes PII-free data/processed/premises.json
python -m tests.test_calculations    # calculation + contract tests
```

These scripts use only the standard library + pandas/numpy (already installed) — no new
dependencies. `data/extracted/` and raw PII never leave your machine; only aggregate,
anonymized values are written to `data/processed/`.

Select a backend explicitly with an env var (default is `auto`):

```bash
Beacon_BACKEND=real streamlit run app.py   # real anonymized premises
Beacon_BACKEND=demo streamlit run app.py   # synthetic fallback
```

## Live AI concierge (milestone 3)

**Ask Beacon AI** lets a customer ask what their estimate means, why it changed, or how
to prepare. Answers EXPLAIN the engine's calculated results — the assistant never invents
numbers, weather, outages, or AEP program eligibility.

"Would another crew help?" compares the current crew count with **exactly one more
crew**, re-running the engine with the same household, severity, damage preset, and
access (the active scenario is not changed). The engine's scheduler also reports whether
the schedule is at its critical path, so the answer gives the real reason:

| Situation | Answer |
| --- | --- |
| One more crew shortens the window | Old → new window from the engine. |
| Unchanged, schedule at its critical path | Sequential jobs (or a single job) that extra crews can't shorten. |
| Unchanged, not at the critical path | How jobs fit across crews; no critical-path claim. |
| "No repairs modeled" | No repair jobs to shorten, plus "this does not guarantee uninterrupted power". |
| Unknown estimate | The missing labor-hour mapping is why; no hours are stated. |
| Already at 10 crews (the maximum) | Says so; nothing beyond 10 is evaluated. |

The live model and the rule-based fallback receive the same engine-backed facts.
`used_counterfactual` is true only when a comparison was actually computed.

It uses **Amazon Bedrock** (Converse API via `boto3`). If AWS isn't configured, the
app stays fully usable with a **clearly-labeled rule-based fallback** that composes
answers directly from the engine.

Configure externally (never in code or Git). Credentials come from the normal AWS
credential chain (profile / SSO / env / role):

```bash
export BEDROCK_REGION=us-east-1                 # or AWS_REGION
export BEDROCK_MODEL_ID=<model-or-inference-profile-id>   # e.g. an Anthropic/Titan id
export AWS_PROFILE=<your-profile>               # or configure SSO / env credentials
python api_server.py                            # or: streamlit run app.py
```

The UI status badge shows whether live AI is connected or the fallback is active. No
credentials or provider configuration are ever entered in the customer interface.

Check provider readiness without exposing secrets:

```bash
python -c "from concierge.provider import provider_status as s; print(s())"
```

## Declared needs (optional)

The React console has two optional, unchecked-by-default declarations: "I rely on
electricity-dependent medical equipment." and "I may need accessibility assistance during
an outage." They are explicit customer choices, never inferred from a household or the
data, held only in browser memory for the session (no storage or logging), and cleared by
Reset. Only the two booleans are sent; no diagnoses, device details, or free text.

They add short prewritten planning lines (`engine/needs.py`, reusing the approved medical
safety line) to the checklist (listed first), the concierge context and fallback, and
notice previews, with "call 911" for immediate risk. They do **not** change outage risk,
restoration hours, crew scheduling, or alert eligibility, and they do not imply AEP
program enrollment, eligibility, or restoration priority. `evaluate_scenario(...,
declared_needs=None)` keeps existing callers unchanged.

## Notification send rule

A simulated notice is recommended for sending only when scenario eligibility, customer
consent, and an available channel all line up. An **"Estimate updated"** notice also needs
a **material** estimate change: the midpoint moves ≥ 2.0 h or ≥ 25%, or the estimate moves
into or out of Unknown. Unchanged, below-threshold, still-Unknown, or no-previous-estimate
cases show the preview with a plain-language blocker. Nothing is ever sent. See
`docs/notifications_integration.md`.

## Tests

```bash
source .venv/bin/activate
for t in test_calculations test_concierge test_crew_comparison test_notifications \
         test_notification_integration test_declared_needs test_ui_components; do
  python -m tests.$t || break
done
cd frontend && npx tsc --noEmit && npm run test:e2e   # e2e needs the API and app running
```

Provider calls are mocked in automated tests. `scripts/validate_concierge_live.py` is a
separate, manual live check that needs AWS access.

## Smoke check (no browser)

```bash
source .venv/bin/activate
python -c "from engine.api import get_customers, evaluate_scenario, active_backend_name; \
print('backend:', active_backend_name()); \
cid=get_customers()[0]['id']; print('customer:', cid); \
print(evaluate_scenario(cid,'high',2,True))"
```

## Project layout

```
frontend/       React/Next.js UI (primary) — see frontend/README.md
api_server.py   FastAPI bridge used by the React UI
app.py          Streamlit entry point (alternative UI)
ui/             Streamlit components incl. concierge chat panel
engine/         Contract, public API, demo + real-data backends, scheduler (owner: Samai)
concierge/      Live AI concierge: context, grounding, Bedrock provider, orchestration
scripts/        Extraction, inspection, and processed-data builders (owner: Samai)
tests/          Calculation, contract, concierge, crew-comparison, notification, and declared-needs tests
data/raw/       Supplied archives (zipped)
data/extracted/ Unzipped shapefiles/topology (git-ignored; may contain PII)
data/processed/ PII-free derived JSON consumed by the engine
docs/           Challenge brief and diagrams
AGENTS.md       Product scope, architecture, shared contract, ownership
```

## What is real vs simulated vs assumed

- **Real (anonymized):** network topology (customer→transformer→upstream devices),
  equipment types, anonymized circuit names, historical damage counts, and the labor
  install/removal references with the indirect labor multiplier (ILM 4.5).
- **Simulated:** the storm severity, and the *specific damage scenario* (which assets
  are damaged, how many, and the repair tasks). These are chosen by the user via
  presets, not read from a live feed.
- **Historical context, not current damage:** circuit damage from a prior assessment
  (`arcos_prod_damage_09_28`) is shown only as background. It is **not** evidence that
  any equipment is damaged now, and it does not drive the repair plan.
- **Unvalidated heuristic:** the restoration estimate is a transparent effort
  calculation from the simulated repair jobs. It has **not** been checked against actual
  restoration outcomes. The low–high range is an **assumed uncertainty band**, not a
  statistically validated confidence interval.
- **Evidence quality** describes *how much real data backs the inputs* (topology/labor
  are real; storm/damage are simulated). It does **not** describe prediction accuracy.
- **Open question (labor units):** neither the workbook (`INSTALL_HOURS` /
  `REMOVE_HOURS`, "Avg Install Hours", and an ILM note covering drive, safety-discussion,
  and setup time) nor the challenge brief ("representative labor hours by damage type")
  says whether the hours are worker-hours, crew-hours, or elapsed hours. Beacon keeps the
  labeled assumption: hours are effort, one crew per job, crew size 1, ILM 4.5 applied
  once. The multiplier and scheduler are unchanged until AEP answers. Question for the
  mentors: *"Are the workbook's install/remove hours per worker, per crew, or elapsed
  clock time, and if per worker, what crew size should we assume for one repair job?"*
- **Synthetic fallback:** the three fictional demo households in `engine/demo.py` remain
  available and clearly labeled when the real data is not built.

Not in this prototype: geometry/GIS mapping, model training, real messaging or enrollment,
and AWS deployment. (Live AI runs locally through Bedrock when AWS is configured.)
