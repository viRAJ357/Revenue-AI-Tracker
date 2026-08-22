"""
RecoverAI - Guardrail Engine
============================
Rule-based safety layer that runs BEFORE the ML policy engine.
If any guardrail is triggered, its decision overrides the model output entirely,
ensuring high-risk cases are always escalated or blocked appropriately.

Guardrail Priority (highest → lowest):
  1. High risk score       → human_review
  2. Risk check failure    → human_review
  3. Too many failures     → human_review
  4. High value amount     → human_review
  5. Too many retries      → block silent_wait, suggest smart_delay
  6. Default               → pass (let ML decide)
"""

from typing import Tuple, Optional
from models import PaymentEvent


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RISK_SCORE_THRESHOLD = 80          # Force human review above this score
MAX_FAILED_ATTEMPTS = 4            # Force human review at or above this count
HIGH_VALUE_THRESHOLD = 50_000      # INR - Force human review above this amount
MAX_RETRY_COUNT = 3                # Block silent_wait at or above this retry count

RISKY_ERROR_REASONS = {
    "payment_risk_check_failed",   # Explicit risk flag from payment gateway
}


# ---------------------------------------------------------------------------
# Individual rule checkers (each returns (triggered, action, reason))
# ---------------------------------------------------------------------------

def _rule_high_risk_score(event: PaymentEvent) -> Tuple[bool, str, str]:
    """
    Rule 1: Transactions with a risk score >= 80 must be reviewed by a human.
    Prevents the system from auto-retrying potentially fraudulent payments.
    """
    if event.risk_score >= RISK_SCORE_THRESHOLD:
        return True, "human_review", f"High risk score ({event.risk_score:.1f} >= {RISK_SCORE_THRESHOLD})"
    return False, "", ""


def _rule_risk_check_failed(event: PaymentEvent) -> Tuple[bool, str, str]:
    """
    Rule 2: If the payment gateway itself flagged a risk check failure,
    always escalate to human review regardless of other signals.
    """
    if event.error_reason in RISKY_ERROR_REASONS:
        return True, "human_review", f"Payment gateway risk check failed (error: {event.error_reason})"
    return False, "", ""


def _rule_too_many_failures(event: PaymentEvent) -> Tuple[bool, str, str]:
    """
    Rule 3: Four or more previous failed attempts on the same transaction
    indicate a structural problem that a simple retry cannot solve.
    """
    if event.previous_failed_attempts >= MAX_FAILED_ATTEMPTS:
        return (
            True,
            "human_review",
            f"Too many previous failures ({event.previous_failed_attempts} >= {MAX_FAILED_ATTEMPTS})"
        )
    return False, "", ""


def _rule_high_value_transaction(event: PaymentEvent) -> Tuple[bool, str, str]:
    """
    Rule 4: Transactions exceeding ₹50,000 require human oversight to prevent
    large erroneous or fraudulent payments from being automatically retried.
    """
    if event.amount > HIGH_VALUE_THRESHOLD:
        return (
            True,
            "human_review",
            f"High-value transaction (₹{event.amount:,.2f} > ₹{HIGH_VALUE_THRESHOLD:,})"
        )
    return False, "", ""


def _rule_excessive_retries(event: PaymentEvent) -> Tuple[bool, str, str]:
    """
    Rule 5: If the system has already retried 3 or more times, block further
    silent waits and suggest a smart_delay to space out attempts.
    This rule does NOT force human review — it only modifies action selection.
    """
    if event.retry_count >= MAX_RETRY_COUNT:
        return (
            True,
            "smart_delay",
            f"Excessive retries ({event.retry_count} >= {MAX_RETRY_COUNT}); smart_delay recommended"
        )
    return False, "", ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Ordered list of rules — evaluated top-to-bottom; first match wins.
_RULES = [
    _rule_high_risk_score,
    _rule_risk_check_failed,
    _rule_too_many_failures,
    _rule_high_value_transaction,
    _rule_excessive_retries,   # Must come last as it's a softer override
]


def check_guardrails(event: PaymentEvent) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Evaluate all guardrail rules against a payment event.

    Returns
    -------
    (guardrail_triggered: bool, forced_action: str | None, reason: str | None)

    If ``guardrail_triggered`` is True the caller MUST use ``forced_action``
    instead of the ML model's recommendation.
    """
    for rule_fn in _RULES:
        triggered, forced_action, reason = rule_fn(event)
        if triggered:
            return True, forced_action, reason

    # All rules passed — let the policy engine decide
    return False, None, None


def summarize_guardrails() -> dict:
    """
    Return a human-readable summary of all active guardrail thresholds.
    Useful for the /api/health and admin endpoints.
    """
    return {
        "rules": [
            {
                "id": "high_risk_score",
                "description": "Force human_review when risk_score >= threshold",
                "threshold": RISK_SCORE_THRESHOLD,
            },
            {
                "id": "risk_check_failed",
                "description": "Force human_review on explicit gateway risk errors",
                "trigger_values": list(RISKY_ERROR_REASONS),
            },
            {
                "id": "too_many_failures",
                "description": "Force human_review when previous_failed_attempts >= threshold",
                "threshold": MAX_FAILED_ATTEMPTS,
            },
            {
                "id": "high_value_transaction",
                "description": "Force human_review when amount > threshold (INR)",
                "threshold": HIGH_VALUE_THRESHOLD,
            },
            {
                "id": "excessive_retries",
                "description": "Suggest smart_delay when retry_count >= threshold",
                "threshold": MAX_RETRY_COUNT,
            },
        ]
    }
