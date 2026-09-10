from datetime import datetime
from pathlib import Path
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..auth import require_admin
from ..database import get_db
from ..models import AuditLog, ClassificationResult, Report, SMSMessage, SystemError, User
from ..observability import performance_summary, verify_audit_chain
from ..config import settings

router = APIRouter(prefix="/api/admin", tags=["Administration"])

@router.get("/metrics")
def metrics(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    label_counts = {
        cls: count
        for cls, count in db.query(ClassificationResult.predicted_class, func.count(ClassificationResult.id))
        .group_by(ClassificationResult.predicted_class)
        .all()
    }
    return {
        "users": db.query(User).count(),
        "messages": db.query(SMSMessage).count(),
        "reports": db.query(Report).count(),
        "classifications": label_counts,
    }

@router.get("/reports")
def reports(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Report).order_by(Report.report_date.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "sms_id": r.sms_id,
            "user_id": r.user_id,
            "reason": r.reason,
            "date": r.report_date
        }
        for r in rows
    ]

@router.get("/performance")
def performance(hours: int = 24, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    safe_hours = min(max(hours, 1), 24 * 90)
    return performance_summary(db, safe_hours)

@router.get("/errors")
def errors(limit: int = 100, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    safe_limit = min(max(limit, 1), 500)
    rows = db.query(SystemError).order_by(SystemError.created_at.desc()).limit(safe_limit).all()
    return [
        {
            "id": row.id,
            "request_id": row.request_id,
            "method": row.method,
            "path": row.path,
            "error_type": row.error_type,
            "message": row.message,
            "created_at": row.created_at,
        }
        for row in rows
    ]

@router.delete("/errors")
def clear_errors(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    count = db.query(SystemError).delete()
    db.add(AuditLog(user_id=admin.id, action="SYSTEM_ERRORS_CLEARED", detail=f"cleared={count}"))
    db.commit()
    return {"message": f"Successfully cleared {count} error log entries", "deleted_count": count}

@router.get("/audit-integrity")
def audit_integrity(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return verify_audit_chain(db)

@router.get("/users")
def list_users(limit: int = 100, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.id.desc()).limit(limit).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "language_preference": u.language_preference,
            "notifications_enabled": u.notifications_enabled,
            "auth_provider": u.auth_provider,
            "created_at": u.created_at
        }
        for u in rows
    ]

@router.patch("/users/{user_id}/role")
def update_user_role(user_id: int, role: str = Query(..., pattern="^(admin|user)$"), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, detail="User not found")
    if target.id == admin.id and role != "admin":
        raise HTTPException(400, detail="Cannot demote your own admin account")
    setattr(target, "role", role)
    db.add(AuditLog(user_id=admin.id, action="USER_ROLE_UPDATED", detail=f"target_user={target.username}; new_role={role}"))
    db.commit()
    return {"message": f"User {target.username} role updated to {role}", "role": role}

@router.get("/backups")
def list_backups(admin: User = Depends(require_admin)):
    backups_dir = Path(__file__).resolve().parents[2] / "backups"
    if not backups_dir.exists():
        return []
    files = sorted(
        list(backups_dir.glob("kriss-*.sqlite3")) + list(backups_dir.glob("kriss-*.sql")),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    result = []
    for f in files:
        stat = f.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        result.append({
            "filename": f.name,
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024.0, 1),
            "created_at": mtime
        })
    return result

@router.post("/backup/create")
def trigger_backup(admin: User = Depends(require_admin)):
    try:
        from ...scripts.database_backup import create_backup
    except Exception:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from scripts.database_backup import create_backup

    output_dir = Path(__file__).resolve().parents[2] / "backups"
    backup_file = create_backup(settings.database_url, output_dir)
    return {
        "status": "SUCCESS",
        "backup_file": backup_file.name,
        "size_bytes": backup_file.stat().st_size
    }

@router.post("/backup/restore-test")
def trigger_restore_test(filename: str | None = Query(None), admin: User = Depends(require_admin)):
    try:
        from ...scripts.restore_backup import restore_and_test
    except Exception:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from scripts.restore_backup import restore_and_test

    backups_dir = Path(__file__).resolve().parents[2] / "backups"
    if filename:
        target = backups_dir / Path(filename).name
    else:
        backups = sorted(
            list(backups_dir.glob("kriss-*.sqlite3")) + list(backups_dir.glob("kriss-*.sql")),
            key=lambda p: p.stat().st_mtime
        )
        if not backups:
            raise HTTPException(404, detail="No backups available to test")
        target = backups[-1]

    if not target.exists():
        raise HTTPException(404, detail=f"Backup file '{target.name}' not found")

    report = restore_and_test(target)
    report["valid"] = bool(report.get("restoration_status") == "SUCCESS" and report.get("smoke_tests_passed"))
    report["filename"] = target.name
    return report

@router.post("/backup/restore-live")
def trigger_restore_live(filename: str = Query(...), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    backups_dir = Path(__file__).resolve().parents[2] / "backups"
    target = backups_dir / Path(filename).name
    if not target.exists() or not target.is_file():
        raise HTTPException(404, detail=f"Backup file '{filename}' not found")

    raw_db = settings.database_url.removeprefix("sqlite:///")
    live_db_path = Path(raw_db).resolve()

    if target.suffix == ".sqlite3":
        with sqlite3.connect(target) as src_chk:
            integrity = src_chk.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise HTTPException(400, detail=f"Backup corrupted: {integrity}")

        db.close()
        with sqlite3.connect(target) as src, sqlite3.connect(live_db_path) as dst:
            src.backup(dst)

        db.add(AuditLog(user_id=admin.id, action="DATABASE_RESTORED_LIVE", detail=f"source_backup={target.name}"))
        db.commit()

        return {
            "status": "SUCCESS",
            "message": f"Successfully restored database from {target.name}",
            "filename": target.name
        }
    else:
        raise HTTPException(400, detail="Live restoration only supported for SQLite backup files")

@router.get("/uptime")
def uptime_summary(admin: User = Depends(require_admin)):
    try:
        from ...scripts.generate_uptime_report import generate_uptime_report
    except Exception:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from scripts.generate_uptime_report import generate_uptime_report

    log_path = Path(__file__).resolve().parents[2] / "uptime.jsonl"
    return generate_uptime_report(log_path)
