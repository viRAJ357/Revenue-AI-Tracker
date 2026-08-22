"""
RecoverAI — Dataset Auto Downloader
=====================================
Ye script sab datasets automatically download karegi
Pehle kaggle.json file C:\Users\nikhi\.kaggle\ mein rakho
Phir is script ko run karo: python download_datasets.py
"""

import os
import subprocess
import sys

# ─── Download folder ───────────────────────────────────────────────
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "datasets")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ─── All datasets to download ──────────────────────────────────────
DATASETS = [
    {
        "name": "1. PaySim — Mobile Money Transactions (6M+ rows)",
        "slug": "ealaxi/paysim1",
        "folder": "paysim"
    },
    {
        "name": "2. Financial Transactions — Full Banking Dataset",
        "slug": "computingvictor/transactions-fraud-datasets",
        "folder": "financial_transactions"
    },
    {
        "name": "3. Bank Transaction Dataset — Device/Location/Error",
        "slug": "valakhorasani/bank-transaction-dataset-for-fraud-detection",
        "folder": "bank_transactions"
    },
    {
        "name": "4. Online Payments Fraud Detection",
        "slug": "rupakroy/online-payments-fraud-detection-dataset",
        "folder": "online_payments"
    },
    {
        "name": "5. Credit Card Fraud Detection (Benchmark)",
        "slug": "mlg-ulb/creditcardfraud",
        "folder": "credit_card_fraud"
    },
]

# ─── Check kaggle.json ─────────────────────────────────────────────
kaggle_json = os.path.join(os.path.expanduser("~"), ".kaggle", "kaggle.json")
if not os.path.exists(kaggle_json):
    print("=" * 60)
    print("❌ ERROR: kaggle.json nahi mila!")
    print("=" * 60)
    print("\nSteps:")
    print("  1. kaggle.com pe jaao → Login karo")
    print("  2. Profile → Settings → API → 'Create New Token'")
    print("  3. Downloaded kaggle.json ko yahan rakho:")
    print(f"     {kaggle_json}")
    print("\nPhir dobara ye script run karo!")
    sys.exit(1)

print("=" * 60)
print("  RecoverAI — Dataset Auto Downloader")
print("=" * 60)
print(f"\n📁 Download folder: {DOWNLOAD_DIR}\n")

# ─── Download each dataset ─────────────────────────────────────────
success = 0
failed  = 0

for i, ds in enumerate(DATASETS, 1):
    target = os.path.join(DOWNLOAD_DIR, ds["folder"])
    os.makedirs(target, exist_ok=True)

    print(f"[{i}/{len(DATASETS)}] Downloading: {ds['name']}")
    print(f"         Slug : {ds['slug']}")
    print(f"         Path : {target}")

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "kaggle",
                "datasets", "download",
                "-d", ds["slug"],
                "-p", target,
                "--unzip"
            ],
            capture_output=True,
            text=True,
            timeout=600   # 10 min timeout per dataset
        )

        if result.returncode == 0:
            files = os.listdir(target)
            print(f"         ✅ Done! Files: {files[:3]}")
            success += 1
        else:
            print(f"         ❌ Failed: {result.stderr.strip()[:200]}")
            failed += 1

    except subprocess.TimeoutExpired:
        print(f"         ⏱️  Timeout — dataset bohot bada hai, manually download karo")
        failed += 1
    except Exception as e:
        print(f"         ❌ Error: {e}")
        failed += 1

    print()

# ─── Summary ──────────────────────────────────────────────────────
print("=" * 60)
print(f"  ✅ Successful : {success}/{len(DATASETS)}")
print(f"  ❌ Failed     : {failed}/{len(DATASETS)}")
print(f"  📁 Location   : {DOWNLOAD_DIR}")
print("=" * 60)

if success > 0:
    print("\n🎉 Datasets ready hain! Ab RecoverAI project shuru karo!")
