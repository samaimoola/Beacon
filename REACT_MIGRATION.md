# Beacon React Migration Notes

The primary interface moved from Streamlit to a React/Next.js frontend backed by a small
FastAPI bridge. The engine, concierge, and notification service did not move: both UIs
call the same Python code, and the Streamlit app (`app.py`, `ui/`) remains a working
alternative.

> The first React version used an "Ohio State" scarlet theme and a sidebar layout. Both
> were replaced by the current "Storm Observatory" design; see `frontend/README.md` for
> the current frontend.

## Architecture

```
Browser (Next.js, :3000) ──/api/* proxy──► api_server.py (FastAPI, :8000)
                                              ├─ engine/api.py      scenario engine (single source of numbers)
                                              ├─ engine/notifications.py  simulated notice previews
                                              └─ concierge/         grounded Bedrock concierge + labeled fallback
```

- The bridge recomputes every result the concierge sees from the submitted inputs; it
  never trusts numbers from the browser.
- AWS/Bedrock configuration and credentials stay server-side.
- If the API is down, the frontend says "Engine disconnected" and shows no estimates.
  There is no offline demo data.

## API endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/status` | GET | Active engine backend (`real` or `demo`) |
| `/api/customers` | GET | Anonymized households |
| `/api/damage-scenarios/{id}` | GET | Simulated damage presets for a household |
| `/api/evaluate` | POST | Evaluate a scenario (optional `declared_needs`) |
| `/api/notification-preview` | POST | Simulated, never-sent notice preview |
| `/api/concierge/ask` | POST | Grounded concierge answer (`mode`: `live` or `fallback`) |
| `/health` | GET | Health check |

## Run

```bash
source .venv/bin/activate && python api_server.py     # API on :8000
cd frontend && npm install && npm run dev              # UI on :3000
streamlit run app.py                                   # optional Streamlit alternative on :8501
```
