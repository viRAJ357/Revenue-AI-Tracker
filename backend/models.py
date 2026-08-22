"""
RecoverAI - Pydantic Data Models
Defines input/output schemas and audit records for the payment recovery system.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Literal
from datetime import datetime
import uuid


# ---------------------------------------------------------------------------
# Input Model: PaymentEvent
# ---------------------------------------------------------------------------

class PaymentEvent(BaseModel):
    """
    Represents an inbound payment failure event submitted for recovery analysis.
    All fields map directly to the features used by the CatBoost policy engine.
    """

    # --- Core transaction identifiers ---
    transaction_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the transaction"
    )
    amount: float = Field(..., gt=0, description="Transaction amount in INR")
    payment_method: Literal["upi", "card", "netbanking"] = Field(
        ..., description="Payment method used"
    )
    bank: str = Field(..., description="Issuing bank name")
    error_reason: str = Field(..., description="Machine-readable failure reason code")

    # --- Customer profile ---
    customer_id: str = Field(..., description="Unique customer identifier")
    customer_segment: Literal["premium", "regular", "new"] = Field(
        ..., description="Customer loyalty/value tier"
    )
    opt_out_notification: bool = Field(
        default=False, description="True if the customer has opted out of notifications"
    )
    device_type: str = Field(..., description="Device used (mobile/desktop/tablet)")
    channel: str = Field(..., description="Acquisition/interaction channel")
    region: str = Field(..., description="Geographic region of the customer")
    customer_age: int = Field(..., ge=18, le=100, description="Customer age in years")
    account_balance: float = Field(..., ge=0, description="Current account balance in INR")
    customer_tenure_months: int = Field(
        ..., ge=0, description="Number of months since customer onboarding"
    )

    # --- Transaction history & risk signals ---
    previous_failed_attempts: int = Field(
        ..., ge=0, description="Count of prior failed attempts for this transaction"
    )
    retry_count: int = Field(
        ..., ge=0, description="Number of retries attempted so far"
    )
    risk_score: float = Field(
        ..., ge=0, le=100, description="Fraud/risk score (0=low risk, 100=high risk)"
    )
    merchant_category: str = Field(..., description="Merchant category code / label")
    card_type: str = Field(
        default="NA", description="Card type (credit/debit/prepaid/NA if not card)"
    )

    # --- Temporal features ---
    hour_of_day: int = Field(..., ge=0, le=23, description="Hour of transaction (24h)")
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Mon, 6=Sun)")
    is_weekend: int = Field(..., ge=0, le=1, description="1 if weekend, else 0")
    time_since_last_failure_hr: float = Field(
        ..., ge=0, description="Hours elapsed since previous failure"
    )

    # --- Behavioural features ---
    transaction_frequency_30d: int = Field(
        ..., ge=0, description="Number of transactions in past 30 days"
    )
    recovery_attempt_count: int = Field(
        ..., ge=0, description="Previous recovery attempts on this account"
    )

    # --- Notification tracking ---
    notification_sent: int = Field(
        default=0, ge=0, le=1, description="1 if a notification was already sent"
    )

    class Config:
        schema_extra = {
            "example": {
                "transaction_id": "TXN-DEMO-001",
                "amount": 4999.0,
                "payment_method": "upi",
                "bank": "HDFC",
                "error_reason": "insufficient_funds",
                "customer_id": "CUST-12345",
                "customer_segment": "premium",
                "opt_out_notification": False,
                "device_type": "mobile",
                "channel": "app",
                "region": "South",
                "customer_age": 32,
                "account_balance": 1200.0,
                "customer_tenure_months": 24,
                "previous_failed_attempts": 1,
                "retry_count": 0,
                "risk_score": 25.0,
                "merchant_category": "ecommerce",
                "card_type": "NA",
                "hour_of_day": 14,
                "day_of_week": 2,
                "is_weekend": 0,
                "time_since_last_failure_hr": 2.5,
                "transaction_frequency_30d": 12,
                "recovery_attempt_count": 0,
                "notification_sent": 0,
            }
        }


# ---------------------------------------------------------------------------
# Output Model: RecoveryDecision
# ---------------------------------------------------------------------------

class RecoveryDecision(BaseModel):
    """
    Represents the system's recovery recommendation returned to the caller.
    """

    transaction_id: str = Field(..., description="Mirrors input transaction_id")
    recommended_action: str = Field(
        ...,
        description=(
            "One of: smart_retry / smart_delay / send_notification / "
            "silent_wait / human_review"
        ),
    )
    recovery_probability: float = Field(
        ..., ge=0, le=1, description="Confidence score for the recommended action"
    )
    guardrail_triggered: bool = Field(
        default=False, description="True if a guardrail rule overrode the ML policy"
    )
    guardrail_reason: Optional[str] = Field(
        default=None, description="Human-readable reason if a guardrail was triggered"
    )
    risk_score: float = Field(..., description="Risk score echoed from input event")
    all_action_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Predicted recovery probability for every candidate action",
    )
    status: Literal["success", "error"] = Field(default="success")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "transaction_id": "TXN-DEMO-001",
                "recommended_action": "smart_retry",
                "recovery_probability": 0.78,
                "guardrail_triggered": False,
                "guardrail_reason": None,
                "risk_score": 25.0,
                "all_action_scores": {
                    "smart_retry": 0.78,
                    "smart_delay": 0.55,
                    "send_notification": 0.60,
                    "silent_wait": 0.30,
                    "human_review": 0.20,
                },
                "status": "success",
                "timestamp": "2026-08-22T12:00:00",
            }
        }


# ---------------------------------------------------------------------------
# Audit Model: AuditRecord
# ---------------------------------------------------------------------------

class AuditRecord(BaseModel):
    """
    Full record persisted to SQLite for every decision made by RecoverAI.
    Combines all input fields with the system's output for traceability.
    """

    # Identifiers
    transaction_id: str
    customer_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Input snapshot
    amount: float
    payment_method: str
    bank: str
    error_reason: str
    customer_segment: str
    opt_out_notification: bool
    device_type: str
    channel: str
    region: str
    customer_age: int
    account_balance: float
    customer_tenure_months: int
    previous_failed_attempts: int
    retry_count: int
    risk_score: float
    merchant_category: str
    card_type: str
    hour_of_day: int
    day_of_week: int
    is_weekend: int
    time_since_last_failure_hr: float
    transaction_frequency_30d: int
    recovery_attempt_count: int
    notification_sent: int

    # Output snapshot
    recommended_action: str
    recovery_probability: float
    guardrail_triggered: bool
    guardrail_reason: Optional[str] = None
    all_action_scores: str = "{}"  # stored as JSON string

    # Operator review fields
    operator_decision: Optional[str] = None   # 'approved' | 'rejected'
    operator_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
