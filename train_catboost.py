"""
RecoverAI — CatBoost Model Training
=====================================
Dataset: recoverai_training.csv   (300,000 rows)
Validation: recoverai_validation.csv (60,000 rows)
Target: recovered_within_72h (0/1)
"""

import sys
import os
import time
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

# ── Install CatBoost if needed ─────────────────────────────────────
try:
    from catboost import CatBoostClassifier, Pool
    print("CatBoost already installed!")
except ImportError:
    print("Installing CatBoost...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "catboost", "-q"], check=True)
    from catboost import CatBoostClassifier, Pool
    print("CatBoost installed!")

try:
    from sklearn.metrics import (
        accuracy_score, roc_auc_score, f1_score,
        precision_score, recall_score, classification_report,
        confusion_matrix
    )
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "scikit-learn", "-q"], check=True)
    from sklearn.metrics import (
        accuracy_score, roc_auc_score, f1_score,
        precision_score, recall_score, classification_report,
        confusion_matrix
    )

BASE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
os.makedirs(MODEL_DIR, exist_ok=True)

print("\n" + "="*65)
print("  RecoverAI — CatBoost Model Training")
print("="*65)

# ─────────────────────────────────────────────────────────────────
# STEP 1: Load Data
# ─────────────────────────────────────────────────────────────────
print("\n[1/6] Loading datasets...")
train_df = pd.read_csv(os.path.join(BASE, "recoverai_training.csv"))
val_df   = pd.read_csv(os.path.join(BASE, "recoverai_validation.csv"))
print(f"  Train : {train_df.shape[0]:,} rows x {train_df.shape[1]} cols")
print(f"  Val   : {val_df.shape[0]:,} rows x {val_df.shape[1]} cols")
print(f"  Target distribution (train):")
print(f"    recovered=1 : {train_df['recovered_within_72h'].sum():,} ({train_df['recovered_within_72h'].mean()*100:.1f}%)")
print(f"    recovered=0 : {(train_df['recovered_within_72h']==0).sum():,} ({(1-train_df['recovered_within_72h'].mean())*100:.1f}%)")

# ─────────────────────────────────────────────────────────────────
# STEP 2: Feature Selection
# ─────────────────────────────────────────────────────────────────
print("\n[2/6] Selecting features...")

# Drop ID columns and target
DROP_COLS = ["transaction_id", "customer_id", "merchant_id", "timestamp", "recovered_within_72h"]
TARGET    = "recovered_within_72h"

FEATURES = [c for c in train_df.columns if c not in DROP_COLS]

# Identify categorical columns (CatBoost handles them natively!)
CAT_FEATURES = [
    "payment_method", "bank", "card_type", "merchant_category",
    "error_reason", "customer_segment", "region",
    "device_type", "channel", "amount_bucket", "treatment_action"
]

print(f"  Total features    : {len(FEATURES)}")
print(f"  Numeric features  : {len(FEATURES) - len(CAT_FEATURES)}")
print(f"  Categorical feats : {len(CAT_FEATURES)} (CatBoost handles natively)")
print(f"  Cat columns: {CAT_FEATURES}")

X_train = train_df[FEATURES]
y_train = train_df[TARGET]
X_val   = val_df[FEATURES]
y_val   = val_df[TARGET]

# ─────────────────────────────────────────────────────────────────
# STEP 3: CatBoost Pools
# ─────────────────────────────────────────────────────────────────
print("\n[3/6] Creating CatBoost Pools...")

train_pool = Pool(
    data=X_train,
    label=y_train,
    cat_features=CAT_FEATURES
)
val_pool = Pool(
    data=X_val,
    label=y_val,
    cat_features=CAT_FEATURES
)
print("  Pools created!")

# ─────────────────────────────────────────────────────────────────
# STEP 4: Define & Train Model
# ─────────────────────────────────────────────────────────────────
print("\n[4/6] Training CatBoost model...")
print("  (This may take 2-4 minutes for 300K rows)")

