"""
RecoverAI - SQLite Database Layer
==================================
Provides a lightweight, dependency-free persistence layer using the built-in
sqlite3 module.  Every decision made by the recovery engine is stored here
for audit, analytics, and operator review purposes.

No ORM is used intentionally — this keeps the footprint minimal and avoids
heavy migrations for this project phase.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve DB path relative to THIS file so it works regardless of cwd
_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_HERE, "..", "recoverai_audit.db")
DB_PATH = os.path.normpath(DB_PATH)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS recovery_events (
    -- Primary key
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id              TEXT    NOT NULL UNIQUE,
    customer_id                 TEXT    NOT NULL,
    timestamp                   TEXT    NOT NULL,

    -- Transaction inputs
    amount                      REAL    NOT NULL,
    payment_method              TEXT    NOT NULL,
    bank                        TEXT    NOT NULL,
    error_reason                TEXT    NOT NULL,
    customer_segment            TEXT    NOT NULL,
    opt_out_notification        INTEGER NOT NULL DEFAULT 0,
    device_type                 TEXT,
    channel                     TEXT,
    region                      TEXT,
    customer_age                INTEGER,
    account_balance             REAL,
    customer_tenure_months      INTEGER,
    previous_failed_attempts    INTEGER,
    retry_count                 INTEGER,
    risk_score                  REAL,
    merchant_category           TEXT,
    card_type                   TEXT,
    hour_of_day                 INTEGER,
    day_of_week                 INTEGER,
    is_weekend                  INTEGER,
    time_since_last_failure_hr  REAL,
    transaction_frequency_30d   INTEGER,
    recovery_attempt_count      INTEGER,
    notification_sent           INTEGER,

    -- Recovery decision outputs
    recommended_action          TEXT    NOT NULL,
    recovery_probability        REAL    NOT NULL,
    guardrail_triggered         INTEGER NOT NULL DEFAULT 0,
    guardrail_reason            TEXT,
    all_action_scores           TEXT    DEFAULT '{}',

    -- Operator review
    operator_decision           TEXT,
    operator_notes              TEXT,
    reviewed_at                 TEXT
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_recovery_events_timestamp
    ON recovery_events (timestamp DESC);
"""


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """
    Return a sqlite3 connection with row_factory set to dict-like access.
    Uses check_same_thread=False so FastAPI's async workers can share it
    safely (SQLite handles its own serialisation for writes).
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row   # allows dict-style column access
    return conn


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create the database file and schema if they do not already exist.
    Safe to call on every startup — uses IF NOT EXISTS guards.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _get_connection() as conn:
        conn.execute(_CREATE_TABLE_SQL)
        conn.execute(_CREATE_INDEX_SQL)
        conn.commit()
    logger.info("SQLite database initialised at: %s", DB_PATH)


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def insert_record(record: Dict[str, Any]) -> None:
    """
    Persist a single recovery decision audit record.

    Parameters
    ----------
    record : dict
        Must contain all required columns.  ``all_action_scores`` should be
        passed as a dict; it will be JSON-serialised automatically.
    """
    # Serialise nested dict to JSON string for storage
    record = dict(record)  # shallow copy to avoid mutating caller's dict
    if isinstance(record.get("all_action_scores"), dict):
        record["all_action_scores"] = json.dumps(record["all_action_scores"])

    # Convert datetime objects to ISO strings
    for key, val in record.items():
        if isinstance(val, datetime):
            record[key] = val.isoformat()

    # Convert booleans to integers (SQLite has no native bool)
    for key in ("opt_out_notification", "guardrail_triggered", "notification_sent"):
        if key in record and isinstance(record[key], bool):
            record[key] = int(record[key])

    columns = ", ".join(record.keys())
    placeholders = ", ".join(["?" for _ in record])
    sql = f"INSERT OR REPLACE INTO recovery_events ({columns}) VALUES ({placeholders})"

    with _get_connection() as conn:
        conn.execute(sql, list(record.values()))
        conn.commit()
    logger.debug("Inserted record for transaction_id=%s", record.get("transaction_id"))


def update_operator_decision(
    transaction_id: str,
    operator_decision: str,
    operator_notes: Optional[str] = None,
) -> bool:
    """
    Update the operator review fields for a specific transaction.

    Returns True if a row was updated, False if the transaction_id was not found.
    """
    sql = """
        UPDATE recovery_events
        SET operator_decision = ?,
            operator_notes    = ?,
            reviewed_at       = ?
        WHERE transaction_id  = ?
    """
    with _get_connection() as conn:
        cur = conn.execute(
            sql,
            (operator_decision, operator_notes, datetime.utcnow().isoformat(), transaction_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_all_records(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent ``limit`` recovery events, newest first.
    ``all_action_scores`` is deserialised from JSON back to a dict.
    """
    sql = """
        SELECT * FROM recovery_events
        ORDER BY timestamp DESC
        LIMIT ?
    """
    with _get_connection() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        # Deserialise JSON fields
        try:
            d["all_action_scores"] = json.loads(d.get("all_action_scores") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["all_action_scores"] = {}
        results.append(d)
    return results


def get_record_by_id(transaction_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single record by transaction_id, or None if not found."""
    sql = "SELECT * FROM recovery_events WHERE transaction_id = ? LIMIT 1"
    with _get_connection() as conn:
        row = conn.execute(sql, (transaction_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    try:
        d["all_action_scores"] = json.loads(d.get("all_action_scores") or "{}")
    except (json.JSONDecodeError, TypeError):
        d["all_action_scores"] = {}
    return d


# ---------------------------------------------------------------------------
# Analytics / Stats
# ---------------------------------------------------------------------------

def get_stats() -> Dict[str, Any]:
    """
    Compute aggregate statistics over all recovery events.

    Returns
    -------
    dict with keys:
        total_events        : int
        recovery_rate       : float  (fraction of non-human_review actions)
        action_distribution : dict   {action: count}
        error_distribution  : dict   {error_reason: count}
        avg_recovery_prob   : float
        guardrail_rate      : float  (fraction of events with guardrail triggered)
        pending_review      : int    (human_review events without operator decision)
    """
    stats: Dict[str, Any] = {
        "total_events": 0,
        "recovery_rate": 0.0,
        "action_distribution": {},
        "error_distribution": {},
        "avg_recovery_prob": 0.0,
        "avg_risk_score": 0.0,
        "guardrail_rate": 0.0,
        "pending_review": 0,
    }

    with _get_connection() as conn:
        # Total events
        total = conn.execute("SELECT COUNT(*) FROM recovery_events").fetchone()[0]
        stats["total_events"] = total
        if total == 0:
            return stats

        # Average recovery probability
        avg_prob = conn.execute(
            "SELECT AVG(recovery_probability) FROM recovery_events"
        ).fetchone()[0]
        stats["avg_recovery_prob"] = round(avg_prob or 0.0, 4)

        # Average risk score
        avg_risk = conn.execute(
            "SELECT AVG(risk_score) FROM recovery_events"
        ).fetchone()[0]
        stats["avg_risk_score"] = round(avg_risk or 0.0, 1)

        # Guardrail rate
        guardrail_count = conn.execute(
            "SELECT COUNT(*) FROM recovery_events WHERE guardrail_triggered = 1"
        ).fetchone()[0]
        stats["guardrail_rate"] = round(guardrail_count / total, 4)

        # Action distribution
        rows = conn.execute(
            "SELECT recommended_action, COUNT(*) as cnt FROM recovery_events GROUP BY recommended_action"
        ).fetchall()
        action_dist = {r["recommended_action"]: r["cnt"] for r in rows}
        stats["action_distribution"] = action_dist

        # Recovery rate = fraction of events NOT routed to human_review
        human_review_count = action_dist.get("human_review", 0)
        stats["recovery_rate"] = round((total - human_review_count) / total, 4)

        # Top error reasons (top 10)
        rows = conn.execute(
            """
            SELECT error_reason, COUNT(*) as cnt
            FROM recovery_events
            GROUP BY error_reason
            ORDER BY cnt DESC
            LIMIT 10
            """
        ).fetchall()
        stats["error_distribution"] = {r["error_reason"]: r["cnt"] for r in rows}

        # Pending human review (no operator decision yet)
        pending = conn.execute(
            """
            SELECT COUNT(*) FROM recovery_events
            WHERE recommended_action = 'human_review'
              AND operator_decision IS NULL
            """
        ).fetchone()[0]
        stats["pending_review"] = pending

    return stats
