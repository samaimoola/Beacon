"""
concierge/assistant.py
=====================
Orchestrates a grounded answer:

  1. Build an allowlisted context (context.py).
  2. If the question is a crew counterfactual ("would another crew help?"),
     compare the current crew count with EXACTLY ONE more crew — never beyond the
     supported maximum — by calling the ENGINE with otherwise identical inputs.
     The comparison is classified (more crews help / no repairs modeled / unknown
     estimate / critical-path limited / ...) from engine facts only, so neither
     the model nor the fallback has to guess why a window did or didn't change.
     The active scenario is never mutated.
  3. Try the live provider (provider.py). On any failure, use the rule-based
     fallback (grounding.py). The returned reply records which mode produced it
     so the UI can label live vs fallback honestly.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Callable, Optional

from concierge import context as _ctx
from concierge import grounding as _ground
from concierge import provider as _provider
from engine.contracts import AVAILABLE_CREWS_MAX
from engine.formatting import format_window

# Type of the engine entry points we depend on (injected for testability).
EvaluateFn = Callable[..., dict]
ScheduleFn = Callable[..., Optional[dict]]


@dataclass
class AssistantReply:
    text: str
    mode: str          # "live" | "fallback"
    provider_error: Optional[str] = None  # sanitized; shown as a subtle note
    # True only when an engine comparison was actually computed for this answer.
    used_counterfactual: bool = False


def _is_crew_counterfactual(question: str) -> bool:
    q = (question or "").lower()
    keywords = ("more crew", "another crew", "extra crew", "additional crew",
                "would a crew", "would crews", "add a crew", "add crews",
                "one more crew")
    return any(k in q for k in keywords)


def _as_int(v) -> Optional[int]:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


def _kind(result: Optional[dict]) -> str:
    """'unknown' | 'none' (no repairs modeled) | 'range' — mirrors format_window."""
    r = result or {}
    lo, hi = r.get("restoration_low_hours"), r.get("restoration_high_hours")
    if lo is None or hi is None:
        return "unknown"
    if lo == 0 and hi == 0:
        return "none"
    return "range"


def _window(result: Optional[dict]) -> str:
    r = result or {}
    return format_window(r.get("restoration_low_hours"), r.get("restoration_high_hours"))


def _facts(basis: str, cmp: dict, sched: Optional[dict]) -> tuple[list[str], list[str]]:
    """
    Deterministic, engine-backed sentences for the comparison (used verbatim by the
    fallback and given to the live model), plus things the answer must NOT claim.
    """
    n, n1, mx = cmp["current_crews"], cmp.get("compared_crews"), cmp["max_supported_crews"]
    cur_w, cf_w = cmp["current_window"], cmp.get("compared_window")
    no_cp = "Do not attribute the result to a critical path or dependency chain."
    facts: list[str] = []
    must_not: list[str] = []

    if basis == "at_maximum":
        facts.append(
            f"This scenario already uses {n} crews, the most Beacon's scenario model supports, "
            f"so there is no one-more-crew comparison to run. Beacon does not estimate beyond "
            f"{mx} crews."
        )
        must_not += ["Do not estimate or describe results for more than the maximum crews.", no_cp]
        if cmp["current_kind"] == "none":
            facts.append(
                "This preset models no equipment damage (no repairs modeled). That does NOT "
                "guarantee uninterrupted power in a real storm."
            )
        elif cmp["current_kind"] == "unknown":
            facts.append("The current restoration estimate is unknown; Beacon does not guess a number.")
        else:
            facts.append(f"The current modeled window is {cur_w}.")
    elif basis == "no_repairs_modeled":
        also = (f" (the engine also shows no repairs modeled with {n1} crews)"
                if cmp.get("compared_kind") == "none" else "")
        facts.append(
            "This preset models no equipment damage, so there are no repair jobs for another crew "
            f"to shorten{also}."
        )
        facts.append(
            "\"No repairs modeled\" does NOT guarantee uninterrupted power in a real storm — it only "
            "means this simulated scenario includes no damage."
        )
        must_not.append(no_cp)
    elif basis == "estimate_unknown":
        k = (sched or {}).get("unknown_jobs") or 0
        if k:
            jobs_txt = "1 repair job in this preset has" if k == 1 else f"{k} repair jobs in this preset have"
            facts.append(
                f"The restoration estimate is unknown because {jobs_txt} no labor-hour reference "
                "in the workbook, so the engine cannot schedule "
                + ("it." if k == 1 else "them.")
            )
        else:
            facts.append(
                "The restoration estimate is unknown because the engine could not map this "
                "scenario's damage to labor references."
            )
        if cmp.get("compared_kind") == "unknown":
            facts.append(
                f"With {n1} crews it is still unknown: the missing labor information, not the crew "
                "count, is what prevents an estimate. Beacon does not guess a number."
            )
        else:
            facts.append(f"With {n1} crews the engine reports {cf_w}. Beacon does not guess beyond that.")
        must_not += [no_cp, "Do not state or guess any number of hours."]
    elif basis == "crew_limited":
        line = (f"With one more crew ({n1} instead of {n}), the engine's heuristic window changes "
                f"from {cur_w} to {cf_w}")
        line += (", because more independent repair jobs can run at the same time."
                 if sched is not None else ".")
        facts.append(line)
        facts.append("This is a scenario estimate, not a commitment.")
        must_not.append(no_cp)
    elif basis == "dependency_limited":
        facts.append(f"One more crew ({n1} instead of {n}) does not change this scenario's window ({cur_w}).")
        jobs = (sched or {}).get("repair_jobs") or 0
        if jobs == 1:
            facts.append(
                "The preset has a single repair job, and the engine assigns each job to one crew, "
                "so an extra crew cannot finish it sooner."
            )
        else:
            cp = (sched or {}).get("critical_path_hours")
            cp_txt = f" (about {cp:.1f} effort-hours)" if isinstance(cp, (int, float)) else ""
            facts.append(
                "The engine's schedule is already at its critical path — repair jobs that must "
                f"happen in sequence{cp_txt} — which additional crews cannot shorten."
            )
    elif basis == "not_dependency_limited":
        facts.append(f"One more crew ({n1} instead of {n}) does not change this scenario's window ({cur_w}).")
        facts.append(
            "The engine's schedule is not at its critical-path limit here; the unchanged result "
            "comes from how the repair jobs fit across the available crews."
        )
        must_not.append(no_cp)
    else:  # unexplained_no_change — backend reports no job schedule (synthetic demo)
        facts.append(f"One more crew ({n1} instead of {n}) does not change this scenario's window ({cur_w}).")
        facts.append("This backend does not report a job schedule, so Beacon cannot say which limit applies.")
        must_not.append(no_cp)

    if sched and sched.get("access_delay_hours") and basis in ("dependency_limited", "not_dependency_limited"):
        facts.append(
            f"The simulated +{sched['access_delay_hours']:g} h blocked-access delay applies regardless "
            "of the crew count."
        )
    return facts, must_not


def _crew_comparison(
    evaluate_fn: EvaluateFn,
    schedule_fn: Optional[ScheduleFn],
    customer_id: str,
    inputs: dict,
    result: dict,
) -> Optional[dict]:
    """
    Compare the current crew count with exactly one more crew via the engine.

    Returns None when the inputs carry no usable crew count. Otherwise a dict with
    `status` ("compared" | "at_maximum" | "comparison_failed"), `basis`, the two
    windows, engine-backed `engine_facts`, and (when computed) the compared result.
    """
    crews = _as_int(inputs.get("available_crews"))
    if crews is None:
        return None

    def scenario(n: int) -> dict:
        return dict(
            customer_id=customer_id,
            storm_severity=inputs["storm_severity"],
            available_crews=n,
            access_blocked=inputs["access_blocked"],
            damage_scenario=inputs.get("damage_scenario"),
        )

    sched = None
    if schedule_fn is not None:
        try:
            sched = schedule_fn(**scenario(crews))
        except Exception:
            sched = None

    cmp: dict = {
        "current_crews": crews,
        "compared_crews": None,
        "max_supported_crews": AVAILABLE_CREWS_MAX,
        "current_window": _window(result),
        "compared_window": None,
        "current_kind": _kind(result),
        "window_changed": None,
        "compared_result": None,
    }

    if crews >= AVAILABLE_CREWS_MAX:
        cmp.update(status="at_maximum", basis="at_maximum")
    else:
        try:
            cf = evaluate_fn(**scenario(crews + 1))
        except Exception:
            cmp.update(status="comparison_failed", basis="comparison_failed",
                       engine_facts=["Beacon could not compute the one-more-crew comparison right "
                                     "now, so it will not guess."],
                       must_not=["Do not estimate the effect of more crews."])
            return cmp
        changed = (
            (cf.get("restoration_low_hours"), cf.get("restoration_high_hours"))
            != (result.get("restoration_low_hours"), result.get("restoration_high_hours"))
        )
        if cmp["current_kind"] == "none":
            basis = "no_repairs_modeled"
        elif cmp["current_kind"] == "unknown":
            basis = "estimate_unknown"
        elif changed:
            basis = "crew_limited"
        elif sched is None or sched.get("dependency_limited") is None:
            basis = "unexplained_no_change"
        elif sched.get("dependency_limited"):
            basis = "dependency_limited"
        else:
            basis = "not_dependency_limited"
        cmp.update(
            status="compared", basis=basis, compared_crews=crews + 1,
            compared_window=_window(cf), compared_kind=_kind(cf), window_changed=changed,
            compared_result=_ctx._pick(cf, _ctx._RESULT_ALLOWLIST),
        )

    cmp["engine_facts"], cmp["must_not"] = _facts(cmp["basis"], cmp, sched)
    return cmp


def _model_view(cmp: dict) -> dict:
    """The comparison as given to the live model (drops internal-only keys)."""
    return {k: v for k, v in cmp.items() if k not in ("current_kind", "compared_kind")}


def _build_user_message(question: str, ctx: dict,
                        crew_comparison: Optional[dict]) -> str:
    """Serialize context + question for the model. Context is PII-free JSON."""
    payload = {
        "context": ctx,
        "approved_safety_guidance": _ground.APPROVED_SAFETY_GUIDANCE,
        "question": question,
    }
    if crew_comparison is not None:
        # Engine-computed comparison so the model explains it WITHOUT doing its
        # own arithmetic or inventing reasons.
        payload["engine_crew_comparison"] = _model_view(crew_comparison)
    return (
        "Answer the customer's question using ONLY the JSON context below. "
        "All numbers must come from the context; do not compute or invent any.\n\n"
        + json.dumps(payload, indent=2, default=str)
    )


def _default_schedule_fn(evaluate_fn: EvaluateFn) -> Optional[ScheduleFn]:
    """Use the engine's schedule facts when the injected evaluator IS the engine."""
    try:
        from engine import api as _engine_api
    except Exception:
        return None
    return _engine_api.schedule_summary if evaluate_fn is _engine_api.evaluate_scenario else None


