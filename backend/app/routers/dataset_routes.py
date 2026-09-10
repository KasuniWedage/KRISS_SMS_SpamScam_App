import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import AuditLog, TrainingSample, User
from ..schemas import TrainingSampleCreate, TrainingSampleReview
from ..text_utils import anonymize_text


router = APIRouter(prefix="/api/admin/dataset", tags=["Dataset Management"])
LABELS = {"Legitimate", "Spam", "Scam"}
LANGUAGES = {"English", "Sinhala", "Singlish", "Tamil"}
SOURCE_TYPES = {"public", "licensed", "consented", "synthetic"}
REVIEW_STATES = {"pending", "approved", "rejected"}


def validate_governance(body: TrainingSampleCreate) -> None:
    if body.label not in LABELS:
        raise HTTPException(400, detail="label must be Legitimate, Spam, or Scam")
    if body.language not in LANGUAGES:
        raise HTTPException(400, detail="unsupported language")
    if body.source_type not in SOURCE_TYPES:
        raise HTTPException(400, detail="unsupported source_type")
    if body.source_type == "consented" and not body.consent_reference:
        raise HTTPException(400, detail="consent_reference is required for consented data")
    if body.source_type == "licensed" and not body.license_name:
        raise HTTPException(400, detail="license_name is required for licensed data")


@router.post("/samples", status_code=201)
def create_sample(body: TrainingSampleCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    validate_governance(body)
    sample = TrainingSample(
        masked_text=anonymize_text(body.message.strip()),
        label=body.label,
        language=body.language,
        category=body.category,
        source_type=body.source_type,
        source_reference=body.source_reference.strip(),
        consent_reference=body.consent_reference,
        license_name=body.license_name,
    )
    db.add(sample)
    db.flush()
    db.add(AuditLog(user_id=admin.id, action="DATASET_SAMPLE_CREATED", detail=f"sample_id={sample.id}; source={sample.source_type}"))
    db.commit()
    return {"id": sample.id, "status": sample.review_status}


@router.get("/samples")
def list_samples(status: str | None = None, language: str | None = None, limit: int = Query(100, ge=1, le=500), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(TrainingSample)
    if status:
        query = query.filter(TrainingSample.review_status == status)
    if language:
        query = query.filter(TrainingSample.language == language)
    rows = query.order_by(TrainingSample.created_at.desc()).limit(limit).all()
    return [{
        "id": row.id, "message": row.masked_text, "label": row.label, "language": row.language,
        "category": row.category, "source_type": row.source_type, "source_reference": row.source_reference,
        "consent_reference": row.consent_reference, "license_name": row.license_name,
        "review_status": row.review_status, "reviewer_id": row.reviewer_id,
        "created_at": row.created_at, "reviewed_at": row.reviewed_at,
    } for row in rows]


@router.patch("/samples/{sample_id}/review")
def review_sample(sample_id: int, body: TrainingSampleReview, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if body.status not in REVIEW_STATES - {"pending"}:
        raise HTTPException(400, detail="status must be approved or rejected")
    sample = db.query(TrainingSample).filter(TrainingSample.id == sample_id).first()
    if not sample:
        raise HTTPException(404, detail="training sample not found")
    sample.review_status = body.status
    sample.reviewer_id = admin.id
    sample.reviewed_at = datetime.utcnow()
    db.add(AuditLog(user_id=admin.id, action="DATASET_SAMPLE_REVIEWED", detail=f"sample_id={sample.id}; status={body.status}"))
    db.commit()
    return {"id": sample.id, "status": sample.review_status}


@router.get("/export.csv")
def export_approved(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(TrainingSample).filter(TrainingSample.review_status == "approved").order_by(TrainingSample.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "message", "label", "language", "category", "source_type", "source_reference", "consent_reference", "license_name"])
    for row in rows:
        writer.writerow([row.id, row.masked_text, row.label, row.language, row.category or "", row.source_type, row.source_reference, row.consent_reference or "", row.license_name or ""])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=kriss-approved-training-data.csv"})
