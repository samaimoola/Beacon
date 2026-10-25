"""
api_server.py
=============
FastAPI backend to serve the React frontend and expose Beacon engine.

Run with:
    uvicorn api_server:app --reload --port 8000

Owner: Backend API layer for React UI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from engine.needs import describe_declared_needs, normalize_declared_needs
from engine.api import (
    get_customers,
    get_damage_scenarios,
    evaluate_scenario,
    build_notification_preview,
    active_backend_name,
    LIFECYCLE_STATES,
)

# Labels for scenario-input comparisons, mirroring the Streamlit UI's
# "What changed?" wording so both interfaces explain transitions the same way.
_INPUT_CHANGE_LABELS = (
    ("customer_id", "Household"),
    ("storm_severity", "Storm severity"),
    ("damage_scenario", "Damage scenario"),
    ("available_crews", "Crews"),
    ("access_blocked", "Access blocked"),
    ("declared_needs", "Declared needs"),
)

_REQUIRED_INPUT_KEYS = ("storm_severity", "available_crews", "access_blocked")

app = FastAPI(title="Beacon API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ScenarioRequest(BaseModel):
    customer_id: str
    storm_severity: str
    available_crews: int
    access_blocked: bool
    damage_scenario: Optional[str] = None
    # Optional customer declarations (two booleans; see engine/needs.py). They
    # tailor preparation guidance only and are never stored or logged.
    declared_needs: Optional[Dict[str, Any]] = None


class NotificationRequest(BaseModel):
    lifecycle_state: str
    inputs: Dict[str, Any]
    result: Dict[str, Any]
    prev_result: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None


class ConciergeRequest(BaseModel):
    question: str
    customer_id: str
    customer_label: str
    inputs: Dict[str, Any]
    # Accepted for backward compatibility but NOT trusted: the bridge
    # recomputes the current result from `inputs` with the engine so every
    # number the concierge sees is engine-computed.
    result: Optional[Dict[str, Any]] = None
    # Previous meaningful scenario (optional). Its result is also recomputed
    # server-side from these inputs.
    prev_customer_id: Optional[str] = None
    prev_inputs: Optional[Dict[str, Any]] = None


def _customer_label(customer_id: str, fallback: str = "") -> str:
    """Look up the anonymized household label server-side (never trust the client)."""
    for c in get_customers():
        if c["id"] == customer_id:
            return c["label"]
    return fallback or customer_id


def _scenario_label(customer_id: str, scenario_id: Optional[str]) -> Optional[str]:
    if not scenario_id:
        return scenario_id
    try:
        for s in get_damage_scenarios(customer_id):
            if s.get("id") == scenario_id:
                return s.get("label", scenario_id)
    except Exception:
        pass
    return scenario_id


def _evaluate_inputs(customer_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    missing = [k for k in _REQUIRED_INPUT_KEYS if k not in inputs]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing scenario inputs: {missing}")
    return evaluate_scenario(
        customer_id=customer_id,
        storm_severity=inputs["storm_severity"],
        available_crews=int(inputs["available_crews"]),
        access_blocked=bool(inputs["access_blocked"]),
        damage_scenario=inputs.get("damage_scenario"),
        declared_needs=inputs.get("declared_needs"),
    )


def compute_input_changes(
    prev_customer_id: str, prev_inputs: Dict[str, Any],
    customer_id: str, inputs: Dict[str, Any],
) -> List[tuple]:
    """[(field_label, before, after), ...] using human-readable household/preset labels."""
    before = dict(prev_inputs, customer_id=prev_customer_id)
    after = dict(inputs, customer_id=customer_id)
    changes = []
    for key, label in _INPUT_CHANGE_LABELS:
        b, a = before.get(key), after.get(key)
        if key == "declared_needs":
            b, a = normalize_declared_needs(b), normalize_declared_needs(a)
        if b == a:
            continue
        if key == "declared_needs":
            b, a = describe_declared_needs(b), describe_declared_needs(a)
        elif key == "customer_id":
            b, a = _customer_label(b), _customer_label(a)
        elif key == "damage_scenario":
            b, a = _scenario_label(prev_customer_id, b), _scenario_label(customer_id, a)
        changes.append((label, b, a))
    return changes


# API Routes
@app.get("/")
async def root():
    return {
        "name": "Beacon API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/customers")
async def api_get_customers():
    """Get list of available customers."""
    try:
        customers = get_customers()
        return customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/damage-scenarios/{customer_id}")
async def api_get_damage_scenarios(customer_id: str):
    """Get damage scenarios for a customer."""
    try:
        scenarios = get_damage_scenarios(customer_id)
        return scenarios
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/evaluate")
async def api_evaluate_scenario(request: ScenarioRequest):
    """Evaluate a scenario and return risk/restoration estimates."""
    try:
        result = evaluate_scenario(
            customer_id=request.customer_id,
            storm_severity=request.storm_severity,
            available_crews=request.available_crews,
            access_blocked=request.access_blocked,
            damage_scenario=request.damage_scenario,
            declared_needs=request.declared_needs,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notification-preview")
async def api_notification_preview(request: NotificationRequest):
    """Generate a notification preview."""
    try:
        if request.lifecycle_state not in LIFECYCLE_STATES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid lifecycle_state. Must be one of: {LIFECYCLE_STATES}"
            )
        
        preview = build_notification_preview(
            lifecycle_state=request.lifecycle_state,
            inputs=request.inputs,
            result=request.result,
            prev_result=request.prev_result,
            preferences=request.preferences,
        )
        return preview
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/concierge/ask")
async def api_concierge_ask(request: ConciergeRequest):
    """
    Ask the grounded concierge a question about the current scenario.

    The bridge (not the browser) supplies every engine-derived value: the
    current and previous results are recomputed here, the active backend name
    comes from the engine, and damage presets come from the engine's catalog.
    AWS/Bedrock configuration stays entirely server-side.
    """
    try:
        # Import here to avoid circular dependencies
        import concierge

        customer_label = _customer_label(request.customer_id, request.customer_label)
        inputs = dict(request.inputs, customer_label=customer_label)
        result = _evaluate_inputs(request.customer_id, inputs)

        prev_inputs = prev_result = None
        input_changes: List[tuple] = []
        if request.prev_inputs:
            prev_cid = request.prev_customer_id or request.customer_id
            prev_inputs = dict(
                request.prev_inputs,
                customer_label=_customer_label(prev_cid, request.prev_inputs.get("customer_label", "")),
            )
            prev_result = _evaluate_inputs(prev_cid, prev_inputs)
            input_changes = compute_input_changes(prev_cid, prev_inputs, request.customer_id, inputs)

        reply = concierge.answer_question(
            request.question,
            customer_id=request.customer_id,
            customer_label=customer_label,
            inputs=inputs,
            result=result,
            backend_name=active_backend_name(),
            evaluate_fn=evaluate_scenario,
            damage_scenarios=get_damage_scenarios(request.customer_id),
            prev_inputs=prev_inputs,
            prev_result=prev_result,
            input_changes=input_changes,
        )

        return {
            "text": reply.text,
            "mode": reply.mode,
            "provider_error": getattr(reply, "provider_error", None),
            "used_counterfactual": getattr(reply, "used_counterfactual", False),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def api_status():
    """Which engine backend is serving ('real' anonymized data or 'demo' synthetic)."""
    return {"backend": active_backend_name()}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
