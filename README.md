# StormReady
HackOHI/O 2026 — AEP AI Outage Concierge

A prototype that lets a residential customer select an anonymized household and see an
outage-risk band, a restoration-time estimate, preparation guidance, alert eligibility,
and a notification preview — with controls judges can change to see results update.

> ⚠️ **What this is.** The default backend uses **real, anonymized** AEP network
> topology and labor references, but the **storm and the specific damage are
> SIMULATED**, and the restoration model is an **unvalidated heuristic** — not a
> measured or statistically validated prediction. Historical circuit damage is shown
> as *context*, never as proof of current damage. A clearly-labeled synthetic demo
> backend is also available as a fallback. See `AGENTS.md` for full scope.

## Setup & run (exact commands)

From the repository root (`StormReady/`):

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
STORMREADY_BACKEND=real streamlit run app.py   # real anonymized premises
STORMREADY_BACKEND=demo streamlit run app.py   # synthetic fallback
```

## Live AI concierge (milestone 3)

The **Ask StormReady** tab lets a customer ask what their estimate means, why it
changed, or how to prepare. Answers EXPLAIN the engine's calculated results — the
assistant never invents numbers, weather, outages, or AEP program eligibility. All
numbers come from the engine; a "would more crews help?" question is answered by
re-running the engine with the same scenario and more crews.

It uses **Amazon Bedrock** (Converse API via `boto3`). If AWS isn't configured, the
app stays fully usable with a **clearly-labeled rule-based fallback** that composes
answers directly from the engine.

Configure externally (never in code or Git). Credentials come from the normal AWS
credential chain (profile / SSO / env / role):

```bash
export BEDROCK_REGION=us-east-1                 # or AWS_REGION
export BEDROCK_MODEL_ID=<model-or-inference-profile-id>   # e.g. an Anthropic/Titan id
export AWS_PROFILE=<your-profile>               # or configure SSO / env credentials
streamlit run app.py
```

The UI status badge shows whether live AI is connected or the fallback is active. No
credentials or provider configuration are ever entered in the customer interface.

Check provider readiness without exposing secrets:

```bash
python -c "from concierge.provider import provider_status as s; print(s())"
```

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
app.py          Streamlit entry point (owner: roommate)
ui/             Customer interface components incl. concierge chat panel (owner: roommate)
engine/         Contract, public API, demo + real-data backends, scheduler (owner: Samai)
concierge/      Live AI concierge: context, grounding, Bedrock provider, orchestration
scripts/        Extraction, inspection, and processed-data builders (owner: Samai)
tests/          Calculation, contract, and concierge tests
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
- **Open question (labor units):** the workbook does not state whether its hours are
  worker-hours, crew-hours, or elapsed hours. StormReady treats them as effort and any
  conversion to elapsed time exposes its assumed interpretation and crew size.
- **Synthetic fallback:** the three fictional demo households in `engine/demo.py` remain
  available and clearly labeled when the real data is not built.

Deferred to later milestones: geometry/GIS mapping, model training, live AI, real
messaging, and AWS deployment.
