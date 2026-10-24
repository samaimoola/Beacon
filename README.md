# StormReady
HackOHI/O 2026 — AEP AI Outage Concierge

A prototype that lets a residential customer select an anonymized household and see an
outage-risk band, a restoration-time estimate, preparation guidance, alert eligibility,
and a notification preview — with controls judges can change to see results update.

> ⚠️ **Milestone 1 uses synthetic demo data only.** Nothing here reflects real AEP
> network data or confirmed predictions. See `AGENTS.md` for scope and architecture.

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

## Smoke check (no browser)

```bash
source .venv/bin/activate
python -c "from engine.api import get_customers, evaluate_scenario; \
print(get_customers()); \
print(evaluate_scenario('demo-001','high',2,True))"
```

## Project layout

```
app.py          Streamlit entry point
ui/             Customer interface components (sidebar, cards, previews)
engine/         Contract, public API, and synthetic demo backend
data/           Challenge datasets (see data/README.md to extract)
docs/           Challenge brief and diagrams
AGENTS.md       Product scope, architecture, shared contract, ownership
```

## What is synthetic right now

- The three demo households (`engine/demo.py`) are fictional.
- Risk bands, restoration windows, and alert eligibility come from simple deterministic
  rules, not real data or a trained model.
- `evidence_quality` is always `"Low"` until real GIS data is integrated.

Deferred to later milestones: GIS processing, model training, live AI, real messaging,
and AWS deployment.
