# Beacon React UI — Quick Start

Prerequisites: Node.js 18+ and the project's Python virtual environment.

```bash
# Terminal 1 — Python API (repository root)
source .venv/bin/activate
pip install -r requirements.txt      # first time only
python api_server.py                 # serves http://localhost:8000

# Terminal 2 — frontend
cd frontend
npm install                          # first time only
npm run dev                          # opens on http://localhost:3000
```

For live AI answers, sign in to AWS first and start the API with your region and model
configured outside the code (see the main `README.md`). Without that, Ask Beacon AI uses
its clearly labeled rule-based fallback.

## Using the page

1. **Scenario console**: pick an anonymized household, a simulated storm severity, a
   damage preset, the crew count (dial, arrow keys, or −/+), and access. Optionally tick
   the declared-needs boxes. Every change re-runs the engine; the last reading stays
   visible while it updates.
2. **Reading**: the modeled restoration range (a heuristic band), the outage-risk band,
   evidence quality, the prototype alert rule, what drives them, "What changed", and the
   preparation checklist.
3. **Ask Beacon AI**: suggested or typed questions. Nothing is sent until you ask. It is
   disabled whenever the reading doesn't match your controls.
4. **Notice previews**: choose a simulated lifecycle moment and preferences to see the
   draft and the delivery decision. Nothing is sent.

**Reset scenario** restores the defaults and clears the comparison, chat, checklist ticks,
and declared needs.

If the API stops, the page says "Engine disconnected" and shows no new estimates. Use
**Retry** once the API is back.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 (`/health`, `/docs`) |
| Streamlit alternative | `streamlit run app.py` → http://localhost:8501 |
