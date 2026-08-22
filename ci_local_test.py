from catboost import CatBoostClassifier
import json, os, sys

print("="*55)
print("  STEP 1: Verify pre-trained CatBoost model")
print("="*55)
model_path = 'model/recoverai_catboost.cbm'
assert os.path.exists(model_path), f'Model not found: {model_path}'
model = CatBoostClassifier()
model.load_model(model_path)
print(f'  Model loaded OK!')
print(f'  Tree count : {model.tree_count_}')
print(f'  Features   : {len(model.feature_names_)}')

with open('model/metrics.json') as f:
    m = json.load(f)
print(f'  AUC-ROC    : {m["auc_roc"]}')
print(f'  Accuracy   : {m["accuracy"]}')
print(f'  F1 Score   : {m["f1_score"]}')
print()

print("="*55)
print("  STEP 2: Verify backend modules")
print("="*55)
sys.path.insert(0, 'backend')
from models import PaymentEvent, RecoveryDecision
from guardrails import check_guardrails, summarize_guardrails
from policy import get_best_action, is_model_loaded
print(f'  All modules imported OK!')
print(f'  Model loaded : {is_model_loaded()}')
g = summarize_guardrails()
print(f'  Guardrail rules : {len(g["rules"])}')
print()

print("="*55)
print("  STEP 3: End-to-end inference test")
print("="*55)
event = PaymentEvent(
    transaction_id='TXN-CI-TEST-001',
    amount=1499.0,
    payment_method='upi',
    bank='HDFC',
    error_reason='insufficient_funds',
    customer_id='CUST-CI-001',
    customer_segment='premium',
    opt_out_notification=False,
    device_type='mobile',
    channel='app',
    region='South',
    customer_age=28,
    account_balance=500.0,
    customer_tenure_months=36,
    previous_failed_attempts=1,
    retry_count=0,
    risk_score=22.0,
    merchant_category='ecommerce',
    card_type='NA',
    hour_of_day=15,
    day_of_week=3,
    is_weekend=0,
    time_since_last_failure_hr=3.0,
    transaction_frequency_30d=8,
    recovery_attempt_count=0,
    notification_sent=0,
)
triggered, action, reason = check_guardrails(event)
print(f'  Guardrails triggered : {triggered}')
rec_action, prob, scores = get_best_action(event)
print(f'  Recommended action   : {rec_action}')
print(f'  Recovery probability : {prob:.4f}')
print()
print("="*55)
print("  ALL CHECKS PASSED! CI will succeed on GitHub.")
print("="*55)
