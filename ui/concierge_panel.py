"""
ui/concierge_panel.py
=====================
"Ask StormReady" chat area.

Presentation + interaction only. It calls the concierge ONLY in response to an
explicit user action (typing a question or clicking a suggested question), never
on an ordinary Streamlit rerun. It records each answer's mode so a fallback
response is never shown as live AI.

Owner: Roommate (ui/) — built during the solo arrangement.
"""

from __future__ import annotations
import streamlit as st

from concierge import answer_question, provider_status
from concierge.grounding import SUGGESTED_QUESTIONS
from engine.api import evaluate_scenario

# Session keys owned by this panel.
_HISTORY = "_concierge_history"          # list[dict]: {role, text, mode, note}
_SCENARIO_SIG = "_concierge_scenario_sig"  # signature of the scenario the history belongs to
_PENDING = "_concierge_pending"          # a queued question from a suggested-click


def clear_history() -> None:
    """Clear chat history. Safe to call from the global reset callback."""
    for key in (_HISTORY, _SCENARIO_SIG, _PENDING):
        if key in st.session_state:
            del st.session_state[key]


def _scenario_signature(customer_id: str, inputs: dict) -> tuple:
    """Identity of the active scenario — history is tied to this."""
    return (
        customer_id,
        inputs.get("storm_severity"),
        inputs.get("available_crews"),
        inputs.get("access_blocked"),
        inputs.get("damage_scenario"),
    )


def _status_badge() -> None:
    status = provider_status()
    if status.ready:
        st.success("🟢 Live AI: connected to Amazon Bedrock. Answers are generated and "
                   "grounded in the engine's results.", icon="🤖")
    else:
        st.warning(
            "🟡 Rule-based fallback (live AI not configured). Answers are composed directly "
            "from the engine's results — accurate, but not AI-generated.\n\n"
            f"Blocker: {status.blocker}",
            icon="🛟",
        )


def _ask(question: str, *, customer_id: str, customer_label: str, inputs: dict,
         result: dict, backend_name: str, damage_scenarios, prev_inputs,
         prev_result, input_changes) -> None:
    """Call the concierge and append the exchange to history."""
    reply = answer_question(
        question,
        customer_id=customer_id,
        customer_label=customer_label,
        inputs=inputs,
        result=result,
        backend_name=backend_name,
        evaluate_fn=evaluate_scenario,
        damage_scenarios=damage_scenarios,
        prev_inputs=prev_inputs,
        prev_result=prev_result,
        input_changes=input_changes,
    )
    history = st.session_state.setdefault(_HISTORY, [])
    history.append({"role": "user", "text": question})
    note = None
    if reply.mode == "fallback":
        note = "Rule-based fallback" + (f" · {reply.provider_error}" if reply.provider_error else "")
    else:
        note = "Live AI (Bedrock)"
    history.append({"role": "assistant", "text": reply.text, "mode": reply.mode, "note": note})


def render_concierge(
    *,
    customer_id: str,
    customer_label: str,
    inputs: dict,
    result: dict,
    backend_name: str,
    damage_scenarios,
    prev_inputs,
    prev_result,
    input_changes,
) -> None:
    """Render the Ask StormReady area."""
    st.subheader("💬 Ask StormReady")
    st.caption(
        "Ask what your estimate means, why it changed, or how to prepare. Answers explain "
        "the engine's calculated results — the assistant never invents numbers, weather, "
        "outages, or AEP program eligibility."
    )

    _status_badge()

    # --- Reset history when the active scenario changes, so stale answers can't
    #     appear to describe the new scenario. ---
    sig = _scenario_signature(customer_id, inputs)
    if st.session_state.get(_SCENARIO_SIG) != sig:
        # Scenario changed (household or any input): drop old chat.
        if _HISTORY in st.session_state and st.session_state.get(_SCENARIO_SIG) is not None:
            st.info("Scenario changed — cleared the previous chat so answers match the "
                    "current scenario.", icon="♻️")
        st.session_state[_HISTORY] = []
        st.session_state[_SCENARIO_SIG] = sig

    ask_kwargs = dict(
        customer_id=customer_id, customer_label=customer_label, inputs=inputs,
        result=result, backend_name=backend_name, damage_scenarios=damage_scenarios,
        prev_inputs=prev_inputs, prev_result=prev_result, input_changes=input_changes,
    )

    # --- Suggested questions (explicit clicks only) ---
    st.markdown("**Suggested questions**")
    cols = st.columns(2)
    for i, q in enumerate(SUGGESTED_QUESTIONS):
        if cols[i % 2].button(q, key=f"suggest_{i}", use_container_width=True):
            _ask(q, **ask_kwargs)

    # --- Render history ---
    for msg in st.session_state.get(_HISTORY, []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])
            if msg["role"] == "assistant" and msg.get("note"):
                icon = "🤖" if msg.get("mode") == "live" else "🛟"
                st.caption(f"{icon} {msg['note']}")

    # --- Free-text chat input (explicit submit only) ---
    typed = st.chat_input("Ask about this scenario…")
    if typed:
        _ask(typed, **ask_kwargs)
        # Re-render immediately so the new exchange appears without an extra click.
        st.rerun()
