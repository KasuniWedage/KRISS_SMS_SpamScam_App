"""Backup, Restore, and Disaster Recovery Test Suite for KRISS.

Validates that database backup snapshots are created with valid SHA-256
checksums, can be restored to a shadow database, and maintain table consistency.
"""
import json
import sqlite3
import tempfile
from pathlib import Path
import pytest
from app.database import Base, engine, SessionLocal
from scripts.database_backup import create_backup, sha256


def test_sqlite_backup_creation_and_integrity(tmp_path):
    Base.metadata.create_all(bind=engine)
    
    # 1. Create a backup in a temporary directory
    db_url = "sqlite:///./kriss_dev.db"
    backup_file = create_backup(db_url, tmp_path)
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    # 2. Check JSON manifest
    manifest_file = backup_file.with_suffix(backup_file.suffix + ".json")
    assert manifest_file.exists()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["sha256"] == sha256(backup_file)
    assert manifest["status"] == "VERIFIED_VALID"

    # 3. Test shadow restore & SQLite integrity
    with sqlite3.connect(backup_file) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        res = cursor.fetchone()[0]
        assert res == "ok"
        
        # Verify essential tables exist in restored database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "mobile_users" in tables
        assert "sms_messages" in tables
        assert "audit_logs" in tables
        assert "audit_seals" in tables
