import sqlite3
from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import RESET_TOKEN_MAX_ATTEMPTS, _reset_token_hash, verify_reset_token
from app.database import Base
from app.models import PasswordResetToken, User
from scripts.database_backup import create_backup
from scripts.verify_backup import verify


def test_wrong_reset_codes_invalidate_latest_token():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(name="Test User", username="test_user", email="test@example.com", password_hash="unused")
    db.add(user)
    db.flush()
    token = PasswordResetToken(user_id=user.id, token_hash=_reset_token_hash("123456"), expires_at=datetime.utcnow() + timedelta(minutes=10))
    db.add(token)
    db.commit()
    for _ in range(RESET_TOKEN_MAX_ATTEMPTS):
        assert verify_reset_token(db, "999999", cast(int, user.id)) is None
    db.refresh(token)
    assert token.used is True
    assert token.attempts == RESET_TOKEN_MAX_ATTEMPTS
    db.close()


def test_sqlite_backup_has_checksum_and_integrity(tmp_path):
    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT INTO sample(value) VALUES ('ok')")
    backup = create_backup(f"sqlite:///{source}", tmp_path / "backups")
    result = verify(backup)
    assert result["valid"] is True
    assert result["tables"] >= 1
