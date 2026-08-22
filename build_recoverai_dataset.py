"""
RecoverAI — Hybrid Dataset Builder
====================================
Real Kaggle data (PaySim + Financial Transactions) se
missing columns engineer karke 360,000 rows x 31 columns
project-ready dataset banata hai.

Output:
  datasets/recoverai_training.csv    -> 300,000 rows
  datasets/recoverai_validation.csv  -> 60,000 rows
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

sys.stdout.reconfigure(encoding='utf-8')
np.random.seed(42)
random.seed(42)

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")
OUT  = BASE

TOTAL      = 360_000
TRAIN_SIZE = 300_000
VAL_SIZE   =  60_000

print("=" * 65)
print("  RecoverAI — Hybrid Dataset Builder")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────
# STEP 1: Load Real Data for realistic distributions
# ─────────────────────────────────────────────────────────────────
print("\n[1/6] Loading real Kaggle datasets...")

# PaySim — amount distribution + transaction types
paysim_path = os.path.join(BASE, "paysim", "PS_20174392719_1491204439457_log.csv")
paysim = pd.read_csv(paysim_path, usecols=["amount", "type", "isFraud"], nrows=500_000)
real_amounts = paysim["amount"].dropna().values
real_amounts = real_amounts[real_amounts > 0]
real_amounts = real_amounts[real_amounts < 100_000]  # remove outliers
print(f"  PaySim loaded: {len(real_amounts):,} real amount values")

# Financial Transactions — merchant categories
txn_path = os.path.join(BASE, "financial_transactions", "transactions_data.csv")
fin_txn = pd.read_csv(txn_path, usecols=["mcc"], nrows=100_000)
real_mcc_codes = fin_txn["mcc"].dropna().astype(str).unique().tolist()[:50]
print(f"  Financial Transactions loaded: {len(real_mcc_codes)} merchant categories")

# Cards data — for realistic card types
cards_path = os.path.join(BASE, "financial_transactions", "cards_data.csv")
cards = pd.read_csv(cards_path, usecols=["card_type"], nrows=10_000)
card_type_dist = cards["card_type"].value_counts(normalize=True)
card_types = card_type_dist.index.tolist()[:4]
card_probs  = card_type_dist.values[:4]
card_probs  = card_probs / card_probs.sum()
print(f"  Cards loaded: card types = {card_types}")

print("  Real data loaded successfully!")

# ─────────────────────────────────────────────────────────────────
# STEP 2: Define RecoverAI domain values
# ─────────────────────────────────────────────────────────────────
print("\n[2/6] Defining RecoverAI domain schema...")

PAYMENT_METHODS = ["upi", "card", "netbanking"]
METHOD_PROBS    = [0.52, 0.32, 0.16]

BANKS        = ["SBI", "HDFC", "ICICI", "Axis", "Kotak", "PNB", "BOB", "Yes Bank"]
BANK_PROBS   = [0.24, 0.22, 0.18, 0.12, 0.10, 0.07, 0.05, 0.02]

ERROR_REASONS = [
    "insufficient_funds",
    "bank_technical_error",
    "invalid_otp",
    "payment_risk_check_failed",
    "payment_cancelled",
    "network_timeout",
    "daily_limit_exceeded",
    "card_expired",
]
ERROR_PROBS = [0.30, 0.20, 0.18, 0.12, 0.10, 0.05, 0.03, 0.02]

TREATMENT_ACTIONS = [
    "silent_wait",
    "smart_delay",
    "payment_link",
    "notify_payment_link",
    "human_review",
]

CUSTOMER_SEGMENTS = ["premium", "regular", "new"]
SEG_PROBS         = [0.20, 0.60, 0.20]

DEVICE_TYPES = ["mobile", "desktop", "tablet"]
DEV_PROBS    = [0.68, 0.25, 0.07]

CHANNELS = ["app", "web", "branch", "atm"]
CHAN_PROBS = [0.55, 0.25, 0.12, 0.08]

REGIONS = ["North", "South", "East", "West", "Central"]
REG_PROBS = [0.25, 0.22, 0.18, 0.20, 0.15]

MERCHANT_CATEGORIES = [
    "grocery", "fuel", "ecommerce", "utilities", "education",
    "healthcare", "travel", "entertainment", "insurance", "rent"
]

print("  Schema defined: 31 columns ready")

# ─────────────────────────────────────────────────────────────────
# STEP 3: Generate base columns from real data distributions
# ─────────────────────────────────────────────────────────────────
print("\n[3/6] Generating 360,000 rows from real distributions...")

N = TOTAL

# --- IDs ---
transaction_id   = [f"TX{i:08d}" for i in range(1, N+1)]
customer_id      = [f"CUST{np.random.randint(10000, 99999)}" for _ in range(N)]
merchant_id      = [f"M{np.random.randint(100, 999)}" for _ in range(N)]

# --- Amount: sampled from REAL PaySim distribution ---
amount = np.random.choice(real_amounts, size=N, replace=True).round(2)

# --- Payment Method ---
payment_method = np.random.choice(PAYMENT_METHODS, size=N, p=METHOD_PROBS)

# --- Bank ---
bank = np.random.choice(BANKS, size=N, p=BANK_PROBS)

# --- Error Reason ---
error_reason = np.random.choice(ERROR_REASONS, size=N, p=ERROR_PROBS)

# --- Timestamps: last 2 years ---
base_date = datetime(2023, 1, 1)
seconds_range = int((datetime(2024, 12, 31) - base_date).total_seconds())
timestamps = [
    (base_date + timedelta(seconds=int(np.random.randint(0, seconds_range)))).strftime("%Y-%m-%d %H:%M:%S")
    for _ in range(N)
]
ts_series = pd.to_datetime(timestamps)
hour_of_day  = ts_series.hour.values
day_of_week  = ts_series.dayofweek.values   # 0=Mon, 6=Sun
is_weekend   = (day_of_week >= 5).astype(int)

# --- Customer demographics ---
customer_age            = np.random.randint(18, 72, size=N)
customer_segment        = np.random.choice(CUSTOMER_SEGMENTS, size=N, p=SEG_PROBS)
customer_tenure_months  = np.random.randint(1, 120, size=N)
opt_out_notification    = np.random.choice([0, 1], size=N, p=[0.85, 0.15])

# --- Device & channel ---
device_type = np.random.choice(DEVICE_TYPES, size=N, p=DEV_PROBS)
channel     = np.random.choice(CHANNELS, size=N, p=CHAN_PROBS)
region      = np.random.choice(REGIONS, size=N, p=REG_PROBS)

# --- Merchant ---
merchant_category = np.random.choice(MERCHANT_CATEGORIES, size=N)

# --- Card type: from real cards distribution ---
if len(card_types) >= 2:
    card_type = np.random.choice(card_types, size=N, p=card_probs)
else:
    card_type = np.random.choice(["Debit", "Credit", "Prepaid"], size=N, p=[0.55, 0.35, 0.10])

# --- Behavioral features ---
previous_failed_attempts    = np.random.choice([0,1,2,3,4,5], size=N, p=[0.45,0.28,0.15,0.07,0.03,0.02])
time_since_last_failure_hr  = np.where(
    previous_failed_attempts > 0,
    np.random.exponential(scale=24, size=N).clip(0.5, 720).round(1),
    -1.0
)
retry_count                 = np.random.choice([0,1,2,3], size=N, p=[0.50,0.30,0.15,0.05])
transaction_frequency_30d   = np.random.randint(1, 60, size=N)

# --- Account balance: realistic w.r.t. amount ---
account_balance = (amount * np.random.uniform(0.2, 5.0, size=N)).round(2)
# For insufficient_funds: set balance below amount
insuff_mask = error_reason == "insufficient_funds"
account_balance[insuff_mask] = (amount[insuff_mask] * np.random.uniform(0.1, 0.85, size=insuff_mask.sum())).round(2)

# --- Risk score: 0-100 ---
risk_score = (
    (previous_failed_attempts * 8) +
    (retry_count * 5) +
    np.where(error_reason == "payment_risk_check_failed", 30, 0) +
    np.where(opt_out_notification == 1, 5, 0) +
    np.random.randint(0, 20, size=N)
).clip(0, 100)

# --- Amount bucket ---
amount_bucket = pd.cut(
    amount,
    bins=[0, 500, 2000, 10000, float("inf")],
    labels=["low", "medium", "high", "very_high"]
).astype(str)

# --- Notification sent ---
notification_sent = np.where(opt_out_notification == 0, np.random.choice([0,1], size=N, p=[0.3,0.7]), 0)

# --- Recovery attempt count ---
recovery_attempt_count = np.random.choice([0,1,2,3], size=N, p=[0.35,0.40,0.18,0.07])

print("  Base columns generated!")

# ─────────────────────────────────────────────────────────────────
# STEP 4: Engineer TARGET variable with realistic logic
# ─────────────────────────────────────────────────────────────────
print("\n[4/6] Engineering target variable (recovered_within_72h)...")

# Base recovery probability
base_prob = np.full(N, 0.55)

# Error reason effect
error_effect = {
    "insufficient_funds":        -0.20,   # low chance — no money
    "bank_technical_error":      +0.25,   # high — retry works
    "invalid_otp":               +0.30,   # very high — user just re-enters OTP
    "payment_risk_check_failed": -0.30,   # very low — bank blocks
    "payment_cancelled":         -0.10,   # medium-low — user cancelled
    "network_timeout":           +0.28,   # high — just retry
    "daily_limit_exceeded":      -0.25,   # low — cant recover same day
    "card_expired":              -0.40,   # very low — card change needed
}
for reason, effect in error_effect.items():
    base_prob[error_reason == reason] += effect

# Segment effect
base_prob[customer_segment == "premium"] += 0.12
base_prob[customer_segment == "new"]     -= 0.08

# Notification effect
base_prob[notification_sent == 1]        += 0.10
base_prob[opt_out_notification == 1]     -= 0.15

# Amount effect — higher amount = slightly less likely to retry
base_prob[amount_bucket == "very_high"]  -= 0.08
base_prob[amount_bucket == "low"]        += 0.05

# Time of day — off-hours harder to recover
base_prob[(hour_of_day < 8) | (hour_of_day > 22)] -= 0.07

# Risk score effect
base_prob -= (risk_score / 1000)

# Previous failures — more failures = less likely
base_prob -= (previous_failed_attempts * 0.04)

# Recovery attempts — more attempts = more likely recovered
base_prob += (recovery_attempt_count * 0.06)

# Clip to valid probability range
base_prob = base_prob.clip(0.05, 0.95)

# Generate binary target
recovered_within_72h = (np.random.rand(N) < base_prob).astype(int)

print(f"  Recovery rate: {recovered_within_72h.mean()*100:.1f}% (realistic: 40-65% expected)")

# ─────────────────────────────────────────────────────────────────
# STEP 5: Engineer TREATMENT ACTION with smart logic
# ─────────────────────────────────────────────────────────────────
print("\n[5/6] Engineering treatment_action column...")

treatment_action = np.empty(N, dtype=object)

# Rule-based assignment (mimicking guardrail + ML logic)
# High risk -> human_review
high_risk = risk_score >= 70
treatment_action[high_risk] = "human_review"

# Risk check failed -> human_review
treatment_action[error_reason == "payment_risk_check_failed"] = "human_review"

# Technical error / timeout -> smart_delay
tech_mask = (
    np.isin(error_reason, ["bank_technical_error", "network_timeout"]) &
    ~high_risk
)
treatment_action[tech_mask] = "smart_delay"

# OTP error -> payment_link (send fresh payment link)
otp_mask = (error_reason == "invalid_otp") & ~high_risk
treatment_action[otp_mask] = "payment_link"

# Opt-out notification -> notify_payment_link (if allowed)
notify_mask = (
    (opt_out_notification == 0) &
    (notification_sent == 1) &
    np.isin(error_reason, ["insufficient_funds", "daily_limit_exceeded", "card_expired"]) &
    ~high_risk
)
treatment_action[notify_mask] = "notify_payment_link"

# Remaining -> silent_wait
remaining = treatment_action == None
treatment_action[remaining] = "silent_wait"

# Distribution check
unique, counts = np.unique(treatment_action, return_counts=True)
print("  Action distribution:")
for u, c in zip(unique, counts):
    print(f"    {u:<25}: {c:>7,} ({c/N*100:.1f}%)")

# ─────────────────────────────────────────────────────────────────
# STEP 6: Assemble Final DataFrame (31 columns) and Save
# ─────────────────────────────────────────────────────────────────
print("\n[6/6] Assembling 31-column DataFrame and saving CSVs...")

df = pd.DataFrame({
    # --- Identification ---
    "transaction_id":               transaction_id,
    "customer_id":                  customer_id,
    "merchant_id":                  merchant_id,

    # --- Core Payment Info (from real distributions) ---
    "amount":                       amount,
    "payment_method":               payment_method,
    "bank":                         bank,
    "card_type":                    card_type,
    "merchant_category":            merchant_category,

    # --- Error Info ---
    "error_reason":                 error_reason,

    # --- Time Features ---
    "timestamp":                    timestamps,
    "hour_of_day":                  hour_of_day,
    "day_of_week":                  day_of_week,
    "is_weekend":                   is_weekend,

    # --- Customer Profile ---
    "customer_age":                 customer_age,
    "customer_segment":             customer_segment,
    "customer_tenure_months":       customer_tenure_months,
    "opt_out_notification":         opt_out_notification,
    "region":                       region,

    # --- Device & Channel ---
    "device_type":                  device_type,
    "channel":                      channel,

    # --- Behavioral Features ---
    "previous_failed_attempts":     previous_failed_attempts,
    "time_since_last_failure_hr":   time_since_last_failure_hr,
    "retry_count":                  retry_count,
    "transaction_frequency_30d":    transaction_frequency_30d,
    "recovery_attempt_count":       recovery_attempt_count,

    # --- Financial Features ---
    "account_balance":              account_balance,
    "amount_bucket":                amount_bucket,
    "risk_score":                   risk_score,

    # --- Intervention Features ---
    "notification_sent":            notification_sent,

    # --- ACTION (what system did) ---
    "treatment_action":             treatment_action,

    # --- TARGET VARIABLE ---
    "recovered_within_72h":         recovered_within_72h,
})

print(f"  Final shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
assert df.shape[1] == 31, f"Column count mismatch! Got {df.shape[1]}"

# Shuffle
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

# Split
train_df = df.iloc[:TRAIN_SIZE]
val_df   = df.iloc[TRAIN_SIZE:]

# Save
train_path = os.path.join(OUT, "recoverai_training.csv")
val_path   = os.path.join(OUT, "recoverai_validation.csv")

train_df.to_csv(train_path, index=False)
val_df.to_csv(val_path, index=False)

# ─── Final Summary ────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  DONE! RecoverAI Hybrid Dataset Ready!")
print("=" * 65)
print(f"\n  Training CSV  : {train_path}")
print(f"  Rows          : {len(train_df):,}")
print(f"\n  Validation CSV: {val_path}")
print(f"  Rows          : {len(val_df):,}")
print(f"\n  Total Columns : {df.shape[1]} (exactly 31)")
print(f"\n  Columns List  :")
for i, col in enumerate(df.columns, 1):
    print(f"    {i:>2}. {col}")

print(f"\n  Recovery Rate (Train) : {train_df['recovered_within_72h'].mean()*100:.1f}%")
print(f"  Recovery Rate (Val)   : {val_df['recovered_within_72h'].mean()*100:.1f}%")

print("\n  Action Distribution (Training):")
print(train_df["treatment_action"].value_counts().to_string())

print("\n  Error Reason Distribution (Training):")
print(train_df["error_reason"].value_counts().to_string())

print("\n  Data Quality Checks:")
print(f"    Null values   : {df.isnull().sum().sum()}")
print(f"    Duplicate IDs : {df['transaction_id'].duplicated().sum()}")
print(f"    Amount range  : Rs {df['amount'].min():.2f} — Rs {df['amount'].max():.2f}")

print("\n  RecoverAI project ke liye dataset READY hai!")
print("=" * 65)
