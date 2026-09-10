import csv
import io
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import AuditLog, DatasetVersion, Feedback, SMSMessage, User
from ..text_utils import detect_language

router = APIRouter(prefix="/api/admin/dataset", tags=["Dataset Management"])


class DatasetSampleOut(BaseModel):
    id: int
    sms_id: Optional[int] = None
    message: str
    sender_no: Optional[str] = None
    language: str
    expected_label: Optional[str] = None
    status: str
    review_note: Optional[str] = None
    duplicate_count: int = 1
    consent_confirmed: bool = True
    created_at: datetime


class ReviewSampleRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected|pending)$")
    review_note: Optional[str] = Field(default=None, max_length=255)


class CreateVersionRequest(BaseModel):
    version_tag: str = Field(min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_\-\.]+$")


class DatasetVersionOut(BaseModel):
    id: int
    version_tag: str
    sample_count: int
    file_path: str
    created_at: datetime


@router.get("/samples", response_model=List[DatasetSampleOut])
def list_dataset_samples(
    status: str = Query("all", description="Filter by status: pending, approved, rejected, all"),
    language: str = Query("all", description="Filter by language: Sinhala, Tamil, English, Singlish, all"),
    limit: int = Query(100, ge=1, le=500),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Feedback)
    if status.lower() != "all":
        query = query.filter(Feedback.status == status.lower())
    
    feedbacks = query.order_by(Feedback.created_at.desc()).limit(limit).all()
    results = []

    for fb in feedbacks:
        sms = db.query(SMSMessage).filter(SMSMessage.id == fb.sms_id).first() if fb.sms_id else None
        msg_text = sms.masked_text if sms else (fb.feedback_text or "")
        detected_lang = sms.language if sms else detect_language(msg_text)
        
        if language.lower() != "all" and detected_lang.lower() != language.lower():
            continue

        # Check duplicate count
        dup_count = 1
        if msg_text:
            dup_count = db.query(SMSMessage).filter(SMSMessage.masked_text == msg_text).count()

        results.append(
            DatasetSampleOut(
                id=fb.id,
                sms_id=fb.sms_id,
                message=msg_text,
                sender_no=sms.sender_no if sms else None,
                language=detected_lang,
                expected_label=fb.expected_label or "Unlabeled",
                status=fb.status or "pending",
                review_note=fb.review_note,
                duplicate_count=max(dup_count, 1),
                consent_confirmed=True,
                created_at=fb.created_at
            )
        )
    return results


@router.patch("/samples/{sample_id}", response_model=DatasetSampleOut)
def review_dataset_sample(
    sample_id: int,
    body: ReviewSampleRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    fb = db.query(Feedback).filter(Feedback.id == sample_id).first()
    if not fb:
        raise HTTPException(404, detail="Dataset sample not found")

    setattr(fb, "status", body.status.lower())
    if body.review_note is not None:
        setattr(fb, "review_note", body.review_note.strip())

    db.add(
        AuditLog(
            user_id=admin.id,
            action="DATASET_SAMPLE_REVIEWED",
            detail=f"sample_id={fb.id}; status={body.status}; note={body.review_note or ''}"
        )
    )
    db.commit()
    db.refresh(fb)

    sms = db.query(SMSMessage).filter(SMSMessage.id == fb.sms_id).first() if fb.sms_id else None
    msg_text = sms.masked_text if sms else (fb.feedback_text or "")

    return DatasetSampleOut(
        id=fb.id,
        sms_id=fb.sms_id,
        message=msg_text,
        sender_no=sms.sender_no if sms else None,
        language=sms.language if sms else detect_language(msg_text),
        expected_label=fb.expected_label or "Unlabeled",
        status=fb.status,
        review_note=fb.review_note,
        duplicate_count=1,
        consent_confirmed=True,
        created_at=fb.created_at
    )


@router.get("/duplicates")
def detect_duplicate_samples(
    min_count: int = Query(2, ge=2),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    duplicates = (
        db.query(SMSMessage.masked_text, func.count(SMSMessage.id).label("count"))
        .group_by(SMSMessage.masked_text)
        .having(func.count(SMSMessage.id) >= min_count)
        .order_by(func.count(SMSMessage.id).desc())
        .limit(50)
        .all()
    )
    return [{"message": text, "duplicate_count": count} for text, count in duplicates]


@router.get("/export-csv")
def export_approved_dataset_csv(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    approved_feedbacks = (
        db.query(Feedback)
        .filter(Feedback.status == "approved")
        .order_by(Feedback.created_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["sample_id", "sms_id", "message", "label", "language", "consent_confirmed", "reviewed_at"])

    for fb in approved_feedbacks:
        sms = db.query(SMSMessage).filter(SMSMessage.id == fb.sms_id).first() if fb.sms_id else None
        msg_text = sms.masked_text if sms else (fb.feedback_text or "")
        lang = sms.language if sms else detect_language(msg_text)
        writer.writerow([
            fb.id,
            fb.sms_id or "",
            msg_text,
            fb.expected_label or "Legitimate",
            lang,
            "true",
            fb.created_at.isoformat()
        ])

    csv_data = output.getvalue()
    filename = f"kriss_approved_dataset_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/versions", response_model=DatasetVersionOut, status_code=201)
def create_dataset_version(
    body: CreateVersionRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(DatasetVersion).filter(DatasetVersion.version_tag == body.version_tag).first()
    if existing:
        raise HTTPException(409, detail=f"Dataset version '{body.version_tag}' already exists")

    approved_feedbacks = db.query(Feedback).filter(Feedback.status == "approved").all()
    sample_count = len(approved_feedbacks)

    snapshots_dir = Path(__file__).resolve().parents[2] / "dataset" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshots_dir / f"dataset_{body.version_tag}.csv"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["sample_id", "sms_id", "message", "label", "language", "version", "created_at"])
    for fb in approved_feedbacks:
        sms = db.query(SMSMessage).filter(SMSMessage.id == fb.sms_id).first() if fb.sms_id else None
        msg = sms.masked_text if sms else (fb.feedback_text or "")
        lang = sms.language if sms else detect_language(msg)
        writer.writerow([fb.id, fb.sms_id or "", msg, fb.expected_label or "Legitimate", lang, body.version_tag, fb.created_at.isoformat()])

    snapshot_file.write_text(output.getvalue(), encoding="utf-8")

    version_record = DatasetVersion(
        version_tag=body.version_tag,
        sample_count=sample_count,
        file_path=str(snapshot_file.name),
        created_by_user_id=admin.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(version_record)
    db.add(
        AuditLog(
            user_id=admin.id,
            action="DATASET_VERSION_CREATED",
            detail=f"version={body.version_tag}; samples={sample_count}"
        )
    )
    db.commit()
    db.refresh(version_record)

    return DatasetVersionOut(
        id=version_record.id,
        version_tag=version_record.version_tag,
        sample_count=version_record.sample_count,
        file_path=version_record.file_path,
        created_at=version_record.created_at
    )


@router.get("/versions", response_model=List[DatasetVersionOut])
def list_dataset_versions(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    rows = db.query(DatasetVersion).order_by(DatasetVersion.created_at.desc()).all()
    return [
        DatasetVersionOut(
            id=r.id,
            version_tag=r.version_tag,
            sample_count=r.sample_count,
            file_path=r.file_path,
            created_at=r.created_at
        )
        for r in rows
    ]
