import csv, io
from datetime import datetime, timedelta, timezone
from typing import cast
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..models import AuditLog, ClassificationResult, SMSMessage, User
from ..schemas import HistoryItem
from ..services import auto_prune_history

router = APIRouter(prefix="/api/history", tags=["History"])

def to_item(sms, result):
    return HistoryItem(sms_id=sms.id, message=sms.masked_text, language=sms.language, label=result.predicted_class,
                       confidence=result.confidence_score, scam_type=result.scam_type, explanation=result.explanation,
                       created_at=result.created_at)

@router.get("", response_model=list[HistoryItem])
def history(q: str | None = Query(None), limit: int = Query(100, ge=1, le=200), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auto_prune_history(db, cast(int, user.id), max_limit=100)
    if user.auto_delete_history:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        old=db.query(SMSMessage).filter(SMSMessage.user_id==user.id,SMSMessage.received_date<cutoff).all()
        if old:
            for sms in old: db.delete(sms)
            db.add(AuditLog(user_id=user.id,action="HISTORY_AUTO_DELETED",detail=f"records={len(old)}; retention_days=30"));db.commit()
    query = db.query(SMSMessage, ClassificationResult).join(ClassificationResult).filter(SMSMessage.user_id == user.id)
    if q:
        query = query.filter(SMSMessage.masked_text.ilike(f"%{q}%"))
    rows = query.order_by(SMSMessage.received_date.desc()).limit(limit).all()
    return [to_item(s,r) for s,r in rows]

@router.delete("/{sms_id}")
def delete_history(sms_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sms = db.query(SMSMessage).filter(SMSMessage.id == sms_id, SMSMessage.user_id == user.id).first()
    if not sms:
        raise HTTPException(404, detail="SMS record not found")
    db.delete(sms); db.add(AuditLog(user_id=user.id, action="SMS_DELETED", detail=f"sms_id={sms_id}")); db.commit()
    return {"message":"SMS record permanently deleted"}

@router.delete("")
def delete_bulk_history(category: str | None = Query(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SMSMessage).filter(SMSMessage.user_id == user.id)
    if category and category.lower() not in ("all", ""):
        cat_map = {"spam": "Spam", "scam": "Scam", "legitimate": "Legitimate", "legit": "Legitimate"}
        norm_cat = cat_map.get(category.lower(), category.capitalize())
        query = query.join(ClassificationResult).filter(ClassificationResult.predicted_class == norm_cat)
    records = query.all()
    count = len(records)
    if count > 0:
        for sms in records:
            db.delete(sms)
        db.add(AuditLog(user_id=user.id, action="BULK_HISTORY_DELETED", detail=f"category={category or 'all'}; count={count}"))
        db.commit()
    return {"message": f"Successfully deleted {count} records", "deleted_count": count}

@router.get("/export.csv")
def export_csv(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(SMSMessage, ClassificationResult).join(ClassificationResult).filter(SMSMessage.user_id == user.id).order_by(SMSMessage.received_date.desc()).all()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["sms_id","message","language","label","confidence","scam_type","date"])
    for s,r in rows: w.writerow([s.id,s.masked_text,s.language,r.predicted_class,r.confidence_score,r.scam_type or "",r.created_at.isoformat()])
    return Response(content=out.getvalue(), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=kriss_sms_history.csv"})
