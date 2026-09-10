import json
import time
from datetime import datetime
from typing import cast
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..ml_service import ml_service
from ..models import BatchAnalysis, User
from ..rate_limit import check_rate_limit
from ..schemas import BatchRequest, ClassificationRequest, ClassificationResponse
from ..services import classify_and_store

router = APIRouter(prefix="/api", tags=["SMS Classification"])

@router.post("/classify", response_model=ClassificationResponse)
def classify(body: ClassificationRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_rate_limit(f"classify:{user.id}", 60, 60)
    if not body.message.strip():
        raise HTTPException(400, detail="SMS must not be empty")
    if not ml_service.ready:
        raise HTTPException(503, detail="ML model unavailable. Train/export the Colab model first.")
    return classify_and_store(db, cast(int, user.id), body.message.strip(), body.sender_no)

@router.post("/classify/batch", response_model=list[ClassificationResponse])
def classify_batch(body: BatchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_rate_limit(f"batch:{user.id}", 10, 60)
    if not ml_service.ready:
        raise HTTPException(503, detail="ML model unavailable")
    
    uid = cast(int, user.id)
    results = [classify_and_store(db, uid, item.message.strip(), item.sender_no) for item in body.messages]
    
    # Persist batch record into database
    batch_id = f"batch_{int(time.time() * 1000)}"
    items_data = [
        {
            "sms_id": r["sms_id"],
            "message": body.messages[idx].message.strip(),
            "label": r["label"],
            "confidence": r["confidence"],
            "language": r["language"],
            "scam_type": r.get("scam_type"),
            "explanation": r["explanation"],
        }
        for idx, r in enumerate(results)
    ]
    safe_cnt = sum(1 for r in results if r["label"].lower() in ("safe", "legitimate"))
    spam_cnt = sum(1 for r in results if r["label"].lower() == "spam")
    scam_cnt = sum(1 for r in results if r["label"].lower() == "scam")

    batch_record = BatchAnalysis(
        batch_id=batch_id,
        user_id=user.id,
        total_count=len(results),
        safe_count=safe_cnt,
        spam_count=spam_cnt,
        scam_count=scam_cnt,
        report_language="en",
        items_json=json.dumps(items_data, ensure_ascii=False),
        created_at=datetime.utcnow()
    )
    db.add(batch_record)
    db.commit()

    return results
