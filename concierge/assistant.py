"""
concierge/assistant.py
=====================
Orchestrates a grounded answer:

  1. Build an allowlisted context (context.py).
  2. If the question is a crew counterfactual ("would more crews help?"),
     compute the comparison through the ENGINE using the SAME scenario inputs
     but a higher crew count. The model never invents this arithmetic and the
     active scenario is never mutated.
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

# Type of the engine entry point we depend on (injected for testability).
EvaluateFn = Callable[..., dict]

# How many crews to use for the counterfactual, if not otherwise bounded.
_COUNTERFACTUAL_CREWS = 10


@dataclass
class AssistantReply:
    text: str
    mode: str          # "live" | "fallback"
    provider_error: Optional[str] = None  # sanitized; shown as a subtle note
    used_counterfactual: bool = False


def _is_crew_counterfactual(question: str) -> bool:
    q = (question or "").lower()
    keywords = ("more crew", "another crew", "extra crew", "additional crew",
                "would a crew", "would crews", "add a crew", "add crews")
    return any(k in q for k in keywords)


def _compute_counterfactual(
    evaluate_fn: EvaluateFn,
    customer_id: str,
    inputs: dict,
) -> Optional[dict]:
    """
    Re-run the engine with MORE crews but otherwise identical scenario inputs.
    Returns {"crews", "result"} or None if not applicable.
    """
    base_crews = inputs.get("available_crews")
    if not isinstance(base_crews, int):
        return None
    target = max(base_crews + 1, _COUNTERFACTUAL_CREWS)
    try:
        res = evaluate_fn(
            customer_id=customer_id,
            storm_severity=inputs["storm_severity"],
            available_crews=target,
            access_blocked=inputs["access_blocked"],
            damage_scenario=inputs.get("damage_scenario"),
        )
    except Exception:
        return None
    return {"crews": target, "result": res}


def _build_user_message(question: str, ctx: dict,
                        counterfactual: Optional[dict]) -> str:
    """Serialize context + question for the model. Context is PII-free JSON."""
    payload = {
        "context": ctx,
        "approved_safety_guidance": _ground.APPROVED_SAFETY_GUIDANCE,
        "question": question,
    }
    if counterfactual is not None:
        # Provide the engine-computed comparison so the model explains it
        # WITHOUT doing its own arithmetic.
        payload["engine_counterfactual_more_crews"] = {
            "crews": counterfactual["crews"],
            "result": _ctx._pick(counterfactual["result"], _ctx._RESULT_ALLOWLIST),
        }
    return (
        "Answer the customer's question using ONLY the JSON context below. "
        "All numbers must come from the context; do not compute or invent any.\n\n"
        + json.dumps(payload, indent=2, default=str)
    )


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
) -> AssistantReply:
    """
    Produce a grounded answer. `evaluate_fn` is injected (engine.api.evaluate_scenario
    in production, a stub in tests). `force_provider` overrides availability for
    tests (True=attempt provider even if status checks are mocked).
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

    counterfactual = None
    if _is_crew_counterfactual(question):
        counterfactual = _compute_counterfactual(evaluate_fn, customer_id, inputs)

    # Decide whether to attempt the live provider.
    status = _provider.provider_status()
    attempt_live = status.ready if force_provider is None else force_provider

    if attempt_live:
        user_msg = _build_user_message(question, ctx, counterfactual)
        pr = _provider.converse(_ground.SYSTEM_INSTRUCTIONS, user_msg)
        if pr.ok and pr.text:
            return AssistantReply(
                text=pr.text, mode="live",
                used_counterfactual=counterfactual is not None,
            )
        # Fall through to fallback on any provider failure, keeping the error.
        fb = _ground.fallback_answer(question, ctx, counterfactual)
        return AssistantReply(
            text=fb, mode="fallback", provider_error=pr.error,
            used_counterfactual=counterfactual is not None,
        )

    # Provider not configured/available: rule-based fallback.
    fb = _ground.fallback_answer(question, ctx, counterfactual)
    return AssistantReply(
        text=fb, mode="fallback",
        provider_error=status.blocker,
        used_counterfactual=counterfactual is not None,
    )
