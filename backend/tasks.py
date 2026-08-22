"""
tasks.py — Celery Background Worker
=====================================
Defines asynchronous tasks that run in the Celery worker process.
The Celery broker and result-backend are read from environment variables:

  REDIS_URL  — e.g. redis://redis:6379/0   (set in docker-compose or .env)
"""

import os
import logging
import time
import random

from celery import Celery

logger = logging.getLogger("recoverai.tasks")

# ---------------------------------------------------------------------------
# Celery app initialisation
# ---------------------------------------------------------------------------
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "recoverai",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Retry failed tasks up to 3 times with exponential back-off
    task_max_retries=3,
    task_acks_late=True,          # acknowledge only after task completes
    worker_prefetch_multiplier=1, # one task per worker slot — fair scheduling
)

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="recoverai.tasks.send_notification", max_retries=3)
def send_notification(self, transaction_id: str, customer_id: str, action: str) -> dict:
    """
    Simulate sending an email / SMS notification to the customer.

    In a real production system you would integrate Twilio / SendGrid / etc.
    Retries automatically on failure (up to max_retries times).
    """
    try:
        logger.info(
            "Sending notification | action=%s | customer=%s | txn=%s",
            action,
            customer_id,
            transaction_id,
        )
        # Simulate network latency (replace with real SDK call in production)
        time.sleep(random.uniform(0.3, 1.0))

        logger.info(
            "Notification sent    | action=%s | customer=%s | txn=%s",
            action,
            customer_id,
            transaction_id,
        )
        return {
            "status": "sent",
            "transaction_id": transaction_id,
            "customer_id": customer_id,
            "action": action,
        }
    except Exception as exc:
        logger.error("Notification failed for %s: %s", transaction_id, exc)
        # Exponential back-off: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, name="recoverai.tasks.smart_retry_payment", max_retries=3)
def smart_retry_payment(self, transaction_id: str, amount: float, payment_method: str) -> dict:
    """
    Simulate an automatic smart-retry attempt for a failed payment.

    Replace the body with your real payment-gateway SDK call.
    """
    try:
        logger.info(
            "Smart-retry attempt  | txn=%s | amount=%.2f | method=%s",
            transaction_id,
            amount,
            payment_method,
        )
        time.sleep(random.uniform(0.5, 2.0))

        # Simulate ~70 % success rate for demo
        if random.random() < 0.70:
            logger.info("Smart-retry succeeded | txn=%s", transaction_id)
            return {"status": "recovered", "transaction_id": transaction_id}
        else:
            raise RuntimeError("Payment gateway returned a transient error")

    except RuntimeError as exc:
        logger.warning("Smart-retry failed (attempt %d): %s", self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
