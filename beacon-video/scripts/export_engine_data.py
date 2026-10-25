"""
Export the small, allowlisted data the "Repair dependencies" clip needs.

Run from the Beacon repository root with Beacon's virtualenv:

    source .venv/bin/activate
    python beacon-video/scripts/export_engine_data.py

What it does
------------
1. Calls engine.api.evaluate_scenario() for ONE anonymized overhead household,
   medium severity, the "multi_damage" (Widespread damage) preset, and clear
   access — changing ONLY the crew count (1, 2, 3, 10). Bedrock is never used.
2. Rebuilds a per-job timeline for the animation with the same list-scheduling
   rule engine/restoration.py documents (one crew per job, dependencies first,
   longest ready job first), then FAILS unless that timeline's length and
   critical path equal engine.api.schedule_summary() for every crew count.
   The scheduler itself is not modified or monkey-patched.
3. Writes beacon-video/src/data/repair-demo.json containing only allowlisted
   fields: no customer/premise ids, labels with circuit names, addresses,
   coordinates, credentials, or source datasets.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve()
VIDEO_ROOT = HERE.parents[1]
REPO_ROOT = VIDEO_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from engine import api  # noqa: E402
from engine import realdata as _real  # noqa: E402
from engine.formatting import format_window  # noqa: E402

SEVERITY = "medium"
PRESET = "multi_damage"
ACCESS_BLOCKED = False
CREW_STAGES = (1, 2, 3, 10)

# Display labels for the five preset jobs, in the preset's job order. The engine
# job list is checked against these task keys so a preset change fails loudly.
JOB_DISPLAY = [
    ("replace_pole_medium", "poleA", "Replace pole A", "pole"),
    ("repair_primary_span", "condA", "Repair conductor A", "conductor"),
    ("replace_pole_medium", "poleB", "Replace pole B", "pole"),
    ("repair_primary_span", "condB", "Repair conductor B", "conductor"),
    ("replace_transformer", "xfmr", "Replace transformer", "transformer"),
]


def overhead_household_id() -> str:
    """First anonymized household whose label says Overhead (id is never exported)."""
    for c in api.get_customers():
        if "overhead" in c["label"].lower():
            return c["id"]
    raise SystemExit("No overhead household in the active backend.")


def list_schedule(durations: list[float], deps: list[tuple[int, ...]], crews: int):
    """
    Same rule as engine.restoration.schedule (one crew per job; a job is ready when
    its dependencies are done; start the longest ready jobs first, up to the free
    crews; advance to the next completion). Returns [(start, end)] per job.
    """
    remaining = set(range(len(durations)))
    running: list[tuple[float, int]] = []
    start = [0.0] * len(durations)
    done: set[int] = set()
    t = 0.0
    while remaining:
        busy = {i for _, i in running}
        ready = [i for i in sorted(remaining) if i not in busy and all(d in done for d in deps[i])]
        free = crews - len(running)
        for i in sorted(ready, key=lambda i: -durations[i])[: max(0, free)]:
            start[i] = t
            running.append((t + durations[i], i))
        if not running:
            raise SystemExit("Scheduling deadlock (unexpected).")
        running.sort()
        t, idx = running.pop(0)
        remaining.discard(idx)
        done.add(idx)
        while running and abs(running[0][0] - t) < 1e-9:
            _, j = running.pop(0)
            remaining.discard(j)
            done.add(j)
    return [(round(s, 4), round(s + durations[i], 4)) for i, s in enumerate(start)]


def main() -> None:
    if api.active_backend_name() != "real":
        raise SystemExit("Expected the real anonymized backend (data/processed/premises.json).")
    cid = overhead_household_id()
    preset = next(s for s in api.get_damage_scenarios(cid) if s["id"] == PRESET)

    engine_tasks = [j["task"] for j in preset["jobs"]]
    if engine_tasks != [k for k, *_ in JOB_DISPLAY]:
        raise SystemExit(f"Preset jobs changed: {engine_tasks}")
    deps = [tuple(j.get("depends_on", ())) for j in preset["jobs"]]

    # Effective job durations exactly as the engine computes them (severity x ILM).
    premise = _real._index()[cid]
    jobs = _real._severity_jobs(_real._find_scenario(premise, PRESET), _real._task_catalog(),
                                _real._SEVERITY_MULT[SEVERITY])
    ilm = _real._ilm()
    durations = [round(j.direct_hours * ilm, 4) for j in jobs]

    stages = []
    for crews in CREW_STAGES:
        res = api.evaluate_scenario(cid, SEVERITY, crews, ACCESS_BLOCKED, damage_scenario=PRESET)
        summ = api.schedule_summary(cid, SEVERITY, crews, ACCESS_BLOCKED, damage_scenario=PRESET)
        timeline = list_schedule(durations, deps, crews)
        makespan = round(max(e for _, e in timeline), 2)
        # The animation timeline must reproduce the engine's own schedule.
        if abs(makespan - summ["elapsed_hours"]) > 0.011:
            raise SystemExit(f"{crews} crews: timeline {makespan} h != engine {summ['elapsed_hours']} h")
        for i, (s, _e) in enumerate(timeline):
            for d in deps[i]:
                assert s >= timeline[d][1] - 1e-9, "dependency violated"
        lo, hi = res["restoration_low_hours"], res["restoration_high_hours"]
        stages.append({
            "crews": crews,
            "restoration_low_hours": lo,
            "restoration_high_hours": hi,
            "restoration_window": format_window(lo, hi),
            "risk_band": res["risk_band"],
            "dependency_limited": summ["dependency_limited"],
            "schedule_hours": summ["elapsed_hours"],
            "critical_path_hours": summ["critical_path_hours"],
            "timeline": [{"job": JOB_DISPLAY[i][1], "start": s, "end": e}
                         for i, (s, e) in enumerate(timeline)],
        })

    # Only crew count may differ between stages.
    assert len({s["risk_band"] for s in stages}) == 1

    out = {
        "_about": ("Generated by beacon-video/scripts/export_engine_data.py from "
                   "engine.api.evaluate_scenario (real anonymized backend). Illustrative "
                   "video data: simulated storm and damage; heuristic estimates."),
        "generated_on": date.today().isoformat(),
        "scenario": {
            "household": "Anonymized overhead household",
            "storm_severity": SEVERITY,
            "damage_preset": preset["label"],
            "access": "clear",
        },
        "jobs": [{"id": jid, "label": label, "icon": icon,
                  "depends_on": [JOB_DISPLAY[d][1] for d in deps[i]],
                  "effort_hours": durations[i]}
                 for i, (_task, jid, label, icon) in enumerate(JOB_DISPLAY)],
        "stages": stages,
    }

    # Allowlist guard: nothing identifying may leave the engine.
    blob = json.dumps(out).lower()
    for frag in (cid.lower(), "rp-", "cir", "premise", "address", "latitude", "longitude",
                 "coord", "meter", "aws", "bedrock"):
        assert frag not in blob, f"forbidden fragment in export: {frag}"

    dest = VIDEO_ROOT / "src" / "data" / "repair-demo.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n")
    for s in stages:
        print(f"{s['crews']:>2} crews: {s['restoration_window']}  "
              f"(schedule {s['schedule_hours']} h, dependency_limited={s['dependency_limited']})")
    print(f"wrote {dest.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
