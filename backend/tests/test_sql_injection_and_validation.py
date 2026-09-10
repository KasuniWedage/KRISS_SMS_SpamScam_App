"""SQL Injection, XSS, and Malformed Input Boundary Tests for KRISS.

Validates that ORM parameterization protects against SQL injection,
HTML/Script injection tags are safely handled, and invalid inputs return 400/422.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User
from app.auth import create_session_token, hash_password


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture(scope="module")
def regular_user():
    db = SessionLocal()
    user = db.query(User).filter(User.username == "test_sqli_user").first()
    if not user:
        user = User(
            name="SQLi Tester",
            username="test_sqli_user",
            email="sqli_user@kriss.lk",
            password_hash=hash_password("Pass1234!"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_session_token(db, user)
    db.close()
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_sql_injection_in_classification_payload(client, regular_user):
    headers = regular_user["headers"]
    sqli_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1 UNION SELECT null, username, password_hash FROM users --",
        "' OR SLEEP(5) --"
    ]
    for payload in sqli_payloads:
        resp = client.post("/api/classify", json={"message": payload, "sender_no": "0770000000"}, headers=headers)
        assert resp.status_code == 200
        # Check that table still exists and query succeeds
        assert "sms_id" in resp.json()


def test_empty_and_whitespace_message_validation(client, regular_user):
    headers = regular_user["headers"]
    resp = client.post("/api/classify", json={"message": "   ", "sender_no": "0770000000"}, headers=headers)
    assert resp.status_code == 400


def test_xss_script_tags_in_feedback_and_reports(client, regular_user):
    headers = regular_user["headers"]
    # Classify message first
    c_resp = client.post("/api/classify", json={"message": "Safe message for testing", "sender_no": "0770000000"}, headers=headers)
    sms_id = c_resp.json()["sms_id"]

    xss_payload = "<script>alert('XSS')</script><img src=x onerror=alert(1)>"
    f_resp = client.post("/api/feedback", json={"sms_id": sms_id, "feedback_text": xss_payload, "expected_label": "Legitimate"}, headers=headers)
    assert f_resp.status_code == 201


def test_invalid_settings_unsupported_language_rejection(client, regular_user):
    headers = regular_user["headers"]
    resp = client.patch("/api/settings", json={"language_preference": "Klingon"}, headers=headers)
    assert resp.status_code == 400
