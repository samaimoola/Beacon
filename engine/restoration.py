"""
engine/restoration.py
======================
Restoration-effort and elapsed-time model for a SIMULATED damage scenario.

Key ideas (reviewer corrections, Pass 2):
  - We schedule repairs for DAMAGED assets only — never "replace every device
    on the upstream path". Healthy equipment generates no work.
  - Effort comes from repair JOBS (task + workbook/assumption hours).
  - The indirect labor multiplier (ILM) is applied exactly ONCE, to total effort.
  - Elapsed time respects task concurrency AND dependencies:
      * one job runs on one crew; more crews do NOT shorten an individual job;
      * dependent jobs form a critical path that more crews cannot bypass;
      * independent jobs run in parallel up to the crew count.
  - The low/high band is an ASSUMED uncertainty band, not a validated interval.
  - Labor hours are treated as effort in the workbook's own (unresolved) unit.

This module is pure/deterministic and has no Streamlit or I/O dependencies.

Owner: engine/ (solo maintainer during the temporary arrangement)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# Simulated access delay (hours) added before any work can begin.
ACCESS_DELAY_HOURS = 3.0

# Assumed uncertainty band applied to the scheduled elapsed time.
# Explicitly an assumption — NOT a statistically validated confidence interval.
UNCERTAINTY_LOW = 0.80
UNCERTAINTY_HIGH = 1.35


@dataclass
class RepairJob:
    """One unit of repair work for a damaged asset."""
    task: str                       # human-readable task, e.g. "Replace Medium pole"
    direct_hours: Optional[float]   # effort in workbook hour-units; None = unknown mapping
    depends_on: tuple[int, ...] = ()  # indices of jobs that must finish first
    hours_source: str = ""          # provenance / basis for direct_hours
    is_assumption: bool = True      # True if direct_hours is assumed (not from workbook)


@dataclass
class ScheduleResult:
    total_direct_hours: Optional[float]
    effective_effort_hours: Optional[float]   # total_direct * ILM
    elapsed_hours: Optional[float]            # crew/dependency-limited wall time (before access delay)
    critical_path_hours: Optional[float]      # min elapsed with unlimited crews
    low_hours: Optional[float]
    high_hours: Optional[float]
    notes: list[str] = field(default_factory=list)
    unknown_jobs: int = 0
    # True when the crew-limited schedule already equals the critical path, i.e.
    # adding crews cannot finish any sooner. None when there is nothing to
    # schedule (no jobs) or the schedule is unknown.
    dependency_limited: Optional[bool] = None
    access_delay_hours: float = 0.0


def schedule(jobs: list[RepairJob], crews: int, ilm: float,
             access_blocked: bool) -> ScheduleResult:
    """
    Compute effort and crew/dependency-limited elapsed time for a set of jobs.

    Returns a ScheduleResult. If there are no jobs, elapsed time is 0 (nothing to
    repair). If crews < 1, elapsed time is unknown (None). If any job has an
    unknown hour mapping, totals are None and the result is flagged.
    """
    notes: list[str] = []

    if crews < 1:
        notes.append("No crews available — elapsed restoration time cannot be estimated (unknown).")
        return ScheduleResult(None, None, None, None, None, None, notes, unknown_jobs=0)

    if not jobs:
        notes.append("No damaged assets in this scenario — no repair work required.")
        return ScheduleResult(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, notes, unknown_jobs=0)

    unknown = sum(1 for j in jobs if j.direct_hours is None)
    if unknown:
        notes.append(
            f"{unknown} repair job(s) have no workbook hour mapping — effort and time are "
            "UNKNOWN for this scenario rather than invented."
        )
        return ScheduleResult(None, None, None, None, None, None, notes, unknown_jobs=unknown)

    total_direct = round(sum(j.direct_hours for j in jobs), 3)
    effective = round(total_direct * ilm, 2)

    # --- critical path (longest dependency chain, in EFFECTIVE hours) ---
    eff = [round(j.direct_hours * ilm, 4) for j in jobs]
    memo: dict[int, float] = {}

    def chain_len(i: int, seen: frozenset[int]) -> float:
        if i in seen:
            # Defensive: ignore cyclic dependency rather than loop forever.
            return 0.0
        if i in memo:
            return memo[i]
        best_pred = 0.0
        for d in jobs[i].depends_on:
            if 0 <= d < len(jobs):
                best_pred = max(best_pred, chain_len(d, seen | {i}))
        memo[i] = best_pred + eff[i]
        return memo[i]

    critical_path = round(max(chain_len(i, frozenset()) for i in range(len(jobs))), 2)

    # --- crew/dependency-limited list scheduling ---
    # Each job occupies one crew for its effective duration. A job becomes ready
    # when all its dependencies are finished. We simulate time advancing.
    durations = eff[:]
    remaining = set(range(len(jobs)))
    finish_time = [0.0] * len(jobs)
    running: list[tuple[float, int]] = []  # (end_time, job_index)
    t = 0.0

    def ready(done_set: set[int]) -> list[int]:
        out = []
        for i in remaining:
            if i not in {idx for _, idx in running} and all(
                (d in done_set) for d in jobs[i].depends_on if 0 <= d < len(jobs)
            ):
                out.append(i)
        return out

    done: set[int] = set()
    # Guard against pathological loops.
    guard = 0
    max_iter = len(jobs) * 4 + 8
    while remaining and guard < max_iter:
        guard += 1
        free = crews - len(running)
        # Start as many ready jobs as crews allow. Longest-job-first for a
        # stable, sensible critical-path-respecting order.
        startable = sorted(ready(done), key=lambda i: -durations[i])
        for i in startable[:max(0, free)]:
            finish_time[i] = t + durations[i]
            running.append((finish_time[i], i))
        if not running:
            break
        # Advance time to the next job completion.
        running.sort()
        end_t, idx = running.pop(0)
        t = end_t
        remaining.discard(idx)
        done.add(idx)
        # Any other jobs finishing at the same instant.
        while running and abs(running[0][0] - t) < 1e-9:
            _, j2 = running.pop(0)
            remaining.discard(j2)
            done.add(j2)

    elapsed = round(t, 2)
    # Elapsed can never be below the critical path even with abundant crews.
    elapsed = max(elapsed, critical_path)
    # At the critical path, no number of extra crews can finish sooner.
    dependency_limited = elapsed <= critical_path + 1e-9

    if access_blocked:
        elapsed = round(elapsed + ACCESS_DELAY_HOURS, 2)
        notes.append(f"Simulated blocked access adds a flat +{ACCESS_DELAY_HOURS:g} h before work begins.")

    if crews == 1:
        notes.append("With 1 crew, all jobs run sequentially (elapsed ≈ total effort).")
    else:
        notes.append(
            f"{crews} crews run independent jobs in parallel, but the critical path "
            f"(dependent chain ≈ {critical_path:g} effort-h) cannot be shortened by adding crews."
        )

    low = round(elapsed * UNCERTAINTY_LOW, 1)
    high = round(elapsed * UNCERTAINTY_HIGH, 1)
    low = max(0.0, low)
    high = max(low + 0.5, high) if elapsed > 0 else 0.0
    notes.append(
        f"Range is an ASSUMED uncertainty band (×{UNCERTAINTY_LOW:g}–×{UNCERTAINTY_HIGH:g} of the "
        "scheduled time), not a statistically validated interval."
    )

    return ScheduleResult(
        total_direct_hours=total_direct,
        effective_effort_hours=effective,
        elapsed_hours=elapsed,
        critical_path_hours=critical_path,
        low_hours=low,
        high_hours=high,
        notes=notes,
        unknown_jobs=0,
        dependency_limited=dependency_limited,
        access_delay_hours=ACCESS_DELAY_HOURS if access_blocked else 0.0,
    )
