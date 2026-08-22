import sys
import os
import json

sys.stdout.reconfigure(encoding='utf-8')

try:
    import pandas as pd
    import numpy as np
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pandas', 'numpy'], check=True)
    import pandas as pd
    import numpy as np

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")

def separator(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def analyze_csv(path, name, nrows=None):
    try:
        df = pd.read_csv(path, nrows=nrows)
        print(f"\nFile      : {os.path.basename(path)}")
        print(f"Shape     : {df.shape[0]:,} rows x {df.shape[1]} columns")
        print(f"Columns   : {list(df.columns)}")
        print(f"\nData Types:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            nulls = df[col].isnull().sum()
            unique = df[col].nunique()
            print(f"  {col:<35} | {dtype:<10} | nulls={nulls:<6} | unique={unique:,}")
        print(f"\nSample Data (3 rows):")
        print(df.head(3).to_string())

        # Check for payment/failure related columns
        keywords = ['status', 'fail', 'error', 'type', 'fraud', 'amount', 'bank',
                    'method', 'recover', 'retry', 'action', 'reason', 'decline']
        matched = [c for c in df.columns if any(k in c.lower() for k in keywords)]
        if matched:
            print(f"\nRecoverAI-relevant columns: {matched}")
            for col in matched[:4]:
                if df[col].dtype == object or df[col].nunique() < 30:
                    print(f"  Value counts [{col}]: {df[col].value_counts().head(8).to_dict()}")
        return df
    except Exception as e:
        print(f"  ERROR reading {path}: {e}")
        return None


# ─── DATASET 1: PaySim ────────────────────────────────────────────────────────
separator("DATASET 1: PaySim — Mobile Money Transactions")
df1 = analyze_csv(os.path.join(BASE, "paysim", "PS_20174392719_1491204439457_log.csv"), "PaySim", nrows=100000)


# ─── DATASET 2: Financial Transactions ───────────────────────────────────────
separator("DATASET 2: Financial Transactions — Banking Dataset")

# transactions_data.csv
analyze_csv(os.path.join(BASE, "financial_transactions", "transactions_data.csv"), "Transactions", nrows=50000)

# users_data.csv
analyze_csv(os.path.join(BASE, "financial_transactions", "users_data.csv"), "Users", nrows=5000)

# cards_data.csv
analyze_csv(os.path.join(BASE, "financial_transactions", "cards_data.csv"), "Cards", nrows=5000)

# train_fraud_labels.json
try:
    with open(os.path.join(BASE, "financial_transactions", "train_fraud_labels.json")) as f:
        labels = json.load(f)
    print(f"\ntrain_fraud_labels.json: {len(labels)} entries")
    sample_keys = list(labels.keys())[:5]
    for k in sample_keys:
        print(f"  {k}: {labels[k]}")
except Exception as e:
    print(f"  Could not read fraud labels: {e}")


# ─── DATASET 3: Bank Transactions ────────────────────────────────────────────
separator("DATASET 3: Bank Transaction Dataset — Device/Location/Error")
df3 = analyze_csv(os.path.join(BASE, "bank_transactions", "bank_transactions_data_2.csv"), "BankTxn", nrows=50000)


# ─── DATASET 4: Online Payments ──────────────────────────────────────────────
separator("DATASET 4: Online Payments Fraud Detection")
df4 = analyze_csv(os.path.join(BASE, "online_payments", "PS_20174392719_1491204439457_log.csv"), "OnlinePay", nrows=100000)


# ─── DATASET 5: Credit Card Fraud ────────────────────────────────────────────
separator("DATASET 5: Credit Card Fraud Detection (Benchmark)")
df5 = analyze_csv(os.path.join(BASE, "credit_card_fraud", "creditcard.csv"), "CreditCard", nrows=50000)


# ─── FINAL RECOMMENDATION ────────────────────────────────────────────────────
separator("FINAL: RecoverAI ke liye BEST Dataset Ranking")
print("""
RecoverAI project mein ye features chahiye:
  - transaction_id, amount, payment_method, bank
  - error_reason, treatment_action
  - recovered_within_72h (target)
  - 31 columns, 360,000 rows

RANKING:
  1. financial_transactions/  => Most feature-rich (cards + users + txns)
  2. bank_transactions/       => Has error/device/location fields
  3. paysim/                  => 6M rows, good for volume training
  4. online_payments/         => Same as paysim (duplicate file)
  5. credit_card_fraud/       => Good benchmark but limited features

RECOMMENDATION: financial_transactions + bank_transactions combine karo!
""")
