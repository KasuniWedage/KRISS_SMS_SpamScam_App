import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import AuditLog, BatchAnalysis, User
from ..schemas import BatchHistoryOut, BatchItemOut

router = APIRouter(prefix="/api/batch", tags=["Batch History"])

@router.get("/history", response_model=list[BatchHistoryOut])
def get_batch_history(
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(BatchAnalysis)
        .filter(BatchAnalysis.user_id == user.id)
        .order_by(BatchAnalysis.created_at.desc())
        .limit(limit)
        .all()
    )
    results = []
    for r in rows:
        try:
            items_raw = json.loads(r.items_json)
        except Exception:
            items_raw = []
        items_out = [
            BatchItemOut(
                sms_id=it.get("sms_id", 0),
                message=it.get("message", ""),
                label=it.get("label", "Legitimate"),
                confidence=float(it.get("confidence", 0.0)),
                language=it.get("language", "English"),
                scam_type=it.get("scam_type"),
                explanation=it.get("explanation", "")
            )
            for it in items_raw
        ]
        results.append(BatchHistoryOut(
            id=r.id,
            batch_id=r.batch_id,
            total_count=r.total_count,
            safe_count=r.safe_count,
            spam_count=r.spam_count,
            scam_count=r.scam_count,
            report_language=r.report_language,
            items=items_out,
            created_at=r.created_at
        ))
    return results

@router.delete("/history/{batch_id}")
def delete_batch(
    batch_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record = (
        db.query(BatchAnalysis)
        .filter(
            (BatchAnalysis.batch_id == batch_id) | (BatchAnalysis.id == int(batch_id) if batch_id.isdigit() else False),
            BatchAnalysis.user_id == user.id
        )
        .first()
    )
    if not record:
        raise HTTPException(404, detail="Batch record not found")
    
    db.delete(record)
    db.add(AuditLog(user_id=user.id, action="BATCH_DELETED", detail=f"batch_id={batch_id}"))
    db.commit()
    return {"message": "Batch record permanently deleted"}

@router.delete("/history")
def clear_all_batches(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = db.query(BatchAnalysis).filter(BatchAnalysis.user_id == user.id).all()
    count = len(records)
    if count > 0:
        for r in records:
            db.delete(r)
        db.add(AuditLog(user_id=user.id, action="BATCH_HISTORY_CLEARED", detail=f"count={count}"))
        db.commit()
    return {"message": f"Successfully deleted {count} batch records", "deleted_count": count}
