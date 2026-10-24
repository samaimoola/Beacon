"""
api_server.py
=============
FastAPI backend to serve the React frontend and expose StormReady engine.

Run with:
    uvicorn api_server:app --reload --port 8000

Owner: Backend API layer for React UI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from engine.api import (
    get_customers,
    get_damage_scenarios,
    evaluate_scenario,
    build_notification_preview,
    LIFECYCLE_STATES,
)

app = FastAPI(title="StormReady API", version="1.0.0")

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
    result: Dict[str, Any]


# API Routes
@app.get("/")
async def root():
    return {
        "name": "StormReady API",
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
    """Ask the AI concierge a question."""
    try:
        # Import here to avoid circular dependencies
        from concierge import answer_question
        from engine.api import evaluate_scenario as eval_fn
        
        reply = answer_question(
            request.question,
            customer_id=request.customer_id,
            customer_label=request.customer_label,
            inputs=request.inputs,
            result=request.result,
            backend_name="real",  # TODO: Get from engine
            evaluate_fn=eval_fn,
            damage_scenarios=[],
            prev_inputs=None,
            prev_result=None,
            input_changes=[],
        )
        
        return {
            "text": reply.text,
            "mode": reply.mode,
            "provider_error": getattr(reply, "provider_error", None),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
