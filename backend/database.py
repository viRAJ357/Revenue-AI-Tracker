import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Use environment variable for database URL, fallback to sqlite for local dev if not provided
# Docker compose provides postgresql://admin:password@db/recoverai
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./recoverai_audit.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class RecoveryEvent(Base):
    __tablename__ = "recovery_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    timestamp = Column(String, nullable=False)

    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)
    bank = Column(String, nullable=False)
    error_reason = Column(String, nullable=False)
    customer_segment = Column(String, nullable=False)
    opt_out_notification = Column(Boolean, default=False)
    device_type = Column(String)
    channel = Column(String)
    region = Column(String)
    customer_age = Column(Integer)
    account_balance = Column(Float)
    customer_tenure_months = Column(Integer)
    previous_failed_attempts = Column(Integer)
    retry_count = Column(Integer)
    risk_score = Column(Float)
    merchant_category = Column(String)
    card_type = Column(String)
    hour_of_day = Column(Integer)
    day_of_week = Column(Integer)
    is_weekend = Column(Boolean)
    time_since_last_failure_hr = Column(Float)
    transaction_frequency_30d = Column(Integer)
    recovery_attempt_count = Column(Integer)
    notification_sent = Column(Boolean, default=False)

    recommended_action = Column(String, nullable=False)
    recovery_probability = Column(Float, nullable=False)
    guardrail_triggered = Column(Boolean, default=False)
    guardrail_reason = Column(String)
    all_action_scores = Column(Text, default="{}")

    operator_decision = Column(String)
    operator_notes = Column(Text)
    reviewed_at = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized with SQLAlchemy.")
    
    # Create default admin user if none exists
    db = SessionLocal()
    try:
        from auth import get_password_hash
        
        if not db.query(User).filter(User.username == "admin").first():
            hashed_pw = get_password_hash("admin")
            admin_user = User(username="admin", hashed_password=hashed_pw)
            db.add(admin_user)
            db.commit()
            logger.info("Created default admin user.")
    except Exception as e:
        logger.error(f"Failed to create default user: {e}")
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def insert_record(record: Dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        rec_copy = dict(record)
        if isinstance(rec_copy.get("all_action_scores"), dict):
            rec_copy["all_action_scores"] = json.dumps(rec_copy["all_action_scores"])
            
        for key, val in rec_copy.items():
            if isinstance(val, datetime):
                rec_copy[key] = val.isoformat()

        db_event = RecoveryEvent(**rec_copy)
        db.add(db_event)
        db.commit()
    except Exception as e:
        logger.error(f"Error inserting record: {e}")
        db.rollback()
    finally:
        db.close()

def update_operator_decision(transaction_id: str, operator_decision: str, operator_notes: Optional[str] = None) -> bool:
    db = SessionLocal()
    try:
        event = db.query(RecoveryEvent).filter(RecoveryEvent.transaction_id == transaction_id).first()
        if event:
            event.operator_decision = operator_decision
            event.operator_notes = operator_notes
            event.reviewed_at = datetime.utcnow().isoformat()
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_all_records(limit: int = 100) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        events = db.query(RecoveryEvent).order_by(RecoveryEvent.timestamp.desc()).limit(limit).all()
        results = []
        for e in events:
            d = {c.name: getattr(e, c.name) for c in e.__table__.columns}
            try:
                d["all_action_scores"] = json.loads(d.get("all_action_scores") or "{}")
            except:
                d["all_action_scores"] = {}
            results.append(d)
        return results
    finally:
        db.close()

def get_stats() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        from sqlalchemy import func
        total = db.query(func.count(RecoveryEvent.id)).scalar()
        if total == 0:
            return {
                "total_events": 0, "recovery_rate": 0.0, "action_distribution": {},
                "error_distribution": {}, "avg_recovery_prob": 0.0, "avg_risk_score": 0.0,
                "guardrail_rate": 0.0, "pending_review": 0
            }

        avg_prob = db.query(func.avg(RecoveryEvent.recovery_probability)).scalar() or 0.0
        avg_risk = db.query(func.avg(RecoveryEvent.risk_score)).scalar() or 0.0
        guardrail_count = db.query(func.count(RecoveryEvent.id)).filter(RecoveryEvent.guardrail_triggered == True).scalar()
        
        action_counts = db.query(RecoveryEvent.recommended_action, func.count(RecoveryEvent.id)).group_by(RecoveryEvent.recommended_action).all()
        action_dist = {a: c for a, c in action_counts}
        
        human_review_count = action_dist.get("human_review", 0)
        recovery_rate = (total - human_review_count) / total
        
        error_counts = db.query(RecoveryEvent.error_reason, func.count(RecoveryEvent.id)).group_by(RecoveryEvent.error_reason).order_by(func.count(RecoveryEvent.id).desc()).limit(10).all()
        error_dist = {e: c for e, c in error_counts}
        
        pending = db.query(func.count(RecoveryEvent.id)).filter(RecoveryEvent.recommended_action == 'human_review', RecoveryEvent.operator_decision == None).scalar()

        return {
            "total_events": total,
            "recovery_rate": round(recovery_rate, 4),
            "action_distribution": action_dist,
            "error_distribution": error_dist,
            "avg_recovery_prob": round(avg_prob, 4),
            "avg_risk_score": round(avg_risk, 1),
            "guardrail_rate": round(guardrail_count / total, 4),
            "pending_review": pending,
        }
    finally:
        db.close()
