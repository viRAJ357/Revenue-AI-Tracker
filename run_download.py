import sys
import os
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")

DATASETS = [
    {
        "name": "1. PaySim - Mobile Money Transactions (6M+ rows)",
        "slug": "ealaxi/paysim1",
        "folder": "paysim"
    },
    {
        "name": "2. Financial Transactions - Full Banking Dataset",
        "slug": "computingvictor/transactions-fraud-datasets",
        "folder": "financial_transactions"
    },
    {
        "name": "3. Bank Transaction Dataset - Device/Location/Error",
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

print("=" * 60)
print("  RecoverAI - Dataset Auto Downloader")
print("=" * 60)
print(f"\nDownload folder: {DOWNLOAD_DIR}\n")

success = 0
failed = 0

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
            timeout=600
        )

        if result.returncode == 0:
            files = os.listdir(target)
            print(f"         OK! Files: {files[:5]}")
            success += 1
        else:
            print(f"         FAILED: {result.stderr.strip()[:300]}")
            failed += 1

    except subprocess.TimeoutExpired:
        print(f"         TIMEOUT - dataset too large, manually download karo")
        failed += 1
    except Exception as e:
        print(f"         ERROR: {e}")
        failed += 1

    print()

print("=" * 60)
print(f"  Successful : {success}/{len(DATASETS)}")
print(f"  Failed     : {failed}/{len(DATASETS)}")
print(f"  Location   : {DOWNLOAD_DIR}")
print("=" * 60)

if success > 0:
    print("\nDatasets ready! Ab RecoverAI project shuru karo!")
