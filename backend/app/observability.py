import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Request
from sqlalchemy import event, func
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from .database import SessionLocal
from .models import ApiPerformanceMetric, AuditLog, AuditSeal, SystemError


logger = logging.getLogger("kriss.observability")
GENESIS_HASH = "0" * 64


def _audit_payload(target: AuditLog, previous_hash: str) -> bytes:
    created = target.created_at.isoformat(timespec="microseconds") if target.created_at else ""
    detail = target.detail or ""
    return f"{target.id}|{target.action}|{detail}|{created}|{previous_hash}".encode("utf-8")


@event.listens_for(AuditLog, "after_insert")
def create_audit_seal(_mapper, connection: Connection, target: AuditLog) -> None:
    previous = connection.execute(
        AuditSeal.__table__.select()
        .with_only_columns(AuditSeal.record_hash)
        .order_by(AuditSeal.id.desc())
        .limit(1)
    ).scalar_one_or_none() or GENESIS_HASH
    record_hash = hashlib.sha256(_audit_payload(target, previous)).hexdigest()
    connection.execute(
        AuditSeal.__table__.insert().values(
            audit_log_id=target.id,
            previous_hash=previous,
            record_hash=record_hash,
            created_at=datetime.now(timezone.utc),
        )
    )


@event.listens_for(AuditLog, "before_update")
@event.listens_for(AuditLog, "before_delete")
@event.listens_for(AuditSeal, "before_update")
@event.listens_for(AuditSeal, "before_delete")
def block_audit_mutation(_mapper, _connection, _target) -> None:
    raise RuntimeError("AuditLog and AuditSeal records are immutable append-only ledgers and cannot be updated or deleted.")


def verify_audit_chain(db: Session) -> dict:
    rows = (
        db.query(AuditLog, AuditSeal)
        .outerjoin(AuditSeal, AuditSeal.audit_log_id == AuditLog.id)
        .order_by(AuditLog.id.asc())
        .all()
    )
    previous = GENESIS_HASH
    for log, seal in rows:
        if seal is None:
            return {
                "valid": False,
                "status": "TAMPER_DETECTED",
                "checked": 0,
                "broken_audit_log_id": log.id,
                "reason": "missing cryptographic seal"
            }
        expected = hashlib.sha256(_audit_payload(log, previous)).hexdigest()
        if seal.previous_hash != previous or seal.record_hash != expected:
            return {
                "valid": False,
                "status": "TAMPER_DETECTED",
                "checked": 0,
                "broken_audit_log_id": log.id,
                "reason": "hash mismatch (payload or chain altered)"
            }
        previous = seal.record_hash
    return {
        "valid": True,
        "status": "VERIFIED_TAMPER_EVIDENT",
        "checked": len(rows),
        "head_hash": previous,
        "integrity_level": "Cryptographically Tamper-Evident SHA-256"
    }


def backfill_audit_seals() -> None:
    """Seal legacy audit rows created before hash chaining was introduced."""
    db = SessionLocal()
    try:
        previous = db.query(AuditSeal.record_hash).order_by(AuditSeal.id.desc()).limit(1).scalar() or GENESIS_HASH
        sealed_ids = db.query(AuditSeal.audit_log_id)
        rows = db.query(AuditLog).filter(~AuditLog.id.in_(sealed_ids)).order_by(AuditLog.id.asc()).all()
        for log in rows:
            record_hash = hashlib.sha256(_audit_payload(log, previous)).hexdigest()
            db.add(AuditSeal(
                audit_log_id=log.id,
                previous_hash=previous,
                record_hash=record_hash,
            ))
            previous = record_hash
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to backfill legacy audit seals")
    finally:
        db.close()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))[:36]
        started = time.perf_counter()
        response = None
        error = None
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error = exc
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            status_code = response.status_code if response is not None else 500
            db = SessionLocal()
            try:
                db.add(ApiPerformanceMetric(
                    request_id=request_id,
                    method=request.method[:10],
                    path=request.url.path[:160],
                    status_code=status_code,
                    duration_ms=duration_ms,
                ))
                if error is not None:
                    db.add(SystemError(
                        request_id=request_id,
                        method=request.method[:10],
                        path=request.url.path[:160],
                        error_type=type(error).__name__[:120],
                        message=str(error)[:2000],
                    ))
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to persist request telemetry")
            finally:
                db.close()
            if response is not None:
                response.headers["X-Request-ID"] = request_id
                response.headers["Server-Timing"] = f"app;dur={duration_ms:.3f}"


def performance_summary(db: Session, hours: int = 24) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = db.query(ApiPerformanceMetric).filter(ApiPerformanceMetric.created_at >= since).all()
    durations: list[float] = sorted(float(row.duration_ms) for row in rows)

    def percentile(percent: float) -> float:
        if not durations:
            return 0.0
        index = min(len(durations) - 1, max(0, int((len(durations) - 1) * percent)))
        return round(durations[index], 3)

    failures = sum(1 for row in rows if row.status_code >= 500)
    classifications: list[float] = [float(row.duration_ms) for row in rows if row.path in {"/api/classify", "/api/classify/batch"}]
    total_dur = sum(durations)
    total_class = sum(classifications)
    return {
        "window_hours": hours,
        "requests": len(rows),
        "server_errors": failures,
        "error_rate_percent": round((failures / len(rows) * 100), 3) if rows else 0.0,
        "latency_ms": {
            "average": round(total_dur / len(durations), 3) if durations else 0.0,
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        },
        "classification": {
            "requests": len(classifications),
            "average_ms": round(total_class / len(classifications), 3) if classifications else 0.0,
            "within_2_seconds_percent": round(sum(x <= 2000.0 for x in classifications) / len(classifications) * 100, 3) if classifications else 0.0,
        },
        "recorded_errors": db.query(func.count(SystemError.id)).filter(SystemError.created_at >= since).scalar() or 0,
    }