def answer_question(
    question: str,
    *,
    customer_id: str,
    customer_label: str,
    inputs: dict,
    result: dict,
    backend_name: str,
    evaluate_fn: EvaluateFn,
    damage_scenarios: Optional[list] = None,
    prev_inputs: Optional[dict] = None,
    prev_result: Optional[dict] = None,
    input_changes: Optional[list] = None,
    force_provider: Optional[bool] = None,
    schedule_fn: Optional[ScheduleFn] = None,
) -> AssistantReply:
    """
    Produce a grounded answer. `evaluate_fn` is injected (engine.api.evaluate_scenario
    in production, a stub in tests). `schedule_fn` (optional) supplies structured
    schedule facts; when omitted and `evaluate_fn` is the engine's, the engine's
    schedule_summary is used. `force_provider` overrides availability for tests.
    """
    ctx = _ctx.build_context(
        customer_label=customer_label,
        inputs=inputs,
        result=result,
        backend_name=backend_name,
        damage_scenarios=damage_scenarios,
        prev_inputs=prev_inputs,
        prev_result=prev_result,
        input_changes=input_changes,
    )
    # Defensive PII guard before anything leaves this process.
    _ctx.assert_no_forbidden_fields(ctx)

    crew_cmp = None
    if _is_crew_counterfactual(question):
        if schedule_fn is None:
            schedule_fn = _default_schedule_fn(evaluate_fn)
        crew_cmp = _crew_comparison(evaluate_fn, schedule_fn, customer_id, inputs, result)
    used_cf = bool(crew_cmp and crew_cmp.get("status") == "compared")

    # Decide whether to attempt the live provider.
    status = _provider.provider_status()
    attempt_live = status.ready if force_provider is None else force_provider

    if attempt_live:
        user_msg = _build_user_message(question, ctx, crew_cmp)
        pr = _provider.converse(_ground.SYSTEM_INSTRUCTIONS, user_msg)
        if pr.ok and pr.text:
            return AssistantReply(text=pr.text, mode="live", used_counterfactual=used_cf)
        # Fall through to fallback on any provider failure, keeping the error.
        fb = _ground.fallback_answer(question, ctx, crew_cmp)
        return AssistantReply(text=fb, mode="fallback", provider_error=pr.error,
                              used_counterfactual=used_cf)

    # Provider not configured/available: rule-based fallback.
    fb = _ground.fallback_answer(question, ctx, crew_cmp)
    return AssistantReply(text=fb, mode="fallback", provider_error=status.blocker,
                          used_counterfactual=used_cf)
