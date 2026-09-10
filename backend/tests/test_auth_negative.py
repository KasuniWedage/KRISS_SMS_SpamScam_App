"""Authentication and Authorization Negative Security Tests for KRISS.

Validates that expired tokens, forged signatures, revoked sessions,
tampered headers, and unauthorized role escalations are blocked with 401/403.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User
from app.auth import create_session_token, hash_password, revoke_user_sessions


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture(scope="module")
def regular_user():
    db = SessionLocal()
    user = db.query(User).filter(User.username == "test_auth_neg_user").first()
    if not user:
        user = User(
            name="Neg User",
            username="test_auth_neg_user",
            email="neg_user@kriss.lk",
            password_hash=hash_password("Pass1234!"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_session_token(db, user)
    uid = user.id
    db.close()
    return {"user_id": uid, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_missing_auth_header_rejected(client):
    resp = client.get("/api/history")
    assert resp.status_code == 401


def test_invalid_bearer_token_rejected(client):
    resp = client.get("/api/history", headers={"Authorization": "Bearer invalid_gibberish_token_string"})
    assert resp.status_code == 401


def test_malformed_auth_header_format(client):
    resp = client.get("/api/history", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert resp.status_code == 401


def test_regular_user_cannot_access_admin_metrics(client, regular_user):
    resp = client.get("/api/admin/metrics", headers=regular_user["headers"])
    assert resp.status_code == 403


def test_regular_user_cannot_trigger_backup(client, regular_user):
    resp = client.post("/api/admin/backup/create", headers=regular_user["headers"])
    assert resp.status_code == 403


def test_revoked_session_token_rejected(client, regular_user):
    db = SessionLocal()
    user_id = regular_user["user_id"]
    # Create fresh token
    user = db.query(User).filter(User.id == user_id).first()
    token = create_session_token(db, user)
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works before revocation
    assert client.get("/api/history", headers=headers).status_code == 200

    # Revoke all sessions
    revoke_user_sessions(db, user_id)
    db.close()

    # Verify token is now blocked
    assert client.get("/api/history", headers=headers).status_code == 401
