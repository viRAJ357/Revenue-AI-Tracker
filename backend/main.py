"""
RecoverAI - FastAPI Application Entry Point
============================================
Exposes the REST API for the payment recovery intelligence system.

Endpoints
---------
POST /api/process-payment       — Core inference endpoint
GET  /api/dashboard-stats       — Aggregate analytics for the dashboard
GET  /api/recent-events         — Last 50 audit records
GET  /api/health                — Health / readiness check
POST /api/approve-action        — Operator approves or rejects a recommendation
GET  /api/demo-event            — Returns a pre-filled sample PaymentEvent (for demos)
POST /api/simulate-notification — Dispatches async notification via Celery

Environment Variables (set in .env or Docker):
  SECRET_KEY                   — JWT signing secret
  ACCESS_TOKEN_EXPIRE_MINUTES  — Token lifetime (default: 60)
  CORS_ORIGINS                 — Comma-separated allowed origins
  REDIS_URL                    — Celery broker URL
  DATABASE_URL                 — SQLAlchemy DB URL

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import sys
import os
import asyncio
import random
import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

# Load .env file first so env vars are available before other imports
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from fastapi import FastAPI, HTTPException, status, Depends, WebSocket, WebSocketDisconnect, File, UploadFile
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
from auth import create_access_token, verify_password, get_password_hash, verify_token
from tasks import send_notification as send_notification_task

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
# CORS — reads from CORS_ORIGINS env var (comma-separated list of origins)
# Falls back to localhost origins for local development.
# ---------------------------------------------------------------------------
_raw_origins = os.environ.get("CORS_ORIGINS", "")
ALLOW_ORIGINS: List[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
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
    asyncio.create_task(generate_live_events())


# ---------------------------------------------------------------------------
# WebSocket Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

async def generate_live_events():
    while True:
        await asyncio.sleep(random.randint(5, 15))
        if manager.active_connections:
            try:
                event_id = "TXN-LIVE-" + datetime.utcnow().strftime("%H%M%S")
                event = PaymentEvent(
                    transaction_id=event_id, amount=random.randint(100, 10000), 
                    payment_method=random.choice(["upi", "card", "netbanking"]), 
                    bank=random.choice(["SBI", "HDFC", "ICICI"]),
                    error_reason=random.choice(["insufficient_funds", "network_timeout", "wrong_pin"]), 
                    customer_id="CUST-LIVE", customer_segment="regular",
                    opt_out_notification=False, device_type="mobile", channel="app",
                    region="South", customer_age=30, account_balance=100.0, customer_tenure_months=12,
                    previous_failed_attempts=0, retry_count=0, risk_score=random.randint(10, 80),
                    merchant_category="ecommerce", card_type="NA", hour_of_day=12,
                    day_of_week=1, is_weekend=0, time_since_last_failure_hr=1.0,
                    transaction_frequency_30d=5, recovery_attempt_count=0, notification_sent=0
                )
                decision = await process_payment(event)
                import json
                payload = {**event.model_dump(), **decision.model_dump()}
                payload["status"] = "pending"
                payload["timestamp"] = payload["timestamp"].isoformat()
                await manager.broadcast(json.dumps(payload))
            except Exception as e:
                logger.error(f"Error generating live event: {e}")


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

class LoginRequest(BaseModel):
    username: str
    password: str

# ===========================================================================
# Auth endpoints
# ===========================================================================

@app.post("/api/login", tags=["Auth"])
async def login(req: LoginRequest):
    """
    Validates credentials against the database and returns a signed JWT.
    Uses bcrypt to verify the stored password hash.
    """
    from database import SessionLocal, User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == req.username).first()
    finally:
        db.close()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    logger.info("Issued JWT for user: %s", user.username)
    return {"access_token": access_token, "token_type": "bearer"}


# ===========================================================================
# WebSocket endpoint
# ===========================================================================

@app.websocket("/api/ws/live-events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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


@app.post(
    "/api/upload-csv",
    summary="Upload a CSV for batch processing",
    tags=["Batch"],
)
async def upload_csv(file: UploadFile = File(...), token: dict = Depends(verify_token)) -> Dict[str, Any]:
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = []
    processed_count = 0
    errors = 0

    for row in reader:
        try:
            # Map CSV row to PaymentEvent
            # We assume CSV columns match PaymentEvent fields approximately
            event_id = row.get('transaction_id') or "TXN-BATCH-" + datetime.utcnow().strftime("%H%M%S%f")
            
            event = PaymentEvent(
                transaction_id=event_id,
                amount=float(row.get('amount', 0)),
                payment_method=row.get('payment_method', 'upi').lower(),
                bank=row.get('bank', 'SBI'),
                error_reason=row.get('error_reason', 'insufficient_funds'),
                customer_id=row.get('customer_id', 'CUST-BATCH'),
                customer_segment=row.get('customer_segment', 'regular'),
                opt_out_notification=row.get('opt_out_notification', 'false').lower() == 'true',
                device_type=row.get('device_type', 'mobile'),
                channel=row.get('channel', 'app'),
                region=row.get('region', 'South'),
                customer_age=int(row.get('customer_age', 30)),
                account_balance=float(row.get('account_balance', 0)),
                customer_tenure_months=int(row.get('customer_tenure_months', 12)),
                previous_failed_attempts=int(row.get('previous_failed_attempts', 0)),
                retry_count=int(row.get('retry_count', 0)),
                risk_score=float(row.get('risk_score', 50.0)),
                merchant_category=row.get('merchant_category', 'ecommerce'),
                card_type=row.get('card_type', 'NA'),
                hour_of_day=int(row.get('hour_of_day', 12)),
                day_of_week=int(row.get('day_of_week', 1)),
                is_weekend=int(row.get('is_weekend', 0)),
                time_since_last_failure_hr=float(row.get('time_since_last_failure_hr', 1.0)),
                transaction_frequency_30d=int(row.get('transaction_frequency_30d', 1)),
                recovery_attempt_count=int(row.get('recovery_attempt_count', 0)),
                notification_sent=int(row.get('notification_sent', 0))
            )
            decision = await process_payment(event)
            results.append({
                "transaction_id": event.transaction_id,
                "recommended_action": decision.recommended_action,
                "status": "success"
            })
            processed_count += 1
        except Exception as e:
            logger.error(f"Error processing CSV row {row}: {e}")
            errors += 1

    return {
        "status": "success",
        "processed": processed_count,
        "errors": errors,
        "message": f"Successfully processed {processed_count} records with {errors} errors."
    }

# ---------------------------------------------------------------------------

@app.get(
    "/api/dashboard-stats",
    summary="Aggregate analytics for the operator dashboard",
    tags=["Analytics"],
)
async def dashboard_stats(token: dict = Depends(verify_token)) -> Dict[str, Any]:
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
async def recent_events(token: dict = Depends(verify_token)) -> Dict[str, Any]:
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


@app.get(
    "/api/analytics-data",
    summary="Retrieve time-series analytics data for charts",
    tags=["Analytics"],
)
async def analytics_data(token: dict = Depends(verify_token)) -> Dict[str, Any]:
    try:
        from database import SessionLocal, RecoveryEvent
        db = SessionLocal()
        events = db.query(RecoveryEvent).order_by(RecoveryEvent.timestamp.desc()).limit(1000).all()
        db.close()

        # Group by day string YYYY-MM-DD
        from collections import defaultdict
        grouped = defaultdict(lambda: {"recovered": 0, "total": 0, "rev_recovered": 0, "rev_lost": 0})
        
        for e in events:
            day = e.timestamp[:10]
            grouped[day]["total"] += 1
            if e.operator_decision == 'approved' or (not e.guardrail_triggered and e.recommended_action != 'human_review'):
                # Simplified assumption of recovery for charting
                grouped[day]["recovered"] += 1
                grouped[day]["rev_recovered"] += e.amount
            else:
                grouped[day]["rev_lost"] += e.amount

        # Sort dates
        sorted_dates = sorted(list(grouped.keys()))[-8:] # last 8 days with data
        if not sorted_dates:
            # Fallback if DB empty
            sorted_dates = [(datetime.utcnow() - pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7, -1, -1)]
            for d in sorted_dates: grouped[d] = {"recovered":0, "total":1, "rev_recovered":0, "rev_lost":0}
            
        dates_ms = [int(datetime.strptime(d, "%Y-%m-%d").timestamp() * 1000) for d in sorted_dates]
        
        recovery_success_rate = []
        revenue_recovered = []
        revenue_lost = []
        
        for d in sorted_dates:
            g = grouped[d]
            rate = int((g["recovered"] / g["total"]) * 100) if g["total"] > 0 else 0
            recovery_success_rate.append(rate)
            revenue_recovered.append(g["rev_recovered"])
            revenue_lost.append(g["rev_lost"])

        return {
            "status": "success",
            "data": {
                "dates": dates_ms,
                "recovery_success_rate": recovery_success_rate,
                "revenue_recovered": revenue_recovered,
                "revenue_lost": revenue_lost
            }
        }
    except Exception as exc:
        logger.exception("Failed to fetch analytics data: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics data: {str(exc)}",
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
async def approve_action(request: ApproveActionRequest, token: dict = Depends(verify_token)) -> Dict[str, Any]:
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

class SimulateNotificationRequest(BaseModel):
    transaction_id: str
    customer_id: str
    action: str

@app.post(
    "/api/simulate-notification",
    summary="Dispatches an async email/SMS notification via Celery",
    tags=["Action"],
)
async def simulate_notification(
    request: SimulateNotificationRequest,
    token: dict = Depends(verify_token),
) -> Dict[str, Any]:
    """
    Enqueues a notification task in the Celery worker (backed by Redis).
    Returns immediately — the worker processes delivery asynchronously.
    In production, replace the Celery task body with Twilio / SendGrid SDK calls.
    """
    task = send_notification_task.delay(
        transaction_id=request.transaction_id,
        customer_id=request.customer_id,
        action=request.action,
    )
    logger.info(
        "Notification task enqueued | task_id=%s | txn=%s",
        task.id,
        request.transaction_id,
    )
    return {
        "status": "queued",
        "task_id": task.id,
        "message": f"Notification for {request.customer_id} queued for delivery.",
        "transaction_id": request.transaction_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

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
