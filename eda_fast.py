import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")

def show(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def eda(path, label, nrows=50000):
    if not os.path.exists(path):
        print(f"  FILE NOT FOUND: {path}")
        return
    df = pd.read_csv(path, nrows=nrows)
    print(f"\n  File    : {os.path.basename(path)}")
    print(f"  Shape   : {df.shape[0]:,} rows x {df.shape[1]} cols (sample)")
    print(f"  Columns : {list(df.columns)}\n")
    for col in df.columns:
        dtype   = str(df[col].dtype)
        nulls   = df[col].isnull().sum()
        unique  = df[col].nunique()
        sample  = df[col].value_counts().head(4).to_dict() if df[col].dtype == object or unique < 20 else f"min={df[col].min():.2f}  max={df[col].max():.2f}  mean={df[col].mean():.2f}"
        print(f"  {col:<35} | {dtype:<10} | nulls={nulls:<5} | uniq={unique:<6} | {sample}")

# --- Dataset 1: PaySim ---
show("DATASET 1: PaySim — Mobile Money (6M rows)")
eda(os.path.join(BASE, "paysim", "PS_20174392719_1491204439457_log.csv"), "PaySim")

# --- Dataset 2a: Transactions ---
show("DATASET 2a: Financial — transactions_data.csv")
eda(os.path.join(BASE, "financial_transactions", "transactions_data.csv"), "Txn")

# --- Dataset 2b: Users ---
show("DATASET 2b: Financial — users_data.csv")
eda(os.path.join(BASE, "financial_transactions", "users_data.csv"), "Users")

# --- Dataset 2c: Cards ---
show("DATASET 2c: Financial — cards_data.csv")
eda(os.path.join(BASE, "financial_transactions", "cards_data.csv"), "Cards")

# --- Dataset 3: Bank Transactions ---
show("DATASET 3: Bank Transactions — bank_transactions_data_2.csv")
eda(os.path.join(BASE, "bank_transactions", "bank_transactions_data_2.csv"), "Bank")

# --- Dataset 5: Credit Card ---
show("DATASET 5: Credit Card Fraud — creditcard.csv")
eda(os.path.join(BASE, "credit_card_fraud", "creditcard.csv"), "CC")

# --- Summary ---
show("SUMMARY: RecoverAI Fit Score")
print("""
  Dataset                    | Rows(approx) | Key Matching Columns
  ---------------------------|--------------|------------------------------
  PaySim                     | 6,000,000    | type, amount, isFraud
  financial/transactions     | large        | amount, date, merchant_id
  financial/users            | moderate     | card, bank, account info
  bank_transactions          | moderate     | device, location, error?
  credit_card_fraud          | 284,807      | amount, Class (fraud label)
  ---------------------------|--------------|------------------------------

  BEST FOR RecoverAI:
    PRIMARY  -> financial_transactions (multi-table, richest features)
    SUPPORT  -> bank_transactions      (device + location + error data)
    VOLUME   -> paysim                 (6M rows for training volume)
""")