model = CatBoostClassifier(
    iterations          = 500,
    learning_rate       = 0.05,
    depth               = 7,
    l2_leaf_reg         = 3,
    loss_function       = "Logloss",
    eval_metric         = "AUC",
    random_seed         = 42,
    early_stopping_rounds = 50,
    verbose             = 50,        # print every 50 iterations
    task_type           = "CPU",
    thread_count        = -1,        # use all CPU cores
)

start = time.time()
model.fit(
    train_pool,
    eval_set    = val_pool,
    use_best_model = True,
)
elapsed = time.time() - start
print(f"\n  Training done in {elapsed:.1f} seconds!")
print(f"  Best iteration: {model.best_iteration_}")

# ─────────────────────────────────────────────────────────────────
# STEP 5: Evaluate
# ─────────────────────────────────────────────────────────────────
print("\n[5/6] Evaluating model...")

y_pred_proba = model.predict_proba(val_pool)[:, 1]
y_pred       = (y_pred_proba >= 0.5).astype(int)

acc       = accuracy_score(y_val, y_pred)
auc       = roc_auc_score(y_val, y_pred_proba)
f1        = f1_score(y_val, y_pred)
precision = precision_score(y_val, y_pred)
recall    = recall_score(y_val, y_pred)

print("\n" + "="*65)
print("  MODEL EVALUATION RESULTS")
print("="*65)
print(f"  Accuracy  : {acc*100:.2f}%")
print(f"  AUC-ROC   : {auc:.4f}")
print(f"  F1 Score  : {f1:.4f}")
print(f"  Precision : {precision:.4f}")
print(f"  Recall    : {recall:.4f}")
print("="*65)

print("\n  Classification Report:")
print(classification_report(y_val, y_pred, target_names=["Not Recovered", "Recovered"]))

print("  Confusion Matrix:")
cm = confusion_matrix(y_val, y_pred)
print(f"              Predicted")
print(f"              Not-Rec  Rec")
print(f"  Actual Not-Rec  {cm[0][0]:>6}  {cm[0][1]:>6}")
print(f"  Actual Rec      {cm[1][0]:>6}  {cm[1][1]:>6}")

# ─────────────────────────────────────────────────────────────────
# STEP 6: Feature Importance + Save Model
# ─────────────────────────────────────────────────────────────────
print("\n[6/6] Feature importance & saving model...")

importance = model.get_feature_importance()
feat_imp_df = pd.DataFrame({
    "feature":    FEATURES,
    "importance": importance
}).sort_values("importance", ascending=False)

print("\n  Top 15 Most Important Features:")
print(f"  {'Rank':<5} {'Feature':<35} {'Importance':>10}")
print(f"  {'-'*55}")
for i, row in feat_imp_df.head(15).iterrows():
    print(f"  {feat_imp_df.index.get_loc(i)+1:<5} {row['feature']:<35} {row['importance']:>10.2f}")

# Save model
model_path = os.path.join(MODEL_DIR, "recoverai_catboost.cbm")
model.save_model(model_path)

# Save feature importance
fi_path = os.path.join(MODEL_DIR, "feature_importance.csv")
feat_imp_df.to_csv(fi_path, index=False)

# Save metrics summary
metrics = {
    "accuracy":   round(acc, 4),
    "auc_roc":    round(auc, 4),
    "f1_score":   round(f1, 4),
    "precision":  round(precision, 4),
    "recall":     round(recall, 4),
    "best_iter":  model.best_iteration_,
    "train_rows": len(train_df),
    "val_rows":   len(val_df),
    "features":   len(FEATURES),
}
import json
metrics_path = os.path.join(MODEL_DIR, "metrics.json")
with open(metrics_path, "w") as f:
    json.dump(metrics, f, indent=2)

print(f"\n  Model saved    : {model_path}")
print(f"  Features saved : {fi_path}")
print(f"  Metrics saved  : {metrics_path}")

print("\n" + "="*65)
print("  RecoverAI CatBoost Model COMPLETE!")
print(f"  AUC-ROC = {auc:.4f}  |  Accuracy = {acc*100:.2f}%  |  F1 = {f1:.4f}")
print("="*65)
