"""
RecoverAI - FastAPI Application Entry Point
============================================
Exposes the REST API for the payment recovery intelligence system.

Endpoints
---------
POST /api/process-payment  — Core inference endpoint
GET  /api/dashboard-stats  — Aggregate analytics for the dashboard
GET  /api/recent-events    — Last 50 audit records
GET  /api/health           — Health / readiness check
POST /api/approve-action   — Operator approves or rejects a recommendation
GET  /api/demo-event       — Returns a pre-filled sample PaymentEvent (for demos)

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Path setup — allow imports from the backend/ directory itself
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import PaymentEvent, RecoveryDecision, AuditRecord
from guardrails import check_guardrails, summarize_guardrails
from database import init_db, insert_record, get_all_records, get_stats, update_operator_decision
from policy import get_best_action, is_model_loaded

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("recoverai.main")

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RecoverAI API",
    description=(
        "Intelligent payment failure recovery engine powered by CatBoost. "
        "Combines rule-based guardrails with ML-driven treatment selection."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow the React / Next.js frontend running on localhost during dev
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev server
        "http://localhost:5173",   # Vite dev server
        "http://localhost:8080",
        "*",                       # Widen for demo; restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup / shutdown hooks
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """Initialise the database schema on startup."""
    logger.info("RecoverAI API starting up …")
    init_db()
    model_status = "LOADED ✓" if is_model_loaded() else "NOT FOUND — using heuristic fallback"
    logger.info("CatBoost model status: %s", model_status)
    logger.info("RecoverAI API ready.")


# ===========================================================================
# Request/Response helper models
# ===========================================================================

class ApproveActionRequest(BaseModel):
    """Request body for the operator approval endpoint."""
    transaction_id: str
    decision: str                  # 'approved' or 'rejected'
    notes: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "transaction_id": "TXN-DEMO-001",
                "decision": "approved",
                "notes": "Manually verified — safe to retry.",
            }
        }


# ===========================================================================
# Core endpoints
# ===========================================================================

@app.post(
    "/api/process-payment",
    response_model=RecoveryDecision,
    status_code=status.HTTP_200_OK,
    summary="Process a failed payment and get a recovery recommendation",
    tags=["Recovery"],
)
async def process_payment(event: PaymentEvent) -> RecoveryDecision:
    """
    Main inference endpoint.

    Pipeline:
    1. Run guardrail checks (rule-based).
    2. If guardrails pass, run the CatBoost policy engine.
    3. Persist the full audit record to SQLite.
    4. Return a ``RecoveryDecision`` to the caller.
    """
    logger.info(
        "Processing payment | transaction_id=%s | amount=%.2f | method=%s",
        event.transaction_id,
        event.amount,
        event.payment_method,
    )

    try:
        # --- Step 1: Guardrails ---
        guardrail_triggered, forced_action, guardrail_reason = check_guardrails(event)

        if guardrail_triggered:
            # Guardrail overrides ML entirely
            recommended_action = forced_action
            recovery_probability = 0.0   # guardrails don't produce probabilities
            all_action_scores: Dict[str, float] = {
                action: 0.0
                for action in ["smart_retry", "smart_delay", "send_notification", "silent_wait", "human_review"]
            }
            all_action_scores[recommended_action] = 1.0
            logger.info(
                "Guardrail triggered for %s: %s → %s",
                event.transaction_id,
                guardrail_reason,
                recommended_action,
            )
        else:
            # --- Step 2: ML Policy Engine ---
            recommended_action, recovery_probability, all_action_scores = get_best_action(event)
            guardrail_reason = None
            logger.info(
                "Policy decision for %s: action=%s prob=%.4f",
                event.transaction_id,
                recommended_action,
                recovery_probability,
            )

        # --- Step 3: Persist audit record ---
        audit_row = {
            # identifiers
            "transaction_id":             event.transaction_id,
            "customer_id":                event.customer_id,
            "timestamp":                  datetime.utcnow().isoformat(),
            # inputs
            "amount":                     event.amount,
            "payment_method":             event.payment_method,
            "bank":                       event.bank,
            "error_reason":               event.error_reason,
            "customer_segment":           event.customer_segment,
            "opt_out_notification":       int(event.opt_out_notification),
            "device_type":                event.device_type,
            "channel":                    event.channel,
            "region":                     event.region,
            "customer_age":               event.customer_age,
            "account_balance":            event.account_balance,
            "customer_tenure_months":     event.customer_tenure_months,
            "previous_failed_attempts":   event.previous_failed_attempts,
            "retry_count":                event.retry_count,
            "risk_score":                 event.risk_score,
            "merchant_category":          event.merchant_category,
            "card_type":                  event.card_type,
            "hour_of_day":                event.hour_of_day,
            "day_of_week":                event.day_of_week,
            "is_weekend":                 event.is_weekend,
            "time_since_last_failure_hr": event.time_since_last_failure_hr,
            "transaction_frequency_30d":  event.transaction_frequency_30d,
            "recovery_attempt_count":     event.recovery_attempt_count,
            "notification_sent":          event.notification_sent,
            # outputs
            "recommended_action":         recommended_action,
            "recovery_probability":       recovery_probability,
            "guardrail_triggered":        int(guardrail_triggered),
            "guardrail_reason":           guardrail_reason,
            "all_action_scores":          all_action_scores,
        }
        insert_record(audit_row)

        # --- Step 4: Return decision ---
        return RecoveryDecision(
            transaction_id=event.transaction_id,
            recommended_action=recommended_action,
            recovery_probability=recovery_probability,
            guardrail_triggered=guardrail_triggered,
            guardrail_reason=guardrail_reason,
            risk_score=event.risk_score,
            all_action_scores=all_action_scores,
            status="success",
            timestamp=datetime.utcnow(),
        )

    except Exception as exc:
        logger.exception("Unhandled error while processing %s: %s", event.transaction_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


# ---------------------------------------------------------------------------

@app.get(
    "/api/dashboard-stats",
    summary="Aggregate analytics for the operator dashboard",
    tags=["Analytics"],
)
async def dashboard_stats() -> Dict[str, Any]:
    """
    Returns aggregate statistics for the operator dashboard:
    - Total events processed
    - Recovery rate (non-human-review fraction)
    - Action distribution breakdown
    - Top error reasons
    - Guardrail trigger rate
    - Pending human review count
    """
    try:
        raw = get_stats()
        # Map to field names the frontend JS expects
        data = {
            "total_events":    raw.get("total_events", 0),
            # Frontend expects percentage (e.g. 67.3), not a fraction
            "recovery_rate":   round(raw.get("recovery_rate", 0.0) * 100, 1),
            "avg_risk_score":  round(raw.get("avg_risk_score", 0.0), 1),
            # Frontend expects plural key
            "pending_reviews": raw.get("pending_review", 0),
            # Bonus fields for operator dashboards
            "guardrail_rate":        raw.get("guardrail_rate", 0.0),
            "action_distribution":   raw.get("action_distribution", {}),
            "error_distribution":    raw.get("error_distribution", {}),
            "avg_recovery_prob":     raw.get("avg_recovery_prob", 0.0),
        }
        return {"status": "success", "data": data}
    except Exception as exc:
        logger.exception("Failed to fetch dashboard stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stats: {str(exc)}",
        )


# ---------------------------------------------------------------------------

@app.get(
    "/api/recent-events",
    summary="Retrieve the 50 most recent recovery events",
    tags=["Analytics"],
)
async def recent_events() -> Dict[str, Any]:
    """
    Returns the last 50 recovery decisions stored in the audit database,
    ordered by timestamp descending (newest first).
    """
    try:
        records = get_all_records(limit=50)
        return {
            "status": "success",
            "count": len(records),
            "data": records,
        }
    except Exception as exc:
        logger.exception("Failed to fetch recent events: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(exc)}",
        )


# ---------------------------------------------------------------------------

@app.get(
    "/api/health",
    summary="Health and readiness check",
    tags=["System"],
)
async def health_check() -> Dict[str, Any]:
    """
    Returns the health status of the API, including:
    - API version and uptime status
    - CatBoost model availability
    - Active guardrail rules summary
    """
    return {
        "status": "healthy",
        "service": "RecoverAI API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "model_loaded": is_model_loaded(),
        "inference_mode": "catboost" if is_model_loaded() else "heuristic_fallback",
        "guardrails": summarize_guardrails(),
    }


# ---------------------------------------------------------------------------

@app.post(
    "/api/approve-action",
    summary="Operator approves or rejects a recommended recovery action",
    tags=["Operator"],
)
async def approve_action(request: ApproveActionRequest) -> Dict[str, Any]:
    """
    Allows a human operator to record their decision on a ``human_review``
    case.  The ``decision`` field must be either ``'approved'`` or ``'rejected'``.
    """
    valid_decisions = {"approved", "rejected"}
    if request.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"decision must be one of {sorted(valid_decisions)}",
        )

    try:
        updated = update_operator_decision(
            transaction_id=request.transaction_id,
            operator_decision=request.decision,
            operator_notes=request.notes,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction '{request.transaction_id}' not found in audit log.",
            )

        logger.info(
            "Operator %s transaction %s — notes: %s",
            request.decision,
            request.transaction_id,
            request.notes,
        )
        return {
            "status": "success",
            "message": f"Transaction {request.transaction_id} marked as {request.decision}.",
            "transaction_id": request.transaction_id,
            "decision": request.decision,
            "reviewed_at": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to record operator decision: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record decision: {str(exc)}",
        )


# ---------------------------------------------------------------------------

@app.get(
    "/api/demo-event",
    response_model=PaymentEvent,
    summary="Returns a pre-filled sample PaymentEvent for demo / testing",
    tags=["Demo"],
)
async def demo_event() -> PaymentEvent:
    """
    Returns a fully populated ``PaymentEvent`` that can be copy-pasted into
    the ``POST /api/process-payment`` body for a quick end-to-end demo.
    This event is deliberately crafted to bypass all guardrails so the ML
    model path is exercised.
    """
    return PaymentEvent(
        transaction_id="TXN-DEMO-" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        amount=1499.0,
        payment_method="upi",
        bank="HDFC",
        error_reason="insufficient_funds",
        customer_id="CUST-DEMO-001",
        customer_segment="premium",
        opt_out_notification=False,
        device_type="mobile",
        channel="app",
        region="South",
        customer_age=28,
        account_balance=500.0,
        customer_tenure_months=36,
        previous_failed_attempts=1,
        retry_count=0,
        risk_score=22.0,
        merchant_category="ecommerce",
        card_type="NA",
        hour_of_day=15,
        day_of_week=3,
        is_weekend=0,
        time_since_last_failure_hr=3.0,
        transaction_frequency_30d=8,
        recovery_attempt_count=0,
        notification_sent=0,
    )


# ===========================================================================
# Dev entrypoint
# ===========================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
