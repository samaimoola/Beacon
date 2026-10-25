# beacon-video

Silent 1920×1080 · 30 fps H.264 clips for the Beacon demo, built with Remotion 4.0.538.
Standalone project — it does not import the Beacon Next.js app.

| Composition | Length | Output |
| --- | --- | --- |
| BeaconIntro | 6 s | `out/beacon-intro.mp4` |
| RepairDependencies | 14 s | `out/beacon-repair-dependencies.mp4` |
| BeaconOutro | 5 s | `out/beacon-outro.mp4` |
| BeaconPreview | 24 s (0.5 s fades) | `out/beacon-preview.mp4` |

## Commands (Node 20: `export PATH="/opt/homebrew/opt/node@20/bin:$PATH"`)

```sh
npm install
npm run studio          # Remotion Studio on http://localhost:3123
npm run render:all      # or render:intro / render:repair / render:outro / render:preview
npm run data            # re-export engine values into src/data/repair-demo.json (uses ../.venv)
npx tsc --noEmit
```

## Local source media (not committed)

The overlay compositions read screen recordings and narration from `public/source/`.
That folder is git-ignored (raw media is large and local-only). To render the overlay
clips, place these files there with these exact names:

| File | What it is |
| --- | --- |
| `concierge receives.mov` | Screen recording for the concierge overlay |
| `concierge receives.m4a` | Narration audio for the concierge overlay |
| `distinction matters.mov` | Screen recording for the distinction overlay |
| `distinction matters.m4a` | Narration audio for the distinction overlay |

The committed overlay sources also expect the local fonts in `public/fonts/` (tracked).

## Notes

- Ports: Studio 3123, renderer 3124 (Beacon uses 3000, 8000, 8501).
- Browser: Remotion's downloaded headless shell stalls on this Mac, so `remotion.config.ts`
  uses Playwright's `chrome-headless-shell` from `~/Library/Caches/ms-playwright`, or the path
  in `BEACON_VIDEO_BROWSER`. Without either, Remotion falls back to its own browser.
- Repair ranges come from `api.evaluate_scenario` (same overhead household, medium severity,
  multi_damage, clear access; only crews change). The export script fails if its rebuilt
  timeline doesn't match the engine's schedule length, and rejects identifier-like fields.
- Fonts: Fraunces and Inter (SIL OFL, licenses in `public/fonts/`), loaded locally.
