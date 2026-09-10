from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from .hybrid_rules import evaluate_rules
from .ml_service import ml_service
from .models import AuditLog, ClassificationResult, Feedback, PublishedSpam, Report, SMSMessage, User
from .text_utils import anonymize_text, detect_language

STATUS_CODES = {"Legitimate": 1, "Spam": 2, "Scam": 3}

def auto_prune_history(db: Session, user_id: int, max_limit: int = 100):
    """
    1. Checks if 30-day auto-delete is enabled in user settings and deletes records older than 30 days.
    2. Enforces a maximum of `max_limit` (100) messages per user.
       If total messages exceed 100, automatically deletes the oldest unprotected messages,
       EXCEPT messages with Feedback, Reports, or Published to Community.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.auto_delete_history:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        old_messages = db.query(SMSMessage).filter(
            SMSMessage.user_id == user_id,
            SMSMessage.received_date < cutoff
        ).all()
        if old_messages:
            for sms in old_messages:
                db.delete(sms)
            db.add(AuditLog(
                user_id=user_id,
                action="HISTORY_AUTO_DELETED",
                detail=f"records={len(old_messages)}; retention_days=30"
            ))
            db.commit()
    total_count = db.query(SMSMessage).filter(SMSMessage.user_id == user_id).count()
    if total_count <= max_limit:
        return

    excess = total_count - max_limit

    has_feedback = db.query(Feedback.id).filter(Feedback.sms_id == SMSMessage.id).exists()
    has_report = db.query(Report.id).filter(Report.sms_id == SMSMessage.id).exists()
    has_published = db.query(PublishedSpam.id).filter(PublishedSpam.sms_id == SMSMessage.id).exists()

    unprotected_messages = (
        db.query(SMSMessage)
        .filter(
            SMSMessage.user_id == user_id,
            ~has_feedback,
            ~has_report,
            ~has_published
        )
        .order_by(SMSMessage.received_date.asc())
        .limit(excess)
        .all()
    )

    if unprotected_messages:
        ids = [sms.id for sms in unprotected_messages]
        db.query(SMSMessage).filter(SMSMessage.id.in_(ids)).delete(synchronize_session=False)
        db.add(AuditLog(
            user_id=user_id,
            action="HISTORY_AUTO_PRUNED",
            detail=f"pruned={len(ids)}; max_limit={max_limit}; protected_preserved=true"
        ))
        db.commit()

def build_explanation(label: str, rule, ml_label: str, ml_conf: float) -> str:
    if rule.override:
        reason = "; ".join(rule.reasons)
        return f"High-risk scam rules were triggered. {reason}. ML prediction was {ml_label} ({ml_conf*100:.1f}%)."
    if label == "Spam":
        return "The ML model found patterns commonly associated with unsolicited promotional or bulk messages. No high-risk scam override was triggered."
    if label == "Scam":
        return "The ML model found patterns associated with deceptive or fraudulent SMS content. Treat links, payment requests, and credential requests with caution."
    return "No high-risk scam rule was triggered and the ML model identified the message as legitimate."

def classify_and_store(db: Session, user_id: int, message: str, sender_no: str | None = None):
    language = detect_language(message)
    rule = evaluate_rules(message)
    ml_label, ml_conf, dist = ml_service.predict(message)
    final_label = "Scam" if rule.override else ml_label
    confidence = max(rule.confidence, dist.get("Scam", 0.0)) if rule.override else ml_conf
    explanation = build_explanation(final_label, rule, ml_label, ml_conf)
    sms = SMSMessage(user_id=user_id, sender_no=anonymize_text(sender_no) if sender_no else None, masked_text=anonymize_text(message), language=language)
    db.add(sms); db.flush()
    result = ClassificationResult(
        sms_id=sms.id, predicted_class=final_label, confidence_score=round(confidence*100, 2),
        scam_type=rule.scam_type if rule.override else ("ML-detected scam" if final_label=="Scam" else None),
        explanation=explanation, model_version=str(ml_service.metadata.get("model_version", "colab-model"))
    )
    db.add(result)
    db.add(AuditLog(user_id=user_id, action="SMS_CLASSIFIED", detail=f"sms_id={sms.id}; label={final_label}"))
    db.commit(); db.refresh(sms)
    auto_prune_history(db, user_id, max_limit=100)
    return {
        "sms_id": sms.id, "label": final_label, "status_code": STATUS_CODES.get(final_label, 0),
        "confidence": round(confidence*100, 2), "language": language, "scam_type": result.scam_type,
        "explanation": explanation, "rule_override": rule.override,
        "class_probabilities": {k: round(v*100, 2) for k,v in dist.items()}
    }
