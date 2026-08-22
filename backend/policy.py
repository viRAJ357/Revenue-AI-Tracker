"""
RecoverAI - CatBoost Policy Engine
=====================================
Loads the pre-trained CatBoost model and uses it to score all candidate
recovery actions for a given payment event, returning the action with the
highest predicted recovery probability.

Design note
-----------
The model was trained with a ``treatment_action`` feature that encodes which
recovery strategy was applied.  At inference time we iterate over all 5
possible actions, fix ``treatment_action`` to each, predict the recovery
probability, and pick the argmax.  This is a standard counterfactual /
uplift-style inference loop.

Feature order and names match the training script exactly:
    amount, payment_method, bank, card_type, merchant_category,
    error_reason, hour_of_day, day_of_week, is_weekend, customer_age,
    customer_segment, customer_tenure_months, opt_out_notification,
    region, device_type, channel, previous_failed_attempts,
    time_since_last_failure_hr, retry_count, transaction_frequency_30d,
    recovery_attempt_count, account_balance, amount_bucket, risk_score,
    notification_sent, treatment_action
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature specification — must match training script exactly
# ---------------------------------------------------------------------------

# Exact feature order as saved in the model (from model.feature_names_)
FEATURES = [
    "amount",
    "payment_method",
    "bank",
    "card_type",
    "merchant_category",
    "error_reason",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "customer_age",
    "customer_segment",
    "customer_tenure_months",
    "opt_out_notification",
    "region",
    "device_type",
    "channel",
    "previous_failed_attempts",
    "time_since_last_failure_hr",
    "retry_count",
    "transaction_frequency_30d",
    "recovery_attempt_count",
    "account_balance",
    "amount_bucket",          # engineered feature — computed at inference
    "risk_score",
    "notification_sent",
    "treatment_action",       # set dynamically per candidate action
]

# Categorical feature names (must match training cat_features list)
CAT_FEATURES = [
    "payment_method",
    "bank",
    "card_type",
    "merchant_category",
    "error_reason",
    "customer_segment",
    "region",
    "device_type",
    "channel",
    "amount_bucket",
    "treatment_action",
]

# Candidate treatment actions the system can recommend
TREATMENT_ACTIONS = [
    "silent_wait",
    "smart_delay",
    "payment_link",
    "notify_payment_link",
    "human_review",
]

# Path to the saved CatBoost model file
_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.normpath(os.path.join(_HERE, "..", "model", "recoverai_catboost.cbm"))


# ---------------------------------------------------------------------------
# Amount bucket helper (must match training pipeline)
# ---------------------------------------------------------------------------

def _compute_amount_bucket(amount: float) -> str:
    """Bin the transaction amount into the same buckets used at training time."""
    if amount < 500:
        return "low"
    elif amount < 2000:
        return "medium"
    elif amount < 10000:
        return "high"
    else:
        return "very_high"


# ---------------------------------------------------------------------------
# Lazy model loader
# ---------------------------------------------------------------------------

_model = None
_model_available = None   # None = not yet checked, bool after first check


def _load_model():
    """
    Attempt to load the CatBoost model from disk (once, then cached).
    Sets ``_model_available`` based on success/failure.
    """
    global _model, _model_available

    if _model_available is not None:
        return  # already attempted

    if not os.path.exists(MODEL_PATH):
        logger.warning(
            "CatBoost model file not found at %s. "
            "Falling back to heuristic scoring.",
            MODEL_PATH,
        )
        _model_available = False
        return

    try:
        from catboost import CatBoostClassifier  # type: ignore
        model = CatBoostClassifier()
        model.load_model(MODEL_PATH)
        _model = model
        _model_available = True
        logger.info("CatBoost model loaded from %s | features: %s",
                    MODEL_PATH, model.feature_names_)
    except ImportError:
        logger.error("catboost package not installed. Run: pip install catboost")
        _model_available = False
    except Exception as exc:
        logger.error("Failed to load CatBoost model: %s", exc)
        _model_available = False


# ---------------------------------------------------------------------------
# Heuristic fallback (used when model is unavailable)
# ---------------------------------------------------------------------------

def _heuristic_scores(event) -> dict:
    """
    Simple rule-based scoring used when the ML model cannot be loaded.
    Returns plausible scores so the API remains functional for demo purposes.
    """
    base = {
        "payment_link":       0.55,
        "smart_delay":        0.45,
        "notify_payment_link": 0.50,
        "silent_wait":        0.30,
        "human_review":       0.20,
    }

    pm = str(getattr(event, "payment_method", "")).lower()
    if pm == "upi" and event.risk_score < 30:
        base["payment_link"] += 0.15

    if not getattr(event, "opt_out_notification", True):
        base["notify_payment_link"] += 0.10

    if getattr(event, "retry_count", 0) >= 2:
        base["smart_delay"] += 0.20

    if event.risk_score >= 60:
        base["human_review"] += 0.30

    max_val = max(base.values()) or 1.0
    return {k: round(min(v / max_val, 1.0), 4) for k, v in base.items()}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_best_action(event) -> tuple:
    """
    Score all candidate treatment actions for ``event`` and return the best one.

    Parameters
    ----------
    event : PaymentEvent
        Inbound payment failure event.

    Returns
    -------
    (action: str, probability: float, all_scores: dict)
        action       — name of the recommended treatment action
        probability  — predicted recovery probability for that action (0–1)
        all_scores   — mapping of {action: probability} for all 5 actions
    """
    _load_model()

    if not _model_available:
        scores = _heuristic_scores(event)
        best_action = max(scores, key=scores.__getitem__)
        return best_action, scores[best_action], scores

    # --- CatBoost inference path ---
    try:
        from catboost import Pool  # type: ignore
    except ImportError:
        scores = _heuristic_scores(event)
        best_action = max(scores, key=scores.__getitem__)
        return best_action, scores[best_action], scores

    scores: dict = {}

    # Build base feature dict from the event (excluding treatment_action)
    amount = float(event.amount)
    base_row = {
        "amount":                      amount,
        "payment_method":              str(event.payment_method),
        "bank":                        str(event.bank),
        "card_type":                   str(getattr(event, "card_type", "NA")),
        "merchant_category":           str(getattr(event, "merchant_category", "ecommerce")),
        "error_reason":                str(event.error_reason),
        "hour_of_day":                 int(getattr(event, "hour_of_day", 12)),
        "day_of_week":                 int(getattr(event, "day_of_week", 0)),
        "is_weekend":                  int(getattr(event, "is_weekend", 0)),
        "customer_age":                int(getattr(event, "customer_age", 30)),
        "customer_segment":            str(event.customer_segment),
        "customer_tenure_months":      int(getattr(event, "customer_tenure_months", 12)),
        "opt_out_notification":        int(bool(getattr(event, "opt_out_notification", False))),
        "region":                      str(getattr(event, "region", "South")),
        "device_type":                 str(getattr(event, "device_type", "mobile")),
        "channel":                     str(getattr(event, "channel", "app")),
        "previous_failed_attempts":    int(getattr(event, "previous_failed_attempts", 0)),
        "time_since_last_failure_hr":  float(getattr(event, "time_since_last_failure_hr", 0.0)),
        "retry_count":                 int(getattr(event, "retry_count", 0)),
        "transaction_frequency_30d":   int(getattr(event, "transaction_frequency_30d", 5)),
        "recovery_attempt_count":      int(getattr(event, "recovery_attempt_count", 0)),
        "account_balance":             float(getattr(event, "account_balance", 0.0)),
        "amount_bucket":               _compute_amount_bucket(amount),   # engineered
        "risk_score":                  float(event.risk_score),
        "notification_sent":           int(getattr(event, "notification_sent", 0)),
    }

    for action in TREATMENT_ACTIONS:
        row = {**base_row, "treatment_action": action}

        # Build a DataFrame row (CatBoost Pool needs consistent dtypes)
        df = pd.DataFrame([row], columns=FEATURES)

        try:
            pool = Pool(data=df, cat_features=CAT_FEATURES)
            prob_matrix = _model.predict_proba(pool)
            # Index 1 = probability of positive class (recovered = 1)
            recovery_prob = float(prob_matrix[0][1])
        except Exception as exc:
            logger.error("CatBoost prediction failed for action=%s: %s", action, exc)
            recovery_prob = 0.0

        scores[action] = round(recovery_prob, 4)

    best_action = max(scores, key=scores.__getitem__)
    return best_action, scores[best_action], scores


def is_model_loaded() -> bool:
    """Return True if the CatBoost model is available for inference."""
    _load_model()
    return bool(_model_available)
