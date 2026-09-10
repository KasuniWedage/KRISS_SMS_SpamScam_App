"""Cryptographically Tamper-Evident Audit Log Verification Tool for KRISS.

Validates the cryptographic SHA-256 hash chain of the AuditSeal records
associated with AuditLog entries. Detects any row modification, deletion,
or rogue insertion, and periodically exports head hash anchors to an external ledger.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app.models import AuditLog, AuditSeal, SystemError
from app.observability import GENESIS_HASH, _audit_payload


def verify_audit_integrity(export_anchor: bool = True) -> dict:
    db = SessionLocal()
    try:
        rows = (
            db.query(AuditLog, AuditSeal)
            .outerjoin(AuditSeal, AuditSeal.audit_log_id == AuditLog.id)
            .order_by(AuditLog.id.asc())
            .all()
        )
        previous = GENESIS_HASH
        for log, seal in rows:
            if seal is None:
                err_msg = f"Audit log ID={log.id} has missing cryptographic seal"
                _record_audit_failure(db, err_msg)
                return {
                    "valid": False,
                    "status": "TAMPER_DETECTED",
                    "reason": "missing cryptographic seal",
                    "broken_audit_log_id": log.id,
                    "checked": len(rows)
                }
            expected = hashlib.sha256(_audit_payload(log, previous)).hexdigest()
            if seal.previous_hash != previous:
                err_msg = f"Audit chain broken at ID={log.id}: previous_hash mismatch"
                _record_audit_failure(db, err_msg)
                return {
                    "valid": False,
                    "status": "TAMPER_DETECTED",
                    "reason": f"previous_hash mismatch (expected {previous[:16]}..., got {seal.previous_hash[:16]}...)",
                    "broken_audit_log_id": log.id,
                    "checked": len(rows)
                }
            if seal.record_hash != expected:
                err_msg = f"Audit log payload altered at ID={log.id}: record_hash mismatch"
                _record_audit_failure(db, err_msg)
                return {
                    "valid": False,
                    "status": "TAMPER_DETECTED",
                    "reason": "record_hash mismatch (audit log payload altered)",
                    "broken_audit_log_id": log.id,
                    "checked": len(rows)
                }
            previous = seal.record_hash

        result = {
            "valid": True,
            "status": "VERIFIED_TAMPER_EVIDENT",
            "checked": len(rows),
            "head_hash": previous,
            "integrity_level": "Cryptographically Tamper-Evident SHA-256",
            "verified_at": datetime.now(timezone.utc).isoformat()
        }

        # Export external anchor
        if export_anchor and previous != GENESIS_HASH:
            _export_external_anchor(previous, len(rows))

        return result
    finally:
        db.close()


def _record_audit_failure(db, reason: str):
    try:
        err = SystemError(
            method="AUDIT_VERIFY",
            path="/audit/integrity",
            error_type="SECURITY_TAMPER_DETECTED",
            message=reason
        )
        db.add(err)
        db.commit()
    except Exception:
        pass


def _export_external_anchor(head_hash: str, checked_count: int):
    anchors_dir = Path(__file__).resolve().parents[1] / "audit_anchors"
    anchors_dir.mkdir(parents=True, exist_ok=True)
    anchor_file = anchors_dir / "head_hashes.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "head_hash": head_hash,
        "sealed_records_count": checked_count,
        "verification_status": "VERIFIED_TAMPER_EVIDENT"
    }
    with anchor_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KRISS Cryptographically Tamper-Evident Audit Verifier")
    parser.add_argument("--no-anchor", action="store_true", help="Skip external anchor export")
    args = parser.parse_args()

    res = verify_audit_integrity(export_anchor=not args.no_anchor)
    print(json.dumps(res, indent=2))
    if not res["valid"]:
        sys.exit(1)
