# Beacon React Frontend

Next.js 14 (App Router) + Tailwind UI for Beacon — *When the lights go out, your plan
doesn't.* It is a single-page "Storm Observatory": an illustrated hero, a scenario
console, the engine's reading, the Ask Beacon AI concierge, and notice previews.

All numbers come from the Python engine through `api_server.py`. The browser never
computes estimates and never touches AWS credentials.

## Run

```bash
# 1. Python API (from the repository root)
source .venv/bin/activate
python api_server.py                 # http://localhost:8000

# 2. Frontend
cd frontend
npm install                          # first time only
npm run dev                          # http://localhost:3000
```

`next.config.js` proxies `/api/*` to `http://localhost:8000`, so the browser uses
same-origin requests. Set `NEXT_PUBLIC_API_URL` only if the API lives elsewhere.

If the API is unreachable, the app shows "Engine disconnected" and **no estimates** —
there is no offline demo data. Retry makes a real request and clears the warning only
after the engine answers.

## What's on the page

| Section | Component | Notes |
| --- | --- | --- |
| Nav + hero | `Nav.tsx`, `Hero.tsx`, `scene/StormScene.tsx` | Illustration reacts to severity, access, and crew count (decorative). |
| 01 · Scenario console | `Console.tsx`, `CometDial.tsx` | Household, simulated storm severity, damage preset, crews (1–10), access, optional declared needs, reset. |
| 02 · Reading | `Reading.tsx` | Restoration range, risk band, evidence quality, prototype alert rule, drivers, "What changed", checklist, provenance. |
| 03 · Ask Beacon AI | `Concierge.tsx` | Server-side concierge; each answer is labeled live Bedrock or rule-based fallback, as returned by the server. |
| 04 · Notice previews | `Notices.tsx` | Simulated lifecycle notices; eligibility, consent, channel, and (for estimate updates) material change shown separately. Nothing is sent. |

State lives in `hooks/useStormReady.ts` (sequence/abort guards, cached reading, retry,
reset). Pure helpers are in `lib/scenario.ts`; the typed client is `lib/api.ts`.

### Declared needs

Two optional checkboxes — "I rely on electricity-dependent medical equipment." and "I may
need accessibility assistance during an outage." Both start unchecked, are never inferred,
and live only in React state (no storage, no logging); Reset clears them. They are sent as
two booleans and tailor the checklist, concierge answers, and notice wording. Risk,
restoration, crews, and alert eligibility do not change, and nothing implies AEP program
eligibility or restoration priority.

## Checks

```bash
npx tsc --noEmit          # type check
npm run build             # production build (stop `npm run dev` first; it shares .next/)
npm run test:e2e          # browser regression checks (needs the API and the app running)
```

`npm run test:e2e` drives headless Chrome over the DevTools protocol with no extra
packages. It simulates backend outages and errors with request interception and mocks
the concierge endpoint, so it never calls Bedrock. It covers retry recovery, stale-reading
gating of the concierge, preset reload, declared needs and reset, and the estimate-update
delivery decision. Set `CHROME_PATH` if Chrome isn't auto-detected; Node 20 needs the
`--experimental-websocket` flag, which the npm script passes.

## Troubleshooting

- **"Engine disconnected"**: start `python api_server.py` and check `curl localhost:8000/health`.
- **500 with MODULE_NOT_FOUND after a build**: `npm run build` and `npm run dev` share `.next/`.
  Stop the dev server, `rm -rf .next`, and start it again.
