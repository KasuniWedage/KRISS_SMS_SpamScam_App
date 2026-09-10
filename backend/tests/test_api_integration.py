"""End-to-End API Integration Test Suite for KRISS SMS Shield.

Validates complete user flows across classification, batch processing,
user feedback, reporting, settings updates, and admin metrics.
"""
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, SMSMessage, ClassificationResult, Report, Feedback
from app.auth import create_session_token, hash_password


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture(scope="module")
def regular_user():
    db = SessionLocal()
    user = db.query(User).filter(User.username == "test_integ_user").first()
    if not user:
        user = User(
            name="Integration Tester",
            username="test_integ_user",
            email="integ_tester@kriss.lk",
            password_hash=hash_password("Pass1234!"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_session_token(db, user)
    db.close()
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_classify_and_history_integration(client, regular_user):
    headers = regular_user["headers"]
    
    # 1. Classify an SMS
    payload = {
        "message": "Urgent: Your Commercial Bank account is locked. Verify at http://combank-update.xyz",
        "sender_no": "0771234567"
    }
    resp = client.post("/api/classify", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "sms_id" in data
    assert data["label"] in ["Spam", "Scam", "Legitimate"]
    sms_id = data["sms_id"]

    # 2. Verify it appears in user history
    hist_resp = client.get("/api/history?limit=10", headers=headers)
    assert hist_resp.status_code == 200
    history_items = hist_resp.json()
    assert any(item["sms_id"] == sms_id for item in history_items)

    # 3. Report the SMS
    report_resp = client.post("/api/reports", json={"sms_id": sms_id, "reason": "Phishing bank scam link"}, headers=headers)
    assert report_resp.status_code == 201

    # 4. Submit user feedback
    feedback_resp = client.post("/api/feedback", json={"sms_id": sms_id, "feedback_text": "Accurately flagged", "expected_label": "Scam"}, headers=headers)
    assert feedback_resp.status_code == 201


def test_batch_classification_integration(client, regular_user):
    headers = regular_user["headers"]
    payload = {
        "messages": [
            {"message": "Hello brother, are you free this evening?", "sender_no": "0711111111"},
            {"message": "Congratulations! You won Rs 1,000,000 lottery cash prize!", "sender_no": "0722222222"},
            {"message": "Dear customer, your OTP is 998811 for login.", "sender_no": "0733333333"}
        ]
    }
    resp = client.post("/api/classify/batch", json=payload, headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 3
    assert results[0]["label"] == "Legitimate"
    assert results[1]["label"] in ["Spam", "Scam"]


def test_settings_update_integration(client, regular_user):
    headers = regular_user["headers"]
    
    # Update to Tamil
    patch_resp = client.patch("/api/settings", json={"language_preference": "Tamil", "notifications_enabled": True}, headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["language_preference"] == "Tamil"

    # Verify settings persistence
    get_resp = client.get("/api/settings", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["language_preference"] == "Tamil"


def test_admin_dataset_management_integration(client):
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(name="Admin", username="admin", email="admin@kriss.lk", password_hash=hash_password("AdminPass123!"), role="admin")
        db.add(admin); db.commit(); db.refresh(admin)
    token = create_session_token(db, admin)
    db.close()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch samples
    resp = client.get("/api/admin/dataset/samples?status=all&language=all", headers=headers)
    assert resp.status_code == 200
    samples = resp.json()
    assert isinstance(samples, list)

    if samples:
        s_id = samples[0]["id"]
        # 2. Review sample (Approve)
        r_resp = client.patch(f"/api/admin/dataset/samples/{s_id}", json={"status": "approved", "review_note": "Verified genuine sample"}, headers=headers)
        assert r_resp.status_code == 200
        assert r_resp.json()["status"] == "approved"

    # 3. Export CSV
    csv_resp = client.get("/api/admin/dataset/export-csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]

    # 4. Create dataset version
    v_resp = client.post("/api/admin/dataset/versions", json={"version_tag": f"v1_test_{int(time.time())}"}, headers=headers)
    assert v_resp.status_code == 201
    assert "version_tag" in v_resp.json()

    # 5. List versions
    list_v = client.get("/api/admin/dataset/versions", headers=headers)
    assert list_v.status_code == 200
    assert len(list_v.json()) > 0
